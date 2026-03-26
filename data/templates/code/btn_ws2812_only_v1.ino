// hw-kai template: btn_ws2812_only_v1
// 按钮按下 → WS2812 LED Ring 亮起；松开后熄灭

#include <Adafruit_NeoPixel.h>

#define LED_PIN     {{LED_PIN}}
#define LED_COUNT   8
#define BUTTON_PIN  {{BUTTON_PIN}}

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  strip.begin();
  strip.clear();
  strip.show();
}

void loop() {
  bool pressed = digitalRead(BUTTON_PIN) == LOW;

  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, pressed ? strip.Color(255, 255, 255) : strip.Color(0, 0, 0));
  }
  strip.show();
  delay(10);
}
