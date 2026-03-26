// hw-kai template: ultrasonic_v1
// HC-SR04 超声波测距，结果通过串口输出并驱动蜂鸣器（近距离报警）
// 自动生成，请勿手动修改参数行

// === 参数区（由 agent 填充）===
#define TRIG_PIN    {{TRIG_PIN}}
#define ECHO_PIN    {{ECHO_PIN}}
#define BUZZER_PIN  {{BUZZER_PIN}}

// === 报警阈值（单位：厘米）===
#define ALERT_DISTANCE_CM 20  // 小于此距离触发蜂鸣器报警

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  Serial.println("HC-SR04 超声波测距启动");
}

float readDistanceCm() {
  // 发送 10µs 触发脉冲
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // 接收回波，计算距离
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 超时 30ms（约 5m）
  if (duration == 0) return -1; // 超时，目标太远或不在范围内

  float distance = duration * 0.034 / 2.0; // 声速 340m/s，来回除以 2
  return distance;
}

void loop() {
  float dist = readDistanceCm();

  if (dist < 0) {
    Serial.println("超出测量范围（> 4m）");
    digitalWrite(BUZZER_PIN, LOW);
  } else {
    Serial.printf("距离: %.1f cm\n", dist);

    // 近距离报警
    if (dist < ALERT_DISTANCE_CM) {
      // 蜂鸣器短促鸣叫
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      delay(100);
    } else {
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  delay(200); // 每 200ms 测一次
}
