// hw-kai template: btn_led_only_v1
// 按钮按下 → 单色 LED 亮起；松开后熄灭
// 自动生成，请勿手动修改参数行

#define LED_PIN     {{LED_PIN}}
#define BUTTON_PIN  {{BUTTON_PIN}}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    digitalWrite(LED_PIN, HIGH);
  } else {
    digitalWrite(LED_PIN, LOW);
  }
  delay(10);
}
