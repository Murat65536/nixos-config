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
  ];
}
