"""Dedicated authenticated InkStone/Discovery text-model adapter for V28.

Uses ONLY GitHub Actions secret DISCOVERY__API__KEY (mapped into process env).
One fixed HTTPS host; no API key exposure; no model-call retries by default.
Source text remains private to this single opt-in V28 training process and
the explicitly chosen Discovery provider. The provider is third-party.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
import json
import re
import ssl

from .reverse_real_training import _safe_json, RealTrainingError

ENDPOINT = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODELS = {
    "deepseek-v4-pro-0813", "deepseek-v4-flash-0731",
    "glm-5.3", "kimi-k2.6", "intern-s2", "minimax-m3",
}
ROLE_MODELS = {
    "planner": "glm-5.3",
    "writer": "kimi-k2.6",
    "critic": "deepseek-v4-pro-0813",
}
MAX_PROMPT_BYTES = 25000
MAX_OUTPUT_BYTES = 80000
MAX_CALLS = 5
MAX_REQUESTED_OUTPUT_TOKENS = 4000

class DiscoveryError(RealTrainingError):
    pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryError("REDIRECT_REJECTED")

@dataclass
class DiscoveryCallBudget:
    max_calls: int = MAX_CALLS
    calls: int = 0
    max_reserved_output_tokens: int = 16000
    reserved_output_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    def reserve(self, request_bytes: int, requested: int) -> None:
        if not (1 <= self.max_calls <= 6 and
                0 <= self.calls < self.max_calls and
                50 <= requested <= MAX_REQUESTED_OUTPUT_TOKENS and
                request_bytes <= MAX_PROMPT_BYTES and
                self.reserved_output_tokens + requested <= self.max_reserved_output_tokens):
            raise DiscoveryError("MODEL_CALL_OR_TOKEN_BUDGET_EXHAUSTED")
        self.calls += 1
        self.reserved_output_tokens += requested

class DiscoveryModel:
    provider = "discovery"

    def __init__(self, *, name: str, role: str, api_key: str,
                 budget: DiscoveryCallBudget, transport=None):
        if role not in ROLE_MODELS or name not in MODELS:
            raise DiscoveryError("UNSUPPORTED_DISCOVERY_ROLE_OR_MODEL")
        if not isinstance(api_key,str) or not api_key or len(api_key)>512:
            raise DiscoveryError("DISCOVERY_API_KEY_UNAVAILABLE")
        self.name=name
        self.role=role
        self.budget=budget
        self._key=api_key
        self.transport=transport or self._request

    @staticmethod
    def _request(request: Request) -> bytes:
        opener=build_opener(_NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(request,timeout=150) as response:
                raw=response.read(MAX_OUTPUT_BYTES + 1)
        except HTTPError as exc:
            # HTTP body may repeat prompt or key. Only status number survives.
            raise DiscoveryError("DISCOVERY_HTTP_"+str(exc.code)) from None
        except (TimeoutError,URLError,OSError):
            raise DiscoveryError("DISCOVERY_NETWORK_FAILED") from None
        if len(raw)>MAX_OUTPUT_BYTES:
            raise DiscoveryError("DISCOVERY_RESPONSE_OVERSIZE")
        return raw

    def ask(self, system: str, user: str, *, num_predict: int = 1800) -> dict:
        if not isinstance(system,str) or not isinstance(user,str):
            raise DiscoveryError("INVALID_MODEL_PROMPT")
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}]
        body=json.dumps({"model":self.name,"messages":messages,
                         "stream":False,"max_tokens":num_predict,
                         "temperature":1 if self.name=="kimi-k2.6" else 0.4},
                        ensure_ascii=False,separators=(",",":")).encode("utf-8")
        self.budget.reserve(len(body),num_predict)
        req=Request(ENDPOINT,data=body,method="POST",headers={
            "Authorization":"Bearer "+self._key,
            "Content-Type":"application/json",
            "Accept":"application/json",
        })
        raw=self.transport(req)
        if not isinstance(raw,bytes) or len(raw)>MAX_OUTPUT_BYTES:
            raise DiscoveryError("DISCOVERY_RESPONSE_OVERSIZE")
        try:
            result=json.loads(raw)
            usage=result.get("usage") or {}
            if isinstance(usage,dict):
                n=usage.get("prompt_tokens")
                m=usage.get("completion_tokens")
                if type(n) is int and n>=0:self.budget.total_prompt_tokens+=n
                if type(m) is int and m>=0:self.budget.total_completion_tokens+=m
            choice=result["choices"][0]
            message=choice["message"]
            content=message.get("content")
            if not isinstance(content,str) or not content.strip():
                raise DiscoveryError("DISCOVERY_EMPTY_VISIBLE_TEXT")
            return _safe_json(content)
        except DiscoveryError:
            raise
        except (IndexError,KeyError,TypeError,ValueError,RealTrainingError):
            raise DiscoveryError("DISCOVERY_MODEL_JSON_CONTRACT_FAILED") from None
