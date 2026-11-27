#!/usr/bin/env python3
"""Check that the committed .SRCINFO matches the PKGBUILD it came from.

The AUR rejects a push whose .SRCINFO disagrees with its PKGBUILD, so drift
between the two is a real submission failure. This check does not depend on
`makepkg` being installed: it parses the PKGBUILD's top-level assignments, then
compares every field against the committed .SRCINFO. When `makepkg` is
available it additionally runs `makepkg --printsrcinfo` and requires the output
to match the committed file byte for byte, which proves the committed file is
what the AUR tooling would generate.

Pass --require-makepkg to turn a missing `makepkg` into a failure. CI uses it
in an Arch container so the authoritative comparison always runs, instead of
silently degrading to the structural check.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ARCH_DIR = Path(__file__).resolve().parent

# Fields makepkg copies into .SRCINFO. pkgname/pkgbase are handled separately.
SCALAR_FIELDS = ["pkgdesc", "pkgver", "pkgrel", "url"]
ARRAY_FIELDS = ["arch", "license", "depends", "makedepends", "source", "sha256sums"]

# Emitted in this order by makepkg; used only for the structural comparison.
# The strict comparison against real makepkg output catches ordering drift.
SRCINFO_ORDER = [
    "pkgdesc",
    "pkgver",
    "pkgrel",
    "url",
    "arch",
    "license",
    "depends",
    "makedepends",
    "source",
    "sha256sums",
]


def strip_function_bodies(text: str) -> str:
    """Drop shell function bodies so inner assignments are not parsed."""
    kept: list[str] = []
    depth = 0
    for line in text.splitlines():
        if depth == 0 and not line.lstrip().startswith("#") and "()" in line:
            depth += line.count("{") - line.count("}")
            continue
        if depth > 0:
            depth += line.count("{") - line.count("}")
            continue
        kept.append(line)
    return "\n".join(kept)


def expand(value: str, variables: dict[str, str]) -> str:
    """Expand $name and ${name} using the parsed top-level assignments."""
    for _ in range(5):  # nested references settle quickly; loop is defensive
        changed = False
        for name, replacement in variables.items():
            for token in (f"${{{name}}}", f"${name}"):
                if token in value:
                    value = value.replace(token, replacement)
                    changed = True
        if not changed:
            break
    return value


def split_array(raw: str) -> list[str]:
    """Split a bash array body on whitespace, honouring single and double quotes."""
    items: list[str] = []
    current: list[str] = []
    quote = None
    for char in raw:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
        elif char in {"'", '"'}:
            quote = char
        elif char.isspace():
            if current:
                items.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        items.append("".join(current))
    return [item for item in items if item]


def parse_pkgbuild(path: Path) -> dict[str, list[str]]:
    text = strip_function_bodies(path.read_text())
    scalars: dict[str, str] = {}
    arrays: dict[str, list[str]] = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("."):
            continue
        if "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        if not key.isidentifier():
            continue
        raw = raw.strip()
        if raw.startswith("(") and raw.endswith(")"):
            arrays[key] = split_array(raw[1:-1])
        else:
            scalars[key] = raw.strip("'\"")

    variables = dict(scalars)
    for key, values in arrays.items():
        variables[key] = " ".join(values)

    result: dict[str, list[str]] = {}
    for field in SCALAR_FIELDS:
        if field in scalars:
            result[field] = [expand(scalars[field], variables)]
    for field in ARRAY_FIELDS:
        if field in arrays:
            result[field] = [expand(item, variables) for item in arrays[field]]

    for required in ("pkgname", "pkgver", "pkgrel", "sha256sums", "source"):
        if required not in scalars and required not in arrays:
            sys.exit(f"{path}: missing required variable {required!r}")
    return result


def parse_srcinfo(path: Path) -> dict[str, list[str]]:
    """Return the pkgbase fields of a .SRCINFO file.

    A split-package .SRCINFO repeats fields under `pkgname = ...` sections. This
    package is not split, so only the pkgbase section is compared; a pkgname
    section that shadows a pkgbase field is reported as drift.
    """
    if not path.is_file():
        sys.exit(f"{path}: not found; regenerate it from the PKGBUILD")
    pkgbase: dict[str, list[str]] = {}
    pkgname: dict[str, list[str]] = {}
    section = None
    seen_pkgbase = False
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            name, _, value = line.partition("=")
            section = name.strip()
            if section == "pkgbase":
                seen_pkgbase = True
                continue
            if section == "pkgname":
                continue
            sys.exit(f"{path}: unexpected top-level section {section!r}")
        name, _, value = line.strip().partition("=")
        target = pkgbase if section == "pkgbase" else pkgname
        target.setdefault(name.strip(), []).append(value.strip())

    if not seen_pkgbase:
        sys.exit(f"{path}: missing pkgbase section")
    if not pkgbase:
        sys.exit(f"{path}: pkgbase section declares no fields")
    for field in SRCINFO_ORDER:
        if field in pkgname and pkgname[field] != pkgbase.get(field):
            sys.exit(
                f"{path}: pkgname overrides {field} ({pkgname[field]}) but this "
                "package is not split; expected no pkgname section"
            )
    return pkgbase


def compare(structural: dict[str, list[str]], committed: dict[str, list[str]]) -> list[str]:
    problems: list[str] = []
    for field in sorted(set(structural) | set(committed)):
        want = structural.get(field)
        got = committed.get(field)
        if want == got:
            continue
        if want is None:
            problems.append(f".SRCINFO has {field} = {got}, PKGBUILD does not")
        elif got is None:
            problems.append(f".SRCINFO is missing {field}; PKGBUILD sets {want}")
        elif field in ARRAY_FIELDS and sorted(want) == sorted(got):
            problems.append(
                f"{field} entry order differs: PKGBUILD {want} vs .SRCINFO {got}; "
                "makepkg preserves PKGBUILD order, so regenerate .SRCINFO"
            )
        elif field in ARRAY_FIELDS:
            problems.append(f"{field} differs: PKGBUILD {want} vs .SRCINFO {got}")
        else:
            problems.append(f"{field} differs: PKGBUILD {want} vs .SRCINFO {got}")
    return problems


def check_with_makepkg(workdir: Path, committed_text: str) -> tuple[bool, str]:
    """Run the authoritative generator.

    Returns (ok, message). A missing makepkg reports ok=True with an explanatory
    message, because the caller decides whether that is acceptable.
    """
    if shutil.which("makepkg") is None:
        return True, "makepkg is not installed; compared structurally only"
    result = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, (
            "makepkg --printsrcinfo failed with exit "
            f"{result.returncode}: {result.stderr.strip()}"
        )
    if result.stdout == committed_text:
        return True, "makepkg --printsrcinfo matches the committed .SRCINFO"
    return False, (
        "makepkg --printsrcinfo differs from the committed .SRCINFO; "
        "the file is generated, so regenerate it instead of editing it"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arch-dir", default=str(ARCH_DIR), help="directory holding PKGBUILD and .SRCINFO"
    )
    parser.add_argument(
        "--require-makepkg",
        action="store_true",
        help="fail instead of degrading when makepkg is unavailable",
    )
    args = parser.parse_args(argv[1:])

    arch_dir = Path(args.arch_dir).resolve()
    pkgbuild = arch_dir / "PKGBUILD"
    srcinfo = arch_dir / ".SRCINFO"
    if not pkgbuild.is_file():
        sys.exit(f"{pkgbuild}: not found")

    structural = parse_pkgbuild(pkgbuild)
    committed = parse_srcinfo(srcinfo)
    problems = compare(structural, committed)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        print(
            f"\nRegenerate it with: cd {arch_dir} && makepkg --printsrcinfo > .SRCINFO",
            file=sys.stderr,
        )
        return 1
    print(f"{arch_dir.name}: PKGBUILD fields match .SRCINFO structurally")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp) / "arch"
        shutil.copytree(arch_dir, workdir)
        ok, message = check_with_makepkg(workdir, srcinfo.read_text())

    if shutil.which("makepkg") is None:
        # The authoritative comparison did not run. Degrading is fine by
        # default, but --require-makepkg exists so CI cannot skip it silently.
        if args.require_makepkg:
            print(
                f"error: {message}, but --require-makepkg was requested and the "
                "authoritative comparison did not run",
                file=sys.stderr,
            )
            return 1
        print(f"note: {message}")
        return 0

    if not ok:
        print(f"error: {message}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
