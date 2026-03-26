from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import get_code_template

ROLE_TO_PIN_TEMPLATE_KEY = {
    "push_button": {"PIN1": "BUTTON_PIN"},
    "ws2812_led_ring": {"DIN": "LED_PIN"},
    "single_led": {"SIG": "LED_PIN"},
    "active_buzzer": {"SIG": "BUZZER_PIN"},
    "dht22": {"DATA": "DHT_PIN"},
    "oled_ssd1306": {"SDA": "OLED_SDA", "SCL": "OLED_SCL"},
    "soil_moisture_sensor": {"AO": "SOIL_SENSOR_PIN"},
    "relay_module": {"IN": "RELAY_PIN"},
}

SUPPORTED_COMBOS = {
    frozenset(["push_button", "ws2812_led_ring"]): "button_light",
    frozenset(["push_button", "ws2812_led_ring", "active_buzzer"]): "button_light_sound",
    frozenset(["dht22", "oled_ssd1306"]): "temp_display",
    frozenset(["soil_moisture_sensor"]): "soil_only",
    frozenset(["soil_moisture_sensor", "relay_module"]): "soil_relay",
}


class GenerationNotSupportedError(Exception):
    def __init__(self, module_ids: list[str]):
        self.module_ids = module_ids
        self.error_type = "generation_not_supported_yet"
        super().__init__("当前组合还没有可用代码模板")


