import json
from writerforge.scheduler import SkillScheduler

def main():
    s = SkillScheduler()
    scenarios = [
        ("sentence_accepted", s.drafting_decision("sentence_accepted", 8)),
        ("dependency_invalidated", s.drafting_decision("dependency_invalidated", 8)),
        ("scene_boundary", s.boundary_decision("scene_boundary", 24)),
        ("chapter_boundary", s.boundary_decision("chapter_boundary", 32)),
        ("offline_audit", s.offline_decision("offline_audit", 60)),
    ]
    out = {
        name: {"selected": d.selected, "cost": d.total_cost}
        for name,d in scenarios
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out

if __name__ == "__main__":
    main()
