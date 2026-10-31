# CM5 evaluation — considered and deferred

Evaluated 2026-10-31. **Decision: stay on CM4 for CMB-CAT.** A separate CM5 board is
planned later. Reason for deferral: no CM5 hardware on hand, and the performance
question cannot be settled without measurement.

The CM5 rebase exists in this repo at tag `cm5-evaluation` (local) — CM5IO rev 2
(RP-008099-DD-1) installed pristine, KiCad 9 format.

---

## The pin allocation transfers unchanged

Verified against the CM5 datasheet (RP-008180-DS-7) alt-function table. Instance numbers
shift but pin groups are identical, so **no schematic change is needed**:

| CMB-CAT plan (CM4) | CM5 equivalent | Pins |
|---|---|---|
| SPI0 → LAN9252 | SPI0 (a0) | GPIO8–11, same |
| SPI3 + CE1 GPIO24 | SPI2 (a8), CSn[1] GPIO24 | same |
| SPI4 + CE1 GPIO25 | SPI3 (a8), CSn[1] GPIO25 | same |
| SPI6 + CE1 GPIO27 | SPI1 (a0), CSn[1] GPIO27 | same |
| PWM0 / PWM1 | PWM0[0] / PWM0[1] (a0) | GPIO12/13, same |
| UART0 console | UART0_TX / UART0_RX (a4) | GPIO14/15, same |
| I2C0 on connector pins 82/80 | SDA0/SCL0, GPIO38/39 on RP1 | same connector pins, same 1.8 kΩ pull-ups |

Only overlay names and Linux bus numbers differ.

### RP1 SSI instance table (datasheet §3.6.1) — note the trap

| Instance | Role | Chip selects | Max I/O |
|---|---|---|---|
| SPI0 | Master | 4 | Quad |
| SPI1 | Master | 3 | Dual |
| SPI2 | Master | 2 | Dual |
| SPI3 | Master | 2 | Dual |
| **SPI4** | **Slave** | 1 | Single |
| SPI5 | Master | 2 | Dual |

**SPI4 is slave-only** yet appears on GPIO8–11 in the CM5 pin table. Easy to misuse.
Also: SPI2 and SPI3 have only **2 chip selects**, and the plan needs exactly 2 on each —
zero spare.

---

## What CM5 would gain

- **Native RTC** — `VBAT` on pin 76. Deletes the PCF8563T circuit.
- **Native fan control** — `Fan_tacho` pin 16, `Fan_PWM` pin 19. Deletes the EMC2301.
- **Two native USB 3.0 ports** on the otherwise-unused CAM0 (128–142) and DSI0 (157–171)
  pins. USB3 **without** consuming the PCIe lane — reverses the CM4 constraint entirely.
- `nRPIBOOT`, `USB_OTG_ID`, `USB_P/N` unchanged, so recovery is identical.

## What CM5 would cost

- **Power: 5 V at up to 2.5 A for the module alone** (datasheet §B.3). The 5 V 3 A input
  would not close; closer to 5 A needed with LAN9252 and four drives' logic.
- **ESD protection removed** from SDA/SCL versus CM4 — the carrier must add it.
- **`nEXTRST` is gone** (pin 100 is now `CAM_GPIO1`) and `RUN_PG` became `PWR_Button`.
  The supervisor scheme needs rework around `PMIC_ENABLE` (pin 99).
- Higher module cost and more heat.
- Pin 76 is **"Reserved — do not connect"** on CM4, so a CM5-wired battery must be
  jumpered out before fitting a CM4 to the same board.

---

## The open performance question

RP1 peripherals sit behind PCIe. A separate analysis predicted CM5 would be **slower per
SPI transfer** than CM4 for this workload, because each register read is a PCIe round trip
(datasheet §3.3.1: ~1 µs link latency, doubled for reads) and the design makes many small
transfers — measured at 188 µs across 21 transfers per 1 ms cycle on CM4.

### What weakens that prediction

RP1 Chapter 9 describes an 8-channel AXI DMAC whose stated purpose is exactly this:

