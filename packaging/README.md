# Distribution packaging

This directory holds the source-package recipes for tachyon-fetch 0.7.1. Every
recipe builds from the immutable `v0.7.1` tag tarball, never from a branch
archive.

Release tarball: `https://github.com/Sifr-Dev/tachyon-fetch/archive/refs/tags/v0.7.1.tar.gz`
SHA256: `b0f53b9b0947f5d96bfbb31c8ab241db251fe35830e921be52d2260a0f69b502`

## Status per channel

Nothing below has been submitted, uploaded or accepted by any distribution.
Each row states what has actually been built and verified, and what still
blocks an external submission.

| Channel | File | Locally verified | External blocker |
|---|---|---|---|
| AUR (user repo) | `arch/PKGBUILD`, `arch/.SRCINFO`, `arch/LICENSE` | `makepkg -s` builds, package installs, binary runs | Needs an AUR account, an SSH key registered in it, and a human review of the name conflict below |
| nixpkgs (PR) | `nixpkgs/package.nix` | Full build, 62 unit + 14 CLI tests, and version install check pass on Nix 2.36.0 / Rust 1.99.1 | Needs a maintainer-list entry and a PR; no acceptance is claimed |
| openSUSE (devel project) | `opensuse/tachyon-fetch.spec`, `.changes`, `_service` | Spec reviewed against `cargo-packaging` macros; not built | Needs an openSUSE account, `osc mkpac`, a devel project that accepts it, and `osc build` on a real target |
| Debian/Ubuntu | `debian/` | Not built: `dpkg-buildpackage` and `debhelper` are absent here | See "Debian and Ubuntu" below; the vendoring and toolchain gaps are real |
| Gentoo GURU | `gentoo/` | `gen-crates.py --check` passes (206 crates); ebuild syntax-checked | Needs a GURU PR; `Manifest` cannot be generated without the distfiles |
| Fedora/COPR | `fedora/` | Not rebuilt here; spec updated for the binary rename | Not a target channel for this round |

## The `tachyon` name conflict

Upstream installs the binary as `tachyon`. On several distributions that name
is already taken by the Tachyon parallel ray tracer:

| Distribution | Existing package | Path it owns |
|---|---|---|
| Arch | `extra/tachyon` | `/usr/bin/tachyon` |
| Fedora | `tachyon` | `/usr/bin/tachyon` |
| openSUSE | `openSUSE:Factory/tachyon` | `%{_bindir}/tachyon` |
| Gentoo | `media-gfx/tachyon` | `/usr/bin/tachyon` |
| Debian | `tachyon-bin-nox`, `tachyon-bin-ogl` | `/usr/bin/tachyon-nox`, `/usr/bin/tachyon-ogl` |

Arch, Fedora and openSUSE enforce file ownership, so installing to
`/usr/bin/tachyon` would make the package conflict with an unrelated,
already-packaged tool. The Arch, Fedora and openSUSE recipes therefore install
to `tachyon-fetch` instead. This is safe because the binary never inspects
`argv[0]`: it prints `tachyon <version>` from the compiled-in version string.

Debian does **not** ship a `/usr/bin/tachyon` (verified against the contents
index for `sid`, `forky` and `trixie`), so the Debian package keeps
`/usr/bin/tachyon`.

Gentoo's `media-gfx/tachyon` does install `/usr/bin/tachyon`, but GURU is not
co-installed with a conflicting tree; the ebuild is left with the upstream name
and the conflict must be raised during GURU review.

## AUR

```
cd packaging/arch
makepkg --printsrcinfo > .SRCINFO   # regenerate after any PKGBUILD edit
makepkg -s                          # build + install the package
makepkg --install                   # install into the running system
```

Validated on this host (Arch, cargo 1.100.0): `makepkg -s --noconfirm`
completed and produced `tachyon-fetch-0.7.1-1-x86_64.pkg.tar.zst` containing
`usr/bin/tachyon-fetch` plus both licences. Extracting that package into a
staged root and running `tachyon-fetch --version` prints `tachyon 0.7.1`.

`arch/LICENSE` is the 0BSD licence the AUR requires for the package sources;
it is separate from the project's MIT licence, which ships as
`/usr/share/licenses/tachyon-fetch/LICENSE`.

To publish: create the AUR account, register an SSH key, then

```
git -c init.defaultBranch=master clone ssh://aur@aur.archlinux.org/tachyon-fetch.git
# copy PKGBUILD, .SRCINFO and LICENSE in, then
git add PKGBUILD .SRCINFO LICENSE
git commit -m "0.7.1-1"
git push
```

The AUR rejects a push without `.SRCINFO`, and only accepts the `master`
branch. Do not submit a PKGBUILD for anything already in the official
repositories; `tachyon-fetch` itself is absent from both the official repos and
the AUR (checked via the AUR RPC and the package search API).

## nixpkgs

`nixpkgs/package.nix` is the file to submit as
`pkgs/by-name/ta/tachyon-fetch/package.nix`; it is not the same as the in-repo
`default.nix`, which builds from a checkout and uses `cargoLock`.

Before submitting:

