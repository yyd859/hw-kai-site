// hw-kai template: soil_moisture_v1
// 土壤湿度监测 + 自动控制水泵（继电器）
// 湿度低于阈值时自动开泵浇水
// 自动生成，请勿手动修改参数行

// === 参数区（由 agent 填充）===
#define SOIL_SENSOR_PIN {{SOIL_SENSOR_PIN}}  // 模拟输入，接土壤湿度传感器 AO 端
#define RELAY_PIN       {{RELAY_PIN}}         // 继电器控制引脚（控制水泵）
#define LED_PIN         {{LED_PIN}}           // 状态 LED（可选，接内置 LED 或外接）

// === 湿度阈值（ADC 值，0=最湿，4095=最干，ESP32 12bit ADC）===
#define DRY_THRESHOLD   2500  // 超过此值认为土壤干燥，需要浇水
#define WET_THRESHOLD   1500  // 低于此值认为足够湿润，停止浇水

// === 浇水时长限制（防止一直开泵）===
#define WATER_DURATION_MS 5000  // 每次最多浇水 5 秒

// 状态变量
bool isWatering = false;
unsigned long waterStartTime = 0;

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // 继电器默认断开（高电平=断开，低电平=闭合）
  digitalWrite(LED_PIN, LOW);
  Serial.println("土壤湿度监测启动");
}

void loop() {
  int rawValue = analogRead(SOIL_SENSOR_PIN);
  int moisturePercent = map(rawValue, 4095, 0, 0, 100); // 转换为百分比（0=干，100=湿）

  Serial.printf("土壤湿度: %d%% (ADC原始值: %d)\n", moisturePercent, rawValue);

  // 浇水超时保护
  if (isWatering && (millis() - waterStartTime > WATER_DURATION_MS)) {
    stopWatering();
    Serial.println("浇水超时，自动停止");
  }

  // 判断是否需要浇水
  if (!isWatering && rawValue > DRY_THRESHOLD) {
    // 土壤干燥，开始浇水
    startWatering();
    Serial.println("⚠️ 土壤干燥，开始浇水");
  } else if (isWatering && rawValue < WET_THRESHOLD) {
    // 已经足够湿润，停止浇水
    stopWatering();
    Serial.println("✅ 土壤已湿润，停止浇水");
  }

  delay(1000); // 每秒检测一次
}

void startWatering() {
  isWatering = true;
  waterStartTime = millis();
  digitalWrite(RELAY_PIN, LOW);  // 低电平闭合继电器，开泵
  digitalWrite(LED_PIN, HIGH);   // LED 亮表示正在浇水
}

void stopWatering() {
  isWatering = false;
  digitalWrite(RELAY_PIN, HIGH); // 高电平断开继电器，停泵
  digitalWrite(LED_PIN, LOW);    // LED 灭
}
