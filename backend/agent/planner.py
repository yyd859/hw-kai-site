import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import get_recipe_library


def select_recipe(spec: dict) -> dict | None:
    """根据 spec 选择最合适的 recipe

    打分策略：
    - 先过 hard guard，过滤明显不合理的方案
    - 正向匹配（True == True）: +3
    - 负向匹配（False == False）: +1（都不需要某功能）
    - 不匹配: 0
    - 精准字符串匹配（如 sensor_type）: +4
    - 最终选 score 最高的
    """
    recipes = get_recipe_library()["recipes"]

    # 把 spec 转换成 intent 格式（兼容旧版 planner）
    intent = _spec_to_intent(spec)

    best_match = None
    best_score = -1
    best_specificity = -1

    for recipe_id, recipe in recipes.items():
        if not _passes_hard_guards(intent, recipe["intent_match"]):
            continue

        score = _score_recipe(intent, recipe["intent_match"])
        specificity = len(recipe["intent_match"])
        if score > best_score or (score == best_score and specificity > best_specificity):
            best_score = score
            best_specificity = specificity
            best_match = recipe

    return best_match if best_score >= 1 else None


def _spec_to_intent(spec: dict) -> dict:
    """将 chat spec 格式转换为 intent 格式"""
    intent = {}

    if spec.get("trigger"):
        intent["trigger"] = spec["trigger"]

    for key in ["needs_light", "needs_sound", "needs_display", "needs_sensor"]:
        if key in spec:
            intent[key] = spec[key]
            if key == "needs_sensor" and spec.get(key):
                intent["needs_sensor"] = True

    if spec.get("sensor_type"):
        intent["sensor_type"] = spec["sensor_type"]

    # 推断 needs_display
    if spec.get("needs_display"):
        intent["needs_display"] = True

    return intent


def _passes_hard_guards(intent: dict, recipe_match: dict) -> bool:
    sensor_type = intent.get("sensor_type")
    if sensor_type and recipe_match.get("sensor_type") not in (None, sensor_type):
        return False

    if intent.get("needs_sensor") is True and recipe_match.get("needs_sensor") is not True:
        return False

    if intent.get("needs_actuator") is True and recipe_match.get("needs_actuator") is not True:
        return False

    trigger = intent.get("trigger")
    if trigger == "remote" and recipe_match.get("trigger") not in (None, "remote"):
        return False
    if trigger == "rfid" and recipe_match.get("trigger") not in (None, "rfid"):
        return False
    if trigger == "bluetooth" and recipe_match.get("trigger") not in (None, "bluetooth"):
        return False

    return True


def _score_recipe(intent: dict, recipe_match: dict) -> int:
    score = 0
    for key, expected in recipe_match.items():
        actual = intent.get(key)
        if actual is None:
            continue
        if isinstance(expected, bool):
            if actual == expected:
                score += 3 if expected else 1
        elif isinstance(expected, str):
            if actual == expected:
                score += 4
    return score
