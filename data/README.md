# /data 目录说明

hw-kai agent 的核心数据层，定义模块能力、方案库和输入输出格式。

## 文件结构

```
data/
├── capability_registry.json   # 硬件模块能力注册表（GPIO、电源、约束等）
├── recipe_library.json        # 固定方案库（每个 recipe 是完整可执行方案）
├── intent_schema.json         # Intent 解析的标准输出格式（LLM 填充用）
├── output_schema.json         # Agent 最终输出的标准格式
└── templates/
    ├── code/                  # Arduino 代码模板（.ino）
    │   └── btn_led_beep_v1.ino
    └── wiring/                # 接线模板（.json）
        └── btn_led_beep_v1.json
```

## 各文件用途

| 文件 | 用途 |
|------|------|
| `capability_registry.json` | 定义每种硬件模块的引脚规范、兼容板卡、约束条件 |
| `recipe_library.json` | 预定义完整方案，含模块列表、BOM、模板引用 |
| `intent_schema.json` | LLM 解析用户输入后输出的结构化格式定义 |
| `output_schema.json` | Agent 生成最终结果的标准数据结构 |
| `templates/code/` | 可参数化的 Arduino 代码模板，`{{PARAM}}` 由 agent 替换 |
| `templates/wiring/` | 可参数化的接线说明模板 |

## 版本

当前 schema 版本：`0.1.0`
