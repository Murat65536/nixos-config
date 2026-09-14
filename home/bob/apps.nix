{
  pkgs,
  equibopWithoutVaapiEncoder,
  hermesAgent,
  lightpanda,
  ...
}:

{
  home.packages = with pkgs; [
    anki
    chromium
    equibopWithoutVaapiEncoder
    hermesAgent.hermesDesktop
    obs-studio
    obsidian
    papirus-icon-theme
    (symlinkJoin {
      name = "sioyek";
      paths = [ sioyek ];
      nativeBuildInputs = [ makeWrapper ];
      postBuild = ''
        wrapProgram $out/bin/sioyek \
          --prefix XDG_DATA_DIRS : "${gtk3}/share/gsettings-schemas/${gtk3.name}:${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}"
      '';
    })
    slack
    vlc
    xwayland-satellite
    freecad
    ffmpeg
    yt-dlp
    localsend
    cursor-cli
    qwen-code
    lightpanda
    (symlinkJoin {
      name = "en-croissant";
      paths = [ en-croissant ];
      nativeBuildInputs = [ makeWrapper ];
      postBuild = ''
        wrapProgram $out/bin/en-croissant \
          --prefix GIO_EXTRA_MODULES : "${glib-networking}/lib/gio/modules"
      '';
    })
    lc0
    taskwarrior3
    taskwarrior-tui

    # FRC tools
    advantagescope
    choreo
    elastic-dashboard
    pathplanner
    wpilib.datalogtool
    wpilib.glass
    wpilib.outlineviewer
    wpilib.pathweaver
    wpilib.roborioteamnumbersetter
    wpilib.robotbuilder
    wpilib.shuffleboard
    wpilib.smartdashboard
    wpilib.sysid
    wpilib.wpical
    wpilib.wpilib-utility
  ];

  programs.vscode = {
    enable = true;
    mutableExtensionsDir = true;
    profiles.default.extensions = with pkgs.vscode-extensions; [
      wpilibsuite.vscode-wpilib
      redhat.java
    ];
  };
}
