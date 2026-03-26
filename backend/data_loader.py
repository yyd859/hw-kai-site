import json
import os
from pathlib import Path


def _resolve_data_dir() -> Path:
    env_data_dir = os.getenv("DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir).expanduser()

    container_data_dir = Path("/app/data")
    if container_data_dir.exists():
        return container_data_dir

    return Path(__file__).resolve().parent.parent / "data"


DATA_DIR = _resolve_data_dir()


def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def get_capability_registry():
    return load_json("capability_registry.json")


def get_recipe_library():
    return load_json("recipe_library.json")


def get_intent_schema():
    return load_json("intent_schema.json")


def get_code_template(template_id: str) -> str:
    path = DATA_DIR / "templates" / "code" / f"{template_id}.ino"
    return path.read_text(encoding="utf-8")


def get_wiring_template(template_id: str) -> dict:
    path = DATA_DIR / "templates" / "wiring" / f"{template_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))
