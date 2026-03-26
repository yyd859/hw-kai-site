// hw-kai template: ble_led_v1
// 蓝牙控制 LED
// 使用 ESP32 内置蓝牙（BLE 或经典蓝牙 SPP），手机通过蓝牙串口助手发送:
//   "ON"  → LED 亮
//   "OFF" → LED 灭
//   "TOGGLE" → 切换状态
// 推荐手机 APP：Serial Bluetooth Terminal（Android）或 LightBlue（iOS/Android）
// 自动生成，请勿手动修改参数行

#include "BluetoothSerial.h"

// === 参数区（由 agent 填充）===
#define LED_PIN {{LED_PIN}}

// === 蓝牙名称（可自定义）===
#define BT_NAME "HW-KAI LED"

BluetoothSerial SerialBT;

bool ledState = false;  // 当前 LED 状态

// 更新 LED 并通过蓝牙回显状态
void setLed(bool on) {
  ledState = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
  SerialBT.println(on ? "LED: ON ✅" : "LED: OFF ❌");
  Serial.println(on ? "BT CMD → LED ON" : "BT CMD → LED OFF");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // 初始关灯

  // 启动经典蓝牙（ESP32 内置，无需额外模块）
  SerialBT.begin(BT_NAME);
  Serial.println("蓝牙已就绪，设备名：" + String(BT_NAME));
  Serial.println("请用手机蓝牙配对后，发送 ON / OFF / TOGGLE");
}

void loop() {
  // 读取蓝牙接收到的指令
  if (SerialBT.available()) {
    String cmd = SerialBT.readStringUntil('\n');
    cmd.trim();           // 去掉首尾空白和换行符
    cmd.toUpperCase();    // 统一转大写，兼容小写输入

    if (cmd == "ON") {
      setLed(true);
    } else if (cmd == "OFF") {
      setLed(false);
    } else if (cmd == "TOGGLE") {
      setLed(!ledState);
    } else if (cmd == "STATUS") {
      // 查询当前状态
      SerialBT.println(String("状态：") + (ledState ? "ON" : "OFF"));
    } else {
      // 未知指令，给出提示
      SerialBT.println("⚠️ 未知指令。请发送: ON / OFF / TOGGLE / STATUS");
    }
  }

  // 同时监听串口（方便调试）
  if (Serial.available()) {
    SerialBT.write(Serial.read());
  }
}
