# HW-KAI Hardware Library

这个目录是 hw-kai agent 的**硬件零件库**。

它回答的问题是：**"有什么可以用"**。

Recipe（方案）由 agent 根据用户需求从这个库里选零件组合，库本身不包含 recipe。

---

## 目录结构

```
library/
├── boards/     # 主控板
│   └── esp32_devkit_v1.json
├── modules/    # 功能模块
│   ├── ws2812_led_ring.json
│   ├── push_button.json
│   ├── active_buzzer.json
│   ├── dht22.json
│   ├── oled_ssd1306.json
│   ├── soil_moisture_sensor.json
│   └── relay_module.json
└── README.md
```

---

## 文件格式规范

### Board（主控板）

```json
{
  "id": "唯一标识符",
  "label": "显示名称",
  "category": "board",
  "provides": ["能力列表"],
  "gpio": { ... },
  "specs": { ... },
  "notes": ["注意事项"],
  "price_cny": { "min": 0, "max": 0, "typical": 0 }
}
```

### Module（功能模块）

```json
{
  "id": "唯一标识符",
  "label": "显示名称",
  "category": "input | output",
  "subcategory": "sensor | light | sound | display | actuator ...",
  "provides": ["能力列表"],
  "interface": "接口类型",
  "pin_spec": { "引脚名": { "type": "类型", "note": "说明" } },
  "compatible_boards": ["兼容的板子 id"],
  "notes": ["注意事项"],
  "price_cny": { "min": 0, "max": 0, "typical": 0 }
}
```

---

## 当前库存

### 主控板
| ID | 名称 | 关键能力 |
|---|---|---|
| esp32_devkit_v1 | ESP32 DevKit V1 | WiFi, BLE, PWM, I2C, ADC |

### 功能模块
| ID | 名称 | 类型 | 能力 |
|---|---|---|---|
| ws2812_led_ring | WS2812 RGB LED Ring | output/light | 彩色灯光、动画 |
| push_button | 轻触按钮 | input | 按键触发 |
| active_buzzer | 有源蜂鸣器 | output/sound | 蜂鸣、报警 |
| dht22 | DHT22 温湿度传感器 | input/sensor | 温度、湿度 |
| oled_ssd1306 | OLED 显示屏 0.96寸 | output/display | 文字、图形显示 |
| soil_moisture_sensor | 土壤湿度传感器 | input/sensor | 土壤含水量 |
| relay_module | 继电器模块 | output/actuator | 控制水泵、强电 |
