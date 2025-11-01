import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from uuid import uuid4

GOALS_FILE = os.getenv("GOALS_FILE", os.path.join(os.path.dirname(__file__), "goals.json"))
_LOCK = threading.Lock()


def _ensure_file() -> None:
    if not os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _read_goals() -> List[Dict]:
    if not os.path.exists(GOALS_FILE):
        return []
    try:
        with open(GOALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _write_goals(goals: List[Dict]) -> None:
    tmp_path = f"{GOALS_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(goals, f, indent=2)
    os.replace(tmp_path, GOALS_FILE)


def _coerce_number(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Convert various numeric inputs to a float, returning None when not possible.
    Keeps ints precise while gracefully handling empty strings.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _recompute_progress(goal: Dict) -> None:
    """
    Ensure goal['progress'] reflects goal['progress_value'] vs goal['target_value'] when available.
    Leaves existing progress intact if target data is incomplete.
    """
    target_value = goal.get("target_value")
    progress_value = goal.get("progress_value")
    if isinstance(target_value, (int, float)) and target_value > 0 and isinstance(progress_value, (int, float)):
        ratio = max(0.0, progress_value) / target_value
        pct = int(round(min(ratio, 1.0) * 100))
        goal["progress"] = pct
        # Auto-finish when we hit or exceed target
        if pct >= 100 and goal.get("status") not in ("completed", "archived"):
            goal["status"] = "completed"


def list_goals(status: Optional[str] = None) -> List[Dict]:
    with _LOCK:
        goals = _read_goals()
    if status:
        status_lower = status.lower()
        goals = [g for g in goals if g.get("status", "").lower() == status_lower]
    return goals


def get_goal(goal_id: str) -> Optional[Dict]:
    with _LOCK:
        goals = _read_goals()
    for goal in goals:
        if goal.get("id") == goal_id:
            return goal
    return None


def create_goal(
    title: str,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
    target_value: Optional[Union[str, int, float]] = None,
    target_unit: Optional[str] = None,
    target_period: Optional[str] = None,
    progress_value: Optional[Union[str, int, float]] = None,
) -> Dict:
    if not title or not title.strip():
        raise ValueError("Goal title is required.")

    now = datetime.now(timezone.utc).isoformat()
    target_value_num = _coerce_number(target_value)
    if target_value_num is not None and target_value_num <= 0:
        target_value_num = None
    progress_value_num = _coerce_number(progress_value)
    if progress_value_num is not None and progress_value_num < 0:
        progress_value_num = 0.0

    progress_pct = 0
    if (
        isinstance(target_value_num, (int, float))
        and target_value_num > 0
        and isinstance(progress_value_num, (int, float))
    ):
        ratio = max(0.0, progress_value_num) / target_value_num
        progress_pct = int(round(min(ratio, 1.0) * 100))

    status = "completed" if progress_pct >= 100 else "active"
    goal = {
        "id": uuid4().hex,
        "title": title.strip(),
        "description": (description or "").strip(),
        "target_date": target_date,
        "progress": progress_pct,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "history": [],
        "target_value": target_value_num,
        "target_unit": (target_unit or "").strip() or None,
        "target_period": (target_period or "").strip() or None,
        "progress_value": progress_value_num,
    }

    _recompute_progress(goal)

    with _LOCK:
        goals = _read_goals()
        goals.append(goal)
        _write_goals(goals)

    return goal


def update_goal(
    goal_id: str,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
    target_value: Optional[Union[str, int, float]] = None,
    target_unit: Optional[str] = None,
    target_period: Optional[str] = None,
    progress: Optional[int] = None,
    progress_value: Optional[Union[str, int, float]] = None,
    status: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict:
    allowed_status = {"active", "completed", "archived"}
    with _LOCK:
        goals = _read_goals()
        for idx, goal in enumerate(goals):
            if goal.get("id") != goal_id:
                continue

            modified = False
            if title is not None and title.strip() and title.strip() != goal.get("title"):
                goal["title"] = title.strip()
                modified = True
            if description is not None and description != goal.get("description"):
                goal["description"] = description
                modified = True
            if target_date is not None and target_date != goal.get("target_date"):
                goal["target_date"] = target_date
                modified = True
            needs_recompute = False
            if target_value is not None:
                coerced = _coerce_number(target_value)
                if coerced is not None and coerced <= 0:
                    coerced = None
                if coerced != goal.get("target_value"):
                    goal["target_value"] = coerced
                    modified = True
                    needs_recompute = True
            if target_unit is not None:
                cleaned_unit = (target_unit or "").strip() or None
                if cleaned_unit != goal.get("target_unit"):
                    goal["target_unit"] = cleaned_unit
                    modified = True
            if target_period is not None:
                cleaned_period = (target_period or "").strip() or None
                if cleaned_period != goal.get("target_period"):
                    goal["target_period"] = cleaned_period
                    modified = True
            if progress is not None:
                pct = max(0, min(100, int(progress)))
                if pct != goal.get("progress"):
                    goal["progress"] = pct
                    modified = True
                    needs_recompute = True
                if pct == 100:
                    goal["status"] = "completed"
                target_val = goal.get("target_value")
                if isinstance(target_val, (int, float)) and target_val > 0:
                    goal["progress_value"] = (target_val * pct) / 100.0
            if progress_value is not None:
                coerced_progress_value = _coerce_number(progress_value)
                if coerced_progress_value is None:
                    raise ValueError("Progress value must be numeric.")
                if coerced_progress_value < 0:
                    coerced_progress_value = 0.0
                if coerced_progress_value != goal.get("progress_value"):
                    goal["progress_value"] = coerced_progress_value
                    modified = True
                    needs_recompute = True
            if status is not None:
                status_lower = status.lower()
                if status_lower not in allowed_status:
                    raise ValueError(f"Invalid status '{status}'.")
                if status_lower != goal.get("status"):
                    goal["status"] = status_lower
                    modified = True

            if note:
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": note.strip(),
                }
                goal.setdefault("history", []).append(entry)
                modified = True

            if modified:
                if needs_recompute:
                    _recompute_progress(goal)
                goal["updated_at"] = datetime.now(timezone.utc).isoformat()
                goals[idx] = goal
                _write_goals(goals)
            return goal

    raise ValueError(f"Goal with id '{goal_id}' not found.")


def delete_goal(goal_id: str) -> bool:
    with _LOCK:
        goals = _read_goals()
        new_goals = [g for g in goals if g.get("id") != goal_id]
        if len(new_goals) == len(goals):
            return False
        _write_goals(new_goals)
    return True


_ensure_file()
