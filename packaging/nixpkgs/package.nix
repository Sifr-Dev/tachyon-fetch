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
    hash = "sha256-sPU7mwlH9dlr+7McirJB2yUf41gw6SG+UtImCg9ptQI=";
  };

  # Placeholder: regenerate with
  #   nix-build -A tachyon-fetch 2>&1 | grep 'got:'
  # or `nix-prefetch-url` on the vendored crate set before opening the PR.
  cargoHash = lib.fakeHash;

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
