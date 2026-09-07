{
  fetchPypi,
  lib,
  python3,
  runCommand,
  symlinkJoin,
  systemd,
  writeShellApplication,
}:

let
  source = ./src;

  # NixOS 26.05 currently carries pycync 0.5.0, while this setup flow uses
  # APIs from 0.6.1. Keep the previously tested version reproducible.
  pycync_0_6_1 = python3.pkgs.pycync.overridePythonAttrs (_old: rec {
    version = "0.6.1";
    src = fetchPypi {
      pname = "pycync";
      inherit version;
      hash = "sha256-oeXePlbJleyBUz29PaugC8pJEl4PsJE4E1JzWEGCGMY=";
    };
    doCheck = false;
    preCheck = null;
  });

  runtimePython = python3.withPackages (
    pythonPackages: with pythonPackages; [
      aiohttp
      bleak
      pycryptodome
    ]
  );

  setupPython = python3.withPackages (
    pythonPackages:
    with pythonPackages;
    [
      aiohttp
      bleak
      pycryptodome
    ]
    ++ [ pycync_0_6_1 ]
  );

  bridge = writeShellApplication {
    name = "cync-lights";
    text = ''
      exec ${runtimePython}/bin/python ${source}/bridge.py "$@"
    '';
  };

  setup = writeShellApplication {
    name = "cync-lights-setup";
    runtimeInputs = [ systemd ];
    text = ''
      ${setupPython}/bin/python ${source}/setup.py
      systemctl --user restart cync-lights.service
    '';
  };

  tests = runCommand "cync-lights-tests" { nativeBuildInputs = [ runtimePython ]; } ''
    cp -r ${source} source
    chmod -R u+w source
    cd source
    HOME="$TMPDIR" PYTHONDONTWRITEBYTECODE=1 \
      python -m unittest discover -s . -p 'test_*.py'
    touch "$out"
  '';
in
symlinkJoin {
  name = "cync-lights-0.1.0";
  paths = [
    bridge
    setup
  ];

  passthru = { inherit tests; };

  meta = {
    description = "Local Cync Bluetooth mesh bridge for Dank Material Shell";
    license = lib.licenses.mit;
    mainProgram = "cync-lights";
    platforms = lib.platforms.linux;
  };
}
