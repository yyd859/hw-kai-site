// hw-kai template: ir_remote_led_v1
// 红外遥控器控制单色 LED 开关
// 按下遥控器任意有效按键，即可切换 LED 亮灭状态
// 自动生成，请勿手动修改参数行

#include <IRremote.hpp>

// === 参数区（由 agent 填充）===
#define LED_PIN         {{LED_PIN}}
#define IR_RECEIVER_PIN {{IR_RECEIVER_PIN}}

bool ledOn = false;
unsigned long lastToggleAt = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // 启动红外接收
  IrReceiver.begin(IR_RECEIVER_PIN, DISABLE_LED_FEEDBACK);
  Serial.println("红外遥控 LED 启动，按下遥控器任意按键即可切换 LED");
}

void loop() {
  if (!IrReceiver.decode()) {
    delay(10);
    return;
  }

  // 读取到任意有效红外码后切换 LED
  unsigned long now = millis();
  if (now - lastToggleAt > 250) {
    ledOn = !ledOn;
    digitalWrite(LED_PIN, ledOn ? HIGH : LOW);

    Serial.print("收到红外信号，LED 状态切换为: ");
    Serial.println(ledOn ? "ON" : "OFF");
    Serial.print("协议: ");
    Serial.println(getProtocolString(IrReceiver.decodedIRData.protocol));
    Serial.print("命令值: 0x");
    Serial.println(IrReceiver.decodedIRData.command, HEX);

    lastToggleAt = now;
  }

  // 准备接收下一次按键
  IrReceiver.resume();
}
