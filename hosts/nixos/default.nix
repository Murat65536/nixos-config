{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./hardware-workarounds.nix
    ../../modules/core.nix
    ../../modules/desktop.nix
    ../../modules/home-manager.nix
    ../../modules/maintenance.nix
    ../../modules/services/cync-lights.nix
  ];

  networking.hostName = "nixos";
  system.stateVersion = "26.05";
}
