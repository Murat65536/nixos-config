{ pkgs, lib, ... }:

{
  programs.gh = {
    enable = true;
    gitCredentialHelper.enable = true;
  };

  home.packages = with pkgs; [
    # Compilers & toolchains
    (lib.setPrio 20 clang)
    clang-tools
    gcc
    nodejs
    python3
    rustup

    # Language servers
    haskell-language-server
    lua-language-server
    typescript-language-server
    wgsl-analyzer
    zls
  ];
}
