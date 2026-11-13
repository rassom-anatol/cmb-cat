# Chassis and shield grounding

How connector shields reach chassis, and which components the integrator populates.
Settled 2026-11-09.

---

## The scheme

**Four chassis islands, no chassis ring or plane on the board.** Each mounting hole is an
isolated pad carrying its local connector shield. The islands interconnect **only through
the enclosure**, never through board copper, so the integrator decides the bonding topology
and the board cannot create a ground loop on its own.

Each island is soft-bonded to signal GND through **1 MΩ ∥ 1 nF / 2 kV**:

| Island | Net | Carries | R ∥ C |
|---|---|---|---|
| EtherCAT | `ECAT_MH` | `J18.3`, `J19.3` drains, `H3`, plus C104/C105 from the transformer centre taps | R63 ∥ C85 |
| Ethernet | `Net-(C108-Pad2)` | `U3.19/20` MagJack SHIELD, `H4` | R71 ∥ C108 |
| USB | `Net-(J5-SHIELD)` | `J5.SH` shell, `H2` | R70 ∥ C106 |
| Power | `Net-(C109-Pad1)` | `H1` only — no shield at the power entry | R66 ∥ C109 |

## Why a soft bond and not just a chassis pad

The board cannot assume the integrator fits metal standoffs. With plastic standoffs, or on a
bare board on a bench, islands with no bond would simply **float** — and a floating shield is
the worst of the available options: it is an antenna that picks up and re-radiates, and it
gives ESD nowhere to go except through the signal pins it was meant to protect.

The R ∥ C fixes that. With no chassis present, every island is still referenced to GND. ESD
on a shield sees the 1 nF, which is low impedance at ESD rise times, and the 1 MΩ bleeds
static so the island cannot drift.

## Stuffing

Three islands carry a schematic note; the power one does not, and is the permanent bond.

| Installation | EtherCAT | Ethernet | USB | Power | Result |
|---|---|---|---|---|---|
| Mounting holes bonded to chassis | remove | remove | remove | **keep** | one bond point; islands joined through the enclosure |
| No chassis (plastic standoffs, bare board) | keep | keep | keep | keep | four independent references |
| Mixed | remove where bonded | " | " | **keep** | see the caveat below |

**Never remove all four.** Three removed leaves one bond. Four removed leaves chassis and
signal GND with no defined relationship at all, which is worse for emissions, not better —
the board ground becomes a floating reference relative to the enclosure.

> **Caveat on mixed bonding.** The note is per-hole, so an integrator could bond the EtherCAT
> hole (removing R63 ∥ C85) while leaving the power hole unbonded. The EtherCAT island would
> then reach chassis, chassis would reach nothing, and the shield would float — the exact
> failure this scheme exists to prevent. **If any mounting hole is bonded to chassis, the
> power-entry hole (H1) must be among them.**

Power entry is the designated permanent bond because that is where cable-borne common-mode
current enters and leaves. Bonding there gives it a short path out, rather than letting it
cross the board to reach a bond sitting next to the EtherCAT magnetics.

## Mobile robots — floating chassis

The documented target market is mobile robots and arms, where the chassis is a floating metal
frame with no earth. The scheme still applies, but the reasoning inverts and it is worth
recording why the values do **not** change.

**The isolation argument largely disappears.** R ∥ C rather than 0 Ω exists to break DC
ground loops between separately-earthed equipment at different potentials. A mobile robot has
no earth and no second ground system, so there is no loop to break.

**Keep R ∥ C anyway — do not substitute 0 Ω.** The chassis on a mobile robot is a noisy
conductor: BLDC drives couple PWM common-mode onto the frame capacitively through the motor
windings and cabling, and those are large currents with fast edges. A hard bond injects that
straight into the signal ground reference. The 1 nF still provides the RF bond — roughly 5 Ω
at 30 MHz — while keeping the DC and low-frequency path out.

**The 1 MΩ earns its place here more than in an earthed cabinet.** A machine that moves
accumulates triboelectric charge, and a floating frame with no bleed path holds it until it
discharges somewhere of its own choosing.

**EtherCAT node-to-node isolation is mostly moot within one robot** — every node shares the
frame and the battery ground. It becomes load-bearing again the moment the robot is **docked
for charging or tethered to a diagnostic laptop**, because then there genuinely are two ground
systems. Worth not discarding the isolation on the grounds that it is all one machine.

Shields bonded to chassis at both ends of every EtherCAT link are fine here: the enclosed loop
area is small within one robot, and at these frequencies both-ends bonding beats one-end.

## Component choice

**1 nF / 2 kV in 1206, not 0805.** The 2 kV rating describes the ceramic between the
capacitor's own electrodes. What actually breaks down first is the board surface between the
chassis-side pad and the GND-side pad, and *that gap is the isolation barrier*:

| Case | Pad-to-pad gap | Overall land |
|---|---|---|
| 0603 | 0.65 mm | 2.45 mm |
| 0805 | 0.90 mm | 2.90 mm |
| **1206** | **1.80 mm** | 4.10 mm |

Ethernet's isolation requirement is 1500 Vrms for one minute, and EtherCAT inherits it. At
roughly 1 mm per kV of creepage on an uncoated surface that needs about 1.5 mm — more than
0805 provides, comfortably inside 1206. There are only three such caps and they sit in an
uncongested corner, so 1.2 mm of extra length each is a poor trade against halving the
barrier on the one component whose whole job is to be the barrier.

R63/R66/R70/R71 are 1 MΩ in **1210** for the same creepage reason, not for power.

> These gaps are KiCad's IPC-derived nominal lands. If the fab's solder-mask expansion or
> the project's clearance rules shrink them, the real creepage is whatever ends up on the
> board — check it in layout rather than trusting the library.

## Also settled here

`C107` replaced `C1` on the MagJack centre taps (`U3.4/5`). It was **100 nF 16 V in 0402**,
inherited from CM4IO, sitting in the Bob Smith position on the isolated side of the barrier
with no meaningful surge withstand. Now 1 nF / 2 kV in 1206, matching the EtherCAT side.

Mounting holes consolidated: H5–H8 (plain `MountingHole`, no pad) removed from the root
sheet; H1–H4 are the four pad-type holes.

## Open

**Classic Bob Smith uses 75 Ω from each centre tap** to the common node rather than tying
them directly. T1 and T2 bond TX and RX centre taps straight together, which loses some
common-mode damping. The LAN9252 EVB omits the resistors too, and for a short in-machine
harness it is commonly skipped — recorded so it is a known trade rather than an oversight.

**The EtherCAT "shield" is not a shell.** J18/J19 are JST GH — plastic body, no shield can.
Pin 3 is a drain-wire pin, so it only does anything if the harness is actually shielded
twisted pair. With unshielded discrete wires its real job is the crosstalk guard between the
TX and RX pairs.
