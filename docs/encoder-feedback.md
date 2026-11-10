# Encoder feedback architecture — SSI / BiSS-C and the TMC4671

Why the TMC8100 is on the pin plan, whether it needs to be, and how absolute encoders
should reach the motion controllers. Worked out 2026-11-09 against the TMC4671, TMC6460
and TMC8100 datasheets held in `~/Documents/TMC/`.

---

## The problem

**CMC101 uses a TMC4671, which has no SSI or BiSS-C interface.** Its feedback engine
handles ABN, digital/analog Hall and analog SinCos. Absolute serial encoders are not among
them. CMC301's TMC6460 is better placed but not by as much as its feature list suggests
(see below).

The original plan was to put a TMC8100 protocol converter on CMB-CAT, have the CM4 read
position from it and write that into the TMC4671's external-angle register at about 1 kHz
once PREEMPT_RT is running.

---

## Why host-supplied commutation angle does not work above very low speed

`PHI_E_EXT` (0x1Ch) exists and `PHI_E_SELECTION = 1` selects it, so the mechanism is real.
Two findings kill it as a commutation path.

**The TMC4671 has no extrapolation.** The string "extrapolat" does not appear anywhere in
its datasheet. (The TMC6460 does have a Phi Extrapolator; the TMC4671 does not.) So
`PHI_E_EXT` is a zero-order hold: the angle written is used unchanged until the next write.

**Commutation error is then `360 x Npp x n x dt`.** With 7 pole pairs at a 1 kHz update:

| Motor rpm | phi_e error | Torque remaining |
|---|---|---|
| 100 | 4 deg | 100% |
| 240 | 10 deg | 98% |
| 500 | 21 deg | 93% |
| 1000 | 42 deg | 74% |
| 2000 | 84 deg | 10% |
| 3000 | 126 deg | 0%, torque reverses |

The practical ceiling is about **240 rpm at the motor shaft** for a 10 degree error. Running
3000 rpm within 10 degrees needs a **79 us update, i.e. 12.6 kHz** — and that is *two* SPI
round-trips per cycle (read the TMC8100, write the TMC4671). Not achievable from Linux,
PREEMPT_RT or not.

Also note the datasheet's own register table classes `PHI_E_EXT` under **Usage: Test**,
next to `OPENLOOP_PHI`. It was not intended as a production feedback path.

If this path is ever revisited, host-side extrapolation is the one change that would make it
viable over a useful range: read position *and velocity*, predict the angle for the moment
the write lands. Residual error then tracks jitter rather than update period, so **jitter
becomes the spec that matters, not rate.**

---

## Recommended architecture: ABN commutates, absolute re-references

Keep both loops in TMC4671 hardware and use the absolute encoder only to establish truth at
startup.

```
PHI_E_SELECTION   = 3   (phi_e_abn)    commutation, hardware, full bandwidth
POSITION_SELECTION = 9  (phi_m_abn)    position loop, hardware, full bandwidth
absolute encoder  ->  host  ->  writes the reference at boot, corrects rarely
```

`POSITION_SELECTION` (0x51) is independent of `PHI_E_SELECTION` (0x52), so the two loops can
take different sources.

**Do not use `POSITION_SELECTION = 1` (phi_e_ext) for absolute position.** `phi_e_ext` is a
16-bit *electrical* angle — it wraps every 1/Npp mechanical revolution (every 51 degrees with
7 pole pairs). Useless as an absolute position reference.

### The registers that make it work — all writable at init

| Register | Addr | Use |
|---|---|---|
| `ABN_DECODER_PPR` | 0x26h | encoder pulses per mechanical revolution |
| `ABN_DECODER_COUNT` | 0x27h | seed the count from the absolute reading |
| `ABN_DECODER_PHI_E_PHI_M_OFFSET` | 0x29h | commutation offset, computed from absolute |
| `PID_POSITION_ACTUAL` | 0x6Bh | seed true multi-turn position (RW, Monitor/Init) |

**The real prize is startup alignment.** Read absolute position once at power-up, derive the
rotor's electrical angle, write the offset and seed the counters. You get correct commutation
from the first PWM cycle with **no alignment move** — no jolt, no hard-stop homing — and true
absolute position after power loss. One transaction at boot, not 1 kHz.

### Caveats

**Resolution.** The position loop now resolves to ABN counts, not encoder bits. A 2048 ppr
ABN gives 8192 counts/rev against roughly 8.4 M from a 23-bit absolute. If the application
needs the fine resolution in the loop, this scheme discards it and the absolute has to be in
the loop after all — though only for the position loop, which tolerates latency far better
than commutation does.

