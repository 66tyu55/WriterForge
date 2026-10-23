"""WriterForge-owned DeepSeek Flash literary LEARN model adapter (V74).

Provider: DeepSeek official OpenAI-compatible Chat Completions endpoint.
Model: deepseek-flash (not the retired deepseek-v4-flash identifier).

This adapter is only a bounded WF tool for genre/classification, first-read,
and literary analysis; it is NOT a new WriterForge host, grade/promoter, or
replacement for the LEARN-first / immutable-R2 first-read journal.

No OpenRouter/Discovery fallback. No raw texts or key values are logged.
No automated retries: a timed-out request can already have been charged.
All model input is explicitly sent to DeepSeek, a third-party provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.request import (
    Request, build_opener, HTTPSHandler, HTTPRedirectHandler,
)
import json
import os
import ssl

MODEL = "deepseek-flash"
PROVIDER = "deepseek"
API_URL = "https://api.deepseek.com/chat/completions"
TOKEN_ENV = "DEEPSEEK_API_KEY"
ROLES = frozenset(("genre_classification", "first_read", "craft_analysis", "self_scene_writing"))
MAX_INPUT_BYTES = 512 * 1024
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
MAX_COMPLETION_TOKENS_PER_CALL = 150000
DEFAULT_COMPLETION_TOKENS = 650
MAX_TIMEOUT_SECONDS = 120
DEFAULT_TIMEOUT_SECONDS = 75
# Default one preflight plus one first-read, two analysis calls per opt-in run.
MAX_CALLS = 192
MAX_RESERVED_OUTPUT_TOKENS = 150000
LEGACY_DEFAULT_RESERVED_OUTPUT_TOKENS = 4800


class DeepSeekFlashError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise DeepSeekFlashError(code)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Never forward the private bearer or original source to another host.
        raise DeepSeekFlashError("WF_FLASH_REDIRECT_REFUSED")


@dataclass
class FlashBudget:
    max_calls: int = MAX_CALLS
    max_reserved_output_tokens: int = LEGACY_DEFAULT_RESERVED_OUTPUT_TOKENS
    calls_reserved: int = 0
    tokens_reserved: int = 0
    prompt_tokens_reported: int = 0
    completion_tokens_reported: int = 0
    calls_by_role: dict[str, int] = field(default_factory=dict)
    # None leaves old tiny-call tests unchanged. 150000 enables a new WF
    # full-chapter batch across multiple requests, NOT one giant answer.
    max_total_tokens: int | None = None
    conservative_tokens_committed: int = 0
    last_request_reserved: int = 0
    calls_with_provider_usage: int = 0
    calls_with_uncertain_usage: int = 0

    def reserve(self, role: str, requested: int, payload_bytes: int) -> None:
        require(
            role in ROLES and
            type(requested) is int and
            50 <= requested <= MAX_COMPLETION_TOKENS_PER_CALL and
            type(payload_bytes) is int and 0 < payload_bytes <= MAX_INPUT_BYTES and
            1 <= self.max_calls <= MAX_CALLS and
            50 <= self.max_reserved_output_tokens <= MAX_RESERVED_OUTPUT_TOKENS and
            self.calls_reserved < self.max_calls and
            self.tokens_reserved + requested <= self.max_reserved_output_tokens,
            "WF_FLASH_CALL_OR_TOKEN_BUDGET_EXCEEDED",
        )
        if self.max_total_tokens is not None:
            require(type(self.max_total_tokens) is int and
                    self.max_total_tokens == 150000,
                    "WF_FLASH_TOTAL_BUDGET_CONFIGURATION_INVALID")
            # Conservative upper estimate: input UTF8 bytes (tokenization
            # cannot spend more ordinary text tokens than its byte stream)
            # plus message/role overhead and reserved maximum output.
            # Failed/timeout requests retain full reserve (may bill).
            estimated=payload_bytes + 1024 + requested
            require(
                self.conservative_tokens_committed + estimated <=
                self.max_total_tokens,
                "WF_FLASH_TOTAL_150K_TOKEN_CAP_REACHED",
            )
            self.conservative_tokens_committed += estimated
            self.last_request_reserved = estimated
            self.calls_with_uncertain_usage += 1
        # Reserve BEFORE network, including transport timeouts.
        self.calls_reserved += 1
        self.tokens_reserved += requested
        self.calls_by_role[role] = self.calls_by_role.get(role, 0) + 1

    def add_usage(self, usage: dict) -> None:
        if not isinstance(usage, dict):
            return
        prompt = usage.get("prompt_tokens")
        answer = usage.get("completion_tokens")
        good=(type(prompt) is int and prompt >= 0 and
              type(answer) is int and answer >= 0)
        if type(prompt) is int and prompt >= 0:
            self.prompt_tokens_reported += prompt
        if type(answer) is int and answer >= 0:
            self.completion_tokens_reported += answer
        if self.max_total_tokens is not None and good:
            # Replace conservative held tokens with supplier's actual usage.
            # If provider reports unexpectedly > reserved, fail future calls.
            self.conservative_tokens_committed += (
                prompt + answer - self.last_request_reserved)
            self.last_request_reserved=0
            self.calls_with_provider_usage += 1
            self.calls_with_uncertain_usage -= 1

    def public_receipt(self) -> dict:
        return {
            "provider": PROVIDER,
            "model": MODEL,
            "calls_reserved": self.calls_reserved,
            "requested_output_tokens": self.tokens_reserved,
            "prompt_tokens_reported": self.prompt_tokens_reported,
            "completion_tokens_reported": self.completion_tokens_reported,
            "calls_by_role": dict(self.calls_by_role),
            "model_decisions_not_verified_literary_truth": True,
            "max_total_training_tokens": self.max_total_tokens,
            "tokens_committed_or_held": self.conservative_tokens_committed,
            "calls_with_provider_usage": self.calls_with_provider_usage,
            "calls_with_uncertain_usage": self.calls_with_uncertain_usage,
        }


class DeepSeekFlashModel:
    """JSON-only role client. Returns validated object, never answers for WF."""

    name = MODEL
    provider = PROVIDER

    def __init__(
        self, *,
        api_key: str | None = None,
        budget: FlashBudget | None = None,
        transport=None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        on_response_wire=None,
    ):
        key = api_key if api_key is not None else os.environ.get(TOKEN_ENV)
        require(
            isinstance(key, str) and 16 <= len(key) <= 1024 and
            "\r" not in key and "\n" not in key,
            "WF_FLASH_API_KEY_NOT_CONFIGURED",
        )
        require(
            type(timeout_seconds) is int and 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS,
            "WF_FLASH_TIMEOUT_INVALID",
        )
        self._api_key = key
        self.budget = budget if budget is not None else FlashBudget()
        self.timeout_seconds = timeout_seconds
        # Optional per-request *private* immutable evidence callback.
        # It observes the bytes directly from the provider BEFORE JSON
        # parsing so a schema/truncation error does not erase the paid reply.
        # The caller is responsible for an R2 CAS sink and zero public text.
        require(on_response_wire is None or callable(on_response_wire),
                "WF_FLASH_WIRE_SINK_NOT_CALLABLE")
        self._transport = transport or self._real_transport
        self._on_response_wire = on_response_wire
        # Last call only; never put original provider prose in this receipt.
        self.last_response_format_recovery = None

    def _real_transport(self, request: Request) -> bytes:
        opener = build_opener(
            _NoRedirect(), HTTPSHandler(context=ssl.create_default_context())
        )
        try:
            with opener.open(request, timeout=self.timeout_seconds) as response:
                require(response.status == 200, "WF_FLASH_HTTP_UNEXPECTED_STATUS")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            # An error body may echo private source and is never read/logged.
            code = error.code if 100 <= error.code <= 599 else 0
            raise DeepSeekFlashError(f"WF_FLASH_HTTP_{code}") from None
        except (URLError, OSError, TimeoutError):
            raise DeepSeekFlashError("WF_FLASH_NETWORK_OR_TIMEOUT") from None
        require(
            isinstance(raw, bytes) and len(raw) <= MAX_RESPONSE_BYTES,
            "WF_FLASH_RESPONSE_TOO_LARGE",
        )
        return raw

    def ask_json(
        self,
        *,
        role: str,
        system: str,
        user: str,
        max_tokens: int = DEFAULT_COMPLETION_TOKENS,
    ) -> dict:
        """One actual request. WF performs all literary decisions downstream.

        The prompts, not this transport wrapper, must enforce reading only
        currently unlocked content and an explicitly specified JSON schema.
        """
        require(role in ROLES, "WF_FLASH_ROLE_UNSUPPORTED")
        self.last_response_format_recovery = None
        require(
            isinstance(system, str) and 10 <= len(system) <= 32000 and
            isinstance(user, str) and 1 <= len(user) <= 180000 and
            ("JSON" in system or "json" in system),
            "WF_FLASH_JSON_PROMPT_INVALID",
        )
        message = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system + "\n只输出严格有效的 JSON 对象，不输出 Markdown、代码围栏或解释。",
                },
                {"role": "user", "content": user},
            ],
            "stream": False,
            "max_tokens": max_tokens,
            # DeepSeek Flash defaults to thinking enabled. Structured
            # first-read records use non-thinking JSON for strict bounds.
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
        }
        raw_request = json.dumps(
            message, ensure_ascii=False, separators=(",",":")
        ).encode("utf-8")
        self.budget.reserve(role, max_tokens, len(raw_request))
        request = Request(
            API_URL,
            data=raw_request,
            method="POST",
            headers={
                "Authorization": "Bearer " + self._api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "WriterForge-WF-LEARN-DeepSeekFlash/1.0",
            },
        )
        # Never retry on an uncertain transport response or truncated JSON.
        response = self._transport(request)
        require(
            isinstance(response, bytes) and 0 < len(response) <= MAX_RESPONSE_BYTES,
            "WF_FLASH_RESPONSE_TOO_LARGE_OR_EMPTY",
        )
        if self._on_response_wire is not None:
            # Never swallow an evidence persistence error and never retry
            # a possibly billed response; fail closed before interpreting.
            self._on_response_wire(response)
        try:
            data = json.loads(response.decode("utf-8"))
            require(isinstance(data, dict), "WF_FLASH_WIRE_JSON_NOT_OBJECT")
            choices = data["choices"]
            require(isinstance(choices,list) and len(choices) == 1,
                    "WF_FLASH_CHOICES_INVALID")
            choice = choices[0]
            reason = choice.get("finish_reason")
            if reason == "length":
                raise DeepSeekFlashError("WF_FLASH_OUTPUT_TRUNCATED")
            require(reason == "stop", "WF_FLASH_FINISH_REASON_UNSAFE")
            content = choice["message"]["content"]
            require(isinstance(content, str) and 1 <= len(content) <= MAX_RESPONSE_BYTES,
                    "WF_FLASH_EMPTY_OR_OVERSIZED_CONTENT")
            try:
                result = json.loads(content)
            except json.JSONDecodeError as error:
                # Observed DeepSeek Flash literary PROSE_1 wires ended in
                # a fully valid JSON object followed by the exact 2-char
                # provider/model tail '"}'.  Never guess a missing bracket,
                # repair manuscript characters, or accept arbitrary suffix.
                if (role != "self_scene_writing" or
                    error.msg != "Extra data"):
                    raise
                def unique_pairs(items):
                    out = {}
                    for key,value in items:
                        if key in out:
                            raise ValueError("WF_FLASH_DUPLICATE_RECOVERY_FIELD")
                        out[key] = value
                    return out
                candidate,end = json.JSONDecoder(
                    object_pairs_hook=unique_pairs).raw_decode(content)
                if (content[end:] != '"}' or
                    type(candidate) is not dict or
                    set(candidate) != {"prose","trace"} or
                    type(candidate["prose"]) is not str or
                    type(candidate["trace"]) is not dict):
                    raise
                result = candidate
                self.last_response_format_recovery = {
                    "format":"wf.flash.exact-extra-tail-recovery.v1",
                    "original_content_sha256":sha256(
                        content.encode("utf8")).hexdigest(),
                    "decoded_object_sha256":sha256(
                        content[:end].encode("utf8")).hexdigest(),
                    "extra_suffix_codepoints":2,
                    "recovered_only_complete_existing_json_object":True,
                    "original_prose_unchanged":True,
                    "trace_still_requires_wf_source_validation":True,
                    "no_provider_retry":True,
                }
            require(isinstance(result,dict) and len(result) <= 32,
                    "WF_FLASH_RESULT_NOT_BOUNDED_JSON_OBJECT")
            self.budget.add_usage(data.get("usage",{}))
            # Only the model output object returned to WF, never to public log.
            return result
        except DeepSeekFlashError:
            raise
        except (KeyError,TypeError,ValueError,UnicodeError,IndexError):
            raise DeepSeekFlashError("WF_FLASH_INVALID_JSON_RESPONSE") from None

    def call_for_scene(self, *, role: str, system: str, max_tokens: int = 900):
        """Bridge for SceneLiteraryStudy(model_call(prompt)->JSON text).

        Only usable after its own R2 journal is ready; the caller must lock
        PASS A remotely before permitting a fresh PASS B model invocation.
        """
        require(role in ROLES,"WF_FLASH_ROLE_UNSUPPORTED")
        # No immutable R2 WF LEARN first-read ledger exists in V73/V74.
        # Do not allow this convenience bridge to launch an analyst after
        # locally saving a mutable first-read result.
        require(role=="first_read",
                "WF_FLASH_SECOND_PASS_REQUIRES_R2_LEARN_JOURNAL")
        def wf_call(prompt: str) -> str:
            record = self.ask_json(
                role=role,system=system,user=prompt,max_tokens=max_tokens
            )
            return json.dumps(record,ensure_ascii=False,separators=(",",":"))
        return wf_call


def learner_provider_status(environ=None) -> dict:
    env = environ if environ is not None else os.environ
    present = bool(env.get(TOKEN_ENV))
    return {
        "WF_LEARN_PROVIDER": PROVIDER,
        "WF_LEARN_MODEL": MODEL,
        "base_url": "https://api.deepseek.com",
        "key_variable_name": TOKEN_ENV,
        "key_present": present,
        "discovery_api_used_for_wf_learn": False,
        "auto_paid_training_enabled": False,
        "originals_transmitted_to_model_in_status_check": False,
    }
