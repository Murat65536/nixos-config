{
  pkgs,
  llmAgents,
}:

llmAgents.packages.${pkgs.stdenv.hostPlatform.system}.cli-proxy-api.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ../patches/cli-proxy-api/suspend-aware.patch ];

  # The upstream package only checks cmd/server. Exercise every path changed
  # by the suspend-aware refresh patch whenever this derivation is rebuilt.
  postCheck = (old.postCheck or "") + ''
    go test ./sdk/cliproxy/auth
  '';
})
