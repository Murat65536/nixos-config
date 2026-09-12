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
    cmake
    gcc
    gnumake
    nodejs
    python3
    rustup
    temurin-bin-17
    zig
    typst

    # Language servers
    haskell-language-server
    lua-language-server
    typescript-language-server
    wgsl-analyzer
    zls

    # Formatters & linters
    prettierd
    stylua
  ];
}
