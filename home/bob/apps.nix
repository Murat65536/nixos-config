{
  pkgs,
  equibopWithoutVaapiEncoder,
  hermesAgent,
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
    (vscode-with-extensions.override {
      vscode = vscode;
      vscodeExtensions = [
        vscode-extensions.wpilibsuite.vscode-wpilib
        vscode-extensions.redhat.java
      ];
    })
    xwayland-satellite
    freecad
    ffmpeg
    yt-dlp
    localsend

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
}
