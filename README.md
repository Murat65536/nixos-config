# NixOS configuration

This repository defines the `nixos` host and Bob's Home Manager profile.
The host remains on NixOS 26.05. DMS, Hermes Agent, and CLIProxyAPI retain
their own locked upstream inputs.

## Validate and deploy

```console
nix fmt
nix flake check
nix build .#nixosConfigurations.nixos.config.system.build.toplevel
run0 nixos-rebuild switch --flake .#nixos
```

Use `nixos-rebuild test` before `switch` when changing login, networking,
storage, or suspend behavior.

## Updates

Update one input at a time and build before switching. Kernel updates can
require rebasing the patches under `hosts/nixos/patches/linux`; CLIProxyAPI
updates can require rebasing `patches/cli-proxy-api/suspend-aware.patch`.

```console
nix flake update nixpkgs
nix flake update dms
```

The `stock-kernel` boot specialization retains the same kernel series without
the local Linux patches. It is a recovery path, not the normal configuration.

Runtime state and credentials stay outside the Nix store:

- `~/.config/cli-proxy-api/config.yaml`
- `~/.local/state/cync-lights/`
