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

**RTC backup — settled.** The RTC is now an **MCP7940N (U20)** at 0x6F in TDFN-8 3x2mm.
It has automatic battery switch-over at VTRIP 1.3-1.7 V, so the BAT54C diode-OR (D3) is gone
and the cell connects straight to VBAT (pin 3) from J6. It has **no trickle charger anywhere
in the datasheet**, so the "ship without a cell, the user fits a primary CR1220" requirement
is now enforced by the silicon rather than by a diode arrangement.

Still to do on it:
- **`VBATEN` (RTCWKDAY 03h bit 3) must be set in firmware** or backup never engages. The
  switchover is automatic but the VBAT input is disabled by default. Production test: pull
  power, restore, confirm the time was kept.
- **J6 needs a polarised, keyed housing.** It is a generic `Conn_01x02` and the end user
  fits their own cell, so a reversed insertion puts -3 V on VBAT against a -0.6 V absolute
  maximum. Fix it mechanically; a series diode or clamp is worse.
- **Add 100 nF on VBAT at pin 3.** The cell sits at the end of a connector and flying leads,
  and a CR1220's ESR climbs from ~15 ohm fresh to hundreds as it depletes.

**Confirm CMC301's EEPROM part.**
`docs/i2c-address-map.md` lists it at 0x57 as 24LC32. Confirm that is the part fitted.

---

## EtherCAT (LAN9252)

The sheet is complete and wired as of 2026-11-03: 57 parts, ERC down from 84 violations to 1
(and that one is the stray `GND` label on CM4_GPIO, below). Every net was verified against the
exported netlist.

Front end per port: 4x 49.9R 1% from TXP/TXN/RXP/RXN to `VDD33TXRX(n)`, plus a 0R from the
commoned transformer centre taps to the same rail — this is the topology reconstructed from
Microchip's own `EVB-LAN9252-SPI` Altium files, not a guess. Magnetics are Halo
`TG110-E050N5RL` (one per port); `Wuerth 749013011A` is the second source and uses the same
KiCad symbol and footprint. Cable side goes through a 1 nF / 2 kV cap to chassis (`Earth`) and
out to a JST GH `SM05B-GHS-TB` 5-pin right-angle connector per port, pinned
**TX+, TX-, shield, RX+, RX-** so the shield sits between the pairs as a guard.

**The CM4 to LAN9252 interface is complete and verified.** All six signals join
end-to-end, confirmed against the exported netlist:

| Net | Members |
|---|---|
| `SPI0_CE0_N` | `J8.24` `Module1.39` `U16.50` |
| `SPI0_SCLK` | `J8.23` `Module1.38` `U16.19` |
| `SPI0_MOSI` | `J8.19` `Module1.44` `U16.17` |
| `SPI0_MISO` | `J8.21` `Module1.40` `U16.13` |
| `LAN9252_IRQ` | `J8.36` `Module1.29` `U16.44` |
| `LAN9252_SYNC0` | `J8.11` `Module1.50` `U16.34` |

`CM4_GPIO.kicad_sch` already had stub wires drawn to its hierarchical-label columns
(x=31.75 and x=120.65) with free dangling ends, clearly left for this purpose; six
hierarchical labels were added there and six matching sheet pins on the root CM4_GPIO box.
That also cleared six `unconnected_wire_endpoint` warnings.

No net was renamed. CM4_GPIO still calls the two interrupt lines `GPIO16` and `GPIO17`;
the join happens through root local labels named `LAN9252_IRQ` and `LAN9252_SYNC0` on those
sheet pins' wires, which is legal and avoids touching 132 labels on that sheet. If you would
rather the CM4_GPIO nets carry the descriptive names, rename them in the GUI and rename the
root local labels to match — but it changes nothing electrically.

**Done and verified end-to-end:** `nEXTRST` now drives the LAN9252 reset (the net carries
`Module1.100`, `U15.2`, `U16.11`, `R35.2`, `C83.1`), and SYNC1 reaches the CM4 through `R55`
(0R) — `/SYNC_IN` is `Module1.16` + `R55.2`. The `SYNC_IN` sheet pin was the only thing
missing on the root CM4_GPIO box; its hierarchical label already existed inside the sheet.

