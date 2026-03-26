# HW-KAI Hardware Library

这个目录是 hw-kai agent 的硬件零件库。

Agent 规划方案时从这里查“有什么可以用”，不包含方案（recipe）。

## 目录结构

```
library/
├── boards/                   # 开发板 / MCU / SBC
└── modules/
    ├── *.json               # 早期通用模块
    ├── sensors/             # 传感器
    ├── displays/            # 显示模块
    ├── actuators/           # 执行器 / 灯光 / 泵 / 电磁类
    ├── communication/       # 无线 / 总线 / 通信模块
    ├── power/               # 供电 / 充电 / 电流功率监测
    ├── motor_drivers/       # 电机/舵机驱动
    ├── input_controls/      # 按键 / 键盘 / 编码器 / RFID
    ├── audio/               # 音频播放 / 功放 / 麦克风
    ├── storage/             # 存储 / RTC
    └── robotics/            # 小车 / 云台 / 机器人组件
```

## 当前统计

- Boards: **16**
- Modules: **139**
  - Actuators 执行器: 15
  - Audio 音频: 6
  - Communication 通信: 12
  - Displays 显示: 12
  - Input Controls 输入控件: 12
  - Motor Drivers 电机驱动: 8
  - Power 电源/供电: 12
  - Robotics 机器人组件: 6
  - Sensors 传感器: 44
  - Storage 存储/时钟: 5
- Flat modules (root): **7**
- 总计（不含 README）: **155**

## 完整索引

### Boards (16)
- `arduino_mega_2560` — Arduino Mega 2560
- `arduino_nano` — Arduino Nano
- `arduino_nano_33_iot` — Arduino Nano 33 IoT
- `arduino_uno_r3` — Arduino Uno R3
- `attiny85_digispark` — ATtiny85 Digispark
- `esp32_c3_mini` — ESP32-C3-MINI-1
- `esp32_devkit_v1` — ESP32 DevKit V1
- `esp32_s2_mini` — ESP32-S2 Mini (Wemos)
- `esp32_s3_devkit` — ESP32-S3 DevKit
- `lolin32_lite` — LOLIN32 Lite (ESP32 + 锂电池)
- `nodemcu_esp8266` — NodeMCU ESP8266
- `raspberry_pi_pico` — Raspberry Pi Pico (RP2040)
- `raspberry_pi_pico_w` — Raspberry Pi Pico W
- `seeed_xiao_esp32s3` — Seeed XIAO ESP32S3
- `stm32_bluepill` — STM32F103 Blue Pill
- `wemos_d1_mini` — Wemos D1 Mini (ESP8266)

### Flat Modules (7)
- `active_buzzer` — 有源蜂鸣器（Active Buzzer）
- `dht22` — DHT22 温湿度传感器
- `oled_ssd1306` — OLED 显示屏 SSD1306 (0.96寸)
- `push_button` — 轻触按钮（Momentary Push Button）
- `relay_module` — 继电器模块
- `soil_moisture_sensor` — 土壤湿度传感器
- `ws2812_led_ring` — WS2812 RGB LED Ring

