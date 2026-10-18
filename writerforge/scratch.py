"""Zero-corpus WriterForge starter. No R2, files, SQLite, or model on import.

A new user may inspect a bounded original-writing request without connecting
the author's private library or downloading a novel. Writing still requires
a separately configured REAL model host; it is never advertised as
WriterForge's trained literary ability.
"""
from __future__ import annotations

from hashlib import sha256


class ScratchError(ValueError):
    pass


def prepare_scratch(*, scene: str, goal: str, language: str = "简体中文"):
    if (not isinstance(scene,str) or not 2<=len(scene)<=120 or
        not isinstance(goal,str) or not 12<=len(goal)<=1300 or
        not isinstance(language,str) or language not in ("简体中文","繁體中文")):
        raise ScratchError("SCRATCH_SCENE_GOAL_OR_LANGUAGE_INVALID")
    prompt=(
        f"请创作原创{language}小说正文。场景：{scene}。\n"
        f"本场景的目标：{goal.strip()}\n"
        "根据场景自然描写，不抄录任何原著语句，不输出写作教学说明。"
        "目前没有文学学海或经过验证的经验库；不要声称经过训练。"
    )
    h=sha256(prompt.encode("utf-8")).hexdigest()
    return {"format":"writerforge.scratch.no-corpus.v1",
            "prompt":prompt,"prompt_sha256":h,
            "source_snapshot_required":False,
            "private_r2_required":False,
            "download_requested":False,
            "literary_experience_applied":False,
            "literary_training_proven":False}