**Strap values, from the EVB:** `CHIP_MODE0` (48) and `CHIP_MODE1` (46) each 10k to GND = 00,
two-port mode. `E2PSIZE` (45) 10k to 3V3 = high, required for 32 Kbit and above. Note
CHIP_MODE selects *port topology*, not the host interface — the PDI comes from register
`0x0140`, loaded from the EEPROM, which is why the EEPROM is mandatory.

**LEDs share the strap pins.** Anode to 3V3, cathode through a resistor to the pin, so they
are active-low: `D8`/`R52` 1k on LINKACTLED0, `D9`/`R53` 1k on LINKACTLED1, `D10`/`R54` 270R
on RUNLED. On the two link LEDs the 10k pull-down sits in series with the LED when the pin is
high-Z, giving about 130 uA of leakage — a possible faint glow. The EVB accepts this; raise
the pull-down or drop the LED if it is visible.

**Confirm the crystal before fabrication.** `Y3` is specified only as 25 MHz with 18 pF load
caps copied from the EVB. Table 18-12 requires, for EtherCAT, **+/-15 ppm at 25 C and +/-15 ppm
over temperature** in a +/-25 ppm total budget — far tighter than the +/-40 ppm plain Ethernet
allows, and tighter than most commodity 2520 parts. Load caps follow the chosen crystal's CL
(the chip accepts CL up to 18 pF; its own OSCI/OSCO pin capacitance is 3 pF typ), so
`C81`/`C82` must be recomputed once the part is picked.

**Signal integrity of the 5-pin connector.** 100BASE-TX needs ~100 ohm differential. Discrete
pre-crimped leads laid side by side are not a twisted pair. Specify twisted pair crimped into
the GH housing and keep runs short; the shield pin between the pairs helps. Also keep the
cable-side centre taps off board GND — they go to chassis through the 2 kV cap, because
EtherCAT relies on transformer isolation between nodes.

**`OSCVDD12` (pin 3) is left open** per decision on 2026-11-03, recorded with a no-connect flag.

**Pin types in the LAN9252 symbol were wrong as downloaded** and have been corrected:
`OSCVSS` (4) and `VSS` (65) were `power_output` — a ground pin does not source power;
`REG_EN` (7) and `FXLOSEN` (8) were `unspecified`, now `input`; `RBIAS` (57) `unspecified`,
now `passive`; and the eight PHY pins (52-55, 60-63) were `unspecified`, now `passive`.
Both `cmb-cat.kicad_sym` and the copy embedded in `ethercat.kicad_sch` were updated and agree
on all 65 pins.

**19 parallel-bus pins carry no-connect flags** (12, 15, 16, 21-23, 25-31, 33, 35, 36, 39, 40,
49). They are the parallel/DIGIO/MII alternatives, unused in SPI PDI mode.

**VDDIO decoupling deviates from the EVB on purpose:** five 0.1 uF (one per VDDIO pin) plus
`C76`, a 10 uF bulk, where the EVB fits six 0.1 uF.

---

## CMC301 FFC interface

Placed on `CM4_GPIO.kicad_sch` in the clear area at x>290 (that sheet's content stops at
x=282 on a 431.8 mm page). Putting it there means no cross-sheet plumbing at all — every
signal is already a local label on that sheet. Move it to its own sheet later if you prefer;
it is a drag in the GUI.

**Connector: Hirose `FH12-24S-0.5SH(55)`** (J21), 24-way, 0.5 mm, right-angle ZIF,
bottom contact. The 30-way J20 was removed. KiCad ships no FH12A (top-contact) land pattern,
and the `(55)` suffix is the active part - the bare `FH12-24S-0.5SH` is obsolete. 14,358 in
stock at the time of selection.

> Contact side decides the cable: with bottom contacts at both ends, whether you need a
> same-side (Molex Premo-Flex Type A) or opposite-side (Type D) jumper depends on how the
> two boards face each other. Settle that against the mechanical layout before ordering.