def generate_output(
    board: dict[str, Any],
    selected_modules: list[dict[str, Any]],
    hardware_plan: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    combo_key = _resolve_combo_key(selected_modules)
    if combo_key not in SUPPORTED_COMBOS.values():
        raise GenerationNotSupportedError([module["id"] for module in selected_modules])

    selected_module_ids = [module["id"] for module in selected_modules]
    bom = _build_bom(board, selected_modules)
    bom_total = round(sum(item["qty"] * item["unit_price_cny"] for item in bom), 2)
    wiring = _build_wiring(board, hardware_plan)
    code = _build_code(combo_key, hardware_plan)
    instructions = _build_instructions(combo_key, board, selected_modules)

    return {
        "recipe_label": _build_plan_label(combo_key),
        "board": board,
        "selected_modules": selected_modules,
        "hardware_plan": hardware_plan,
        "bom": bom,
        "bom_total_cny": bom_total,
        "wiring": wiring,
        "code": code,
        "instructions": instructions,
        "validation": {
            "passed": True,
            "warnings": _build_warnings(combo_key, selected_modules, spec),
            "errors": [],
        },
        "meta": {
            "combo": combo_key,
            "selected_module_ids": selected_module_ids,
        },
    }


def _resolve_combo_key(selected_modules: list[dict[str, Any]]) -> str:
    module_ids = frozenset(module["id"] for module in selected_modules)
    combo_key = SUPPORTED_COMBOS.get(module_ids)
    if not combo_key:
        raise GenerationNotSupportedError(sorted(module_ids))
    return combo_key


def _build_bom(board: dict[str, Any], selected_modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [_bom_item(board, qty=1)]
    items.extend(_bom_item(module, qty=1) for module in selected_modules)
    return items


def _bom_item(item: dict[str, Any], qty: int) -> dict[str, Any]:
    price = item.get("price_cny", {})
    return {
        "name": item.get("label") or item.get("id"),
        "component": item.get("id"),
        "qty": qty,
        "unit_price_cny": price.get("typical", 0),
        "note": item.get("description", ""),
    }


def _build_wiring(board: dict[str, Any], hardware_plan: dict[str, Any]) -> list[dict[str, Any]]:
    board_label = board.get("label", board.get("id", "Board"))
    wiring: list[dict[str, Any]] = []

    for module in hardware_plan.get("modules", []):
        module_type = module["type"]
        module_label = module.get("label", module_type)
        module_meta = module.get("meta", {})
        pin_spec = module_meta.get("pin_spec", {})
        assigned = module.get("pins", {})

        for pin_name, gpio in assigned.items():
            note = pin_spec.get(pin_name, {}).get("note", "")
            wiring.append(
                {
                    "from": f"{board_label}.GPIO{gpio}",
                    "to": f"{module_label}.{pin_name}",
                    "note": note,
                }
            )

        for power_pin in ["VCC", "PIN2", "GND"]:
            if power_pin not in pin_spec:
                continue
            target = f"{module_label}.{power_pin}"
            if power_pin == "VCC":
                voltage = str(pin_spec[power_pin].get("voltage") or "")
                board_pin = "5V" if "5" in voltage else "3.3V"
                wiring.append({"from": f"{board_label}.{board_pin}", "to": target, "note": pin_spec[power_pin].get("note", "")})
            elif power_pin == "PIN2":
                wiring.append({"from": f"{board_label}.GND", "to": target, "note": pin_spec[power_pin].get("note", "")})
            elif power_pin == "GND":
                wiring.append({"from": f"{board_label}.GND", "to": target, "note": pin_spec[power_pin].get("note", "")})

        if module_type == "relay_module":
            wiring.extend(
                [
                    {"from": "外部电源正极", "to": f"{module_label}.NO", "note": "常开端接外部负载电源正极"},
                    {"from": f"{module_label}.COM", "to": "执行器/水泵正极", "note": "继电器吸合时给负载供电"},
                    {"from": "执行器/水泵负极", "to": "外部电源负极", "note": "负载负极回到外部电源"},
                ]
            )

    return wiring


def _build_code(combo_key: str, hardware_plan: dict[str, Any]) -> str:
    pin_params = _build_pin_params(hardware_plan)

    if combo_key == "button_light":
        return _render_template("btn_ws2812_only_v1", pin_params)
    if combo_key == "button_light_sound":
        return _render_template("btn_led_beep_v1", pin_params)
    if combo_key == "temp_display":
        return _render_template("dht22_oled_v1", pin_params)
    if combo_key == "soil_relay":
        return _render_template("soil_moisture_v1", {**pin_params, "LED_PIN": 2})
    if combo_key == "soil_only":
        return _render_template("soil_moisture_sensor_only_v1", pin_params)

    raise GenerationNotSupportedError(sorted(module["type"] for module in hardware_plan.get("modules", [])))


def _render_template(template_id: str, params: dict[str, Any]) -> str:
    code = get_code_template(template_id)
    for key, value in params.items():
        code = code.replace(f"{{{{{key}}}}}", str(value))
    return code


def _build_pin_params(hardware_plan: dict[str, Any]) -> dict[str, Any]:
    pin_params: dict[str, Any] = {}
    for module in hardware_plan.get("modules", []):
        mapping = ROLE_TO_PIN_TEMPLATE_KEY.get(module["type"], {})
        for pin_name, gpio in module.get("pins", {}).items():
            template_key = mapping.get(pin_name)
            if template_key:
                pin_params[template_key] = gpio
    return pin_params


def _build_instructions(combo_key: str, board: dict[str, Any], selected_modules: list[dict[str, Any]]) -> dict[str, Any]:
    libraries = [
        module.get("library_required")
        for module in selected_modules
        if module.get("library_required") and module.get("library_required") != "无"
    ]

    upload_steps = [
        "安装 Arduino IDE。",
        "在开发板管理器安装 ESP32 开发板包。",
        f"选择开发板：{board.get('label', 'ESP32 Dev Module')}。",
        "连接 USB 数据线并选择对应串口。",
    ]
    upload_steps.extend([f"安装依赖库：{item}" for item in libraries])
    upload_steps.append("复制生成代码到 Arduino IDE，点击上传。")

    assembly_map = {
        "button_light": [
            "把 WS2812 LED Ring 的 DIN 接到 GPIO5，VCC 接 5V，GND 接 GND。",
            "把按钮一侧接 GPIO12，另一侧接 GND，软件使用内部上拉。",
            "确认共地后再上电。",
        ],
        "button_light_sound": [
            "连接 WS2812 LED Ring：DIN→GPIO5，VCC→5V，GND→GND。",
            "连接有源蜂鸣器：SIG→GPIO18，VCC→5V/3.3V，GND→GND。",
            "连接按钮：PIN1→GPIO12，PIN2→GND。",
        ],
        "temp_display": [
            "连接 DHT22：DATA→GPIO4，VCC→3.3V，GND→GND，并给 DATA 加上拉。",
            "连接 OLED：SDA→GPIO21，SCL→GPIO22，VCC→3.3V，GND→GND。",
            "确认 I2C 地址通常为 0x3C。",
        ],
        "soil_only": [
            "连接土壤湿度传感器：AO→GPIO34，VCC→3.3V，GND→GND。",
            "把探头插入土壤后先读取串口数值，记录干湿参考值。",
        ],
        "soil_relay": [
            "连接土壤湿度传感器：AO→GPIO34，VCC→3.3V，GND→GND。",
            "连接继电器：IN→GPIO19，VCC→5V，GND→GND。",
            "把水泵电源正极串到继电器 NO/COM，使用独立电源并与 ESP32 共地。",
        ],
    }

    test_map = {
        "button_light": ["按下按钮，灯环点亮；松开后熄灭。"],
        "button_light_sound": ["按下按钮，灯环点亮并蜂鸣 1 次。"],
        "temp_display": ["上电后每 2 秒显示一次温湿度读数。"],
        "soil_only": ["打开串口监视器，查看 ADC 数值和湿度百分比。"],
        "soil_relay": ["把探头放入干土中，观察继电器/水泵是否按阈值动作。"],
    }

    return {
        "assembly": assembly_map.get(combo_key, []),
        "upload": upload_steps,
        "test": test_map.get(combo_key, []),
    }


def _build_plan_label(combo_key: str) -> str:
    labels = {
        "button_light": "按钮触发灯光方案",
        "button_light_sound": "按钮触发灯光+蜂鸣器方案",
        "temp_display": "温湿度显示方案",
        "soil_only": "土壤湿度监测方案",
        "soil_relay": "土壤湿度自动浇水方案",
    }
    return labels.get(combo_key, "硬件方案")


def _build_warnings(combo_key: str, selected_modules: list[dict[str, Any]], spec: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if combo_key in {"button_light", "button_light_sound"}:
        warnings.append("WS2812 建议使用 5V 供电，必要时加 300-500Ω 串联电阻和滤波电容。")
    if combo_key == "temp_display":
        warnings.append("DHT22 采样间隔至少 2 秒，DATA 线建议加 4.7kΩ-10kΩ 上拉。")
    if combo_key in {"soil_only", "soil_relay"}:
        warnings.append("土壤湿度传感器需要先在实际盆栽环境中标定干湿阈值。")
    if combo_key == "soil_relay":
        warnings.append("水泵等执行器必须使用外部供电，不要直接由 ESP32 GPIO 驱动。")
    if spec.get("needs_sound") and not any(module["id"] == "active_buzzer" for module in selected_modules):
        warnings.append("需求包含声音，但当前组合未选到蜂鸣器。")
    return warnings

