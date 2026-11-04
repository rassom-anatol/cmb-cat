# I2C address map — CMB-CAT stack

All devices share the CM4's **I2C0** bus, brought out on CM4 connector pins **82 (SDA0)** and
**80 (SCL0)** — GPIO44/GPIO45 on BCM2711. The CM4 provides internal 1.8 kΩ pull-ups to
CM4_3.3V on both lines, so no external pull-ups are fitted.

Addresses below are **7-bit**.

---

## Allocation

| Address | Device | Board | How the address is set |
|---|---|---|---|
| **0x50** | 24LC32 EEPROM | CMB-CAT | A2=0, A1=0, A0=0 |
| **0x51** | PCF85063AT RTC | CMB-CAT | fixed, not changeable |
| 0x52–0x55 | *(free)* | — | available for further EEPROMs |
| **0x56** | CAT24C32YI-GT3 EEPROM | CMC101 | A2=1, A1=1, A0=0 |
| **0x57** | EEPROM (part TBD) | CMC301 | A2=1, A1=1, A0=1 |
| **0x60** | TUSB320 | CMB-CAT | ADDR pulled low (0x61 if pulled high) |
| **0x64** | ATSHA204A | CMB-CAT | config-zone default `0xC8` |
| **0x65** | ATSHA204A | CMC101 | **must be reprogrammed** — see below |
| **0x70** | PCA9538 I/O expander | CMB-CAT | A1=0, A0=0 |
| **0x71** | PCA9538 I/O expander | CMC301 | A1=0, A0=1 |

---

## Constraints that drove this

**0x51 is reserved by the RTC.** The PCF85063AT's address is fixed and sits inside the
24Cxx family's 0x50–0x57 range. No EEPROM may be strapped to 0x51.

**PCA9538 has only two address pins**, giving four addresses (0x70–0x73). Two are used.
If a third expander is ever needed, 0x72 and 0x73 remain; beyond that, the PCA9538A variant
occupies 0x74–0x77. TCA9534 would have given three address pins and eight addresses.

**ATSHA204A has no address pins.** The address is the `I2C_Address` byte in the config zone,
default `0xC8` (7-bit 0x64), with six bits programmable. Two parts on the same bus therefore
collide at 0x64 until one is reprogrammed.

> The config zone is writable only while **unlocked**. Programming order per board is:
> set `I2C_Address`, program keys, then lock. After locking the address is permanent.
> This is a manufacturing step and belongs in the production test plan.

---

## Free addresses

0x52, 0x53, 0x54, 0x55 (EEPROM range) · 0x72, 0x73 (expander range) · 0x74–0x77 (if PCA9538A used)

---

## To verify before release

- **TUSB320 ADDR strap** — 0x60 with ADDR low, 0x61 with ADDR high; confirm which is fitted
- Scan the assembled stack with `i2cdetect -y 0` and check the result matches this table