**Signal count was reduced from 15 to ~12** once CMC301 gained its own expander at 0x71.
Only these cannot go through it: SPI4 SCLK/MOSI/MISO/CE0_N, SPI6 SCLK/MOSI/MISO/CE0_N/CE1_N
(MHz rate, and CE must toggle per frame), and SDA0/SCL0 (the bus that reaches the expander
cannot bootstrap itself). `CTRL_ENABLE` and `CMC301_SLEEP_N` moved to the CMC301 expander,
mirroring what U11 does for CMC101. `SPI4_CE1_N` is not needed on the FFC at all - it goes
to GPIO25, allocated to the TMC8100, which lives on CMB-CAT.

`CTRL_STATUS` was kept as a dedicated conductor: per the TMC6460 errata the part clears
`DRV_EN` itself on fault only *"in most cases"*, and the overtemperature case with
`OVERTEMP_LATCH = 0` does not - so some faults need the host to learn about them faster than
a poll interval.

**Spend freed conductors on ground, not a smaller connector.** At 0.5 mm pitch over flat
flex with 8 MHz SPI, return-path quality is the limit.

**Pin ordering: guard the clock.** The original order (`GND SCLK MOSI GND MISO CE0 ...`) was
signal-listing order with a ground every second pin, not a considered choice, and it is the
wrong grouping - SCLK is the only aggressor, switching every cycle with the fastest edges,
and it sat next to MOSI, which must be valid at the clock edge. Worse, they shared both
adjacent grounds, so their return currents commingled. At identical conductor count prefer:

```
GND  SCLK  GND  MOSI  MISO  GND  CE0  CE1  GND
```

SCLK gets a dedicated return on both sides; MOSI/MISO sit together harmlessly since both are
referenced to the same clock edge and quiet between edges.

### Pinout, as wired

| Pin | Net | Pin | Net | Pin | Net |
|---|---|---|---|---|---|
| 1 | GND | 11 | SPI6_MOSI | 21 | CTRL_ENABLE |
| 2 | SPI4_SCLK | 12 | GND | 22 | CTRL_STATUS |
| 3 | SPI4_MOSI | 13 | SPI6_MISO | 23 | GND |
| 4 | GND | 14 | SPI6_CE0_N | 24 | CMC301_SLEEPN |
| 5 | SPI4_MISO | 15 | GND | 25 | GND |
| 6 | SPI4_CE0_N | 16 | SPI6_CE1_N | 26 | +3.3V |
| 7 | GND | 17 | GND | 27 | +3.3V |
| 8 | SPI4_CE1_N | 18 | SDA0 | 28 | GND |
| 9 | GND | 19 | SCL0 | 29 | GND |
| 10 | SPI6_SCLK | 20 | GND | 30 | GND |

15 signals, 2 supply, 13 ground. Grounds are interleaved so no signal is more than one
conductor from a return, and the two SPI buses are separated by one. All 30 pins were
verified against the exported netlist; every signal reaches the CM4 module.

### Why these signals, from the TMC6460 datasheet

Each TMC6460's host-side pins are CSN (1), SLEEPN (2), DRV_EN (34), FAULTN (35), SCK (36),
SDI (37), SDO (38). Two of those have **internal pull-downs** and so are fail-safe but must
be actively driven to run:

- **`DRV_EN` (34), active high, internal pull-down.** Driven from `CTRL_ENABLE` (GPIO22).
  When the CM4 resets its GPIOs go high-Z and the pull-down disables the power stage, which
  is the behaviour you want.
- **`SLEEPN` (2), active low, internal pull-down.** Register contents are lost in sleep, so
  this is also the reset. Driven from expander pin IO0 with `R57` (10k) pulling it up on
  CMB-CAT, so the default is awake and software has to deliberately assert it. That avoids
  driving it from `nEXTRST`, because the datasheet warns "do not assert this pin while the
  motor is moving" and `nEXTRST` falls on any CPU reset.
- **`FAULTN` (35)** is open-drain with an internal pull-up, so the three devices wire-OR onto
  `CTRL_STATUS` (GPIO26); `R56` (10k) is the external pull-up on this side.
- **`CLK` (7)** is left to CMC301. The internal oscillator is 15 MHz +/-5%, and per the errata
  the 599 Hz electrical output-frequency limit is derived from it, so it can trip at roughly
  542 to 570 Hz. Feed an external clock there if that matters.

