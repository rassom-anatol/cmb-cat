# CMB-CAT — open items

Tracked list of work still outstanding. Verified against the schematic on 2026-11-01;
items already done are listed at the bottom so they aren't re-raised.

---

## Footprints and libraries

**LAN9252 TQFP-64 — remove solder paste from the four thermal vias.**
`cmb-cat.pretty/TQFP-64_L10.0-W10.0-P0.50-LS12.0-BL-EP.kicad_mod` has four 0.30 mm
through-holes at (±0.5, ±0.5) inside the exposed pad, and they carry `*.Paste`. Paste over
an open via wicks solder down the barrel during reflow and starves the joint. Either strip
the paste layer from those pads or specify plugged vias.

**LAN9252 TQFP-64 — add more thermal vias.**
Four vias under a 4.04 mm exposed pad is thin. The datasheet states twice that the
*"exposed pad (VSS) on bottom of package must be connected to ground with a via field."*
The part dissipates around 640 mW with 29 °C/W junction-to-ambient. A 3×3 array or denser
is the usual reading of "via field".

**LAN9252 TQFP-64 — land pattern not verified.**
Section 19.2 of `00001909A.pdf` is a drawing with no extractable text, so pad geometry has
not been checked against Microchip's recommendation. Measure it from the drawing before
committing to fabrication.

**Move `cmb-cat.pretty` from the global footprint table to the project table.**
It is currently registered globally with a `${KIPRJMOD}` path, which resolves to whatever
project happens to be open. Works here, breaks portability and warns in other projects.
Preferences → Manage Footprint Libraries → Project Specific Libraries.

**MPM3810 footprint is unusable if that part is ever revisited.**
The downloaded `QFN-12_MPM3810_MNP.kicad_mod` has five pads at 0.127 × 0.127 mm — generator
defaults, not real lands — including both OUT pins. Superseded by MUN12AD01-SH, but do not
reuse that file.

---

## Schematic

**Rename the hierarchical labels `ID_SD` → `SPI3_CE0_N` and `ID_SC` → `SPI3_MISO`.**
These are the last two entries where the schematic does not match the `RPi Function` column
of `cm4-pin-plan.xlsx`. They appear twice in `CM4_GPIO.kicad_sch` and twice in
`CM4_HighSpeed.kicad_sch`, with matching hierarchical pins on the root sheet boxes.
**Do this in the GUI** so KiCad renames label and sheet pin together — a text edit risks
silently splitting the net. Getting the pair the wrong way round swaps chip select and MISO
on CMC101's bus.

**Decide what `EEPROM_nWP` connects to.**
Internally pulled up via 100 kΩ, so floating leaves the bootloader EEPROM writable. The CM4
datasheet recommends final products pull it low, and it must be low *before power-up* to
take effect. A jumper keeps development flexible and allows production write-protection.
Do not hard-wire low — that removes bootloader updates, and rpiboot is the only other
recovery path.

**Decide `BT_nDis` and `WL_nDisable`.**
Leave floating for software control, tie low to physically guarantee the radios are off, or
fit a jumper. Re-enabling after a disable requires the driver to be reinitialised, so this
is not a runtime toggle. Relevant if industrial customers ask whether radios can be
guaranteed off.

**Route `nEXTRST` to peripheral resets.**
It is an **output** — low during reset, high once the CPU starts booting. Natural
destinations are the LAN9252 reset, the reset lines out to CMC101 and CMC301, and the GPIO
expander reset. Costs no GPIO and is automatically correct at power-up. Check fan-out
across several boards; a 74LVC1G07 buffer may be wanted. Note this pin does not exist on CM5.

**Decide `SYNC_IN` / `SYNC_OUT`.**
Leave unconnected, bring to test points, or use them. The interesting option is
**LAN9252 SYNC1 → CM4 SYNC_IN**, which lets the Ethernet PHY timestamp EtherCAT
distributed-clock events in PTP time — a way to correlate the motion and coordination time
domains. If `SYNC_OUT` goes to a connector it needs GND adjacent on both sides and series
termination at the source. `SYNC_IN` is pin 16, which becomes `Fan_tacho` on CM5.

**Settle the RTC backup.**
No user-replaceable holder meets the under-10 mm constraint: Keystone 3001 is 14.5 × 11.4 mm,
Keystone 2998 is 11.8 × 9.9 mm, and vertical CR1220 holders stand about 12 mm tall. The
option that does fit is the existing `J17` connector with the cell mounted elsewhere in the
enclosure. Alternatives are accepting the Keystone 3001's footprint, or a supercapacitor
(Kemet `FC0H224ZFTBR24`, 0.22 F 5.5 V SMD, ~37 h holdup, no battery shipping classification).
Decision made so far: **ship without a cell; the user buys a primary CR1220**, which means
the board must have **no charging path** — D3's BAT54C arrangement already blocks it.

**Confirm CMC301's EEPROM part.**
`docs/i2c-address-map.md` lists it at 0x57 as 24LC32. Confirm that is the part fitted.

---

## Power

**Pick the footprint for the OS-CON bulk capacitor.**
`16SVPG100M` (100 µF, 16 V, 15 mΩ) replaces the tantalum. Find its case size in the
Panasonic datasheet, then match a `Capacitor_SMD:CP_Elec_<diameter>x<height>` footprint.
Compare against the OS-CON recommended pattern — the pad gap on polymer aluminium parts is
sometimes tighter than the generic electrolytic pattern.

**Measure board power and decide fan or fanless.**
Run the real workload in the real enclosure at worst-case ambient and watch for throttling.
Fanless is more reliable — the fan would be the only moving part. If a fan is needed,
on/off through a GPIO expander pin plus a FET is adequate; remember the flyback diode.

**Check TPS82140 family stock before relying on it.**
`TPS82130` (3 A), `TPS82140` (2 A) and `TPS82150` (1 A) share one footprint and one feedback
divider, so any of the three drops in. Currently superseded by MUN12AD01-SH, but this is the
fallback if that part becomes hard to source.

---

## Verification before release

- Scan the assembled stack with `i2cdetect -y 0` against `docs/i2c-address-map.md`
- Confirm the TUSB320 `ADDR` strap matches the 0x60 recorded in that map
- Program each ATSHA204A's `I2C_Address` **before locking the config zone** — two parts both
  ship at 0x64 and the address is permanent once locked. This belongs in the production test plan.

---

## Closed since raised

- Stale `+12v` hierarchical pins on the PSUs and RTC sheet boxes — removed
- MUN12AD01 PGOOD divider (R16/R23) — removed; PGOOD is open drain and pulls up to 3.3 V
- `TV_OUT` and `CAM_GPIO` labels — removed
- Duplicate I2C address table in `RTC.kicad_sch` — now a single instance
- GPIO label rename from `cm4-pin-plan.xlsx` — 42 labels across 21 nets, ERC unchanged
- `SPI0_CE0` → `SPI0_CE0_N` suffix — fixed in schematic and spreadsheet
- GPIO44/45 naming — spreadsheet now matches the schematic's `SDA0` / `SCL0`
