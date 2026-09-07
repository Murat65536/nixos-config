{ pkgs, ... }:

{
  boot.loader = {
    systemd-boot = {
      enable = true;
      configurationLimit = 10;
    };
    efi.canTouchEfiVariables = true;
  };

  networking.networkmanager.enable = true;
  time.timeZone = "America/New_York";
  i18n.defaultLocale = "en_US.UTF-8";

  services.xserver.xkb = {
    layout = "us";
    options = "caps:swapescape";
  };
  console.useXkbConfig = true;

  users.users.bob = {
    isNormalUser = true;
    description = "Bob";
    extraGroups = [
      "networkmanager"
      "wheel"
    ];
    shell = pkgs.fish;
  };

  programs.fish.enable = true;
  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      vulkan-loader
      libGL
      wayland
      libxkbcommon
      libx11
      libxcursor
      libxi
      libxrandr
    ];
  };

  nixpkgs.config.allowUnfree = true;
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  environment.systemPackages = with pkgs; [
    git
    vim
    wget
  ];

  swapDevices = [
    {
      device = "/var/lib/swapfile";
      size = 16 * 1024;
    }
  ];
  zramSwap.enable = true;
}