`CTRL_ENABLE` and `CTRL_STATUS` were added as labels on the existing `GPIO22` and `GPIO26`
nets, applying the pin plan's naming without deleting anything. KiCad reports two
`multiple_net_names` warnings saying the descriptive name wins — that is intended. Delete
the old `GPIO22` / `GPIO26` labels in the GUI if you want the warnings gone.

---

## I2C GPIO expander (U11, PCA9538BS)

Was placed with power and I2C only. Now also wired:

- `A0` (15) and `A1` (16) to GND, giving **0x70** as `docs/i2c-address-map.md` specifies
- `RESET` (1) from `nEXTRST`
- `INT` (11) to `EXP_INT` with `R58` (10k) pull-up — open-drain, so the pull-up is required
- `IO0` (2) drives `CMC301_SLEEPN`

**IO0-IO6 are now assigned** to CMC101 control: `CMC101_ENABLE`, `CMC101_STATUS`,
`CMC101_FAULT`, `CMC101_FAN`, `CMC101_STO_WDO_N`, `CMC101_RST_N`, and `CMC301_RST_N`. IO7 is
free.

The PCA9538 has no internal pull-downs on its I/Os. Configure IO7 as an output in firmware
rather than leaving it floating as an input.

**`EXP_INT` has no destination.** Every CM4 GPIO is allocated, so the expander is polled over
I2C by default. That is fine for housekeeping. If you want a real interrupt it has to share
an existing line or displace something in `cm4-pin-plan.xlsx`.

> **`nRTC_INT` is pulled up to +5 V, not 3.3 V.** `R19` (510k) on `RTC.kicad_sch` references
> `+5V`, so that net idles at 5 V. Feeding it to any 3.3 V input — the expander included —
> forward-biases the input protection diode. The current is only a few microamps through
> 510k so nothing is damaged, but it is wrong. Re-reference `R19` to `+3.3V` before using
> this signal.

**U11 sits off the 1.27 mm grid** at (193.294, 133.35), so its pins and anything wired to
them are off-grid too. That is part of the project's 239 `endpoint_off_grid` warnings and
pre-dates this work; nudging the symbol onto the grid would need its wires redrawn.

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

## Encoder feedback — see `docs/encoder-feedback.md`

**Decide which encoder protocols CMB-CAT must support.** This gates whether the TMC8100 is
needed at all. The symbol and footprint exist in the project library but the part is not
placed on any sheet, so nothing is committed.

- If **SSI only**: the CM4 can read it over SPI directly (clock-and-data, no chip select),
  and the TMC6460 handles it natively on CMC301. The TMC8100 can be dropped.
- If **BiSS-C**: confirm with ADI that a BiSS-C program exists for the TMC8100 and what it
  costs. Its datasheet mentions BiSS exactly once, against 42 mentions of SSI. The same
  single-sentence claim in the TMC6460 datasheet turned out to rest on an undocumented
  I/O Controller instruction set.

**Do not plan on host-supplied commutation angle.** The TMC4671 has no extrapolation, so
`PHI_E_EXT` is a zero-order hold; at 1 kHz with 7 pole pairs the commutation error is 42
degrees at 1000 rpm and torque reverses by 3000 rpm. The practical ceiling is ~240 rpm.
Use ABN for commutation and the absolute encoder to re-reference at startup instead —
`ABN_DECODER_PHI_E_PHI_M_OFFSET` and `PID_POSITION_ACTUAL` are both writable, which gives
correct commutation from the first PWM cycle with no alignment move.

**Confirm the encoders provide both absolute and incremental**, or budget for two sensors.
Note the position loop then resolves to ABN counts, not encoder bits.

---

## Open decisions

**Current limiting on the 3.3 V going out to the FFC.** U12 (RT9742SNGV) was removed: the
`S` suffix puts its limit in the 0.6 / 0.7 / 0.8 A group, about 9x the 77 mA worst-case
CMC301 load (3x TMC6460 `IVCCIO_DRVOFF` at 25 mA max, plus EEPROM and expander) and *above*
the FH12's 0.5 A per-contact rating, so a fault could damage a contact without tripping it.

