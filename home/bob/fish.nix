{ pkgs, ... }:

{
  programs = {
    fish = {
      enable = true;
      shellAliases = {
        # Safety defaults
        cp = "cp -i";
        mv = "mv -i";
        rm = "rm -i";

        # Nix convenience
        nrs = "run0 nixos-rebuild switch";
        nrt = "run0 nixos-rebuild test";
        nrb = "run0 nixos-rebuild dry-build";
      };
      shellAbbrs = {
        ga = "git add";
        gc = "git commit";
        gs = "git status";
        gd = "git diff";
        gp = "git push";
      };
      interactiveShellInit = ''
        set -g fish_greeting
      '';
    };

    direnv = {
      enable = true;
      nix-direnv.enable = true;
    };
  };
}
