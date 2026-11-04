# CMB-CAT — open items

Tracked list of work still outstanding. Verified against the schematic on 2026-11-01;
items already done are listed at the bottom so they aren't re-raised.

---

## Footprints and libraries

**LAN9252 QFN-64 — check the exposed-pad paste subdivision.**
`cmb-cat.pretty/QFN64_ML_MCH.kicad_mod` came from the Microchip download, not from KiCad's
generator. A single large paste aperture over a 4+ mm exposed pad floats the part on molten
solder and tilts it. The usual fix is to subdivide the paste into a 3x3 array of smaller
apertures covering roughly 50-70% of the pad area. Verify what the file actually has.

**LAN9252 QFN-64 — no thermal vias in the footprint.**
The exposed pad is ground and the part dissipates around 640 mW. The datasheet twice calls
for the pad to be *"connected to ground with a via field."* The downloaded footprint contains
no vias at all, so they must be added either in the footprint or as a via array in the layout.

**LAN9252 QFN-64 — land pattern not verified against the datasheet.**
Section 19 of `00001909A.pdf` is an image with no extractable text, so pad geometry has not
been checked. Measure it from the drawing before fabrication.

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

## EtherCAT (LAN9252)

Passives and the oscillator are placed and wired on `ethercat.kicad_sch` (2026-11-03).
39 functional pins remain unconnected on purpose — each needs a decision:

**Strap `CHIP_MODE0` / `CHIP_MODE1` (pins 48 / 46) before anything else works.**
These are latched at the rising edge of reset and select the host interface: SPI/SQI,
parallel, or MII. They are shared with `LINKACTLED0` / `LINKACTLED1` and with the JTAG
`TDO` / `TDI`, so the strap resistors and the LED circuit have to coexist. The SPI setting
is what the rest of the pin plan assumes. Get this wrong and the device never responds.

**Wire the SPI bus to the CM4.** `cm4-pin-plan.xlsx` allocates GPIO8-11 as SPI0 to the
LAN9252, GPIO16 as `LAN9252-IRQ`, GPIO17 as `LAN9252-SYNC0`. On the LAN9252 side the signals
sit on multiplexed pins: `SCS#` (50), `SCK` (19), `SI/SIO0` (17), `SO/SIO1` (13),
`IRQ` (44), `SYNC0/LATCH0` (34). Confirm the exact mapping against the SPI-mode table
rather than the pin names, since single-SPI and dual/quad-SPI use different pins.

**Add the EtherCAT configuration EEPROM.** `EESDA` (42) and `EESCL` (43) need their own
I2C EEPROM — this is a separate bus from the CM4's I2C0, so it does not appear in
`docs/i2c-address-map.md`. `E2PSIZE` (45, shared with `RUNLED`) selects the address width.
Size it for the ESI/SII content, not arbitrarily.

**Add the Ethernet magnetics and connectors.** Port A is `TXPA/TXNA` (53/52) and
`RXPA/RXNA` (55/54); port B is `TXPB/TXNB` (62/63) and `RXPB/RXNB` (60/61). Two ports means
two sets of magnetics — the integrated PHYs do not replace transformers. A mid-mount
dual RJ45 with integrated magnetics is the compact option.

**Confirm the crystal load capacitors.** `C81` / `C82` are 18 pF placeholders copied from
the EVB. The correct value is `2 x (CL - Cstray)`, so it depends on the crystal actually
chosen. `Y3` is specified only as 25 MHz; EtherCAT distributed clocks want +/-25 ppm or
better, and the LAN9252 datasheet states its own frequency tolerance requirement. Pick a
real part, then recompute.

**`OSCVDD12` (pin 3) is left open** per decision on 2026-11-03, recorded with a no-connect
flag so ERC stays quiet about it.

**Pin types in the LAN9252 symbol were wrong as downloaded** and have been corrected:
`OSCVSS` (4) and `VSS` (65) were `power_output` — a ground pin does not source power;
`REG_EN` (7) and `FXLOSEN` (8) were `unspecified`, now `input`; `RBIAS` (57) was
`unspecified`, now `passive`. This removed 15 `power_pin_not_driven` and 4 `pin_not_driven`
ERC errors. Both `cmb-cat.kicad_sym` and the copy embedded in `ethercat.kicad_sch` were
updated and now agree on all 65 pins.

**VDDIO decoupling deviates from the EVB on purpose.** The EVB fits six 0.1 uF caps; this
board fits five 0.1 uF (one per VDDIO pin) plus `C76`, a 10 uF bulk. Revert if you would
rather match the reference exactly.

---

## Schematic hygiene

**Stray local label `GND` on `CM4_GPIO.kicad_sch`.**
At (85.344, 165.1) there is a local label named `GND` sitting on no wire — it connects
nothing. Because `GND` is also a global power symbol name, it raises a
`same_local_global_label` warning that now surfaces on the EtherCAT sheet. Safe to delete.

**Local labels named `+3.3V` are used in several places** alongside the global `+3.3V`
power symbol (root sheet, `CM4_GPIO`, `CM4_HighSpeed`). Where such a net also carries a
`+3.3V` power symbol the two merge and all is well; where it does not, the local label
creates a sheet-scoped net that only looks like the 3.3 V rail. Worth a pass to confirm
each one touches a power symbol.

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
- LAN9252 passives and oscillator placed and wired on `ethercat.kicad_sch` — FB1-FB4, C66-C83,
  R34-R36, Y3, 5 PWR_FLAGs; 25 U16 pins wired, 1 no-connect; all 10 new nets verified against
  the exported netlist
- LAN9252 symbol swapped from TQFP-EP64 to QFN-64 (`LAN9252I/ML`), TQFP symbol and footprint removed
- Sheet paper sizes set: EtherCAT / CM4_GPIO / CM4_HighSpeed / PSUs on US Ledger, RTC and root on US Letter