A resettable fuse was considered and rejected: holding 77 mA needs a 100-150 mA device, and
those carry 2-5 ohm series resistance - 150-375 mV at load on a 3.3 V rail, drifting upward
with age and each trip.

Want an adjustable-limit load switch set to **~200-250 mA**, roughly 3x max load and safely
under the contact rating. Candidates:

| Part | Range | Notes |
|---|---|---|
| `TPS2553DDBVR` | 75 mA - 1.7 A | SOT-23-6, 2096 in stock. No KiCad symbol. Note `TPS2553DBVR` (one D) was backordered; the suffix also selects enable polarity. |
| `MIC2008YM6` | 0.2 - 2 A | SOT-23-6 or 2x2 DFN, **KiCad symbol exists**, adds slew control and automatic load discharge - the discharge matters so a software power-cycle actually resets CMC301. |

The protection is the weaker half of the argument. The stronger reasons are **inrush**
(mating the FFC powered connects three TMC6460s' worth of decoupling across 3.3 V and can
brown out the CM4), the **enable pin** (cutting CMC301's supply is the only hammer left when
I2C and SPI are both wedged), and the **fault flag** into a spare expander input.

No current limit helps with an FFC inserted one position off, putting 3.3 V on a signal pin.
A keyed or asymmetric cable end is the only defence there.

**Keep 3.3 V on the FFC rather than regulating locally on CMC301.** An LDO does not reduce
FFC current - input equals output - so 5 V plus a local LDO carries the same 77 mA and burns
130 mW for headroom against a 5-8 mV drop that does not matter. Moving the load off CMB-CAT
entirely saves 75 mA of a ~500 mA design target, which does not change a regulator size
class; the LAN9252 at 194 mA is nearly 60% of the subtotal and is where the weight is.
CMC301 self-powering from its motor rail would free the conductors but leaves the CM4 driving
SPI into unpowered TMC6460s, back-powering them through their I/O ESD diodes.

---

## Footprints still unassigned

- **U18** (24LC32, EtherCAT config EEPROM) - SOIC-8 is the obvious choice but the field is
  empty, so it will not reach layout.
- **H3** (MountingHole_Pad on the EtherCAT chassis island) - empty.

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
- RTC swapped PCF85063AT (0x51) to MCP7940N (0x6F); D3 BAT54C removed, VBAT direct to J6
- RTC wake chain migrated +5V to +3.3V - R19, R20, C22 and U14 pin 5. MFP needs its pull-up
  to VCC, and 5 V on it exceeded the VCC+0.3 V absolute maximum; fixing R19 alone would have
  broken the wake circuit, since the pulse coupled through C24 is only as large as the swing
  on nRTC_INT and a 3.3 V step leaves U14's input at 1.7 V, above V_IL for a 5 V LVC gate
- Y2 crystal X32K768S301 (unavailable) to ABS07-32.768KHZ-7-T, 7 pF CL, same 3215 footprint.
  C50/C61 6.8 pF load caps added - the MCP7940N has none internally where the PCF85063AT did
- 74LVC1G07SE-7 (unavailable) to SN74LVC1G07DCK3 across all five instances, the library
  symbol and both cached copies, so an update-from-library cannot revert it
- LAN9252 VDD33 (pin 5) moved off FB3 to +3.3V direct; FB3 now feeds pin 58 alone
- LAN9252 LED strap direction corrected - the strap value latched at reset selects
  open-drain vs open-source, so the LED must follow it
- Shield and chassis grounding unified across all four connectors - see
  `docs/chassis-grounding.md`
- C1 (100n 16V 0402) on the MagJack centre taps replaced by C107 (1n/2kV 1206)
- U10 address straps: A0/A1/A2 to GND through R67 (0R) giving 0x50. The 24LC32 has **no**
  internal pulls - *"these inputs must be connected to either VCC or VSS"* - unlike onsemi's
  CAT24C32. WP is on jumper JP1 with R16
- J20 (30-way FFC) replaced by J21 (FH12-24S-0.5SH(55))
- TMC8100 symbol and footprint added to the project library; part not yet placed
- Watchdog pet line buffered (U8) with R69 pull-up and D3/R11 heartbeat LED