1. The source `hash` is Nix's recursive hash of the unpacked tag tree, not the
   SHA256 of the `.tar.gz` file. The verified value is
   `sha256-ZcjI+xsaVa1chF40FGxW4N+L46w4u4ClI2BDcQvGqNo=`.
2. `cargoHash` is the verified value
   `sha256-pkSuVtVWv/LELCSzF/CEFZwvFCXnunVhfS8Usp4dAP8=`, obtained by
   running Nix's actual vendor derivation.
3. Add an entry to `maintainers/maintainer-list.nix` and reference it from
   `meta.maintainers`; a package PR with an empty maintainer list is normally
   sent back.
4. The tested evaluation helper pins nixpkgs revision
   `2786a2a72088ecf32aea5b3ec52099e6a7cff78f`, with Rust 1.99.1.
   The older `nixos-25.05` snapshot provided Rust 1.86 and correctly failed
   the project's declared 1.88 MSRV.

The complete package build and its 62 unit tests, 14 CLI tests, and version
install check passed with Nix 2.36.0. A PR still needs a commit message in the
`tachyon-fetch: init at 0.7.1` form and a filled-in PR template reporting the
platforms actually built. No submission or acceptance is claimed.

## openSUSE

`opensuse/tachyon-fetch.spec` targets the `cargo-packaging` macros
(`%cargo_build`, `%cargo_test`) and expects a `vendor.tar.zst` produced by the
`cargo_vendor` source service declared in `opensuse/_service`.

```
osc checkout home:<user>
osc mkpac home:<user>/tachyon-fetch
# add tachyon-fetch.spec, tachyon-fetch.changes, _service
osc service disabledrun          # produces the tarball and vendor.tar.zst
osc build openSUSE_Tumbleweed x86_64
osc submitrequest home:<user>/tachyon-fetch devel:openSUSE:Factory
```

openSUSE:Factory requires the package to live in a devel project first;
`home:` projects cannot feed Factory directly. The spec has not been built, and
`osc build` has not been run, because this host has no `osc` and no openSUSE
tree.

## Debian and Ubuntu

The `debian/` tree is a conventional `3.0 (quilt)` source package. Build:

```
# from a copy of the tree at the tag, with debian/ overlaid
dpkg-buildpackage -us -uc -d
```

Two real gaps block an upload, and neither can be fixed by editing these files:

1. **Toolchain.** `Cargo.toml` declares `rust-version = "1.88"`. Debian trixie
   ships rustc 1.85.1 and bookworm 1.63; sid has 1.99.1. Ubuntu 24.04 LTS
   ships rustc 1.75.0. Only Debian unstable currently satisfies the MSRV, so
   an upload to stable/Ubuntu LTS would fail to build as written.
2. **Vendoring.** Debian does not allow network access during a build. The
   `debian/rules` here calls `cargo build` directly, which will try to reach
   crates.io. An upload needs either a `debian/cargo_home` vendor tree or the
   `dh-cargo` machinery (`debian/cargo-checksum.json`, `librust-*-dev`
   dependencies). `fontdue` in particular is not in the Debian archive.

Because of these, the correct next step is an ITP bug (WNPP) describing the
package, followed by packaging work on a machine with `dpkg-buildpackage` and a
1.88+ toolchain -- not an upload from these files. `debian/source/options`
excludes `target/`, `result/` and `.git` from the source tarball.

## Gentoo

```
python3 packaging/gentoo/gen-crates.py --check packaging/gentoo/tachyon-fetch-0.7.1.ebuild
```

prints `206 crates ok` on this host. The ebuild sets `RUST_MIN_VER="1.88"`
before `inherit cargo`, because the eclass reads that variable during inherit.

GURU requires `~arch` keywords (the ebuild uses `~amd64`) and expects new
packages to arrive as a pull request. A `Manifest` cannot be generated without
fetching all 206 crate distfiles, so that step belongs to a machine with the
Gentoo tree available. Forking a package that is already in the Gentoo tree is
prohibited, which is why this ebuild is for `tachyon-fetch` and not for the
existing `media-gfx/tachyon`.

## Fedora

`fedora/tachyon-fetch.spec` builds a `[profile.rpm]` target via
`cargo-rpm-profile.patch` and installs `target/rpm/tachyon`. It was updated to
install to `%{_bindir}/tachyon-fetch` for the same collision reason as Arch.
It has not been rebuilt since that edit, and Fedora is not part of this
submission round.

## Releasing a new version

1. Tag `vX.Y.Z` and publish the GitHub release.
2. Compute `sha256sum` of the tag tarball.
3. Update the version and checksum here and in every recipe that pins them:
   `arch/PKGBUILD` (`pkgver`, `sha256sums`), `arch/.SRCINFO` (regenerate),
   `opensuse/tachyon-fetch.spec` (`Version`), `nixpkgs/package.nix`
   (`version`, `src.hash`, `cargoHash`), `debian/changelog`, and the Gentoo
   ebuild filename plus `CRATES`.
4. Rebuild and run the package on the target distribution before publishing.

## Runtime dependencies

- `fontconfig` for the glyph and font pickers (`fc-list`, `fc-match`).
- A UTF-8 terminal. Kitty graphics is used for the image logo when available;
  otherwise the ASCII or text logo is drawn.
- No daemon, no network access and no writable state is needed to render.
