import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import get_code_template, get_wiring_template


def generate_output(recipe: dict) -> dict:
    """根据 recipe 生成完整输出包"""
    
    ROLE_TO_KEY = {
        "light":            "LED_PIN",
        "sound":            "BUZZER_PIN",
        "trigger":          "BUTTON_PIN",
        "temp_humidity":    "DHT_PIN",
        "display_sda":      "OLED_SDA",
        "display_scl":      "OLED_SCL",
        "ultrasonic_trig":  "TRIG_PIN",
        "ultrasonic_echo":  "ECHO_PIN",
        "soil_sensor":      "SOIL_SENSOR_PIN",
        "relay":            "RELAY_PIN",
        "status_led":       "LED_PIN",
        "remote_receiver":  "IR_RECEIVER_PIN",
        "rfid_sda":         "RFID_SDA_PIN",
        "status_led_ok":    "LED_GREEN_PIN",
        "status_led_deny":  "LED_RED_PIN",
    }

    pin_params = {}
    for module in recipe["modules"]:
        role = module["role"]
        key = ROLE_TO_KEY.get(role, f"{role.upper()}_PIN")
        pin_params[key] = module["pin"]
        if module.get("type") == "mfrc522_rfid":
            if "pin_rst" in module:
                pin_params["RFID_RST_PIN"] = module["pin_rst"]
        if "pin2" in module and "role2" in module:
            key2 = ROLE_TO_KEY.get(module["role2"], f"{module['role2'].upper()}_PIN")
            pin_params[key2] = module["pin2"]
    
    code = get_code_template(recipe["code_template"])
    for key, value in pin_params.items():
        code = code.replace(f"{{{{{key}}}}}", str(value))
    
    wiring_tpl = get_wiring_template(recipe["wiring_template"])
    wiring = []
    for conn in wiring_tpl["connections"]:
        from_pin = conn["from"]
        to_pin = conn["to"]
        for key, value in pin_params.items():
            from_pin = from_pin.replace(f"{{{{{key}}}}}", str(value))
            to_pin = to_pin.replace(f"{{{{{key}}}}}", str(value))
        wiring.append({"from": from_pin, "to": to_pin, "note": conn["note"]})
    
    bom = recipe["bom"]
    bom_total = sum(item["qty"] * item["unit_price_cny"] for item in bom)
    
    instructions = _generate_instructions(recipe)
    
    return {
        "recipe_id": recipe["id"],
        "recipe_label": recipe["label"],
        "board": recipe["board"],
        "bom": bom,
        "bom_total_cny": round(bom_total, 2),
        "wiring": wiring,
        "wiring_notes": wiring_tpl.get("notes", []),
        "code": code,
        "instructions": instructions,
    }


def _generate_instructions(recipe: dict) -> dict:
    intent_match = recipe.get("intent_match", {})
    trigger = intent_match.get("trigger")
    module_types = {module.get("type", "") for module in recipe.get("modules", [])}

    if not trigger:
        if intent_match.get("needs_sensor") or intent_match.get("needs_actuator"):
            trigger = "auto"
        else:
            trigger = "button"

    test_step = "上传成功后，按下按钮测试功能"
    if trigger == "auto":
        test_step = "上传成功后，观察设备是否自动运行"
    elif trigger == "remote":
        test_step = "上传成功后，用红外遥控器对准接收头按任意有效按键测试 LED 开关"
    elif trigger == "rfid":
        test_step = "上传成功后，打开串口监视器（115200）→ 刷卡获取 UID → 复制到代码白名单后重新上传 → 再次刷卡验证绿灯亮起"
    elif trigger == "bluetooth":
        test_step = "上传成功后，手机蓝牙搜索「HW-KAI LED」→ 配对 → 在蓝牙串口 APP 中发送 ON 开灯、OFF 关灯"

    upload_steps = [
        "安装 Arduino IDE（https://www.arduino.cc/en/software）",
        "在 Arduino IDE 中安装 ESP32 开发板包：工具 → 开发板 → 开发板管理器 → 搜索 esp32",
    ]
    if any("ws2812" in t for t in module_types):
        upload_steps.append("安装库：工具 → 管理库 → 搜索 Adafruit NeoPixel")
    if any("ir" in t for t in module_types):
        upload_steps.append("安装库：工具 → 管理库 → 搜索 IRremote")
    if any("mfrc522" in t for t in module_types):
        upload_steps.append("安装库：工具 → 管理库 → 搜索 MFRC522（作者 GithubCommunity）")
    upload_steps.extend([
        "选择开发板：工具 → 开发板 → ESP32 Arduino → ESP32 Dev Module",
        "连接 USB，选择对应串口",
        "点击上传按钮（→）",
    ])

    return {
        "prepare": [
            f"准备好以下元件：{', '.join(item['item'] for item in recipe['bom'])}",
            "确保有 USB 数据线（带数据传输功能，非仅充电线）",
        ],
        "wire": [
            "按照接线表连接元件，建议先接 GND 地线",
            "再接 VCC 电源线",
            "最后接信号线",
            "仔细检查无短路后再通电",
        ],
        "upload": upload_steps,
        "test": [
            test_step,
            "如果没有反应，检查接线是否正确",
            "如果报错，检查串口是否选择正确",
        ],
    }
