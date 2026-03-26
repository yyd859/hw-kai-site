// hw-kai template: rfid_access_v1
// RFID 刷卡门禁系统
// 白名单卡片：绿灯亮 + 蜂鸣 1 声 + 继电器解锁 3 秒（模拟开门）
// 陌生卡片：红灯亮 + 蜂鸣长鸣 + 拒绝
// 自动生成，请勿手动修改参数行

#include <SPI.h>
#include <MFRC522.h>

// === 参数区（由 agent 填充）===
#define RFID_SDA_PIN  {{RFID_SDA_PIN}}
#define RFID_RST_PIN  {{RFID_RST_PIN}}
#define RELAY_PIN     {{RELAY_PIN}}
#define LED_GREEN_PIN {{LED_GREEN_PIN}}
#define LED_RED_PIN   {{LED_RED_PIN}}
#define BUZZER_PIN      {{BUZZER_PIN}}

// === 白名单 UID 列表（十六进制，每张卡一项）===
// 首次运行时打开串口监视器，刷卡后会打印 UID，复制到此处
const char* WHITELIST[] = {
  "DE AD BE EF",   // 示例：请替换为你自己的卡 UID
};
const int WHITELIST_SIZE = sizeof(WHITELIST) / sizeof(WHITELIST[0]);

MFRC522 rfid(RFID_SDA_PIN, RFID_RST_PIN);

// 格式化 UID 为带空格的字符串，便于与白名单比对
String formatUID(MFRC522::Uid &uid) {
  String s = "";
  for (byte i = 0; i < uid.size; i++) {
    if (i > 0) s += " ";
    if (uid.uidByte[i] < 0x10) s += "0";
    s += String(uid.uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

// 判断 UID 是否在白名单中
bool isAuthorized(String uid) {
  for (int i = 0; i < WHITELIST_SIZE; i++) {
    if (uid == String(WHITELIST[i])) return true;
  }
  return false;
}

void grantAccess() {
  Serial.println("✅ 授权通过，开门 3 秒");
  // 绿灯亮 + 蜂鸣 1 声 + 继电器解锁
  digitalWrite(LED_GREEN_PIN, HIGH);
  digitalWrite(RELAY_PIN, LOW);  // 低电平触发继电器（常见模块）
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  delay(2800);
  // 恢复
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(RELAY_PIN, HIGH);
}

void denyAccess() {
  Serial.println("❌ 拒绝访问：陌生卡");
  // 红灯 + 蜂鸣 3 声
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_RED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(200);
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    delay(150);
  }
}

void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // 初始状态：继电器锁门（高电平 = 不触发）
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("RFID 门禁已就绪，请刷卡...");
  Serial.print("读卡器固件版本: 0x");
  Serial.println(rfid.PCD_ReadRegister(MFRC522::VersionReg), HEX);
}

void loop() {
  // 等待新卡靠近
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  String uid = formatUID(rfid.uid);
  Serial.print("检测到卡片 UID: ");
  Serial.println(uid);

  if (isAuthorized(uid)) {
    grantAccess();
  } else {
    denyAccess();
  }

  // 停止读卡，准备下一次
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}
