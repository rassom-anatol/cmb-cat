# CMB-CAT — component and architecture notes

Working notes from design discussion, 2026-10-24. Nothing here is committed to a
schematic yet. Figures are cited to their source so they can be re-checked.

---

## Power input

**Decision: no onboard wide-input converter. CMB-CAT takes external 5V.**

Rationale: CMC targets robotics startups — mobile robots, arms — where the input is
anything from a 24V pack to a 48V pack to an AC/DC supply in a stationary machine.
Rather than try to cover that range on the carrier, the power stage is pushed out to a
separate module, so CMB and CMC stay voltage-agnostic and never need a respin when the
input changes.

### Constraints this creates

- **CM4 input window is 4.75–5.25 V at the connector** (datasheet pin 77/79). Only
  250 mV of droop budget.
- CM4 idle draw is **400 mA typical**, considerably more under load, plus four
  controller boards.
- Therefore: short, properly sized board-to-board connection or a fat short harness.
  Not a thin pigtail. Put real bulk capacitance on CMB to ride out motion transients —
  robot load steps are large and fast.
- Add a TVS on the 5V input. It arrives over a cable in a machine full of inductive loads.

### Open item

Consider selling or qualifying a **reference power module**. Left fully open, customers
improvise, their 5V sags, and the resulting failures look like CMB-CAT bugs.

### Why the inherited CM4IO regulator does not apply

CM4IO uses AP64501SP-13 / AP64351, both **3.8–40 V input**. CMC's bus goes to 48V — the
`VM_LP` annotations spell out the 24/36/48V cases and C30/C27 are 63V bulk caps. A
charged 13S pack sits near 54.6V. So those parts are a 12/24V-only solution. Harvest the
topology and layout practice from the CM4IO `PSUs` sheet, but reselect the controller if
an onboard converter is ever revisited.

---

## 3.3V rail

CM4_3.3V is an **output** rated 300 mA per pin, **600 mA total** (connector pins 84/86),
and the datasheet separately asks that total GPIO loading stay under 50 mA. That is not
enough for this system, so CMB-CAT carries its own 5V→3.3V converter.

### Budget

| Load | mA | Source |
|---|---|---|
| LAN9252 device, D0 100BASE-TX with traffic, internal regulator enabled | 112 (typ) | DS00001909A Table 18-5 |
| LAN9252 TX magnetics, 3.3V, both PHYs copper | 82 | Table 18-5, note 18 |
| TMC4671 `VCCIO` | 70 (max) | `I_IO` absolute max, DS rev 2.08 Table 35 |
| TMC6200 `VCCIO` | 0.03 | 30 µA, negligible |
| 3× TMC6460 `VCC_IO` | 75 (max) | `IVCCIO_DRVOFF` 25 mA max each |
| 3× TMC6460 `VCC_IOF` | 0.3 | negligible |
| **Subtotal** | **~340** | |

Not in the subtotal but real: GPIO expander, four EEPROMs, pull-ups, CMC's 74LVC
buffers, and the Ethernet LEDs — the LAN9252 figures explicitly exclude external LEDs,
and four to six of those is another 30–60 mA.

**Design to ~500 mA.** LAN9252 numbers are typical with no max column published, so do
not size tight.

### Candidate regulators — fully integrated, inductor in package

| Part | Vin | Iout | Package | Output | Note |
|---|---|---|---|---|---|
| **MPS MPM3810** | 2.5–6 V | 1.2 A pk | QFN-12, 2.5 × 3.0 × 0.9 mm | **fixed 3.3V** | Preferred. 0.47 µH integrated. `-AEC1` is automotive-qualified. |
| ADI/Maxim MAXM17630 | 4.5–36 V | 1 A | uSLIC-16, 3.0 × 3.0 × 1.75 mm | **fixed 3.3V** | 900 kHz. 4.5V minimum is only 250 mV under worst-case rail. |
| TI TPS82140 | 3–17 V | 2 A | MicroSiP, 3.0 × 2.8 × 1.5 mm | adjustable | Needs a feedback divider. |
| MPS MPM3620A | 24 V | 2 A | — | adjustable | If a wider input is ever wanted. |