### Sensors 传感器 (44)
- `adxl345` — ADXL345 3轴加速度传感器
- `aht20` — AHT20 温湿度传感器
- `apds9960` — APDS9960 手势+颜色+接近
- `bh1750` — BH1750 数字光照传感器
- `bme280` — BME280 温湿度气压传感器
- `bme680` — BME680 环境传感器
- `ccs811` — CCS811 eCO2+TVOC 传感器
- `dht11` — DHT11 温湿度传感器
- `fingerprint_r307` — R307 指纹传感器
- `flame_sensor` — 火焰传感器
- `force_fsr402` — FSR402 压力传感器
- `gp2y0a21` — GP2Y0A21 红外距离传感器
- `gps_neo6m` — GPS 模块 NEO-6M
- `hall_effect_a3144` — A3144 霍尔效应传感器
- `hc_sr04` — HC-SR04 超声波测距
- `hcsr501_pir` — HC-SR501 PIR 人体红外
- `hx711_load_cell` — HX711 称重传感器模块
- `inmp441_microphone` — INMP441 I2S 数字麦克风
- `ldr_photoresistor` — 光敏电阻 LDR
- `lis3dh` — LIS3DH 低功耗加速度传感器
- `max30102` — MAX30102 心率血氧传感器
- `max4466_microphone` — MAX4466 模拟麦克风放大
- `max9814_microphone` — MAX9814 自动增益麦克风
- `mpr121` — MPR121 12点电容触摸
- `mpu6050` — MPU6050 6轴 IMU
- `mpu9250` — MPU9250 9轴 IMU
- `mq135` — MQ-135 空气质量传感器
- `mq2` — MQ-2 烟雾/可燃气体传感器
- `mq7` — MQ-7 CO 一氧化碳传感器
- `qmc5883l` — QMC5883L 电子罗盘
- `rain_sensor` — 雨滴传感器
- `reed_switch` — 干簧管开关
- `scd40` — SCD40 真实 CO2 传感器
- `sgp30` — SGP30 VOC+CO2 传感器
- `sht31` — SHT31 温湿度传感器
- `soil_moisture_capacitive` — 电容式土壤湿度传感器
- `soil_moisture_resistive` — 电阻式土壤湿度传感器
- `sound_sensor_ky038` — KY-038 声音检测模块
- `tcs34725` — TCS34725 RGB 颜色传感器
- `touch_ttp223` — TTP223 单点电容触摸
- `uv_veml6075` — VEML6075 UV 紫外线传感器
- `veml7700` — VEML7700 高精度光照传感器
- `vl53l0x` — VL53L0X ToF 激光测距
- `water_level_sensor` — 水位传感器

### Displays 显示 (12)
- `dot_matrix_max7219_8x8` — MAX7219 8x8 点阵
- `eink_2_13_ssd1680` — 墨水屏 2.13寸 SSD1680
- `lcd1602_i2c` — LCD1602 I2C 字符屏
- `lcd2004_i2c` — LCD2004 I2C 字符屏
- `oled_sh1106_128x64` — OLED 1.3寸 SH1106
- `oled_ssd1327_128x128` — OLED 1.5寸 SSD1327
- `rgb_lcd1602` — RGB LCD1602
- `seven_segment_max7219_8digit` — MAX7219 八位数码管
- `seven_segment_tm1637` — TM1637 四位数码管
- `tft_ili9341_2_4` — TFT 2.4寸 ILI9341
- `tft_st7735_1_8` — TFT 1.8寸 ST7735
- `tft_st7789_1_9` — TFT 1.9寸 ST7789

### Actuators 执行器 (15)
- `dc_fan_12v` — 12V 直流风扇
- `dc_fan_5v` — 5V 直流风扇
- `laser_module_650nm` — 650nm 红色激光模块
- `linear_actuator_mini` — 迷你线性执行器
- `mini_water_pump_5v` — 5V 微型水泵
- `mist_maker_24v` — 24V 雾化片驱动模块
- `neopixel_stick_8` — NeoPixel Stick 8
- `neopixel_strip_30` — WS2812B 灯带 30LED/m
- `peristaltic_pump_12v` — 12V 蠕动泵
- `servo_mg996r` — MG996R 金属舵机
- `servo_sg90` — SG90 舵机
- `solenoid_lock_12v` — 12V 电磁锁
- `solenoid_push_pull_5v` — 5V 推拉电磁铁
- `stepper_28byj48_uln2003` — 28BYJ-48 步进电机套件
- `vibration_motor_coin` — 纽扣振动马达

### Communication 通信 (12)
- `433mhz_rf_pair` — 433MHz RF 收发对
- `canbus_mcp2515_tja1050` — MCP2515 CAN 模块
- `ethernet_w5500` — W5500 以太网模块
- `hc05_bluetooth` — HC-05 蓝牙串口模块
- `hc06_bluetooth` — HC-06 蓝牙串口模块
- `ir_receiver_vs1838b` — VS1838B 红外接收头
- `nrf24l01` — nRF24L01 2.4G 模块
- `rs485_max485` — MAX485 RS485 模块
- `sim7600_4g` — SIM7600 4G 模块
- `sim800l_gsm` — SIM800L GSM/GPRS 模块
- `sx1276_lora_rfm95` — RFM95 LoRa 模块
- `sx1278_lora_ra02` — SX1278 LoRa RA-02

