# Local Linux patches

These patches are tested on the HP Laptop 14-fq1xxx, board 887C, BIOS F.38,
with the Linux 7.2 series from the locked NixOS 26.05 input.

- `acpi-systemcmos-root-handler.patch` installs the SystemCMOS address-space
  handler at the ACPI root so sibling RTC/TAD devices can inherit it.
- `amd-pmc-rtc-fallback.patch` preserves RTC wake by avoiding deep S0i3 when
  an alarm cannot be represented by the AMD SMU secondary timer.
- `amd-pmc-hp-nvme-smi-quirk.patch` selects AMD-PMC's restore-early quirk for
  this HP board to avoid the firmware NVMe resume SMI stall.

Treat a kernel-series change as a patch rebase. Build the full NixOS closure
and verify suspend, RTC wake, lid wake policy, NVMe, USB, and audio before
switching. The `stock-kernel` specialization is the recovery path.
