// hw-kai template: soil_moisture_sensor_only_v1
// 只读取土壤湿度传感器，不控制执行器

#define SOIL_SENSOR_PIN {{SOIL_SENSOR_PIN}}

void setup() {
  Serial.begin(115200);
  Serial.println("Soil moisture monitor ready");
}

void loop() {
  int rawValue = analogRead(SOIL_SENSOR_PIN);
  int moisturePercent = map(rawValue, 4095, 0, 0, 100);

  Serial.printf("土壤湿度: %d%% (ADC: %d)\n", moisturePercent, rawValue);
  delay(1000);
}
