#
# spec file for package tachyon-fetch
#
# Copyright (c) 2026 Mohamed Salahy
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#

Name:           tachyon-fetch
Version:        0.7.1
Release:        0
Summary:        Cockpit-grade system fetch with a built-in configurator
License:        MIT
Group:          System/Console
URL:            https://github.com/Sifr-Dev/tachyon-fetch
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        vendor.tar.zst
BuildRequires:  cargo-packaging
Requires:       fontconfig

%description
A single-process system fetch that reads /proc, /sys, DMI and hwmon, renders
one composed frame, and ships a built-in configurator. ASCII distro logos, a
system-font text logo and kitty graphics artwork are supported.

%prep
%autosetup -a1 -n %{name}-%{version}

%build
%cargo_build

%install
# The upstream binary is called "tachyon", which the openSUSE:Factory
# "tachyon" package (a ray tracer) already owns at %{_bindir}/tachyon.
# Install it under the package name to avoid a file conflict.
install -Dpm 0755 target/release/tachyon %{buildroot}%{_bindir}/%{name}

%check
%cargo_test

%files
%{_bindir}/%{name}
%license LICENSE
%license logos/LICENSE-fastfetch
%doc README.md

%changelog
