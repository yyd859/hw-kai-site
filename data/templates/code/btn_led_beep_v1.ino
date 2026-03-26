// hw-kai template: btn_led_beep_v1
// 按钮按下 → WS2812 LED 亮 + 有源蜂鸣器响
// 自动生成，请勿手动修改参数行

#include <Adafruit_NeoPixel.h>

// === 参数区（由 agent 填充）===
#define LED_PIN     {{LED_PIN}}
#define LED_COUNT   8
#define BUZZER_PIN  {{BUZZER_PIN}}
#define BUTTON_PIN  {{BUTTON_PIN}}

// === 初始化 ===
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  strip.begin();
  strip.show(); // 初始全灭
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) { // 按钮按下（低电平）
    // LED 全亮白色
    for (int i = 0; i < LED_COUNT; i++) {
      strip.setPixelColor(i, strip.Color(255, 255, 255));
    }
    strip.show();

    // 蜂鸣器响 200ms
    digitalWrite(BUZZER_PIN, HIGH);
    delay(200);
    digitalWrite(BUZZER_PIN, LOW);

    // 等待按钮松开
    while (digitalRead(BUTTON_PIN) == LOW) delay(10);

    // LED 全灭
    strip.clear();
    strip.show();
  }
  delay(10);
}