> ...to service low-bandwidth APB peripherals and interface with their flow control
> handshakes to pace DMA transfers across PCIe. A secondary intent is that DMA traffic can
> be more efficiently bursted across the PCIe using this controller, as each TLP carries a
> fixed overhead that becomes large when small (e.g. single 32-bit) transfers are used.

"Almost all peripherals are connected, with the exception of I2C6" — so SPI has a DMAC
handshake. On the DMA path the FIFO is drained locally inside RP1 and results cross PCIe
as burst posted writes (~2 Gbps), not per-byte non-posted reads. The pessimistic estimate
holds **only on the PIO path**, and whether the `dw-spi` driver takes DMA for 5–40 byte
transfers is a driver-threshold question.

### Interrupt path is genuinely worse on CM5

`LAN9252-SYNC0` is a GPIO interrupt. On CM4 that is on-die. On CM5 it travels
pad → RP1 interrupt controller → **MSI-X over PCIe** → host GIC → kernel (RP1 datasheet
§6.2, with an interrupt-to-message translation block for level-sensitive sources).
PREEMPT_RT bounds scheduling latency, not this.

### Bench plan for when hardware is available

Run `tools/bus_bench.c` on a CM5 IO board with a TMC4671 and LAN9252 attached. Compare
median per datagram against the CM4 baseline of 10.5 µs, across four variables:

1. ASPM on vs off (§3.3.1.3: adds ~2 µs L0s / ~5 µs L1 on first access after idle; a 1 ms
   cycle idles between wake-ups, so this hits every cycle — likely must be disabled)
2. **DMA forced on vs off** — the variable that actually decides it
3. **Batched vs unbatched** — submitting the 21 transfers as one `spi_message` amortises
   per-transfer overhead, and matters far more on CM5 than CM4
4. **Frame size** — DW_apb_ssi supports up to 32-bit frames; if RP1 exposes that, a 40-bit
   datagram is 2 FIFO accesses instead of 5

Measure end-to-end SYNC0 edge → IRQ → thread → SPI complete, at the 99.9th percentile.
`cyclictest` alone measures timer-to-thread wakeup, which is the easy path and will look
fine on both.

### Clock divider note

RP1 SPI derives from `clk_sys` (typically 200 MHz) through a divider that must be even.
That gives exactly 25 MHz for the LAN9252, but no exact 8 MHz for the TMC4671 — nearest
are 7.69 MHz and 8.33 MHz.

---

## The underlying issue, independent of module

188 µs of SPI per 1 ms cycle is already 19% of the budget, in userspace on a non-realtime
kernel. That is fragile on any host and a kernel update can move it. The TMC4671 and
TMC6460 close their own current and velocity loops, and EtherCAT distributed clocks exist
to synchronise the *drives*, not the host. Whether the host needs 21 round trips per
millisecond is worth revisiting before module choice is treated as load-bearing.

One relaxation: CMB-CAT is an EtherCAT **slave**. The LAN9252 has 4 KB DPRAM and
SyncManagers buffering process data, so the host must complete within the cycle rather
than respond in microseconds — considerably more forgiving than master-side timing.

---

## Ubuntu 26.04 note

PREEMPT_RT is in the main archive from 26.04 — `sudo apt install ubuntu-realtime`, **no
Ubuntu Pro subscription**, which removes a per-machine cost on a shipped product. Caution:
Ubuntu's RP1/CM5 support is downstream of Raspberry Pi's, and PREEMPT_RT has been mainline
since 6.12, so building the Pi kernel with it is also an option.

---

## Related

- `component-notes.md`, `security-notes.md`, `architecture.drawio`
- CM5 datasheet: `/home/rasid/Documents/RPi/RP-008180-DS-7-cm5-datasheet.pdf`
- RP1 peripherals: `/home/rasid/Documents/RPi/RP-008370-DS-1-rp1-peripherals.pdf`
- CM5IO rev 2 KiCad: `/home/rasid/Documents/RPi/RP-008099-DD-1-CM5 IO Board, revision 2, KiCAD files..zip`
