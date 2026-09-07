{
  description = "Bob's NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    dms.url = "github:AvengeMedia/DankMaterialShell";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hermes-agent.url = "github:NousResearch/hermes-agent";

    # Keep this exact packaging revision until the local suspend-aware patch
    # is either upstream or deliberately rebased.
    llm-agents.url = "github:numtide/llm-agents.nix/496d8f2d508dcd4673a1480cd58b3e9bf3400c15";
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      dms,
      home-manager,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      cyncLights = pkgs.callPackage ./packages/cync-lights { };
      cliProxyApi = import ./packages/cli-proxy-api.nix {
        inherit pkgs;
        llmAgents = inputs.llm-agents;
      };
    in
    {
      packages.${system} = {
        cync-lights = cyncLights;
        cli-proxy-api = cliProxyApi;
        default = cyncLights;
      };

      checks.${system}.cync-lights = cyncLights.tests;
      formatter.${system} = pkgs.nixfmt-tree;

      nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [
          dms.nixosModules.dank-material-shell
          home-manager.nixosModules.home-manager
          ./hosts/nixos
        ];
      };
    };
}
