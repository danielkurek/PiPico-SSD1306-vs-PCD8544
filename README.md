# SSD1306 vs PCD8544
Test project to compare different kinds of displays
 - SSD1306 - OLED 0.96"
 - PCD8544 - Nokia 5110 display
 
# Connections 
## OLED
| Pi pico | OLED |
|---------|------|
| GND     | GND  |
| 3V3     | VDD  |
| GP4     | SDA  |
| GP5     | SCL  |

## Nokia 5110

| Pi pico | Nokia 5110 |
|---------|------------|
| GP9     | RST        |
| GP8     | CE         |
| GP7     | DC         |
| GP11    | DIN        |
| GP10    | CLK        |
| 3V3     | VCC        |
| GP3     | LIGHT      |
| GND     | GND        |

## Buttons

| Pi pico | Button |
|---------|--------|
| GP18    | DOWN   |
| GP19    | UP     |
| GP20    | OK     |
