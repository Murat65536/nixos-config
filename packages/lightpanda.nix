{
  lib,
  stdenv,
  fetchurl,
  autoPatchelfHook,
}:

stdenv.mkDerivation rec {
  pname = "lightpanda";
  version = "0.4.0";

  src = fetchurl {
    url = "https://github.com/lightpanda-io/browser/releases/download/${version}/lightpanda-x86_64-linux";
    hash = "sha256-v8+b1+gJObhyMqoRSknY85f1GvDCYy2fxY1KbUOGYk8=";
  };

  dontUnpack = true;

  nativeBuildInputs = [ autoPatchelfHook ];
  buildInputs = [ stdenv.cc.cc.lib ];

  installPhase = ''
    runHook preInstall
    install -m755 -D $src $out/bin/lightpanda
    runHook postInstall
  '';

  meta = {
    description = "Headless browser designed for AI and automation";
    homepage = "https://github.com/lightpanda-io/browser";
    platforms = [ "x86_64-linux" ];
    mainProgram = "lightpanda";
  };
}
