{
  lib,
  pkgs,
  ...
}:

{
  # Pin the currently tested series. Moving to a newer series is a deliberate
  # patch-rebase event rather than a side effect of updating nixpkgs.
  boot.kernelPackages = pkgs.linuxPackages_7_2;

  # HP firmware occasionally restores the Ryzen TSC with a discontinuity
  # after deep S0i3. Select a stable clocksource before any resume path can
  # consume a post-S0i3 TSC jump.
  boot.kernelParams = [ "tsc=unstable" ];

  boot.kernelPatches = [
    {
      name = "acpi-systemcmos-root-handler";
      patch = ./patches/linux/acpi-systemcmos-root-handler.patch;
    }
    {
      name = "amd-pmc-rtc-wake-fallback";
      patch = ./patches/linux/amd-pmc-rtc-fallback.patch;
    }
    {
      name = "amd-pmc-hp-nvme-smi-quirk";
      patch = ./patches/linux/amd-pmc-hp-nvme-smi-quirk.patch;
    }
  ];

  # Keep a boot-menu recovery entry using the same kernel series without the
  # local patches. The TSC parameter remains because it is independently
  # recommended by the kernel's clocksource validation on this machine.
  specialisation.stock-kernel = {
    inheritParentConfig = true;
    configuration.boot.kernelPatches = lib.mkForce [ ];
  };

  # Avoid systemd's second userspace freeze. On this machine it can deadlock a
  # FUSE client after the kernel PM freezer has already frozen the FUSE server.
  systemd.services.systemd-suspend.environment = {
    SYSTEMD_SLEEP_FREEZE_USER_SESSIONS = "false";
  };

  services.udev.extraRules = ''
    # Prevent attached USB mice from causing closed-lid wakeups.
    ACTION=="add", SUBSYSTEM=="usb", ENV{ID_USB_INTERFACES}=="*:030102:*", TEST=="power/wakeup", ATTR{power/wakeup}="disabled"

    # Texas Instruments TI-84 Plus CE direct user access for CEmu/TI Connect.
    SUBSYSTEM=="usb", ATTR{idVendor}=="0451", ATTR{idProduct}=="e008", TAG+="uaccess"
  '';
}
