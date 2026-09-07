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
    ./fish.nix
    ./kitty.nix
    ./services.nix
  ];

  home = {
    username = "bob";
    homeDirectory = "/home/bob";
    stateVersion = "26.05";
    sessionPath = [ "$HOME/.local/bin" ];

    packages =
      (with pkgs; [
        anki
        btop
        chromium
        (lib.setPrio 20 clang)
        clang-tools
        claude-code
        codex
        ddcutil
        fastfetch
        fd
        fuzzel
        fzf
        gcc
        haskell-language-server
        kitty
        lua-language-server
        neovim
        nodejs
        obs-studio
        obsidian
        papirus-icon-theme
        python3
        ripgrep
        rustup
        sioyek
        slack
        typescript-language-server
        unzip
        vlc
        vscode
        wgsl-analyzer
        xwayland-satellite
        zip
        zls
      ])
      ++ [
        cliProxyApi
        cyncLights
        equibopWithoutVaapiEncoder
        hermesAgent
        hermesAgent.hermesDesktop
      ];
  };

  programs.home-manager.enable = true;
  xdg.enable = true;

  _module.args = {
    inherit cliProxyApi cyncLights;
  };
}
