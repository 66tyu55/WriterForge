"""V76: bounded per-request DeepSeek usage evidence for examiner reconciliation.

Wraps the existing official DeepSeek Flash adapter rather than calling GPT,
Discovery or OpenRouter. No prompt, API key, model response or original
novel excerpt appears in the emitted audit ledger; only hashes, role, time,
limits, outcome, and provider-reported token counters.

Provider's dashboard is the source of truth for billed requests. Usage
returned in a successful HTTP response is *not* a bank/billing statement;
timeouts or invalid responses may still incur charges and must be
reconciled, never silently counted as zero cost.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
import json
import re

from .deepseek_flash_model import (
    DeepSeekFlashModel,DeepSeekFlashError,
    DEFAULT_COMPLETION_TOKENS,
)

MAX_EVENTS_PER_RUN=4
ERRORCODE=re.compile(r"WF_FLASH_[A-Z0-9_]+\Z")

class WFApiUsageAuditError(RuntimeError):
    pass

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


class MeteredDeepSeekFlashModel(DeepSeekFlashModel):
    """Drop-in DeepSeekFlashModel with monotonic zero-prose usage log."""

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.usage_events=[]

    def ask_json(self,*,role,system,user,
                 max_tokens=DEFAULT_COMPLETION_TOKENS):
        # A call can happen only when the user's opt-in trial is running.
        limit=(self.budget.max_calls
               if self.budget.max_total_tokens==150000
               else MAX_EVENTS_PER_RUN)
        if len(self.usage_events)>=limit:
            raise WFApiUsageAuditError(
                "WF_USAGE_PER_RUN_EVENT_LIMIT_EXCEEDED")
        stamp=datetime.now(timezone.utc).isoformat(timespec="seconds")
        req_hash=sha256(canonical({
            "role":role,"system":system,"user":user,
            "max_tokens":max_tokens,
            "model":self.name,
        })).hexdigest()
        old_calls=self.budget.calls_reserved
        old_in=self.budget.prompt_tokens_reported
        old_out=self.budget.completion_tokens_reported
        response_hash=None
        status="UNKNOWN"
        error_code=None
        try:
            output=super().ask_json(
                role=role,system=system,user=user,
                max_tokens=max_tokens)
            status="JSON_CONTRACT_OK_NOT_LITERARY_CERTIFIED"
            response_hash=sha256(canonical(output)).hexdigest()
            return output
        except (DeepSeekFlashError,WFApiUsageAuditError) as err:
            code=str(err)
            error_code=code if ERRORCODE.fullmatch(code) else \
                "WF_FLASH_UNCLASSIFIED_FAILURE"
            status="FAILED_MAY_HAVE_BEEN_BILLED"
            raise
        finally:
            billable_requests=self.budget.calls_reserved-old_calls
            # Prevent uncalled input validation errors being charged as
            # accepted network request in the WF-side audit.
            self.usage_events.append({
                "provider":"deepseek",
                "model":"deepseek-flash",
                "role":role if role in (
                    "first_read","genre_classification","craft_analysis"
                ) else "INVALID_ROLE",
                "requested_at_utc":stamp,
                "request_sha256":req_hash,
                "output_sha256":response_hash,
                "reserved_model_requests":billable_requests,
                "output_token_budget":max_tokens,
                "status":status,
                "error_code":error_code,
                "provider_prompt_tokens_reported_delta":
                    self.budget.prompt_tokens_reported-old_in,
                "provider_completion_tokens_reported_delta":
                    self.budget.completion_tokens_reported-old_out,
                "provider_billing_reconciled":False,
                "original_prose_or_key_logged":False,
                "literary_quality_verified":False,
            })

    def public_usage_report(self):
        """No raw model inputs/outputs. Count unresolved billable requests."""
        records=list(self.usage_events)
        return {
            "format":"writerforge.deepseek-usage-audit.v1",
            "provider":"deepseek",
            "model":"deepseek-flash",
            "event_count":len(records),
            "reserved_requests":sum(
                max(0,x["reserved_model_requests"]) for x in records),
            "prompt_tokens_reported":sum(
                x["provider_prompt_tokens_reported_delta"] for x in records),
            "completion_tokens_reported":sum(
                x["provider_completion_tokens_reported_delta"] for x in records),
            "calls_that_may_have_billed_without_visible_usage":sum(
                x["reserved_model_requests"]
                for x in records
                if x["status"]!="JSON_CONTRACT_OK_NOT_LITERARY_CERTIFIED"),
            "usage_needs_dashboard_reconciliation":True,
            "batch_total_token_cap":self.budget.max_total_tokens,
            "conservatively_committed_tokens":self.budget.conservative_tokens_committed,
            "budget_remaining_estimate":(self.budget.max_total_tokens-self.budget.conservative_tokens_committed if self.budget.max_total_tokens is not None else None),
            "r2_learning_evidence_not_implied_by_usage":True,
            "events":records,
        }


def reconcile_dashboard_snapshot(*,before_requests,after_requests,
                                 before_tokens,after_tokens,
                                 wf_usage_report,other_apps_used=False):
    """Conservatively compare a matching-period provider dashboard delta.

    When the dashboard spans other applications or nonidentical periods, the
    result is UNRECONCILED; never claim exact cost or book understanding.
    """
    nums=(before_requests,after_requests,
          before_tokens,after_tokens)
    if not all(type(x) is int and x>=0 for x in nums):
        raise WFApiUsageAuditError(
            "WF_USAGE_DASHBOARD_VALUES_INVALID")
    if after_requests<before_requests or after_tokens<before_tokens:
        return {"status":"UNRECONCILED_DASHBOARD_WINDOW_MISMATCH"}
    if not isinstance(wf_usage_report,dict) or \
       wf_usage_report.get("provider")!="deepseek":
        raise WFApiUsageAuditError("WF_USAGE_RECEIPT_INVALID")
    count=after_requests-before_requests
    tokens=after_tokens-before_tokens
    budgeted=wf_usage_report.get("reserved_requests")
    reported=wf_usage_report.get("prompt_tokens_reported",0)+\
             wf_usage_report.get("completion_tokens_reported",0)
    if other_apps_used or count!=budgeted or tokens!=reported:
        return {
            "status":"UNRECONCILED",
            "dashboard_delta_requests":count,
            "dashboard_delta_tokens":tokens,
            "wf_reserved_requests":budgeted,
            "wf_response_usage_tokens":reported,
            "possible_other_apps_or_billing_semantics":True,
        }
    return {
        "status":"COUNTS_MATCH_FOR_SPECIFIED_TIME_WINDOW",
        "dashboard_delta_requests":count,
        "dashboard_delta_tokens":tokens,
        "provider_billing_website_verified_by_automation":False,
        "literary_quality_not_implied":True,
    }
