{
  lib,
  rustPlatform,
  fetchFromGitHub,
  makeWrapper,
  fontconfig,
  versionCheckHook,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "tachyon-fetch";
  version = "0.7.1";

  src = fetchFromGitHub {
    owner = "Sifr-Dev";
    repo = "tachyon-fetch";
    tag = "v${finalAttrs.version}";
    hash = "sha256-ZcjI+xsaVa1chF40FGxW4N+L46w4u4ClI2BDcQvGqNo=";
  };

  cargoHash = "sha256-pkSuVtVWv/LELCSzF/CEFZwvFCXnunVhfS8Usp4dAP8=";

  nativeBuildInputs = [ makeWrapper ];

  postInstall = ''
    # The glyph and font pickers shell out to fc-list and fc-match.
    wrapProgram $out/bin/tachyon \
      --suffix PATH : ${lib.makeBinPath [ fontconfig ]}
  '';

  nativeCheckInputs = [ versionCheckHook ];
  doInstallCheck = true;

  meta = {
    description = "Cockpit-grade system fetch with a built-in configurator and distro logos";
    homepage = "https://github.com/Sifr-Dev/tachyon-fetch";
    license = lib.licenses.mit;
    mainProgram = "tachyon";
    maintainers = with lib.maintainers; [ ];
    platforms = lib.platforms.linux;
  };
})
