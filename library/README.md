# HW-KAI Hardware Library

这个目录是 hw-kai agent 的硬件零件库。

Agent 规划方案时从这里查"有什么可以用"，不包含方案（recipe）。

## 目录结构

```
library/
├── boards/    # 开发板（ESP32、Arduino 等）
└── modules/   # 功能模块（传感器、执行器、显示等）
```

## 当前收录

### Boards
- `esp32_devkit_v1` — ESP32 DevKit V1

### Modules
- `ws2812_led_ring` — WS2812 RGB LED Ring（多规格）
- `push_button` — 轻触按钮
- `active_buzzer` — 有源蜂鸣器
- `dht22` — DHT22 温湿度传感器
- `oled_ssd1306` — OLED 显示屏 0.96寸 SSD1306

## 字段规范

每个模块至少包含：
- `id` — 唯一标识符
- `label` — 人类可读名称
- `category` — board / input / output
- `provides` — 能力列表（agent 用来匹配用户需求）
- `pin_spec` — 引脚规范
- `compatible_boards` — 兼容的板子
- `notes` — 注意事项
- `price_cny` — 价格参考