**Preference: MPM3810 fixed 3.3V.** Smallest and thinnest, fixed output so no divider,
and its 2.5–6 V window matches the actual input instead of buying headroom the design
has already engineered away. MAXM17630's only edge is input range that CMB-CAT does not use.

ADI has no low-Vin equivalent: MAXM17225 is a boost, MAXM15462 is 300 mA,
MAXM17532 is 100 mA, MAX17270 is a SIMO buck-boost.

---

## EtherCAT IN / OUT connectors

The LAN9252 (TQFP-EP64) integrates two 100BASE-TX PHYs, so ports 0 and 1 need only
magnetics plus a connector. Port 2 is MII and is unused. **The integrated PHY removes the
PHY chip, not the magnetics** — isolation is a transformer function.

### Connector options

- **M8 4-pin D-coded — recommended.** The de-facto compact industrial Ethernet connector,
  rated 100 Mbit/s, which is exactly what EtherCAT needs. ~30% less installation space
  than RJ45 and screw-locked, so it tolerates vibration. Standardized pinout, off-the-shelf
  cables. Phoenix Contact, Murrelektronik, TE, Turck, Harting, CONEC. Panel-mount and
  PCB-mount receptacles both available.
- **Harting ix Industrial** — ~70% smaller than RJ45, Cat6A, but IP20, so inside-enclosure only.
- **JST GH/SH or Molex PicoBlade, 4-pin** — for daisy-chaining drives inside one enclosure.
  Smallest and cheapest, but unshielded and unlatched. Not for anything leaving the box.
- **Sunk-type / mid-mount RJ45 with integrated magnetics** — body drops into a PCB cutout,
  roughly halving height above board. Mostly through-hole; THT shield tabs recommended to
  anchor it. Specify a **1000BASE** part if used for the CM4's own gigabit port — many
  low-profile magjacks are 10/100 only. The cutout interrupts the ground plane exactly
  where the MDI pairs route, which can cost more than the height it saves.

### Magnetics

Discrete 10/100 1CT:1CT SMD transformers, **two required**, one per EtherCAT port.

- **Halo TG110** family, e.g. `TG110-E050N5LF` — 16-pin SMD, 12.70 × 7.11 × 6.35 mm
- Equivalents: Pulse `H1102NL`, Bel Fuse, LINK-PP `LP1102NL` / `LP1183NL`

Follow Microchip's **LAN9252 schematic checklist** for termination and coupling.

**Area caution:** two TG110s plus two M8 receptacles plus Bob Smith termination is not
obviously smaller than two sunk RJ45 magjacks — the magnetics have moved from inside the
connector onto the board. The real wins are mechanical robustness and enclosure sealing,
not necessarily PCB area.

Note the CM4's own Ethernet port is **gigabit** and needs different magnetics from the
10/100 EtherCAT ports. Two distinct part numbers on one board — easy to confuse when
laying out near-identical connectors.

---

## Host network port

**Keep the CM4's gigabit Ethernet.** The PHY is already on the module and paid for; the
incremental cost of using it is one magjack and four differential pairs.

- **A USB-to-Ethernet adapter is strictly worse.** Any BASE-T interface still needs
  isolation magnetics, so the magjack stays, and you have added a chip, board area, and a
  downgrade from gigabit to USB2-limited throughput.
- **USB3 remains unavailable** — it needs the PCIe lane for a VL805, and PCIe is dropped.
- **USB gadget mode is an addition, not a replacement.** The USB-C is already present for
  `rpiboot` recovery; device mode gives gadget Ethernet over the same connector for free.
- If the RJ45's **size or ruggedness** is the real constraint, keep the CM4 Ethernet but
  drop the magjack: discrete magnetics feeding an M8/M12 or board-to-board connector out
  to a backplane. Keeps gigabit, loses the fragile latch and the dust ingress.

---

## Related

- Pin allocation and conflicts: `../cm4-pin-plan.xlsx`
- Architecture diagram: `architecture.drawio`, notes in `architecture-notes.md`
- CMC header usage: `/home/rasid/Documents/TMC/CMC/CMC_RPi_GPIO_Usage.xlsx`
