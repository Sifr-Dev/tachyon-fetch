let
  pkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/2786a2a72088ecf32aea5b3ec52099e6a7cff78f.tar.gz") { };
in
pkgs.callPackage ./package.nix { }