### Power 电源/供电 (12)
- `18650_holder_single` — 18650 单节电池座
- `acs712_current_sensor_5a` — ACS712 5A 电流传感器
- `boost_mt3608` — MT3608 升压模块
- `buck_lm2596` — LM2596 降压模块
- `buckboost_xl6009` — XL6009 升降压模块
- `ds3231_backup_battery` — DS3231 RTC 电池板
- `ina219_current_monitor` — INA219 电流电压监测
- `ina226_power_monitor` — INA226 功率监测模块
- `ip5306_power_bank` — IP5306 充放电模块
- `mb102_breadboard_power` — MB102 面包板电源模块
- `solar_charger_cn3065` — CN3065 太阳能充电模块
- `tp4056_usb_c` — TP4056 USB-C 锂电充电板

### Motor Drivers 电机驱动 (8)
- `a4988_stepper_driver` — A4988 步进驱动板
- `bts7960_high_power_driver` — BTS7960 大功率驱动
- `drv8825_stepper_driver` — DRV8825 步进驱动板
- `drv8833` — DRV8833 电机驱动
- `l298n_dual_hbridge` — L298N 双路电机驱动
- `pca9685_servo_driver` — PCA9685 16路舵机驱动
- `tb6612fng` — TB6612FNG 电机驱动
- `uln2003_driver_board` — ULN2003 驱动板

### Input Controls 输入控件 (12)
- `barcode_scanner_gm65` — GM65 条码扫描头
- `capacitive_keypad_ttp229` — TTP229 触摸键盘
- `joystick_ps2` — PS2 摇杆模块
- `keypad_3x4` — 3x4 矩阵键盘
- `keypad_4x4` — 4x4 矩阵键盘
- `limit_switch_kw12` — KW12 限位开关
- `nfc_pn532` — PN532 NFC 模块
- `potentiometer_10k_module` — 10K 旋钮电位器模块
- `rfid_rc522` — MFRC522 RFID 模块
- `rotary_encoder_ec11` — EC11 旋转编码器
- `slide_potentiometer_10k` — 10K 滑动电位器
- `toggle_switch_module` — 拨动开关模块

### Audio 音频 (6)
- `dfplayer_mini` — DFPlayer Mini MP3 模块
- `i2s_max98357a` — MAX98357A I2S 功放
- `microphone_analog_ky037` — KY-037 模拟麦克风
- `pam8403_amp` — PAM8403 功放模块
- `speaker_4ohm_3w` — 4Ω 3W 喇叭
- `voice_recognition_v3` — 离线语音识别模块 V3

### Storage 存储/时钟 (5)
- `eeprom_at24c256` — AT24C256 EEPROM 模块
- `fram_mb85rc256v` — MB85RC256V FRAM 模块
- `micro_sd_spi` — MicroSD SPI 模块
- `rtc_ds1307` — DS1307 RTC 模块
- `usb_host_ch376s` — CH376S USB Host 模块

### Robotics 机器人组件 (6)
- `encoder_motor_jga25` — JGA25 编码减速电机
- `mecanum_wheel_set` — 麦克纳姆轮套件
- `pan_tilt_2axis_kit` — 双轴云台支架
- `robot_chassis_2wd` — 2WD 小车底盘
- `robot_chassis_4wd` — 4WD 小车底盘
- `vacuum_pump_mini` — 微型真空泵

## 字段规范

每个模块至少包含：
- `id` — 唯一标识符
- `label` — 人类可读名称
- `category` — board / input / output / power / interface / signal
- `subcategory` — 更细的模块分组
- `provides` — 能力列表（agent 用来匹配用户需求）
- `pin_spec` — 引脚规范
- `compatible_boards` — 兼容的板子
- `notes` — 注意事项
- `price_cny` — 价格参考
