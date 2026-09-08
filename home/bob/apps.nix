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
    sioyek
    slack
    vlc
    vscode
    xwayland-satellite
    freecad

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
