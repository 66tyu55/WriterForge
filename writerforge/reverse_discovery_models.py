"""Dedicated authenticated InkStone/Discovery text-model adapter for V28.

Uses ONLY GitHub Actions secret DISCOVERY__API__KEY (mapped into process env).
One fixed HTTPS host; no API key exposure; no model-call retries by default.
Source text remains private to this single opt-in V28 training process and
the explicitly chosen Discovery provider. The provider is third-party.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    "planner": "deepseek-v4-flash-0731",
    "writer": "glm-5.3",
    "critic": "deepseek-v4-flash-0731",
}
FIXED_MODEL_CONTEXT_TOKENS = {
    "deepseek-v4-flash-0731": 1_048_576,
    "glm-5.3": 1_048_576,
}
# DeepSeek V4 and GLM-5.3 have documented 1M capacities on their own
# official model endpoints. Discovery /models omits context_window and the
# third-party gateway has NOT been load-tested at 1M tokens.
DISCOVERY_GATEWAY_1M_LOAD_VERIFIED = False
MAX_PROMPT_BYTES = 4_194_304  # bounded input transport; 1M is model capability, NOT verified gateway load
MAX_OUTPUT_BYTES = 1_000_000  # up to 50k completion tokens incl. Chinese UTF-8, bounded
MAX_CALLS = 7
MAX_REQUESTED_OUTPUT_TOKENS = 50_000

class DiscoveryError(RealTrainingError):
    pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryError("REDIRECT_REJECTED")

@dataclass
class DiscoveryCallBudget:
    max_calls: int = MAX_CALLS
    calls: int = 0
    max_reserved_output_tokens: int = 50_000
    last_requested_role: str = "not_started"
    calls_by_role: dict[str,int] = field(default_factory=dict)
    response_observations: list[dict] = field(default_factory=list)
    reserved_output_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    def reserve(self, request_bytes: int, requested: int, *, role: str = "unknown") -> None:
        self.last_requested_role=role
        # Default remains seven. Only explicitly bounded newer examiner repair
        # workflows can opt into ten, still capped by 50k reserved output.
        if not (1 <= self.max_calls <= 10 and
                0 <= self.calls < self.max_calls and
                50 <= requested <= MAX_REQUESTED_OUTPUT_TOKENS and
                request_bytes <= MAX_PROMPT_BYTES and
                self.reserved_output_tokens + requested <= self.max_reserved_output_tokens):
            raise DiscoveryError("MODEL_CALL_OR_TOKEN_BUDGET_EXHAUSTED")
        self.calls += 1
        self.calls_by_role[role]=self.calls_by_role.get(role,0)+1
        self.reserved_output_tokens += requested

class DiscoveryModel:
    provider = "discovery"

    def __init__(self, *, name: str, role: str, api_key: str,
                 budget: DiscoveryCallBudget, transport=None,
                 reasoning_effort: str | None = None):
        if role not in ROLE_MODELS or name not in MODELS:
            raise DiscoveryError("UNSUPPORTED_DISCOVERY_ROLE_OR_MODEL")
        if not isinstance(api_key,str) or not api_key or len(api_key)>512:
            raise DiscoveryError("DISCOVERY_API_KEY_UNAVAILABLE")
        if reasoning_effort is not None and not (
            name=="glm-5.3" and role=="writer" and reasoning_effort=="low"):
            raise DiscoveryError("UNVERIFIED_REASONING_EFFORT_COMBINATION")
        self.reasoning_effort=reasoning_effort
        self.name=name
        self.role=role
        self.budget=budget
        self._key=api_key
        self.transport=transport or self._request

    @staticmethod
    def _request(request: Request) -> bytes:
        opener=build_opener(_NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(request,timeout=300) as response:
                raw=response.read(MAX_OUTPUT_BYTES + 1)
        except HTTPError as exc:
            # Response bodies may repeat private prompts; never print them.
            raise DiscoveryError("DISCOVERY_HTTP_"+str(exc.code)) from None
        except TimeoutError:
            raise DiscoveryError("DISCOVERY_TIMEOUT") from None
        except URLError as exc:
            if isinstance(exc.reason,TimeoutError):
                raise DiscoveryError("DISCOVERY_TIMEOUT") from None
            raise DiscoveryError("DISCOVERY_CONNECTION_FAILED") from None
        except OSError:
            raise DiscoveryError("DISCOVERY_CONNECTION_FAILED") from None
        if len(raw)>MAX_OUTPUT_BYTES:
            raise DiscoveryError("DISCOVERY_RESPONSE_OVERSIZE")
        return raw

    def ask(self, system: str, user: str, *, num_predict: int = 1800) -> dict:
        if not isinstance(system,str) or not isinstance(user,str):
            raise DiscoveryError("INVALID_MODEL_PROMPT")
        if not 50 <= num_predict <= MAX_REQUESTED_OUTPUT_TOKENS:
            raise DiscoveryError("MODEL_OUTPUT_BUDGET_INVALID")
        # Long novel prose is PLAIN TEXT. Only planning/review returns JSON.
        # No raw novel response ever reaches public logs or permanent R2.
        prose_mode=self.role=="writer"
        instructions=(
            "只输出原创小说正文。不输出JSON、Markdown、解释或标题。" if prose_mode
            else "仅返回一个合法JSON对象，所有字段必须完整闭合。"
        )
        messages=[{"role":"system","content":system+" "+instructions},
                  {"role":"user","content":user}]
        requested=num_predict
        partial_prose=""
        for turn in range(2):
            request_data={
                "model":self.name,"messages":messages,
                "stream":False,"max_tokens":requested,
                "temperature":1 if self.name=="kimi-k2.6" else (0.2 if turn else 0.4),
            }
            if self.reasoning_effort is not None:
                # Optional GLM-5.3 feature gate. Default behavior unchanged.
                # Explicit opt-in only after separate gateway compatibility
                # probe; cannot disable thinking on GLM-5.3.
                request_data["reasoning_effort"]=self.reasoning_effort
            if self.name in ("deepseek-v4-flash-0731","deepseek-v4-pro-0813"):
                # Verified on Discovery gateway: both give visible text with
                # OpenAI-compatible thinking.type=disabled. Planning needs
                # bounded visible JSON; novelist needs finished native prose.
                request_data["thinking"]={"type":"disabled"}
            if not prose_mode:
                request_data["response_format"]={"type":"json_object"}
            body=json.dumps(request_data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
            req=Request(ENDPOINT,data=body,method="POST",headers={
                "Authorization":"Bearer "+self._key,
                "Content-Type":"application/json","Accept":"application/json",
            })
            # One extra attempt for a transient transport failure only.
            # Charge/budget BOTH attempts, because a timed-out provider
            # request might already have completed and been billed.
            raw=None
            for transport_attempt in range(2):
                self.budget.reserve(len(body),requested,role=self.role)
                try:
                    raw=self.transport(req)
                    break
                except DiscoveryError as exc:
                    code=str(exc)
                    transient=code in (
                        "DISCOVERY_TIMEOUT","DISCOVERY_CONNECTION_FAILED",
                        "DISCOVERY_HTTP_429","DISCOVERY_HTTP_502",
                        "DISCOVERY_HTTP_503","DISCOVERY_HTTP_504",
                    )
                    if not transient:
                        raise
                    self.budget.response_observations.append({
                        "role":self.role,"finish_reason":"transport_failure",
                        "transport_code":code,"visible_chars":0,
                        "turn":turn+1,"transport_attempt":transport_attempt+1,
                    })
                    if transport_attempt:
                        raise
            if not isinstance(raw,bytes) or len(raw)>MAX_OUTPUT_BYTES:
                raise DiscoveryError("DISCOVERY_RESPONSE_OVERSIZE")
            try:
                result=json.loads(raw)
                usage=result.get("usage") or {}
                if isinstance(usage,dict):
                    n=usage.get("prompt_tokens")
                    m=usage.get("completion_tokens")
                    if type(n) is int and n>=0:
                        self.budget.total_prompt_tokens+=n
                    if type(m) is int and m>=0:
                        self.budget.total_completion_tokens+=m
                choice=result["choices"][0]
                message=choice["message"]
                content=message.get("content")
                reason=choice.get("finish_reason")
                safe_reason=reason if reason in ("stop","length","content_filter") else "unknown"
                self.budget.response_observations.append({
                    "role":self.role,
                    "finish_reason":safe_reason,
                    "visible_chars":len(content) if isinstance(content,str) else 0,
                    "turn":turn+1,
                })
                if reason=="length":
                    if turn:
                        raise DiscoveryError("DISCOVERY_"+self.role.upper()+"_OUTPUT_TRUNCATED")
                    if prose_mode and isinstance(content,str) and 180<=len(content)<=3500:
                        # Actual prose continuation, not a fresh second story:
                        # the original request remains, the generated partial
                        # is explicitly the prior assistant turn. Nothing
                        # persists outside the current API request.
                        partial_prose=content
                        messages.append({"role":"assistant","content":content})
                        messages.append({"role":"user","content":
                            "只续写前文尚未完成的这一段，不重述已写部分。"
                            "使主人公的选择产生可见后果，并在本次输出中"
                            "完成场景；只返回新增加的小说正文，不要解释。"})
                    else:
                        # Reasoning-only or too-short result: bound a single
                        # re-try with a shorter target, never loop forever.
                        messages[0]["content"] += " 控制为800至1000汉字并结束完整场景。"
                    requested=min(MAX_REQUESTED_OUTPUT_TOKENS,max(2500,requested))
                    continue
                if not isinstance(content,str) or not content.strip():
                    if turn:
                        raise DiscoveryError("DISCOVERY_"+self.role.upper()+"_EMPTY_VISIBLE_TEXT")
                    requested=min(MAX_REQUESTED_OUTPUT_TOKENS,max(2500,requested))
                    continue
                if prose_mode:
                    candidate=(partial_prose+content).strip()
                    if candidate.startswith("{") and not partial_prose:
                        structured=_safe_json(candidate)
                        if set(structured)!={"scene"} or not isinstance(structured["scene"],str):
                            raise DiscoveryError("DISCOVERY_WRITER_INVALID_JSON_SCENE")
                        candidate=structured["scene"].strip()
                    fence=chr(96)*3
                    if (len(candidate)<220 or len(candidate)>4500
                        or candidate.startswith((fence,"抱歉","作为AI","作为一个AI"))
                        or fence in candidate):
                        if turn:
                            raise DiscoveryError("DISCOVERY_WRITER_INVALID_PROSE")
                        requested=min(MAX_REQUESTED_OUTPUT_TOKENS,max(2500,requested))
                        continue
                    return {"scene":candidate}
                return _safe_json(content)
            except DiscoveryError:
                raise
            except (IndexError,KeyError,TypeError,ValueError,RealTrainingError):
                if turn:
                    raise DiscoveryError("DISCOVERY_"+self.role.upper()+"_STRUCTURED_OUTPUT_FAILED") from None
                requested=min(4000,max(2400,requested))
        raise DiscoveryError("DISCOVERY_"+self.role.upper()+"_RETRY_EXHAUSTED")
