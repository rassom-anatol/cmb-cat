# CMB-CAT architecture — notes on the diagram

Diagram source: [`architecture.mmd`](architecture.mmd)

Comments are kept out of the `.mmd` because the visual editor collapses a leading
`%%` block into line 1 and breaks the parse. Keep `flowchart LR` as line 1.

## Assumptions to correct

- **Controller placement.** CMC is shown on the 40-pin header and controllers 2–4
  on the FFC. You said "the other" in the singular — adjust if they are split
  across more connectors, or if each gets its own FFC.
- **SPI allocation.** The diagram shows the stated plan of five dedicated buses:
  SPI0 → LAN9252, SPI3 → CMC, SPI4/5/6 → the FFC controllers.
  **Open:** dropping SPI5 returns GPIO14/15 for a UART console and GPIO12/13 for
  hardware PWM0, at the cost of two controllers sharing SPI6 via CE0/CE1.
  See `../cm4-pin-plan.xlsx`.
- **Input rail.** 12 V or 24 V undecided. AP64501/AP64351 accept 3.8–40 V, so the
  regulator topology carries over either way; passives and thermals need review at 24 V.

## Fixed facts encoded in the diagram

- CM4 must be an **eMMC variant** — microSD is dropped.
- LAN9252 TQFP-EP64 has **two integrated 100BASE-TX PHYs**, so ports 0/1 need only
  magnetics + RJ45. Port 2 is MII and is unused.
- EtherCAT magnetics are **10/100**; the CM4's own port needs **gigabit** magnetics.
  Two different magjack part numbers on one board.
- **I2C0 lives on GPIO44/45** (CM4 connector pins 82/80, internal 1.8 kΩ pull-ups),
  free because CSI1/DSI1 are unused.
- USB-C is **dual role** — device mode is the only `rpiboot` recovery path once
  microSD is gone.
