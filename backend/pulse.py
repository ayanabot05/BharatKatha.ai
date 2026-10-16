"""Ram AI Pulse — feedback-loop learning from real user activity.

What it does:
  - Logs every user decision (idea shown/picked, script generated/edited/approved/rejected, render done).
  - Aggregates a weekly "what's actually working" view per language + region.
  - Feeds winning hooks back into ai.suggest_ideas and ai.write_script.
  - Prunes hooks that keep getting rejected.

What it does NOT do:
  - It does not train model weights.
  - It does not scrape YouTube.
  - It does not predict virality.
"""
from collections import Counter
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from core import db, new_id, now_iso, log


# ---------- 1. LOG ----------

async def log_event(
    user_id: str,
    event: str,           # idea_shown | idea_picked | script_generated | script_edited
                          # | script_approved | script_rejected | scene_regenerated | render_done
    language: str,
    region: str,
    genre: str = "",
    hook: str = "",
    idea_title: str = "",
    project_id: str = "",
    meta: Optional[Dict[str, Any]] = None,
):
    doc = {
        "id": new_id(),
        "user_id": user_id,
        "event": event,
        "language": language or "",
        "region": region or "",
        "genre": (genre or "")[:80],
        "hook": (hook or "")[:280],
        "idea_title": (idea_title or "")[:200],
        "project_id": project_id or "",
        "meta": meta or {},
        "created_at": now_iso(),
    }
    try:
        await db.pulse_events.insert_one(dict(doc))
    except Exception:
        log.exception("pulse.log_event")


# ---------- 2. QUERIES ----------

async def _recent(days: int, language: str = "", region: str = "", event: str = "", limit: int = 20000, user_id: str = "") -> List[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q: Dict[str, Any] = {"created_at": {"$gte": since}}
    if language:
        q["language"] = language
    if region:
        q["region"] = region
    if event:
        q["event"] = event
    if user_id:
        q["user_id"] = user_id
    return await db.pulse_events.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def pulse_hooks_for(language: str, region: str, limit: int = 6, days: int = 30, user_id: str = "") -> List[Dict[str, Any]]:
    """Real hooks that survived approvals. Scoped to user_id when provided to prevent privacy leakage."""
    if os.environ.get("PERSONALIZED_HOOKS", "false").lower() != "true":
        return []
    rows = await _recent(days, language=language, region=region, event="script_approved", user_id=user_id)
    counts: Counter = Counter()
    genres: Dict[str, str] = {}
    for r in rows:
        h = (r.get("hook") or "").strip()
        if not h:
            continue
        counts[h] += 1
        genres[h] = r.get("genre") or ""
    return [{"hook": h, "genre": genres.get(h, ""), "hits": n} for h, n in counts.most_common(limit)]


async def dead_hooks(language: str, region: str, limit: int = 10, days: int = 30) -> List[str]:
    """Hooks that kept getting rejected and never approved. Candidates to drop from the corpus."""
    approved = {(r.get("hook") or "").strip() for r in await _recent(days, language, region, "script_approved")}
    rejected = Counter((r.get("hook") or "").strip() for r in await _recent(days, language, region, "script_rejected"))
    return [h for h, n in rejected.most_common(limit) if h and n >= 2 and h not in approved]


async def weekly_pulse(language: str = "", region: str = "") -> Dict[str, Any]:
    events = await _recent(7, language=language, region=region)
    genres = Counter(e["genre"] for e in events if e.get("genre"))
    regions = Counter(e["region"] for e in events if e.get("region"))
    langs = Counter(e["language"] for e in events if e.get("language"))

    approved = Counter((e.get("hook") or "").strip() for e in events if e["event"] == "script_approved")
    rejected = Counter((e.get("hook") or "").strip() for e in events if e["event"] == "script_rejected")
    picked = Counter((e.get("hook") or "").strip() for e in events if e["event"] == "idea_picked")

    def survive(h: str) -> float:
        a, r = approved.get(h, 0), rejected.get(h, 0)
        return round(a / (a + r), 2) if (a + r) else 0.0

    winners = sorted(
        [h for h in picked if (approved.get(h, 0) + rejected.get(h, 0)) >= 2 and survive(h) >= 0.5],
        key=lambda h: (survive(h), approved.get(h, 0)),
        reverse=True,
    )[:10]

    return {
        "window_days": 7,
        "total_events": len(events),
        "top_genres": genres.most_common(8),
        "top_regions": regions.most_common(8),
        "top_languages": langs.most_common(6),
        "winning_hooks": [{"hook": h, "survive_rate": survive(h), "approved": approved.get(h, 0)} for h in winners],
        "dead_hooks": [h for h, n in rejected.most_common(10) if n >= 2 and h not in approved],
    }


# ---------- 3. HEALTH ----------

async def learning_report(user_id: str = "") -> Dict[str, Any]:
    total = await db.pulse_events.count_documents({})
    approved = await db.pulse_events.count_documents({"event": "script_approved"})
    rejected = await db.pulse_events.count_documents({"event": "script_rejected"})
    rendered = await db.pulse_events.count_documents({"event": "render_done"})

    stage = "cold" if total < 200 else ("warm" if total < 2000 else "hot")
    return {
        "stage": stage,
        "total_events": total,
        "approved": approved,
        "rejected": rejected,
        "rendered": rendered,
        "fine_tune_allowed": False,
        "gate": "Requires explicit permission, human-reviewed examples, held-out evaluation and an approved cloud training run.",
        "note": "Activity is recorded for review. Model weights are never updated automatically.",
    }
