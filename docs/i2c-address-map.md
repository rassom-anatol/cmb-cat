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
| 0x51 | *(free)* | — | released when the RTC moved to 0x6F |
| 0x52–0x55 | *(free)* | — | available for further EEPROMs |
| **0x56** | CAT24C32YI-GT3 EEPROM | CMC101 | A2=1, A1=1, A0=0 |
| **0x57** | EEPROM (part TBD) | CMC301 | A2=1, A1=1, A0=1 |
| **0x60** | TUSB320 | CMB-CAT | ADDR pulled low (0x61 if pulled high) |
| **0x64** | ATSHA204A | CMB-CAT | config-zone default `0xC8` |
| **0x65** | ATSHA204A | CMC101 | **must be reprogrammed** — see below |
| **0x6F** | MCP7940N RTC (U20) | CMB-CAT | fixed, not changeable |
| **0x70** | PCA9538 I/O expander | CMB-CAT | A1=0, A0=0 |
| **0x71** | PCA9538 I/O expander | CMC301 | A1=0, A0=1 |

---

## Constraints that drove this

**0x51 is no longer reserved.** The RTC was changed from a PCF85063AT (fixed 0x51,
inside the 24Cxx 0x50–0x57 range) to an **MCP7940N at 0x6F**, whose address is also fixed —
the control code is `1101` plus three chip-select bits hardwired to `1`. That releases the
whole 0x50–0x57 block to the 24Cxx family.

**The 24LC32 address pins have no internal pulls.** The datasheet is explicit: *"These
inputs must be connected to either VCC or VSS."* Unlike onsemi's CAT24C32, which pulls them
down internally, a floating pin on a 24LC32 gives an undefined address. U10's A0/A1/A2 are
tied to GND through R67 (0R) giving 0x50; U18's are tied directly.

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

---

## Changed 2026-11-09

RTC moved **0x51 → 0x6F** (PCF85063AT → MCP7940N). The move was not made to free the
address — it was chosen for a 3 × 2 mm TDFN package, automatic battery switch-over that
removes the BAT54C diode-OR, and the absence of any trickle charger, which enforces the
"ship without a cell, no charging path" requirement in silicon rather than by a diode
arrangement. Freeing 0x51 was a side effect.

`VBATEN` (RTCWKDAY 03h bit 3) **must be set in firmware** or battery backup never engages —
the hardware switchover is automatic but the VBAT input is disabled by default. This belongs
in the production test: pull power, restore, confirm time was kept.
