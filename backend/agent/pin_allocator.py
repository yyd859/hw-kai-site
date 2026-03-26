from __future__ import annotations

from typing import Any

DEFAULT_PINS = {
    "ws2812_led_ring": {"DIN": 5},
    "single_led": {"SIG": 5},
    "active_buzzer": {"SIG": 18},
    "push_button": {"PIN1": 12},
    "dht22": {"DATA": 4},
    "oled_ssd1306": {"SDA": 21, "SCL": 22},
    "soil_moisture_sensor": {"AO": 34},
    "relay_module": {"IN": 19},
}


class PinAllocationError(Exception):
    pass


def allocate_pins(board: dict[str, Any], selected_modules: list[dict[str, Any]]) -> dict[str, Any]:
    board_id = board["id"]
    allocations: list[dict[str, Any]] = []
    used_pins: dict[int, str] = {}

    for module in selected_modules:
        module_id = module["id"]
        pin_spec = module.get("pin_spec", {})
        desired = dict(DEFAULT_PINS.get(module_id, {}))
        assigned: dict[str, int] = {}

        for pin_name, pin_meta in pin_spec.items():
            if pin_name in {"VCC", "GND", "PIN2", "COM", "NO", "NC"}:
                continue
            pin_number = desired.get(pin_name)
            if pin_number is None:
                continue
            _assert_pin_available(board, pin_number, pin_meta, used_pins, module_id, pin_name)
            used_pins[pin_number] = f"{module_id}.{pin_name}"
            assigned[pin_name] = pin_number

        allocations.append(
            {
                "id": module.get("instance_id") or module_id,
                "type": module_id,
                "label": module.get("label", module_id),
                "pins": assigned,
                "interface": module.get("interface"),
                "meta": module,
            }
        )

    return {
        "board": board_id,
        "board_meta": board,
        "modules": allocations,
    }


def _assert_pin_available(
    board: dict[str, Any],
    pin_number: int,
    pin_meta: dict[str, Any],
    used_pins: dict[int, str],
    module_id: str,
    pin_name: str,
) -> None:
    if pin_number in used_pins:
        raise PinAllocationError(f"GPIO{pin_number} 已被 {used_pins[pin_number]} 占用，无法分配给 {module_id}.{pin_name}")

    gpio = board.get("gpio", {})
    pin_type = str(pin_meta.get("type") or "")
    is_analog = "analog" in pin_type
    is_input_only = pin_number in set(gpio.get("input_only", []))
    adc_pins = set(gpio.get("adc", []))
    digital_io = set(gpio.get("digital_io", [])) | set(gpio.get("input_only", []))

    if is_analog and pin_number not in adc_pins:
        raise PinAllocationError(f"GPIO{pin_number} 不是 {module_id}.{pin_name} 可用的 ADC 引脚")

    if not is_analog and pin_number not in digital_io:
        raise PinAllocationError(f"GPIO{pin_number} 不在开发板可用 GPIO 范围内")

    needs_output_capability = any(token in pin_type for token in ["digital_output", "pwm_output", "clock_output", "serial_output"])
    if needs_output_capability and is_input_only and "input_output" not in pin_type:
        raise PinAllocationError(f"GPIO{pin_number} 是仅输入引脚，不能分配给 {module_id}.{pin_name}")
