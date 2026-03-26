// hw-kai template: auto_blink_v1
// 单色 LED 自动闪烁
// 自动生成，请勿手动修改参数行

// === 参数区（由 agent 填充）===
#define LED_PIN {{LED_PIN}}

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);
}
