# CMB-CAT / CMC — security notes

Working notes, 2026-10-24. Discussion-stage; nothing here is implemented.

Context: CMC already carries an **ATSHA204A-MAHDA-T** (I2C, 8-pad UDFN). These notes
cover what that part can and cannot do for this product, and where the design should
rely on something else.

---

## Part status

`ATSHA204A-MAHDA-T` is the **I2C** variant in 8-pad UDFN, tape and reel. It suits the
I2C bus already planned on CMB-CAT for the board EEPROMs and GPIO expander.

The "not recommended for new design" note in the datasheet attaches to the **TSSOP
package drawing**, not to this package.

**Capabilities:** SHA-256 / HMAC symmetric authentication, host *and* client operation,
16 key slots at 256 bits, guaranteed-unique 72-bit serial, internal RNG, 4.5 kb EEPROM,
512-bit OTP, 2.0–5.5 V supply.

---

## Why a secure element belongs here regardless

**IEC 62443.** SL2 and above expects cryptographic boot verification and secure key
storage for controllers. A secure element is the standard way to satisfy it. Microchip's
[AN3983, *Demystifying ISA/IEC 62443 and Secure Elements*](https://ww1.microchip.com/downloads/en/Appnotes/Demystifying-ISA-IEC-62443-and-Secure-Elements-DS00003983.pdf)
is effectively the justification document for this part.

**EtherCAT has no security of its own.** It is raw Ethernet with no authentication or
encryption, so device identity has to come from somewhere else.

**Signed firmware update with anti-rollback.** ATECC608B + MCUboot + ECDSA P-256 is a
documented pattern aligned to IEC 62443-4-2.

---

## Anti-counterfeiting: assessed and set aside

### The reasoning

Open-sourcing the software does **not** by itself break hardware authentication.
Kerckhoffs's principle holds: publishing the verification algorithm reveals nothing, the
key lives in silicon with no read-back path, and provisioning keys stay closed even when
the code is open.

What open source *does* break is a **pass/fail gate**. `if (!authenticate()) exit();`
running on a CM4 whose filesystem the user controls is deleted and recompiled in five
minutes.

The construction that would survive is to make the crypto result a **functional
dependency** rather than a check — encrypt something operationally necessary under a key
only a genuine chip can reproduce, so there is no boolean to patch, just data that fails
to decrypt.

### Why it does not apply to CMC

That construction needs a secret the legitimate system holds and the user cannot
recreate. CMC has none:

- **Calibration is user-generated** and specific to each customer's mechanical setup, so
  there is no factory-provisioned blob to encrypt.
- **CMC has no MCU** — TMC4671 + TMC6200 are configured over SPI by the CM4 — so there is
  no firmware image to sign on the board itself.
- **The software is open source**, so the configuration know-how is published too.

With no secret payload, authentication collapses back to a patchable check.

### What a counterfeiter can and cannot do

- **Cannot** obtain the key. ATSHA204A is sold openly, but a chip they provision holds
  *their* secret. Producing valid responses needs key extraction from a genuine part
  (what the hardware key storage resists) or brute-forcing 256 bits.
- **Can** harvest genuine chips from real CMCs — works, but costs a genuine board per
  fake, so the economics collapse.
- **Can** sell to complicit customers running patched software. Unavoidable when the
  attacker owns the host.
- **Can** ship a complete competing ecosystem — their board, their keys, their software
  fork. This is **competition, not counterfeiting**, and publishing the hardware design
  makes it legal and expected. Crypto never prevented this.

### Conclusion

Drop the anti-counterfeiting expectation and **do not let it shape the architecture**.
For an open-source product aimed at robotics startups, the moat is support,
documentation, and the quality of the EtherCAT and ROS integration.

---

## What to actually use the chip for

**Device identity and traceability.** Provable serial number, manufacturing provenance,
field-return verification, fleet inventory. Unaffected by open source and operationally
useful to customers.

**IEC 62443 posture.** Secure key storage, secure boot of the CM4 image, signed update
verification, device identity on the fieldbus.

**Detection rather than prevention.** Report a non-genuine board — UI warning, log entry,
refused support ticket. Stops nobody, but makes fakes visibly second-class and provides
evidence when a customer presents a board that is not yours.

**Binding calibration to a board — for safety, not anti-counterfeiting.** Encrypt or MAC
the user's calibration against that board's key so a calibration cannot silently be
applied to a different drive/motor pairing. That is a genuine failure mode in multi-axis
robots. It does not stop a counterfeiter, who simply recalibrates.

---

## Open question: ATSHA204A vs ATECC608B

ATSHA204A is **symmetric**, so whatever verifies a response must hold the same key. If
that verifier is the CM4, the key sits in the eMMC image and is extractable by anyone
with physical access — which is awkward for an open-source product.

Three ways out:

1. **Second ATSHA204A on CMB-CAT** as the host-side device. The part supports host and
   client operation, and CMB-CAT already has the I2C bus. Cheapest fix.
2. **Verify against a remote service.** Unattractive for offline robots.
3. **Move to ATECC608B** (asymmetric, ECDSA P-256). The verifier holds only a public key,
   so the entire verification path — host code and key — could be published without
   enabling forgery. Much more comfortable with open source, and it additionally enables
   secure boot and TLS.

**Leaning:** ATECC608B for new work, given the IEC 62443 direction and the open-source
publishing model. Keeping ATSHA204A on CMC is fine if its role is narrowed to identity
and traceability.

---

## Related

- Component and architecture notes: `component-notes.md`
- Architecture diagram: `architecture.drawio`
- ATSHA204A datasheet: `/home/rasid/Documents/TMC/Datasheets/ATSHA204A-Data-Sheet-40002025A.pdf`
