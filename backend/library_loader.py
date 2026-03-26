import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_DIR = REPO_ROOT / "library"


class LibraryLoadError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_library() -> dict[str, Any]:
    if not LIBRARY_DIR.exists():
        raise LibraryLoadError(f"library 目录不存在: {LIBRARY_DIR}")

    boards = _load_collection(LIBRARY_DIR / "boards")
    modules = _load_collection(LIBRARY_DIR / "modules")

    return {
        "boards": boards,
        "boards_by_id": {item["id"]: item for item in boards},
        "modules": modules,
        "modules_by_id": {item["id"]: item for item in modules},
    }


@lru_cache(maxsize=1)
def get_board(board_id: str) -> dict[str, Any] | None:
    return load_library()["boards_by_id"].get(board_id)


@lru_cache(maxsize=1)
def get_modules_index() -> dict[str, dict[str, Any]]:
    return load_library()["modules_by_id"]


@lru_cache(maxsize=1)
def get_modules() -> list[dict[str, Any]]:
    return load_library()["modules"]


@lru_cache(maxsize=1)
def get_boards() -> list[dict[str, Any]]:
    return load_library()["boards"]


@lru_cache(maxsize=1)
def find_module(module_id: str) -> dict[str, Any] | None:
    return get_modules_index().get(module_id)


@lru_cache(maxsize=1)
def find_modules_by_ids(module_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    index = get_modules_index()
    return [index[mid] for mid in module_ids if mid in index]


def _load_collection(base_dir: Path) -> list[dict[str, Any]]:
    if not base_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(base_dir.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("id"):
            continue
        data["__source_path"] = str(path.relative_to(REPO_ROOT))
        items.append(data)
    return items
