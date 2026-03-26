from __future__ import annotations

from typing import Any

from library_loader import get_board, get_modules_index

DEFAULT_BOARD_ID = "esp32_devkit_v1"


class MissingComponentsError(Exception):
    def __init__(self, missing_capabilities: list[str]):
        self.missing_capabilities = missing_capabilities
        super().__init__("当前库里缺少可满足需求的模块")


CAPABILITY_CANDIDATES = {
    "light": ["ws2812_led_ring", "single_led"],
    "sound": ["active_buzzer"],
    "display": ["oled_ssd1306"],
    "temperature_humidity": ["dht22"],
    "soil_moisture": ["soil_moisture_sensor"],
    "button": ["push_button"],
    "actuator": ["relay_module"],
}


MODULE_ORDER = {
    "push_button": 10,
    "ws2812_led_ring": 20,
    "single_led": 21,
    "active_buzzer": 30,
    "oled_ssd1306": 40,
    "dht22": 50,
    "soil_moisture_sensor": 60,
    "relay_module": 70,
}


MODULE_INSTANCE_ID = {
    "push_button": "btn1",
    "ws2812_led_ring": "led1",
    "single_led": "led1",
    "active_buzzer": "buzz1",
    "oled_ssd1306": "oled1",
    "dht22": "sensor1",
    "soil_moisture_sensor": "sensor1",
    "relay_module": "relay1",
}


def select_modules(spec: dict[str, Any]) -> dict[str, Any]:
    board = get_board(DEFAULT_BOARD_ID)
    if not board:
        raise MissingComponentsError(["board:esp32_devkit_v1"])

    modules_index = get_modules_index()
    selected_ids: list[str] = []
    missing_capabilities: list[str] = []

    if spec.get("trigger") == "button":
        _append_module("button", selected_ids, missing_capabilities, modules_index)

    if spec.get("needs_light"):
        _append_module("light", selected_ids, missing_capabilities, modules_index)

    if spec.get("needs_sound"):
        _append_module("sound", selected_ids, missing_capabilities, modules_index)

    if spec.get("needs_display"):
        _append_module("display", selected_ids, missing_capabilities, modules_index)

    if spec.get("needs_sensor"):
        sensor_type = _normalize_sensor_type(spec.get("sensor_type"))
        if sensor_type == "temperature_humidity":
            _append_module("temperature_humidity", selected_ids, missing_capabilities, modules_index)
        elif sensor_type == "soil_moisture":
            _append_module("soil_moisture", selected_ids, missing_capabilities, modules_index)
        elif sensor_type:
            missing_capabilities.append(sensor_type)
        else:
            missing_capabilities.append("sensor")

    if _needs_relay_for_spec(spec):
        _append_module("actuator", selected_ids, missing_capabilities, modules_index)

    missing_capabilities.extend(_infer_explicit_missing_capabilities(spec))

    if missing_capabilities:
        raise MissingComponentsError(_dedupe(missing_capabilities))

    selected_modules = [
        {
            **modules_index[module_id],
            "instance_id": MODULE_INSTANCE_ID.get(module_id, f"module{index + 1}"),
        }
        for index, module_id in enumerate(sorted(selected_ids, key=lambda item: MODULE_ORDER.get(item, 999)))
    ]

    return {
        "board": board,
        "selected_modules": selected_modules,
        "selection_summary": {
            "board_id": board["id"],
            "module_ids": [module["id"] for module in selected_modules],
        },
    }


def _append_module(
    capability: str,
    selected_ids: list[str],
    missing_capabilities: list[str],
    modules_index: dict[str, dict[str, Any]],
) -> None:
    module = _find_best_candidate(capability, modules_index)
    if not module:
        missing_capabilities.append(capability)
        return
    if module["id"] not in selected_ids:
        selected_ids.append(module["id"])


def _find_best_candidate(capability: str, modules_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for module_id in CAPABILITY_CANDIDATES.get(capability, []):
        module = modules_index.get(module_id)
        if module:
            return module
    return None


def _normalize_sensor_type(sensor_type: str | None) -> str | None:
    if not sensor_type:
        return None
    mapping = {
        "temperature": "temperature_humidity",
        "temperature_humidity": "temperature_humidity",
        "humidity": "temperature_humidity",
        "temp_humidity": "temperature_humidity",
        "soil": "soil_moisture",
        "soil_moisture": "soil_moisture",
        "camera": "camera_vision",
        "vision": "camera_vision",
    }
    return mapping.get(sensor_type, sensor_type)


def _needs_relay_for_spec(spec: dict[str, Any]) -> bool:
    if spec.get("needs_actuator"):
        return True

    actuator_type = str(spec.get("actuator_type") or "").lower()
    if actuator_type in {"pump", "water_pump", "relay"}:
        return True

    notes = " ".join(
        str(spec.get(key) or "")
        for key in ["object", "extra_notes", "user_goal", "actuator"]
    ).lower()
    return any(keyword in notes for keyword in ["浇水", "水泵", "pump", "relay", "actuator"])


def _infer_explicit_missing_capabilities(spec: dict[str, Any]) -> list[str]:
    text = " ".join(str(spec.get(key) or "") for key in ["object", "extra_notes", "user_goal"]).lower()
    missing: list[str] = []
    if any(token in text for token in ["震动", "振动", "vibration", "haptic"]):
        missing.append("vibration_feedback")
    if any(token in text for token in ["摄像头", "camera", "视觉识别", "image recognition", "vision"]):
        missing.append("camera_vision")
    return missing


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
