{
  inputs,
  pkgs,
  ...
}:

let
  system = pkgs.stdenv.hostPlatform.system;
  cliProxyApi = import ../../packages/cli-proxy-api.nix {
    inherit pkgs;
    llmAgents = inputs.llm-agents;
  };
  cyncLights = pkgs.callPackage ../../packages/cync-lights { };
  hermesAgent = inputs.hermes-agent.packages.${system}.default;

  equibopWithoutVaapiEncoder = pkgs.equibop.overrideAttrs (old: {
    postFixup = (old.postFixup or "") + ''
      wrapProgram $out/bin/equibop \
        --add-flags "--disable-features=VaapiVideoEncoder"
    '';
  });
in
{
  imports = [
    ./apps.nix
    ./dev.nix
    ./fish.nix
    ./kitty.nix
    ./services.nix
  ];

  home = {
    username = "bob";
    homeDirectory = "/home/bob";
    stateVersion = "26.05";
    sessionPath = [ "$HOME/.local/bin" ];

    # Core CLI tools & background utilities
    packages =
      (with pkgs; [
        btop
        ddcutil
        fastfetch
        fd
        fuzzel
        fzf
        kitty
        neovim
        ripgrep
        unzip
        zip
      ])
      ++ [
        cliProxyApi
        cyncLights
        hermesAgent
      ];
  };

  programs.home-manager.enable = true;
  xdg.enable = true;

  _module.args = {
    inherit
      cliProxyApi
      cyncLights
      hermesAgent
      equibopWithoutVaapiEncoder
      ;
  };
}
