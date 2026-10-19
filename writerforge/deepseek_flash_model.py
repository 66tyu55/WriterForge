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
ROLES = frozenset(("genre_classification", "first_read", "craft_analysis"))
MAX_INPUT_BYTES = 16 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
MAX_COMPLETION_TOKENS_PER_CALL = 1500
DEFAULT_COMPLETION_TOKENS = 650
MAX_TIMEOUT_SECONDS = 120
DEFAULT_TIMEOUT_SECONDS = 75
# Default one preflight plus one first-read, two analysis calls per opt-in run.
MAX_CALLS = 4
MAX_RESERVED_OUTPUT_TOKENS = 4800


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
    max_reserved_output_tokens: int = MAX_RESERVED_OUTPUT_TOKENS
    calls_reserved: int = 0
    tokens_reserved: int = 0
    prompt_tokens_reported: int = 0
    completion_tokens_reported: int = 0
    calls_by_role: dict[str, int] = field(default_factory=dict)

    def reserve(self, role: str, requested: int, payload_bytes: int) -> None:
        require(
            role in ROLES and
            type(requested) is int and 50 <= requested <= MAX_COMPLETION_TOKENS_PER_CALL and
            type(payload_bytes) is int and 0 < payload_bytes <= MAX_INPUT_BYTES and
            1 <= self.max_calls <= 4 and
            50 <= self.max_reserved_output_tokens <= MAX_RESERVED_OUTPUT_TOKENS and
            self.calls_reserved < self.max_calls and
            self.tokens_reserved + requested <= self.max_reserved_output_tokens,
            "WF_FLASH_CALL_OR_TOKEN_BUDGET_EXCEEDED",
        )
        # Reserve before network: even timeouts may have incurred a bill.
        self.calls_reserved += 1
        self.tokens_reserved += requested
        self.calls_by_role[role] = self.calls_by_role.get(role, 0) + 1

    def add_usage(self, usage: dict) -> None:
        if not isinstance(usage, dict):
            return
        prompt = usage.get("prompt_tokens")
        answer = usage.get("completion_tokens")
        if type(prompt) is int and prompt >= 0:
            self.prompt_tokens_reported += prompt
        if type(answer) is int and answer >= 0:
            self.completion_tokens_reported += answer

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
        self._transport = transport or self._real_transport

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
        require(
            isinstance(system, str) and 10 <= len(system) <= 8000 and
            isinstance(user, str) and 1 <= len(user) <= 12000 and
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
            result = json.loads(content)
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
