{
  config,
  pkgs,
  ...
}:

{
  programs.niri = {
    enable = true;

    # Avoid the deprecated no-argument systemd environment import in the
    # upstream niri-session wrapper. --replace-fail makes upstream drift fail
    # at build time instead of silently losing the workaround.
    package = pkgs.niri.overrideAttrs (old: {
      postFixup = (old.postFixup or "") + ''
        substituteInPlace $out/bin/niri-session \
          --replace-fail \
            "systemctl --user import-environment" \
            "systemctl --user import-environment PATH XDG_RUNTIME_DIR XDG_CURRENT_DESKTOP XDG_SESSION_TYPE"
      '';
    });
  };

  systemd.user.extraConfig = ''
    DefaultTimeoutStopSec=10s
  '';

  services.greetd = {
    enable = true;
    settings = {
      initial_session = {
        command = "${config.programs.niri.package}/bin/niri-session";
        user = "bob";
      };
      default_session = {
        command = "${config.programs.niri.package}/bin/niri-session";
        user = "bob";
      };
    };
  };

  programs.dconf.enable = true;
  security.polkit.enable = true;

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
  ];

  services = {
    flatpak.enable = true;
    cloudflare-warp.enable = true;
    gvfs.enable = true;
    udisks2.enable = true;
    tumbler.enable = true;
  };

  programs.thunar = {
    enable = true;
    plugins = with pkgs; [
      thunar-archive-plugin
      thunar-volman
    ];
  };

  hardware = {
    graphics.enable = true;
    i2c.enable = true;
    bluetooth.enable = true;
  };

  # This machine only uses Bluetooth as an A2DP source (for audio playback).
  # Add hfp_hf if a Bluetooth headset microphone is needed later.
  services.pipewire.wireplumber.extraConfig."10-bluetooth" = {
    "monitor.bluez.properties" = {
      "bluez5.roles" = [ "a2dp_source" ];
    };
  };

  programs.dank-material-shell = {
    enable = true;
    systemd.enable = true;
    enableSystemMonitoring = true;
    enableVPN = true;
    enableDynamicTheming = true;
    enableAudioWavelength = true;
    enableCalendarEvents = true;
  };
}