**Never write `PID_POSITION_ACTUAL` while moving.** It steps the feedback, the position PID
sees an error step, and a torque transient follows. Correct at startup, when stationary, or
ramp the correction in.

**Both signals are needed.** Either one encoder providing BiSS/SSI *and* incremental A/B, or
two sensors. Many BiSS encoders do offer incremental, but not all — confirm against the
encoders actually to be supported.

---

## What the silicon actually supports, as opposed to what the feature lists claim

### TMC6460 — SSI real, BiSS-C not

SSI is properly documented: a `SPI_ENC` ROM feature with pin assignment (Table 53), SPI mode,
request type, `SCK_HALF_PERIOD`, bit count, CS-high timing and mask/shift examples
(Table 55), writing position straight into `FEEDBACK.PHI_EXT_A/B`. Usable as written, with
limits:

- **32 bits maximum.** *"Longer datagrams are not supported by this ROM feature."* A 25-bit
  single-turn plus 12-bit multi-turn encoder is 37 bits before status and CRC.
- **SCK 117.2 kHz to 3 MHz**, from `f_SYS / ((SCK_HALF_PERIOD+1) x 2)`.
- **Costs the HALL_W pin.** `DIRECT_OUT[2]` is only available there, so a full SPI encoder
  removes digital Hall, analog Hall and SinCos as a second feedback source, and the second
  ABN's N channel. SSI escapes this only because it needs 2-3 wires and CSN/SDO can be
  swapped.

BiSS-C appears **once in the entire datasheet**: *"Additional encoder protocols such as
BiSS-C, Tamagawa T-format, and more can be integrated to the TMC6460 by uploading a custom
program to the integrated I/O Controller."* The I/O Controller's instruction set is **not
documented** — *"opcodes are part of an additional application note."* BiSS-C is not in the
ROM feature table. Treat it as a marketing sentence, not a supported feature.

### TMC8100 — verify BiSS before committing

Same pattern: **BiSS mentioned once, EnDat once, SSI 42 times.** The difference is that the
TMC8100 is a programmable protocol converter and BiSS-C is on its front-page feature list, so
support presumably ships as a loadable program.

**Before committing to the part, confirm with ADI that a BiSS-C program exists for it, is
available, and what it costs.** BiSS-C itself is licence-free; EnDat needs a Heidenhain
agreement. If that program does not exist, the TMC8100 only buys SSI, which the TMC6460
already does natively.

**The TMC8100 cannot emulate a quadrature output.** This was checked because feeding
TMC8100 -> TMC4671 in hardware would have been the ideal topology. `DECODER_OUT`
*"generates one pulse with programmable length for each encoder counter increment or
decrement"* — a step pulse with no direction, not A/B. There is no hardware bridge from the
TMC8100 to a TMC4671 ABN input.

---

## Consequences for the board

- Under the recommended architecture the TMC8100 is only needed **at startup and for slow
  drift checks**, so its latency stops mattering.
- If the encoders to be supported are **SSI rather than BiSS-C**, a plain SPI read from the
  CM4 does the same job and the chip can be dropped. SSI is clock-and-data with no chip
  select: SPI master, dummy writes, read MISO, Gray-decode. RS-422 transceivers are needed
  either way.
- `cm4-pin-plan.xlsx` currently places the TMC8100 on `SPI4_CE1_N` — host-side, not between
  the encoder and the motion controller. That placement is right for this architecture
  (the host reads absolute position and re-references), but it was originally chosen on the
  assumption of host-in-the-loop commutation, so the reasoning should be re-recorded.
- The symbol and footprint exist in the project library (`cmb-cat:TMC8100`,
  `cmb-cat:TQFN-24_Maxim_T2444_4x4mm_P0.5mm_EP2.6x2.6mm`) but the part is **not placed on any
  sheet**, so nothing is committed yet either way.

### Alternatives if BiSS-C is a firm requirement

| Option | Notes |
|---|---|
| TMC8100 | Works if ADI ships the BiSS-C program. 24-pin TQFN, already drawn. |
| iC-Haus `iC-MB4` | Purpose-built BiSS/SSI master, BiSS-C licensed. |
| RP2040 | PIO is built for bit-level protocols; BiSS-C PIO implementations exist; familiar toolchain, cheap, very available. Spare PIO for other timing-critical work. |
| TMC6460 on CMC101 | Native SSI plus a Phi Extrapolator. A board change, but removes the problem by construction. |
