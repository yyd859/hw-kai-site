from __future__ import annotations

from typing import Any

from agent.generator import GenerationNotSupportedError, generate_output
from agent.module_selector import MissingComponentsError, select_modules
from agent.pin_allocator import PinAllocationError, allocate_pins
from library_loader import find_module, get_board, get_boards, get_modules

DEFAULT_BOARD_ID = "esp32_devkit_v1"

CAPABILITY_TO_MODULE = {
    "button": "push_button",
    "light": "ws2812_led_ring",
    "sound": "active_buzzer",
    "display": "oled_ssd1306",
    "temperature_humidity": "dht22",
    "soil_moisture": "soil_moisture_sensor",
    "relay": "relay_module",
    "pump": "relay_module",
}

MODULE_TO_LEGACY_SENSOR_TYPE = {
    "dht22": "temperature_humidity",
    "soil_moisture_sensor": "soil_moisture",
}

UNSUPPORTED_KEYWORDS = {
    "camera_vision": ["camera", "vision", "摄像头", "视觉识别", "图像识别"],
    "vibration_feedback": ["vibration", "haptic", "震动", "振动"],
}


class ToolExecutionError(Exception):
    pass


def library_search(query: str = "", capabilities: list[str] | None = None, limit: int = 8) -> dict[str, Any]:
    capabilities = capabilities or []
    query_l = (query or "").lower()
    capability_l = [item.lower() for item in capabilities]

    board_hits = []
    for board in get_boards():
        score = _score_item(board, query_l, capability_l)
        if score > 0:
            board_hits.append((score, _compact_item(board)))

    module_hits = []
    for module in get_modules():
        score = _score_item(module, query_l, capability_l)
        if score > 0:
            module_hits.append((score, _compact_item(module)))

    board_hits.sort(key=lambda item: (-item[0], item[1]["id"]))
    module_hits.sort(key=lambda item: (-item[0], item[1]["id"]))

    return {
        "query": query,
        "capabilities": capabilities,
        "boards": [item for _, item in board_hits[: max(1, limit // 2)]],
        "modules": [item for _, item in module_hits[:limit]],
    }


def library_inspect(item_id: str) -> dict[str, Any]:
    board = get_board(item_id)
    if board:
        return {"kind": "board", "item": board}

    module = find_module(item_id)
    if module:
        return {"kind": "module", "item": module}

    raise ToolExecutionError(f"unknown library item: {item_id}")


def build_plan_from_context(context: dict[str, Any]) -> dict[str, Any]:
    preflight = preflight_build_context(context)
    if not preflight["buildable"]:
        missing = preflight.get("missing_components") or ["unknown"]
        raise MissingComponentsError(missing)

    board = get_board(preflight["board_id"])
    if not board:
        raise MissingComponentsError([f"board:{preflight['board_id']}"])

    selected_modules = [
        find_module(module_id)
        for module_id in preflight["selected_module_ids"]
    ]
    selected_modules = [module for module in selected_modules if module]

    if len(selected_modules) != len(preflight["selected_module_ids"]):
        missing = [mid for mid in preflight["selected_module_ids"] if not find_module(mid)]
        raise MissingComponentsError(missing)

    selected_modules = [
        {**module, "instance_id": _instance_id_for(module["id"], index)}
        for index, module in enumerate(selected_modules)
    ]

    hardware_plan = allocate_pins(board, selected_modules)
    generated = generate_output(board, selected_modules, hardware_plan, preflight["legacy_spec"])
    generated["meta"]["build_context"] = preflight["normalized_context"]
    generated["meta"]["buildable"] = True
    return generated


def preflight_build_context(context: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_build_context(context)
    unsupported = infer_unsupported_capabilities(normalized)
    if unsupported:
        return {
            "buildable": False,
            "error_type": "missing_components",
            "missing_components": unsupported,
            "normalized_context": normalized,
            "selected_module_ids": normalized["selected_module_ids"],
            "board_id": normalized["selected_board_id"],
            "legacy_spec": normalized["legacy_spec"],
        }

    explicit_ids = normalized["selected_module_ids"]
    if explicit_ids:
        combo_check = _check_explicit_modules(normalized["selected_board_id"], explicit_ids)
        combo_check["normalized_context"] = normalized
        combo_check["legacy_spec"] = normalized["legacy_spec"]
        return combo_check

    try:
        selection = select_modules(normalized["legacy_spec"])
        module_ids = [module["id"] for module in selection["selected_modules"]]
        return {
            "buildable": True,
            "selected_module_ids": module_ids,
            "board_id": selection["board"]["id"],
            "missing_components": [],
            "normalized_context": {**normalized, "selected_module_ids": module_ids},
            "legacy_spec": normalized["legacy_spec"],
        }
    except MissingComponentsError as exc:
        return {
            "buildable": False,
            "error_type": "missing_components",
            "missing_components": exc.missing_capabilities,
            "selected_module_ids": [],
            "board_id": normalized["selected_board_id"],
            "normalized_context": normalized,
            "legacy_spec": normalized["legacy_spec"],
        }


def normalize_build_context(context: dict[str, Any]) -> dict[str, Any]:
    context = context or {}
    project_brief = str(context.get("project_brief") or context.get("message") or context.get("query") or "").strip()
    requirements = _string_list(context.get("requirements"))
    constraints = _string_list(context.get("constraints"))
    capabilities = _string_list(context.get("capabilities"))
    selected_module_ids = _normalize_selected_module_ids(context.get("selected_module_ids") or context.get("module_ids") or [])
    selected_board_id = str(context.get("selected_board_id") or DEFAULT_BOARD_ID)

    legacy_spec = _context_to_legacy_spec(project_brief, requirements, constraints, capabilities, selected_module_ids)

    return {
        "project_brief": project_brief,
        "requirements": requirements,
        "constraints": constraints,
        "capabilities": capabilities,
        "selected_module_ids": selected_module_ids,
        "selected_board_id": selected_board_id,
        "legacy_spec": legacy_spec,
    }


def execute_tool_call(call: dict[str, Any]) -> dict[str, Any]:
    tool = call.get("tool")
    args = call.get("arguments") or {}

    if tool == "library.search":
        return {"tool": tool, "ok": True, "result": library_search(**args)}
    if tool == "library.inspect":
        return {"tool": tool, "ok": True, "result": library_inspect(args.get("id", ""))}

    raise ToolExecutionError(f"unsupported tool: {tool}")


def _score_item(item: dict[str, Any], query: str, capabilities: list[str]) -> int:
    haystack = " ".join(
        str(item.get(key) or "")
        for key in ["id", "label", "description", "category", "subcategory", "interface"]
    ).lower()
    haystack += " " + " ".join(str(v).lower() for v in item.get("provides", []))

    score = 0
    if query:
        for token in query.replace("/", " ").replace("_", " ").split():
            if token and token in haystack:
                score += 3
    for cap in capabilities:
        if cap in haystack:
            score += 4
    return score


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "label": item.get("label"),
        "category": item.get("category"),
        "subcategory": item.get("subcategory"),
        "description": item.get("description"),
        "provides": item.get("provides", []),
        "interface": item.get("interface"),
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_selected_module_ids(values: list[Any]) -> list[str]:
    result: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value:
            continue
        value = value.lower()
        if value == "soil_moisture_capacitive":
            value = "soil_moisture_sensor"
        if value in CAPABILITY_TO_MODULE:
            value = CAPABILITY_TO_MODULE[value]
        if value not in result:
            result.append(value)
    return result


def _context_to_legacy_spec(project_brief: str, requirements: list[str], constraints: list[str], capabilities: list[str], selected_module_ids: list[str]) -> dict[str, Any]:
    text = " ".join([project_brief, *requirements, *constraints, *capabilities, *selected_module_ids]).lower()
    spec = {
        "object": project_brief or None,
        "trigger": _infer_trigger(text),
        "needs_light": any(token in text for token in ["light", "灯", "led", "ws2812"]),
        "needs_sound": any(token in text for token in ["sound", "蜂鸣", "buzzer", "声音"]),
        "needs_display": any(token in text for token in ["display", "显示", "screen", "oled"]),
        "needs_sensor": any(token in text for token in ["sensor", "传感", "温湿度", "soil", "湿度", "dht22"]),
        "sensor_type": _infer_sensor_type(text, selected_module_ids),
        "needs_actuator": any(token in text for token in ["pump", "relay", "actuator", "浇水", "水泵", "执行器", "继电器"]),
        "actuator_type": _infer_actuator_type(text),
        "extra_notes": None,
    }

    for module_id in selected_module_ids:
        if module_id == "push_button":
            spec["trigger"] = spec["trigger"] or "button"
        elif module_id == "ws2812_led_ring":
            spec["needs_light"] = True
        elif module_id == "active_buzzer":
            spec["needs_sound"] = True
        elif module_id == "oled_ssd1306":
            spec["needs_display"] = True
        elif module_id in MODULE_TO_LEGACY_SENSOR_TYPE:
            spec["needs_sensor"] = True
            spec["sensor_type"] = MODULE_TO_LEGACY_SENSOR_TYPE[module_id]
        elif module_id == "relay_module":
            spec["needs_actuator"] = True
            spec["actuator_type"] = spec["actuator_type"] or "relay"

    if spec["needs_actuator"] and spec["sensor_type"] == "soil_moisture":
        spec["trigger"] = spec["trigger"] or "auto"

    return spec


def infer_unsupported_capabilities(normalized_context: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            normalized_context.get("project_brief", ""),
            *normalized_context.get("requirements", []),
            *normalized_context.get("constraints", []),
            *normalized_context.get("capabilities", []),
        ]
    ).lower()

    missing: list[str] = []
    for capability, keywords in UNSUPPORTED_KEYWORDS.items():
        if any(token in text for token in keywords):
            missing.append(capability)
    return missing


def _check_explicit_modules(board_id: str, module_ids: list[str]) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        return {
            "buildable": False,
            "error_type": "missing_components",
            "missing_components": [f"board:{board_id}"],
            "selected_module_ids": module_ids,
            "board_id": board_id,
        }

    missing_ids = [module_id for module_id in module_ids if not find_module(module_id)]
    if missing_ids:
        return {
            "buildable": False,
            "error_type": "missing_components",
            "missing_components": missing_ids,
            "selected_module_ids": module_ids,
            "board_id": board_id,
        }

    selected_modules = [{**find_module(module_id), "instance_id": _instance_id_for(module_id, index)} for index, module_id in enumerate(module_ids)]

    try:
        allocate_pins(board, selected_modules)
    except PinAllocationError:
        return {
            "buildable": False,
            "error_type": "pin_allocation_failed",
            "missing_components": [],
            "selected_module_ids": module_ids,
            "board_id": board_id,
        }

    try:
        from agent.generator import _resolve_combo_key  # type: ignore

        _resolve_combo_key(selected_modules)
    except GenerationNotSupportedError:
        return {
            "buildable": False,
            "error_type": "generation_not_supported_yet",
            "missing_components": [],
            "selected_module_ids": module_ids,
            "board_id": board_id,
        }
    except Exception:
        return {
            "buildable": False,
            "error_type": "generation_not_supported_yet",
            "missing_components": [],
            "selected_module_ids": module_ids,
            "board_id": board_id,
        }

    return {
        "buildable": True,
        "error_type": None,
        "missing_components": [],
        "selected_module_ids": module_ids,
        "board_id": board_id,
    }


def _infer_trigger(text: str) -> str | None:
    if any(token in text for token in ["button", "按钮", "按下"]):
        return "button"
    if any(token in text for token in ["motion", "人体", "感应"]):
        return "motion"
    if any(token in text for token in ["remote", "遥控"]):
        return "remote"
    if any(token in text for token in ["auto", "自动"]):
        return "auto"
    return None


def _infer_sensor_type(text: str, selected_module_ids: list[str]) -> str | None:
    if "dht22" in selected_module_ids or any(token in text for token in ["温湿度", "temperature", "humidity", "dht"]):
        return "temperature_humidity"
    if "soil_moisture_sensor" in selected_module_ids or any(token in text for token in ["soil", "土壤", "浇花", "湿度"]):
        return "soil_moisture"
    return None


def _infer_actuator_type(text: str) -> str | None:
    if any(token in text for token in ["pump", "水泵"]):
        return "pump"
    if any(token in text for token in ["relay", "继电器"]):
        return "relay"
    return None


def _instance_id_for(module_id: str, index: int) -> str:
    defaults = {
        "push_button": "btn1",
        "ws2812_led_ring": "led1",
        "active_buzzer": "buzz1",
        "oled_ssd1306": "oled1",
        "dht22": "sensor1",
        "soil_moisture_sensor": "sensor1",
        "relay_module": "relay1",
    }
    return defaults.get(module_id, f"module{index + 1}")
