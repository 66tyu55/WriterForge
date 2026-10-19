"""WF LEARN model registry: official DeepSeek Flash, no Discovery fallback.

An adapter selection is not a literary education event. Real first-read PASS A
and analyst PASS B remain blocked until a separate immutable WF R2 learning
journal is deployed, the origin's chapter boundaries are resolved, and the
user-approved external-provider source transfer scope is pinned.
"""
from __future__ import annotations

from .deepseek_flash_model import (
    DeepSeekFlashModel, DeepSeekFlashError,
    FlashBudget, MODEL, PROVIDER, TOKEN_ENV, learner_provider_status,
)

from .wf_api_usage_supervisor import MeteredDeepSeekFlashModel

WF_LEARN_MODEL_ID = MODEL
WF_LEARN_PROVIDER = PROVIDER
WF_LEGACY_DISCOVERY_USED = False
FIRST_READ_R2_JOURNAL_IMPLEMENTED = False


def model_status(environ=None) -> dict:
    result=learner_provider_status(environ=environ)
    result.update({
       "WF_learn_model_registered":True,
       "previous_Discovery_training_not_selected":True,
       "first_read_immutable_r2_journal_deployed":
           FIRST_READ_R2_JOURNAL_IMPLEMENTED,
       "WF_PassA_PassB_execution_unlocked":False,
       "external_genre_classification_preselected":False,
       "literary_skill_promotion_unlocked":False,
    })
    return result


def new_wf_learn_model(*,budget=None,api_key=None,transport=None):
    """One strict DeepSeek client, owned by WF LEARN; never implicit fallback."""
    return MeteredDeepSeekFlashModel(
        api_key=api_key,
        budget=budget if budget is not None else FlashBudget(),
        transport=transport,
    )


def require_sequential_training_ready():
    if not FIRST_READ_R2_JOURNAL_IMPLEMENTED:
        raise DeepSeekFlashError("WF_FLASH_IMMUTABLE_LEARN_JOURNAL_MISSING")
    # Independent model availability and source provenance must also be
    # validated by the owner of the WF study session before any original
    # material is sent off-host.
    raise DeepSeekFlashError("WF_FLASH_LEARN_SESSION_NOT_INITIALIZED")
