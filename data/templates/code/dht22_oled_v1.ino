// hw-kai template: dht22_oled_v1
// DHT22 温湿度传感器 + OLED 显示
// 每 2 秒读取一次温湿度，显示在 OLED 屏幕上
// 自动生成，请勿手动修改参数行

#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// === 参数区（由 agent 填充）===
#define DHT_PIN     {{DHT_PIN}}
#define DHT_TYPE    DHT22
#define OLED_SDA    {{OLED_SDA}}
#define OLED_SCL    {{OLED_SCL}}

// === OLED 配置 ===
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1

DHT dht(DHT_PIN, DHT_TYPE);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(115200);
  dht.begin();

  // 初始化 I2C
  Wire.begin(OLED_SDA, OLED_SCL);

  // 初始化 OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED 初始化失败");
    while (true); // 卡住等待检查硬件
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("KAI Hardware");
  display.println("正在初始化...");
  display.display();
  delay(2000);
}

void loop() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // 摄氏度

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("读取 DHT22 失败，请检查接线");
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("传感器错误!");
    display.println("检查 DHT22 接线");
    display.display();
    delay(2000);
    return;
  }

  // 在 OLED 上显示
  display.clearDisplay();

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("=== KAI 气象站 ===");

  display.setTextSize(2);
  display.setCursor(0, 20);
  display.print("T:");
  display.print(temperature, 1);
  display.println(" C");

  display.setCursor(0, 42);
  display.print("H:");
  display.print(humidity, 1);
  display.println(" %");

  display.display();

  // 串口也输出方便调试
  Serial.printf("温度: %.1f°C  湿度: %.1f%%\n", temperature, humidity);

  delay(2000); // 每 2 秒更新一次
}
