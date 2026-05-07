from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from ..schemas import ProjectRecord

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"
_STORAGE_LOCK = Lock()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text("[]", encoding="utf-8")


def load_projects() -> list[ProjectRecord]:
    _ensure_storage()
    raw_items = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    return [ProjectRecord.model_validate(item) for item in raw_items]


def save_project(project: ProjectRecord) -> ProjectRecord:
    with _STORAGE_LOCK:
        projects = load_projects()
        projects = [existing for existing in projects if existing.id != project.id]
        projects.append(project)
        PROJECTS_FILE.write_text(
            json.dumps([item.model_dump(mode="json") for item in projects], indent=2),
            encoding="utf-8",
        )
    return project


def get_project(project_id: str) -> ProjectRecord | None:
    for project in load_projects():
        if project.id == project_id:
            return project
    return None
