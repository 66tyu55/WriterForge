"""V28 opt-in cloud LLM adapter for protected, reproducible literary trials.

Only fixed official HTTPS endpoints. No arbitrary URLs, no key in logs or
receipts. Bounded requests, responses and calls. Never self-judge 90% mastery.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from urllib.error import HTTPError, URLError
import json
import os
import re
import ssl

from .reverse_real_training import _safe_json, ModelUnavailable, RealTrainingError

PROVIDER_ENDPOINTS = {
    "moonshot": "https://api.moonshot.cn/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
}
ROLES = ("planner", "writer", "critic")
MODEL_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9:._/-]{1,110}\Z")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelUnavailable("cloud provider redirected; rejected")


@dataclass
class CloudCallBudget:
    """Shared, in-process budget for one explicit trial, not recurring billing.

    Token prices are caller-provided caps in USD / 1M. Worst-case requested
    completion tokens are reserved before each call. Unknown prices fail closed.
    """
    max_calls: int = 10
    max_usd: float = 1.0
    calls: int = 0
    reserved_usd: float = 0.0
    observed_input_tokens: int = 0
    observed_output_tokens: int = 0

    def __post_init__(self):
        if not 1 <= self.max_calls <= 16 or not 0 < self.max_usd <= 20:
            raise ModelUnavailable("cloud budget cap is invalid")

    def reserve(self, *, prompt_bytes: int, max_tokens: int,
                price_in: float, price_out: float) -> None:
        if (not 0 < price_in <= 100 or not 0 < price_out <= 100
                or not 50 <= max_tokens <= 4000 or prompt_bytes > 26000):
            raise ModelUnavailable("cloud pricing, prompt or token cap invalid")
        if self.calls >= self.max_calls:
            raise ModelUnavailable("cloud trial call budget exhausted")
        # Conservative assumption: up to 1 input token per UTF-8 byte.
        maximum = (prompt_bytes * price_in + max_tokens * price_out) / 1_000_000
        if self.reserved_usd + maximum > self.max_usd:
            raise ModelUnavailable("cloud trial USD safety limit exceeded")
        self.calls += 1
        self.reserved_usd += maximum


class CloudModel:
    def __init__(self, *, role: str, provider: str, name: str,
                 key: str, budget: CloudCallBudget,
                 input_usd_per_m: float, output_usd_per_m: float,
                 transport=None):
        if role not in ROLES or provider not in PROVIDER_ENDPOINTS:
            raise ModelUnavailable("unsupported model role or provider")
        if not isinstance(name, str) or not MODEL_ID.fullmatch(name):
            raise ModelUnavailable("invalid explicit model identity")
        if not isinstance(key, str) or not 6 <= len(key) <= 500 or any(c.isspace() for c in key):
            raise ModelUnavailable("cloud API credential missing or invalid")
        self.role, self.provider, self.name, self.key = role, provider, name, key
        self.budget = budget
        self.input_usd_per_m = input_usd_per_m
        self.output_usd_per_m = output_usd_per_m
        self.transport = transport if transport is not None else self._transport

    @staticmethod
    def _transport(request: Request, max_bytes: int) -> bytes:
        opener = build_opener(_NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(request, timeout=120) as response:
                data = response.read(max_bytes + 1)
        except HTTPError as exc:
            # Intentionally do not log server error bodies (may echo prompt/key).
            raise ModelUnavailable("cloud request failed HTTP status "+str(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            raise ModelUnavailable("cloud provider unavailable") from None
        if len(data) > max_bytes:
            raise ModelUnavailable("cloud response byte cap exceeded")
        return data

    def ask(self, system: str, user: str, *, num_predict: int = 1800) -> dict:
        if (not isinstance(system, str) or not isinstance(user, str)
            or len(system)+len(user) > 13000 or num_predict > 4000
            or num_predict < 50):
            raise ModelUnavailable("cloud request exceeds bounded context")
        url = PROVIDER_ENDPOINTS[self.provider]
        body = {
            "model": self.name,
            "messages": [{"role":"system","content":system},
                         {"role":"user","content":user}],
            "max_tokens":num_predict,
            "temperature":0.35,
            "response_format":{"type":"json_object"},
            "stream":False,
        }
        packed = json.dumps(body, ensure_ascii=False, separators=(",",":")).encode("utf-8")
        self.budget.reserve(
            prompt_bytes=len(packed),max_tokens=num_predict,
            price_in=self.input_usd_per_m,price_out=self.output_usd_per_m)
        request=Request(url, data=packed, method="POST",headers={
            "Authorization":"Bearer "+self.key,
            "Content-Type":"application/json",
            "Accept":"application/json",
        })
        raw=self.transport(request, 64_000)
        if not isinstance(raw, bytes) or len(raw)>64_000:
            raise ModelUnavailable("cloud transport returned unbounded data")
        try:
            payload=json.loads(raw)
            if not isinstance(payload,dict):
                raise ValueError("response object expected")
            choices=payload["choices"]
            content=choices[0]["message"]["content"]
            if not isinstance(content,str):
                raise ValueError("text JSON content missing")
            usage=payload.get("usage") or {}
            if isinstance(usage,dict):
                for key,attr in (("prompt_tokens","observed_input_tokens"),
                                 ("completion_tokens","observed_output_tokens")):
                    n=usage.get(key)
                    if type(n) is int and 0<=n<=1_000_000:
                        setattr(self.budget,attr,getattr(self.budget,attr)+n)
            return _safe_json(content)
        except (TypeError,KeyError,IndexError,ValueError,RealTrainingError):
            raise ModelUnavailable("cloud response JSON/schema invalid") from None


def configured_cloud_roles(*, environ=None, transport=None):
    """Fail closed; never auto-fallback to 3B/4B local models.

    Each role requires explicit provider, model, credential and declared rate.
    Separate writer and critic MODEL IDs required even on same provider.
    """
    env = os.environ if environ is None else environ
    try:
        max_usd=float(env.get("WF_V28_MAX_USD","1"))
        max_calls=int(env.get("WF_V28_MAX_CALLS","10"))
        budget=CloudCallBudget(max_calls=max_calls,max_usd=max_usd)
    except (ValueError,OverflowError):
        raise ModelUnavailable("invalid cloud safety budget") from None
    roles={}
    for role in ROLES:
        pre="WF_V28_"+role.upper()+"_"
        provider=env.get(pre+"PROVIDER","")
        name=env.get(pre+"MODEL","")
        token=env.get(pre+"API_KEY","")
        try:
            price_in=float(env.get(pre+"INPUT_USD_PER_M","0"))
            price_out=float(env.get(pre+"OUTPUT_USD_PER_M","0"))
        except (ValueError,OverflowError):
            raise ModelUnavailable("missing configured model pricing") from None
        roles[role]=CloudModel(
            role=role, provider=provider, name=name,key=token,
            budget=budget,input_usd_per_m=price_in,
            output_usd_per_m=price_out,transport=transport)
    if (roles["writer"].provider,roles["writer"].name)==(
        roles["critic"].provider,roles["critic"].name):
        raise ModelUnavailable("writer and independent critic must be different model identities")
    return roles, budget


def safe_cloud_readiness(*, environ=None) -> dict:
    """No provider calls. Never expose whether a particular key is present."""
    try:
        roles,budget=configured_cloud_roles(environ=environ)
        return {"ready":True,"reason":"configured_without_call",
                "roles":{r:{"provider":m.provider,"model":m.name} for r,m in roles.items()},
                "call_cap":budget.max_calls,"usd_cap":budget.max_usd,
                "original_text_sent_to_provider":False}
    except ModelUnavailable:
        return {"ready":False,"reason":"cloud_roles_or_price_or_credential_unconfigured",
                "paid_calls_performed":False,"original_text_sent_to_provider":False}
