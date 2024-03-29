# ==================
# Top-level metadata
# ==================

%global pybasever 3.8

# pybasever without the dot:
%global pyshortver 38

Name: python38
Summary: Interpreter of the Python programming language
URL: https://www.python.org/

#  WARNING  When rebasing to a new Python version,
#           remember to update the python3-docs package as well
%global general_version %{pybasever}.17
#global prerel ...
%global upstream_version %{general_version}%{?prerel}
Version: %{general_version}%{?prerel:~%{prerel}}
Release: 2%{?dist}
License: Python

# Exclude i686 arch. Due to a modularity issue it's being added to the
# x86_64 compose of CRB, but we don't want to ship it at all.
# See: https://projects.engineering.redhat.com/browse/RCM-72605
ExcludeArch: i686

# ==================================
# Conditionals controlling the build
# ==================================

# Note that the bcond macros are named for the CLI option they create.
# "%%bcond_without" means "ENABLE by default and create a --without option"


# Flat package, i.e. python36, python37, python38 for tox etc.
# WARNING: This also influences the main_python bcond below.
# in Fedora, never turn this on for the python3 package
# and always keep it on for python37 etc.
# WARNING: This does not change the package name and summary above.
%bcond_with flatpackage

# Main Python, i.e. whether this is the main Python version in the distribution
# that owns /usr/bin/python3 and other unique paths
%bcond_with main_python

# When bootstrapping python3, we need to build setuptools.
# but setuptools BR python3-devel and that brings in python3-rpm-generators;
# python3-rpm-generators needs python3-setuptools, so we cannot have it yet.
#
# Procedure: https://fedoraproject.org/wiki/SIGs/Python/UpgradingPython
#
#   IMPORTANT: When bootstrapping, it's very likely the wheels for pip and
#   setuptools are not available. Turn off the rpmwheels bcond until
#   the two packages are built with wheels to get around the issue.
%bcond_with bootstrap

# Whether to use RPM build wheels from the python-{pip,setuptools}-wheel package
# Uses upstream bundled prebuilt wheels otherwise
%bcond_without rpmwheels

# Expensive optimizations (mainly, profile-guided optimizations)
%bcond_without optimizations

# https://fedoraproject.org/wiki/Changes/PythonNoSemanticInterpositionSpeedup
%bcond_without no_semantic_interposition

# Run the test suite in %%check
%bcond_without tests

# Extra build for debugging the interpreter or C-API extensions
# (the -debug subpackages)
%if %{with flatpackage}
%bcond_with debug_build
%else
%bcond_without debug_build
%endif

# Support for the GDB debugger
%bcond_without gdb_hooks

# The dbm.gnu module (key-value database)
%bcond_without gdbm

# Main interpreter loop optimization
%bcond_without computed_gotos

# Support for the Valgrind debugger/profiler
%ifarch %{valgrind_arches}
%bcond_without valgrind
%else
%bcond_with valgrind
%endif

# https://fedoraproject.org/wiki/Changes/Python_Upstream_Architecture_Names
# For a very long time we have converted "upstream architecture names" to "Fedora names".
# This made sense at the time, see https://github.com/pypa/manylinux/issues/687#issuecomment-666362947
# However, with manylinux wheels popularity growth, this is now a problem.
# Wheels built on a Linux that doesn't do this were not compatible with ours and vice versa.
# We now have a compatibility layer to workaround a problem,
# but we also no longer use the legacy arch names in Fedora 34+.
# This bcond controls the behavior. The defaults should be good for anybody.
%bcond_without legacy_archnames

# =====================
# General global macros
# =====================

# Set python3_pkgversion so that python_provide macro works for python38-
# prefixes in this spec file
# This is also set in the python38-rpm-macros package so that it works in other
# packages of this module.
%global python3_pkgversion 38

%global pylibdir %{_libdir}/python%{pybasever}
%global dynload_dir %{pylibdir}/lib-dynload

# ABIFLAGS, LDVERSION and SOABI are in the upstream configure.ac
# See PEP 3149 for some background: http://www.python.org/dev/peps/pep-3149/
%global ABIFLAGS_optimized %{nil}
%global ABIFLAGS_debug     d

%global LDVERSION_optimized %{pybasever}%{ABIFLAGS_optimized}
%global LDVERSION_debug     %{pybasever}%{ABIFLAGS_debug}

# When we use the upstream arch triplets, we convert them from the legacy ones
# This is reversed in prep when %%with legacy_archnames, so we keep both macros
%global platform_triplet_legacy %{_arch}-linux%{_gnu}
%global platform_triplet_upstream %{expand:%(echo %{platform_triplet_legacy} | sed -E \\
    -e 's/^arm(eb)?-linux-gnueabi$/arm\\1-linux-gnueabihf/' \\
    -e 's/^mips64(el)?-linux-gnu$/mips64\\1-linux-gnuabi64/' \\
    -e 's/^ppc(64)?(le)?-linux-gnu$/powerpc\\1\\2-linux-gnu/')}
%if %{with legacy_archnames}
%global platform_triplet %{platform_triplet_legacy}
%else
%global platform_triplet %{platform_triplet_upstream}
%endif
 
%global SOABI_optimized cpython-%{pyshortver}%{ABIFLAGS_optimized}-%{platform_triplet}
%global SOABI_debug     cpython-%{pyshortver}%{ABIFLAGS_debug}-%{platform_triplet}

# All bytecode files are in a __pycache__ subdirectory, with a name
# reflecting the version of the bytecode.
# See PEP 3147: http://www.python.org/dev/peps/pep-3147/
# For example,
#   foo/bar.py
# has bytecode at:
#   foo/__pycache__/bar.cpython-%%{pyshortver}.pyc
#   foo/__pycache__/bar.cpython-%%{pyshortver}.opt-1.pyc
#   foo/__pycache__/bar.cpython-%%{pyshortver}.opt-2.pyc
%global bytecode_suffixes .cpython-%{pyshortver}*.pyc

# Python's configure script defines SOVERSION, and this is used in the Makefile
# to determine INSTSONAME, the name of the libpython DSO:
#   LDLIBRARY='libpython$(VERSION).so'
#   INSTSONAME="$LDLIBRARY".$SOVERSION
# We mirror this here in order to make it easier to add the -gdb.py hooks.
# (if these get out of sync, the payload of the libs subpackage will fail
# and halt the build)
%global py_SOVERSION 1.0
%global py_INSTSONAME_optimized libpython%{LDVERSION_optimized}.so.%{py_SOVERSION}
%global py_INSTSONAME_debug     libpython%{LDVERSION_debug}.so.%{py_SOVERSION}

# Disable automatic bytecompilation. The python3 binary is not yet be
# available in /usr/bin when Python is built. Also, the bytecompilation fails
# on files that test invalid syntax.
%undefine py_auto_byte_compile


# =======================
# Build-time requirements
# =======================

# (keep this list alphabetized)

BuildRequires: autoconf
BuildRequires: bluez-libs-devel
BuildRequires: bzip2
BuildRequires: bzip2-devel
BuildRequires: desktop-file-utils
BuildRequires: expat-devel

BuildRequires: findutils
BuildRequires: gcc-c++
%if %{with gdbm}
BuildRequires: gdbm-devel
%endif
BuildRequires: glibc-all-langpacks
BuildRequires: glibc-devel
BuildRequires: gmp-devel
BuildRequires: libappstream-glib
BuildRequires: libffi-devel
BuildRequires: libnsl2-devel
BuildRequires: libtirpc-devel
BuildRequires: libGL-devel
BuildRequires: libuuid-devel
BuildRequires: libX11-devel
BuildRequires: ncurses-devel

BuildRequires: openssl-devel
BuildRequires: pkgconfig
BuildRequires: readline-devel
BuildRequires: redhat-rpm-config
BuildRequires: sqlite-devel
BuildRequires: gdb

BuildRequires: tar
BuildRequires: tcl-devel
BuildRequires: tix-devel
BuildRequires: tk-devel

%if %{with valgrind}
BuildRequires: valgrind-devel
%endif

BuildRequires: xz-devel
BuildRequires: zlib-devel

BuildRequires: /usr/bin/dtrace

# workaround http://bugs.python.org/issue19804 (test_uuid requires ifconfig)
BuildRequires: /usr/sbin/ifconfig

# For %%python_provide
BuildRequires: python-rpm-macros

%if %{with rpmwheels}
BuildRequires: python38-setuptools-wheel
BuildRequires: python38-pip-wheel
%endif

%if %{without bootstrap}
# for make regen-all and distutils.tests.test_bdist_rpm
BuildRequires: python%{pyshortver}
%endif

# =======================
# Source code and patches
# =======================

# The upstream tarball includes questionable executable files for Windows,
# which we should not ship even in the SRPM.
# Run the "get-source.sh" with the version as argument to download the upstream
# tarball and generate a version with the .exe files removed. For example:
# $ ./get-source.sh 3.7.0

Source: Python-%{version}-noexe.tar.xz

# A script to remove .exe files from the source distribution
Source1: get-source.sh

Source3: macros.python38

# A simple script to check timestamps of bytecode files
# Run in check section with Python that is currently being built
# Originally written by bkabrda
Source8: check-pyc-timestamps.py

# Desktop menu entry for idle3
Source10: idle3.desktop

# AppData file for idle3
Source11: idle3.appdata.xml

# 00001 #
# Fixup distutils/unixccompiler.py to remove standard library path from rpath:
# Was Patch0 in ivazquez' python3000 specfile:
Patch1:         00001-rpath.patch

# 00102 #
# Change the various install paths to use /usr/lib64/ instead or /usr/lib
# Only used when "%%{_lib}" == "lib64"
# Not yet sent upstream.
Patch102: 00102-lib64.patch

# 00111 #
# Patch the Makefile.pre.in so that the generated Makefile doesn't try to build
# a libpythonMAJOR.MINOR.a
# See https://bugzilla.redhat.com/show_bug.cgi?id=556092
# Downstream only: not appropriate for upstream
Patch111: 00111-no-static-lib.patch

# 00189 #
# Instead of bundled wheels, use our RPM packaged wheels from
# /usr/share/python38-wheels
# Downstream only: upstream bundles
# We might eventually pursuit upstream support, but it's low prio
Patch189: 00189-use-rpm-wheels.patch

# 00251
# Set values of prefix and exec_prefix in distutils install command
# to /usr/local if executable is /usr/bin/python* and RPM build
# is not detected to make pip and distutils install into separate location
# Fedora Change: https://fedoraproject.org/wiki/Changes/Making_sudo_pip_safe
# Downstream only: Awaiting resources to work on upstream PEP
Patch251: 00251-change-user-install-location.patch

# 00328 #
# Restore pyc to TIMESTAMP invalidation mode as default in rpmbubild
# See https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/57#comment-27426
# Downstream only: only used when building RPM packages
# Ideally, we should talk to upstream and explain why we don't want this
Patch328: 00328-pyc-timestamp-invalidation-mode.patch

# 00329 #
# Support OpenSSL FIPS mode
# - Fallback implementations md5, sha1, sha256, sha512 are removed in favor of OpenSSL wrappers
# - In FIPS mode, OpenSSL wrappers are always used in hashlib
# - add a new "usedforsecurity" keyword argument to the various digest
#   algorithms in hashlib so that you can whitelist a callsite with
#   "usedforsecurity=False"
#   The change has been implemented upstream since Python 3.9:
#   https://bugs.python.org/issue9216
# - OpenSSL wrappers for the hashes blake2{b512,s256},
#     sha3_{224,256,384,512}, shake_{128,256} are now exported from _hashlib
# - In FIPS mode, the blake2, sha3 and shake hashes use OpenSSL wrappers
#   and do not offer extended functionality (keys, tree hashing, custom digest size)
# - In FIPS mode, hmac.HMAC can only be instantiated with an OpenSSL wrapper
#   or an string with OpenSSL hash name as the "digestmod" argument.
#   The argument must be specified (instead of defaulting to ‘md5’).
#
# - Also while in FIPS mode, we utilize OpenSSL's DRBG and disable the
#   os.getrandom() function.
#
# Resolves: rhbz#1731424
Patch329: 00329-fips.patch

# 00353 #
# Original names for architectures with different names downstream
#
# https://fedoraproject.org/wiki/Changes/Python_Upstream_Architecture_Names
#
# Pythons in RHEL/Fedora used different names for some architectures
# than upstream and other distros (for example ppc64 vs. powerpc64).
# This was patched in patch 274, now it is sedded if %%with legacy_archnames.
#
# That meant that an extension built with the default upstream settings
# (on other distro or as an manylinux wheel) could not been found by Python
# on RHEL/Fedora because it had a different suffix.
# This patch adds the legacy names to importlib so Python is able
# to import extensions with a legacy architecture name in its
# file name.
# It work both ways, so it support both %%with and %%without legacy_archnames.
#
# WARNING: This patch has no effect on Python built with bootstrap
# enabled because Python/importlib_external.h is not regenerated
# and therefore Python during bootstrap contains importlib from
# upstream without this feature. It's possible to include
# Python/importlib_external.h to this patch but it'd make rebasing
# a nightmare because it's basically a binary file.
Patch353: 00353-architecture-names-upstream-downstream.patch

# 00359 #
# CVE-2021-23336 python: Web Cache Poisoning via urllib.parse.parse_qsl and
# urllib.parse.parse_qs by using a semicolon in query parameters
# Upstream: https://bugs.python.org/issue42967
# Main BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1928904
Patch359: 00359-CVE-2021-23336.patch

# 00378 #
# Support expat 2.4.5
#
# Curly brackets were never allowed in namespace URIs
# according to RFC 3986, and so-called namespace-validating
# XML parsers have the right to reject them a invalid URIs.
#
# libexpat >=2.4.5 has become strcter in that regard due to
# related security issues; with ET.XML instantiating a
# namespace-aware parser under the hood, this test has no
# future in CPython.
#
# References:
# - https://datatracker.ietf.org/doc/html/rfc3968
# - https://www.w3.org/TR/xml-names/
#
# Also, test_minidom.py: Support Expat >=2.4.5
#
# The patch has diverged from upstream as the python test
# suite was relying on checking the expat version, whereas
# in RHEL fixes get backported instead of rebasing packages.
#
# Upstream: https://bugs.python.org/issue46811
Patch378: 00378-support-expat-2-4-5.patch

# 00397 #
# Add filters for tarfile extraction (CVE-2007-4559, PEP-706)
# First patch fixes determination of symlink targets, which were treated
# as relative to the root of the archive,
# rather than the directory containing the symlink.
# Not yet upstream as of this writing.
# The second patch is Red Hat configuration, see KB for documentation:
# - https://access.redhat.com/articles/7004769
Patch397: 00397-tarfile-filter.patch

# (New patches go here ^^^)
#
# When adding new patches to "python" and "python3" in Fedora, EL, etc.,
# please try to keep the patch numbers in-sync between all specfiles.
#
# More information, and a patch number catalog, is at:
#
#     https://fedoraproject.org/wiki/SIGs/Python/PythonPatches
#
# The patches are stored and rebased at:
#
#     https://github.com/fedora-python/cpython


# ==========================================
# Descriptions, and metadata for subpackages
# ==========================================

# People might want to dnf install pythonX.Y instead of pythonXY;
# we enable this in both flat and nonflat package.
Provides: python%{pybasever} = %{version}-%{release}

# When the user tries to `yum install python`, yum will list this package among
# the possible alternatives
Provides: alternative-for(python)

# Require alternatives version that implements the --keep-foreign flag
Requires:         alternatives >= 1.19.1-1
Requires(post):   alternatives >= 1.19.1-1
Requires(postun): alternatives >= 1.19.1-1

%if %{without flatpackage}

# Packages with Python modules in standard locations automatically
# depend on python(abi). Provide that here.
Provides: python(abi) = %{pybasever}

Requires: %{name}-libs%{?_isa} = %{version}-%{release}

# In order to support multiple Python interpreters for development purposes,
# packages with the naming scheme flatpackage (e.g. python35) exist for
# non-default versions of Python 3.
# For consistency, and to keep the upgrade path clean, we Provide/Obsolete
# these names here.
Provides: python%{pyshortver} = %{version}-%{release}

%if %{with main_python}
# https://fedoraproject.org/wiki/Changes/Move_usr_bin_python_into_separate_package
# https://fedoraproject.org/wiki/Changes/Python_means_Python3
# We recommend /usr/bin/python so users get it by default
# Versioned recommends are problematic, and we know that the package requires
# python3 back with fixed version, so we just use the path here:
Recommends: %{_bindir}/python
%endif

# In Fedora 31, /usr/bin/pydoc was moved here from Python 2.
# Ideally we'd have an explicit conflict with "/usr/bin/pydoc < 3",
# but file provides aren't versioned and the file moved across packages.
# Instead, we rely on the conflict in python3-libs.

# Previously, this was required for our rewheel patch to work.
# This is technically no longer needed, but we keep it recommended
# for the developer experience.
Recommends: python38-setuptools
Recommends: python38-pip

# This prevents ALL subpackages built from this spec to require
# /usr/bin/python3*. Granularity per subpackage is impossible.
# It's intended for the libs package not to drag in the interpreter, see
# https://bugzilla.redhat.com/show_bug.cgi?id=1547131
# All others require %%{name} anyway.
%global __requires_exclude ^/usr/bin/python3


# The description used both for the SRPM and the main `python3` subpackage:
%description
Python is an accessible, high-level, dynamically typed, interpreted programming
language, designed with an emphasis on code readability.
It includes an extensive standard library, and has a vast ecosystem of
third-party libraries.

The %{name} package provides the "python3" executable: the reference
interpreter for the Python language, version 3.
The majority of its standard library is provided in the %{name}-libs package,
which should be installed automatically along with %{name}.
The remaining parts of the Python standard library are broken out into the
%{name}-tkinter and %{name}-test packages, which may need to be installed
separately.

Documentation for Python is provided in the %{name}-docs package.

Packages containing additional libraries for Python are generally named with
the "%{name}-" prefix.

For the unversioned "python" executable, see manual page "unversioned-python".


%if %{with main_python}
# https://fedoraproject.org/wiki/Changes/Move_usr_bin_python_into_separate_package
# https://fedoraproject.org/wiki/Changes/Python_means_Python3
%package -n python-unversioned-command
Summary: The "python" command that runs Python 3
BuildArch: noarch

# In theory this could require any python3 version
Requires: python3 == %{version}-%{release}
# But since we want to provide versioned python, we require exact version
Provides: python = %{version}-%{release}
# This also save us an explicit conflict for older python3 builds

%description -n python-unversioned-command
This package contains /usr/bin/python - the "python" command that runs Python 3.

%endif # with main_python


%package libs
Summary:        Python runtime libraries

%if %{with rpmwheels}
Requires: python38-setuptools-wheel
Requires: python38-pip-wheel
%else
Provides: bundled(python38-pip) = 23.0.1
Provides: bundled(python38-setuptools) = 56.0.0
%endif

%{?python_provide:%python_provide python38-libs}

# There are files in the standard library that have python shebang.
# We've filtered the automatic requirement out so libs are installable without
# the main package. This however makes it pulled in by default.
# See https://bugzilla.redhat.com/show_bug.cgi?id=1547131
Recommends: %{name}%{?_isa} = %{version}-%{release}

# tkinter is part of the standard library,
# but it is torn out to save an unwanted dependency on tk and X11.
# we recommend it when tk is already installed (for better UX)
Recommends: (%{name}-tkinter%{?_isa} = %{version}-%{release} if tk%{?_isa})

%description libs
This package contains runtime libraries for use by Python:
- the majority of the Python standard library
- a dynamically linked library for use by applications that embed Python as
  a scripting language, and by the main "python3" executable


%package devel
Summary: Libraries and header files needed for Python development
Requires: %{name} = %{version}-%{release}
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
BuildRequires: python-rpm-macros
# The RPM related dependencies bring nothing to a non-RPM Python developer
# But we want them when packages BuildRequire python3-devel
Requires: (python-rpm-macros if rpm-build)
Requires: (python3-rpm-macros if rpm-build)

# Require alternatives version that implements the --keep-foreign flag
Requires(postun): alternatives >= 1.19.1-1
# python38 installs the alternatives master symlink to which we attach a slave
Requires(post): python38
Requires(postun): python38

%if %{without bootstrap}
# This is not "API" (packages that need setuptools should still BuildRequire it)
# However some packages apparently can build both with and without setuptools
# producing egg-info as file or directory (depending on setuptools presence).
# Directory-to-file updates are problematic in RPM, so we ensure setuptools is
# installed when -devel is required.
# See https://bugzilla.redhat.com/show_bug.cgi?id=1623914
# See https://fedoraproject.org/wiki/Packaging:Directory_Replacement
Requires: (python38-setuptools if rpm-build)
%endif

Requires: (python3-rpm-generators if rpm-build)

%{?python_provide:%python_provide python38-devel}

%description devel
This package contains the header files and configuration needed to compile
Python extension modules (typically written in C or C++), to embed Python
into other programs, and to make binary distributions for Python libraries.

It also contains the necessary macros to build RPM packages with Python modules
and 2to3 tool, an automatic source converter from Python 2.X.

If you want to build an RPM against the python38 module, you also need to
install the python38-rpm-macros package.


%package idle
Summary: A basic graphical development environment for Python
Requires: %{name} = %{version}-%{release}
Requires: %{name}-tkinter = %{version}-%{release}

%{?python_provide:%python_provide python38-idle}

# Require alternatives version that implements the --keep-foreign flag
Requires(postun): alternatives >= 1.19.1-1
# python38 installs the alternatives master symlink to which we attach a slave
Requires(post): python38
Requires(postun): python38

%description idle
IDLE is Python’s Integrated Development and Learning Environment.

IDLE has the following features: Python shell window (interactive
interpreter) with colorizing of code input, output, and error messages;
multi-window text editor with multiple undo, Python colorizing,
smart indent, call tips, auto completion, and other features;
search within any window, replace within editor windows, and
search through multiple files (grep); debugger with persistent
breakpoints, stepping, and viewing of global and local namespaces;
configuration, browsers, and other dialogs.


%package tkinter
Summary: A GUI toolkit for Python
Requires: %{name} = %{version}-%{release}

%{?python_provide:%python_provide python38-tkinter}

%description tkinter
The Tkinter (Tk interface) library is a graphical user interface toolkit for
the Python programming language.


%package test
Summary: The self-test suite for the main python3 package
Requires: %{name} = %{version}-%{release}
Requires: %{name}-libs%{?_isa} = %{version}-%{release}

%{?python_provide:%python_provide python38-test}

%description test
The self-test suite for the Python interpreter.

This is only useful to test Python itself. For testing general Python code,
you should use the unittest module from %{name}-libs, or a library such as
%{name}-pytest or %{name}-nose.


%if %{with debug_build}
%package debug
Summary: Debug version of the Python runtime

# The debug build is an all-in-one package version of the regular build, and
# shares the same .py/.pyc files and directories as the regular build. Hence
# we depend on all of the subpackages of the regular build:
Requires: %{name}%{?_isa} = %{version}-%{release}
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
Requires: %{name}-devel%{?_isa} = %{version}-%{release}
Requires: %{name}-test%{?_isa} = %{version}-%{release}
Requires: %{name}-tkinter%{?_isa} = %{version}-%{release}
Requires: %{name}-idle%{?_isa} = %{version}-%{release}

# Require alternatives version that implements the --keep-foreign flag
Requires(postun): alternatives >= 1.19.1-1
# python38 installs the alternatives master symlink to which we attach a slave
Requires(post): python38
Requires(postun): python38

%{?python_provide:%python_provide python38-debug}

%description debug
python38-debug provides a version of the Python runtime with numerous debugging
features enabled, aimed at advanced Python users such as developers of Python
extension modules.

This version uses more memory and will be slower than the regular Python build,
but is useful for tracking down reference-counting issues and other bugs.

The debug build shares installation directories with the standard Python
runtime. Python modules -- source (.py), bytecode (.pyc), and C-API extensions
(.cpython*.so) -- are compatible between this and the standard version
of Python.

The debug runtime additionally supports debug builds of C-API extensions
(with the "d" ABI flag) for debugging issues in those extensions.
%endif # with debug_build

%else  # with flatpackage

# We'll not provide this, on purpose
# No package in Fedora shall ever depend on flatpackage via this
%global __requires_exclude ^python\\(abi\\) = 3\\..$
%global __provides_exclude ^python\\(abi\\) = 3\\..$

%if %{with rpmwheels}
Requires: python38-setuptools-wheel
Requires: python38-pip-wheel
%else
Provides: bundled(python38-pip) = 23.0.1
Provides: bundled(python38-setuptools) = 56.0.0
%endif

# The description for the flat package
%description
Python %{pybasever} package for developers.

This package exists to allow developers to test their code against a newer
version of Python. This is not a full Python stack and if you wish to run
your applications with Python %{pybasever}, update your Fedora to a newer
version once Python %{pybasever} is stable.

%endif # with flatpackage


%package -n python38-rpm-macros
Summary:    RPM macros for building RPMs with Python 3.8
Provides:   python38-modular-devel = %{version}-%{release}
Provides:   python-modular-rpm-macros == 3.8
Conflicts:  python-modular-rpm-macros > 3.8
Requires:   python3-rpm-macros
BuildArch:  noarch

%description -n python38-rpm-macros
RPM macros for building RPMs with Python 3.8 from the python38 module.
If you want to build an RPM against the python38 module, you need to
BuildRequire: python38-rpm-macros.


# ======================================================
# The prep phase of the build:
# ======================================================

%prep
%setup -q -n Python-%{upstream_version}
# Remove all exe files to ensure we are not shipping prebuilt binaries
# note that those are only used to create Microsoft Windows installers
# and that functionality is broken on Linux anyway
find -name '*.exe' -print -delete

# Remove bundled libraries to ensure that we're using the system copy.
rm -r Modules/expat

#
# Apply patches:
#
%patch1 -p1

%if "%{_lib}" == "lib64"
%patch102 -p1
%endif
%patch111 -p1

%if %{with rpmwheels}
%patch189 -p1
rm Lib/ensurepip/_bundled/*.whl
%endif

%patch251 -p1
%patch328 -p1
%patch329 -p1
%patch353 -p1
%patch359 -p1
%patch378 -p1
%patch397 -p1

# Remove files that should be generated by the build
# (This is after patching, so that we can use patches directly from upstream)
rm configure pyconfig.h.in

# When we use the legacy arch names, we need to change them in configure.ac
%if %{with legacy_archnames}
sed -i configure.ac \
    -e 's/\b%{platform_triplet_upstream}\b/%{platform_triplet_legacy}/'
%endif


# ======================================================
# Configuring and building the code:
# ======================================================

%build

# Regenerate the configure script and pyconfig.h.in
autoconf
autoheader

# Remember the current directory (which has sources and the configure script),
# so we can refer to it after we "cd" elsewhere.
topdir=$(pwd)

# Get proper option names from bconds
%if %{with computed_gotos}
%global computed_gotos_flag yes
%else
%global computed_gotos_flag no
%endif

%if %{with optimizations}
%global optimizations_flag "--enable-optimizations"
%else
%global optimizations_flag "--disable-optimizations"
%endif

# Set common compiler/linker flags
# We utilize the %%extension_...flags macros here so users building C/C++
# extensions with our python won't get all the compiler/linker flags used
# in Fedora RPMs.
# Standard library built here will still use the %%build_...flags,
# Fedora packages utilizing %%py3_build will use them as well
# https://fedoraproject.org/wiki/Changes/Python_Extension_Flags
export CFLAGS="%{extension_cflags} -D_GNU_SOURCE -fPIC -fwrapv"
export CFLAGS_NODIST="%{build_cflags} -D_GNU_SOURCE -fPIC -fwrapv%{?with_no_semantic_interposition: -fno-semantic-interposition}"
export CXXFLAGS="%{extension_cxxflags} -D_GNU_SOURCE -fPIC -fwrapv"
export CPPFLAGS="$(pkg-config --cflags-only-I libffi)"
export OPT="%{extension_cflags} -D_GNU_SOURCE -fPIC -fwrapv"
export LINKCC="gcc"
export CFLAGS="$CFLAGS $(pkg-config --cflags openssl)"
export LDFLAGS="%{extension_ldflags} -g $(pkg-config --libs-only-L openssl)"
export LDFLAGS_NODIST="%{build_ldflags}%{?with_no_semantic_interposition: -fno-semantic-interposition} -g $(pkg-config --libs-only-L openssl)"

# We can build several different configurations of Python: regular and debug.
# Define a common function that does one build:
BuildPython() {
  ConfName=$1
  ExtraConfigArgs=$2
  MoreCFlags=$3

  # Each build is done in its own directory
  ConfDir=build/$ConfName
  echo STARTING: BUILD OF PYTHON FOR CONFIGURATION: $ConfName
  mkdir -p $ConfDir
  pushd $ConfDir

  # Normally, %%configure looks for the "configure" script in the current
  # directory.
  # Since we changed directories, we need to tell %%configure where to look.
  %global _configure $topdir/configure

%configure \
  --enable-ipv6 \
  --enable-shared \
  --with-computed-gotos=%{computed_gotos_flag} \
  --with-dbmliborder=gdbm:ndbm:bdb \
  --with-system-expat \
  --with-system-ffi \
  --enable-loadable-sqlite-extensions \
  --with-dtrace \
  --with-lto \
  --with-ssl-default-suites=openssl \
%if %{with valgrind}
  --with-valgrind \
%endif
  $ExtraConfigArgs \
  %{nil}

%global flags_override EXTRA_CFLAGS="$MoreCFlags" CFLAGS_NODIST="$CFLAGS_NODIST $MoreCFlags"

%if %{without bootstrap}
  # Regenerate generated files (needs python3)
  %make_build %{flags_override} regen-all PYTHON_FOR_REGEN="python%{pybasever}"
%endif

  # Invoke the build
  %make_build %{flags_override}

  popd
  echo FINISHED: BUILD OF PYTHON FOR CONFIGURATION: $ConfName
}

# Call the above to build each configuration.

%if %{with debug_build}
BuildPython debug \
  "--without-ensurepip --with-pydebug" \
  "-Og"
%endif # with debug_build

BuildPython optimized \
  "--without-ensurepip %{optimizations_flag}" \
  ""

# ======================================================
# Installing the built code:
# ======================================================

%install

# As in %%build, remember the current directory
topdir=$(pwd)

# We install a collection of hooks for gdb that make it easier to debug
# executables linked against libpython3* (such as /usr/bin/python3 itself)
#
# These hooks are implemented in Python itself (though they are for the version
# of python that gdb is linked with)
#
# gdb-archer looks for them in the same path as the ELF file or its .debug
# file, with a -gdb.py suffix.
# We put them next to the debug file, because ldconfig would complain if
# it found non-library files directly in /usr/lib/
# (see https://bugzilla.redhat.com/show_bug.cgi?id=562980)
#
# We'll put these files in the debuginfo package by installing them to e.g.:
#  /usr/lib/debug/usr/lib/libpython3.2.so.1.0.debug-gdb.py
# (note that the debug path is /usr/lib/debug for both 32/64 bit)
#
# See https://fedoraproject.org/wiki/Features/EasierPythonDebugging for more
# information

%if %{with gdb_hooks}
DirHoldingGdbPy=%{_usr}/lib/debug/%{_libdir}
mkdir -p %{buildroot}$DirHoldingGdbPy
%endif # with gdb_hooks

# Multilib support for pyconfig.h
# 32- and 64-bit versions of pyconfig.h are different. For multilib support
# (making it possible to install 32- and 64-bit versions simultaneously),
# we need to install them under different filenames, and to make the common
# "pyconfig.h" include the right file based on architecture.
# See https://bugzilla.redhat.com/show_bug.cgi?id=192747
# Filanames are defined here:
%global _pyconfig32_h pyconfig-32.h
%global _pyconfig64_h pyconfig-64.h
%global _pyconfig_h pyconfig-%{__isa_bits}.h

# Use a common function to do an install for all our configurations:
InstallPython() {

  ConfName=$1
  PyInstSoName=$2
  MoreCFlags=$3
  LDVersion=$4

  # Switch to the directory with this configuration's built files
  ConfDir=build/$ConfName
  echo STARTING: INSTALL OF PYTHON FOR CONFIGURATION: $ConfName
  mkdir -p $ConfDir
  pushd $ConfDir

  make \
    DESTDIR=%{buildroot} \
    INSTALL="install -p" \
    EXTRA_CFLAGS="$MoreCFlags" \
    install

  popd

%if %{with gdb_hooks}
  # See comment on $DirHoldingGdbPy above
  PathOfGdbPy=$DirHoldingGdbPy/$PyInstSoName-%{version}-%{release}.%{_arch}.debug-gdb.py
  cp Tools/gdb/libpython.py %{buildroot}$PathOfGdbPy
%endif # with gdb_hooks

  # Rename the -devel script that differs on different arches to arch specific name
  mv %{buildroot}%{_bindir}/python${LDVersion}-{,`uname -m`-}config
  echo -e '#!/bin/sh\nexec `dirname $0`/python'${LDVersion}'-`uname -m`-config "$@"' > \
    %{buildroot}%{_bindir}/python${LDVersion}-config
  echo '[ $? -eq 127 ] && echo "Could not find python'${LDVersion}'-`uname -m`-config. Look around to see available arches." >&2' >> \
    %{buildroot}%{_bindir}/python${LDVersion}-config
    chmod +x %{buildroot}%{_bindir}/python${LDVersion}-config

  # Make python3-devel multilib-ready
  mv %{buildroot}%{_includedir}/python${LDVersion}/pyconfig.h \
     %{buildroot}%{_includedir}/python${LDVersion}/%{_pyconfig_h}
  cat > %{buildroot}%{_includedir}/python${LDVersion}/pyconfig.h << EOF
#include <bits/wordsize.h>

#if __WORDSIZE == 32
#include "%{_pyconfig32_h}"
#elif __WORDSIZE == 64
#include "%{_pyconfig64_h}"
#else
#error "Unknown word size"
#endif
EOF

  echo FINISHED: INSTALL OF PYTHON FOR CONFIGURATION: $ConfName
}

# Install the "debug" build first; any common files will be overridden with
# later builds
%if %{with debug_build}
InstallPython debug \
  %{py_INSTSONAME_debug} \
  -O0 \
  %{LDVERSION_debug}
%endif # with debug_build

# Now the optimized build:
InstallPython optimized \
  %{py_INSTSONAME_optimized} \
  "" \
  %{LDVERSION_optimized}

# Install directories for additional packages
install -d -m 0755 %{buildroot}%{pylibdir}/site-packages/__pycache__
%if "%{_lib}" == "lib64"
# The 64-bit version needs to create "site-packages" in /usr/lib/ (for
# pure-Python modules) as well as in /usr/lib64/ (for packages with extension
# modules).
# Note that rpmlint will complain about hardcoded library path;
# this is intentional.
install -d -m 0755 %{buildroot}%{_prefix}/lib/python%{pybasever}/site-packages/__pycache__
%endif

%if %{with main_python}
# add idle3 to menu
install -D -m 0644 Lib/idlelib/Icons/idle_16.png %{buildroot}%{_datadir}/icons/hicolor/16x16/apps/idle3.png
install -D -m 0644 Lib/idlelib/Icons/idle_32.png %{buildroot}%{_datadir}/icons/hicolor/32x32/apps/idle3.png
install -D -m 0644 Lib/idlelib/Icons/idle_48.png %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/idle3.png
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE10}

# Install and validate appdata file
mkdir -p %{buildroot}%{_metainfodir}
cp -a %{SOURCE11} %{buildroot}%{_metainfodir}
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/idle3.appdata.xml
%endif

# Make sure distutils looks at the right pyconfig.h file
# See https://bugzilla.redhat.com/show_bug.cgi?id=201434
# Similar for sysconfig: sysconfig.get_config_h_filename tries to locate
# pyconfig.h so it can be parsed, and needs to do this at runtime in site.py
# when python starts up (see https://bugzilla.redhat.com/show_bug.cgi?id=653058)
#
# Split this out so it goes directly to the pyconfig-32.h/pyconfig-64.h
# variants:
sed -i -e "s/'pyconfig.h'/'%{_pyconfig_h}'/" \
  %{buildroot}%{pylibdir}/distutils/sysconfig.py \
  %{buildroot}%{pylibdir}/sysconfig.py

# Install pathfix.py to bindir
# See https://github.com/fedora-python/python-rpm-porting/issues/24
cp -p Tools/scripts/pathfix.py %{buildroot}%{_bindir}/pathfix%{pybasever}.py
ln -s pathfix%{pybasever}.py %{buildroot}%{_bindir}/pathfix.py

# Install i18n tools to bindir
# They are also in python2, so we version them
# https://bugzilla.redhat.com/show_bug.cgi?id=1571474
for tool in pygettext msgfmt; do
  cp -p Tools/i18n/${tool}.py %{buildroot}%{_bindir}/${tool}%{pybasever}.py
  ln -s ${tool}%{pybasever}.py %{buildroot}%{_bindir}/${tool}3.py
done

# Switch all shebangs to refer to the specific Python version.
# This currently only covers files matching ^[a-zA-Z0-9_]+\.py$,
# so handle files named using other naming scheme separately.
LD_LIBRARY_PATH=./build/optimized ./build/optimized/python \
  Tools/scripts/pathfix.py \
  -i "%{_bindir}/python%{pybasever}" -pn \
  %{buildroot} \
  %{buildroot}%{_bindir}/*%{pybasever}.py \
  %{?with_gdb_hooks:%{buildroot}$DirHoldingGdbPy/*.py}

# Remove tests for python3-tools which was removed in
# https://bugzilla.redhat.com/show_bug.cgi?id=1312030
rm -rf %{buildroot}%{pylibdir}/test/test_tools

# Remove shebang lines from .py files that aren't executable, and
# remove executability from .py files that don't have a shebang line:
find %{buildroot} -name \*.py \
  \( \( \! -perm /u+x,g+x,o+x -exec sed -e '/^#!/Q 0' -e 'Q 1' {} \; \
  -print -exec sed -i '1d' {} \; \) -o \( \
  -perm /u+x,g+x,o+x ! -exec grep -m 1 -q '^#!' {} \; \
  -exec chmod a-x {} \; \) \)

# Get rid of DOS batch files:
find %{buildroot} -name \*.bat -exec rm {} \;

# Get rid of backup files:
find %{buildroot}/ -name "*~" -exec rm -f {} \;
find . -name "*~" -exec rm -f {} \;

# Do bytecompilation with the newly installed interpreter.
# This is similar to the script in macros.pybytecompile
# compile *.pyc
find %{buildroot} -type f -a -name "*.py" -print0 | \
    LD_LIBRARY_PATH="%{buildroot}%{dynload_dir}/:%{buildroot}%{_libdir}" \
    PYTHONPATH="%{buildroot}%{_libdir}/python%{pybasever} %{buildroot}%{_libdir}/python%{pybasever}/site-packages" \
    xargs -0 %{buildroot}%{_bindir}/python%{pybasever} -O -c 'import py_compile, sys; [py_compile.compile(f, dfile=f.partition("%{buildroot}")[2], optimize=opt) for opt in range(3) for f in sys.argv[1:]]' || :

# Since we have pathfix.py in bindir, this is created, but we don't want it
rm -rf %{buildroot}%{_bindir}/__pycache__

# Fixup permissions for shared libraries from non-standard 555 to standard 755:
find %{buildroot} -perm 555 -exec chmod 755 {} \;

# Create "/usr/bin/python3-debug", a symlink to the python3 debug binary, to
# avoid the user having to know the precise version and ABI flags.
# See e.g. https://bugzilla.redhat.com/show_bug.cgi?id=676748
%if %{with debug_build} && %{with main_python}
ln -s \
  %{_bindir}/python%{LDVERSION_debug} \
  %{buildroot}%{_bindir}/python3-debug
%endif

%if %{without main_python}
# Remove stuff that would conflict with python3 package
rm %{buildroot}%{_bindir}/python3
rm %{buildroot}%{_bindir}/pydoc3
rm %{buildroot}%{_bindir}/pathfix.py
rm %{buildroot}%{_bindir}/pygettext3.py
rm %{buildroot}%{_bindir}/msgfmt3.py
rm %{buildroot}%{_bindir}/idle3
rm %{buildroot}%{_bindir}/python3-*
rm %{buildroot}%{_bindir}/2to3
rm %{buildroot}%{_libdir}/libpython3.so
rm %{buildroot}%{_mandir}/man1/python3.1*
rm %{buildroot}%{_libdir}/pkgconfig/python3.pc
rm %{buildroot}%{_libdir}/pkgconfig/python3-embed.pc
%else # main_python
# Link the unversioned stuff
# https://fedoraproject.org/wiki/Changes/Python_means_Python3
ln -s ./python3 %{buildroot}%{_bindir}/python
ln -s ./pydoc3 %{buildroot}%{_bindir}/pydoc
ln -s ./pygettext3.py %{buildroot}%{_bindir}/pygettext.py
ln -s ./msgfmt3.py %{buildroot}%{_bindir}/msgfmt.py
ln -s ./idle3 %{buildroot}%{_bindir}/idle
ln -s ./python3-config %{buildroot}%{_bindir}/python-config
ln -s ./python3.1 %{buildroot}%{_mandir}/man1/python.1
ln -s ./python3.pc %{buildroot}%{_libdir}/pkgconfig/python.pc
%if %{with debug_build}
ln -s ./python3-debug %{buildroot}%{_bindir}/python-debug
%endif
%endif # main_python


# Python RPM macros
mkdir -p %{buildroot}/%{rpmmacrodir}/
install -m 644 %{SOURCE3} \
    %{buildroot}/%{rpmmacrodir}/

# All ghost files controlled by alternatives need to exist for the files
# section check to succeed
# - Don't list /usr/bin/python as a ghost file so `yum install /usr/bin/python`
#   doesn't install this package
touch %{buildroot}%{_bindir}/unversioned-python
touch %{buildroot}%{_mandir}/man1/python.1.gz
touch %{buildroot}%{_bindir}/python3
touch %{buildroot}%{_mandir}/man1/python3.1.gz
touch %{buildroot}%{_bindir}/pydoc3
touch %{buildroot}%{_bindir}/pydoc-3
touch %{buildroot}%{_bindir}/idle3
touch %{buildroot}%{_bindir}/python3-config
touch %{buildroot}%{_bindir}/python3-debug
touch %{buildroot}%{_bindir}/python3-debug-config

# Strip the LTO bytecode from python.o
# Based on the fedora brp-strip-lto scriptlet
# https://src.fedoraproject.org/rpms/redhat-rpm-config/blob/9dd5528cf9805ebfe31cff04fe7828ad06a6023f/f/brp-strip-lto
find %{buildroot} -type f -name 'python.o' -print0 | xargs -0 \
bash -c "strip -p -R .gnu.lto_* -R .gnu.debuglto_* -N __gnu_lto_v1 \"\$@\"" ARG0

# ======================================================
# Checks for packaging issues
# ======================================================

%check

# first of all, check timestamps of bytecode files
find %{buildroot} -type f -a -name "*.py" -print0 | \
    LD_LIBRARY_PATH="%{buildroot}%{dynload_dir}/:%{buildroot}%{_libdir}" \
    PYTHONPATH="%{buildroot}%{_libdir}/python%{pybasever} %{buildroot}%{_libdir}/python%{pybasever}/site-packages" \
    xargs -0 %{buildroot}%{_bindir}/python%{pybasever} %{SOURCE8}

# Ensure that the curses module was linked against libncursesw.so, rather than
# libncurses.so
# See https://bugzilla.redhat.com/show_bug.cgi?id=539917
ldd %{buildroot}/%{dynload_dir}/_curses*.so \
    | grep curses \
    | grep libncurses.so && (echo "_curses.so linked against libncurses.so" ; exit 1)

# Ensure that the debug modules are linked against the debug libpython, and
# likewise for the optimized modules and libpython:
for Module in %{buildroot}/%{dynload_dir}/*.so ; do
    case $Module in
    *.%{SOABI_debug})
        ldd $Module | grep %{py_INSTSONAME_optimized} &&
            (echo Debug module $Module linked against optimized %{py_INSTSONAME_optimized} ; exit 1)

        ;;
    *.%{SOABI_optimized})
        ldd $Module | grep %{py_INSTSONAME_debug} &&
            (echo Optimized module $Module linked against debug %{py_INSTSONAME_debug} ; exit 1)
        ;;
    esac
done


# ======================================================
# Running the upstream test suite
# ======================================================

topdir=$(pwd)
CheckPython() {
  ConfName=$1
  ConfDir=$(pwd)/build/$ConfName

  echo STARTING: CHECKING OF PYTHON FOR CONFIGURATION: $ConfName

  # Note that we're running the tests using the version of the code in the
  # builddir, not in the buildroot.

  # Show some info, helpful for debugging test failures
  LD_LIBRARY_PATH=$ConfDir $ConfDir/python -m test.pythoninfo

  # Run the upstream test suite
  # --timeout=1800: kill test running for longer than 30 minutes
  # test_gdb skipped on s390x:
  #   https://bugzilla.redhat.com/show_bug.cgi?id=1678277
  # test_gdb skipped everywhere:
  #   https://bugzilla.redhat.com/show_bug.cgi?id=1734327
  # test_distutils
  #   distutils.tests.test_bdist_rpm tests fail when bootstraping the Python
  #   package: rpmbuild requires /usr/bin/pythonX.Y to be installed
  LD_LIBRARY_PATH=$ConfDir $ConfDir/python -m test.regrtest \
    -wW --slowest -j0 --timeout=1800 \
    %if %{with bootstrap}
    -x test_distutils \
    %endif
    -x test_gdb \
    %ifarch %{mips64}
    -x test_ctypes \
    %endif

  echo FINISHED: CHECKING OF PYTHON FOR CONFIGURATION: $ConfName

}

%if %{with tests}

# Check each of the configurations:
%if %{with debug_build}
CheckPython debug
%endif # with debug_build
CheckPython optimized

%endif # with tests


%post
# Alternative for /usr/bin/python -> /usr/bin/python3 + man page
alternatives --install %{_bindir}/unversioned-python \
                       python \
                       %{_bindir}/python3 \
                       300 \
             --slave   %{_bindir}/python \
                       unversioned-python \
                       %{_bindir}/python3 \
             --slave   %{_mandir}/man1/python.1.gz \
                       unversioned-python-man \
                       %{_mandir}/man1/python3.1.gz

# Alternative for /usr/bin/python -> /usr/bin/python3.8 + man page
alternatives --install %{_bindir}/unversioned-python \
                       python \
                       %{_bindir}/python3.8 \
                       208 \
             --slave   %{_bindir}/python \
                       unversioned-python \
                       %{_bindir}/python3.8 \
             --slave   %{_mandir}/man1/python.1.gz \
                       unversioned-python-man \
                       %{_mandir}/man1/python3.8.1.gz

# Alternative for /usr/bin/python3 -> /usr/bin/python3.8 + related files
# Create only if it doesn't exist already
EXISTS=`alternatives --display python3 | \
        grep -c "^/usr/bin/python3.8 - priority [0-9]*"`

if [ $EXISTS -eq 0 ]; then
    alternatives --install %{_bindir}/python3 \
                           python3 \
                           %{_bindir}/python3.8 \
                           3800 \
                 --slave   %{_mandir}/man1/python3.1.gz \
                           python3-man \
                           %{_mandir}/man1/python3.8.1.gz \
                 --slave   %{_bindir}/pydoc3 \
                           pydoc3 \
                           %{_bindir}/pydoc3.8 \
                 --slave   %{_bindir}/pydoc-3 \
                           pydoc-3 \
                           %{_bindir}/pydoc3.8
fi

%postun
# Do this only during uninstall process (not during update)
if [ $1 -eq 0 ]; then
    alternatives --keep-foreign --remove python \
                        %{_bindir}/python3.8

    alternatives --keep-foreign --remove python3 \
                        %{_bindir}/python3.8

    # Remove link python → python3 if no other python3.* exists
    if ! alternatives --display python3 > /dev/null; then
        alternatives --keep-foreign --remove python \
                            %{_bindir}/python3
    fi
fi


%post devel
alternatives --add-slave python3 %{_bindir}/python3.8 \
    %{_bindir}/python3-config \
    python3-config \
    %{_bindir}/python3.8-config

%postun devel
# Do this only during uninstall process (not during update)
if [ $1 -eq 0 ]; then
    alternatives --keep-foreign --remove-slave python3 %{_bindir}/python3.8 \
        python3-config
fi


%post debug
alternatives --add-slave python3 %{_bindir}/python3.8 \
    %{_bindir}/python3-debug \
    python3-debug \
    %{_bindir}/python3.8d
alternatives --add-slave python3 %{_bindir}/python3.8 \
    %{_bindir}/python3-debug-config \
    python3-debug-config \
    %{_bindir}/python3.8d-config

%postun debug
# Do this only during uninstall process (not during update)
if [ $1 -eq 0 ]; then
    alternatives --keep-foreign --remove-slave python3 %{_bindir}/python3.8 \
        python3-debug
    alternatives --keep-foreign --remove-slave python3 %{_bindir}/python3.8 \
        python3-debug-config
fi


%post idle
alternatives --add-slave python3 %{_bindir}/python3.8 \
    %{_bindir}/idle3 \
    idle3 \
    %{_bindir}/idle3.8

%postun idle
# Do this only during uninstall process (not during update)
if [ $1 -eq 0 ]; then
    alternatives --keep-foreign --remove-slave python3 %{_bindir}/python3.8 \
       idle3
fi


%files -n python38-rpm-macros
%license LICENSE
%doc README.rst
%{rpmmacrodir}/macros.python38

%files
%doc README.rst

# Alternatives
%ghost %{_bindir}/unversioned-python
%ghost %{_mandir}/man1/python.1.gz
%ghost %{_bindir}/python3
%ghost %{_mandir}/man1/python3.1.gz
%ghost %{_bindir}/pydoc3
%ghost %{_bindir}/pydoc-3


%if %{with main_python}
%{_bindir}/pydoc*
%{_bindir}/python3
%else
%{_bindir}/pydoc%{pybasever}
%endif

%{_bindir}/python%{pybasever}
%{_bindir}/python%{LDVERSION_optimized}
%{_mandir}/*/*3*


%if %{with main_python}
%if %{without flatpackage}
%files -n python-unversioned-command
%endif
%{_bindir}/python
%{_mandir}/*/python.1*
%endif

%if %{without flatpackage}
%files libs
%doc README.rst
%endif

%dir %{pylibdir}
%dir %{dynload_dir}

%license %{pylibdir}/LICENSE.txt

%{pylibdir}/lib2to3
%if %{without flatpackage}
%exclude %{pylibdir}/lib2to3/tests
%endif

%dir %{pylibdir}/unittest/
%dir %{pylibdir}/unittest/__pycache__/
%{pylibdir}/unittest/*.py
%{pylibdir}/unittest/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/asyncio/
%dir %{pylibdir}/asyncio/__pycache__/
%{pylibdir}/asyncio/*.py
%{pylibdir}/asyncio/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/venv/
%dir %{pylibdir}/venv/__pycache__/
%{pylibdir}/venv/*.py
%{pylibdir}/venv/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/venv/scripts

%{pylibdir}/wsgiref
%{pylibdir}/xmlrpc

%dir %{pylibdir}/ensurepip/
%dir %{pylibdir}/ensurepip/__pycache__/
%{pylibdir}/ensurepip/*.py
%{pylibdir}/ensurepip/__pycache__/*%{bytecode_suffixes}

%if %{with rpmwheels}
%exclude %{pylibdir}/ensurepip/_bundled
%else
%dir %{pylibdir}/ensurepip/_bundled
%{pylibdir}/ensurepip/_bundled/*.whl
%endif

%dir %{pylibdir}/concurrent/
%dir %{pylibdir}/concurrent/__pycache__/
%{pylibdir}/concurrent/*.py
%{pylibdir}/concurrent/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/concurrent/futures/
%dir %{pylibdir}/concurrent/futures/__pycache__/
%{pylibdir}/concurrent/futures/*.py
%{pylibdir}/concurrent/futures/__pycache__/*%{bytecode_suffixes}

%{pylibdir}/pydoc_data

%{dynload_dir}/_blake2.%{SOABI_optimized}.so
%{dynload_dir}/_sha3.%{SOABI_optimized}.so
%{dynload_dir}/_hmacopenssl.%{SOABI_optimized}.so

%{dynload_dir}/_asyncio.%{SOABI_optimized}.so
%{dynload_dir}/_bisect.%{SOABI_optimized}.so
%{dynload_dir}/_bz2.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_cn.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_hk.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_iso2022.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_jp.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_kr.%{SOABI_optimized}.so
%{dynload_dir}/_codecs_tw.%{SOABI_optimized}.so
%{dynload_dir}/_contextvars.%{SOABI_optimized}.so
%{dynload_dir}/_crypt.%{SOABI_optimized}.so
%{dynload_dir}/_csv.%{SOABI_optimized}.so
%{dynload_dir}/_ctypes.%{SOABI_optimized}.so
%{dynload_dir}/_curses.%{SOABI_optimized}.so
%{dynload_dir}/_curses_panel.%{SOABI_optimized}.so
%{dynload_dir}/_dbm.%{SOABI_optimized}.so
%{dynload_dir}/_decimal.%{SOABI_optimized}.so
%{dynload_dir}/_elementtree.%{SOABI_optimized}.so
%if %{with gdbm}
%{dynload_dir}/_gdbm.%{SOABI_optimized}.so
%endif
%{dynload_dir}/_hashlib.%{SOABI_optimized}.so
%{dynload_dir}/_heapq.%{SOABI_optimized}.so
%{dynload_dir}/_json.%{SOABI_optimized}.so
%{dynload_dir}/_lsprof.%{SOABI_optimized}.so
%{dynload_dir}/_lzma.%{SOABI_optimized}.so
%{dynload_dir}/_multibytecodec.%{SOABI_optimized}.so
%{dynload_dir}/_multiprocessing.%{SOABI_optimized}.so
%{dynload_dir}/_opcode.%{SOABI_optimized}.so
%{dynload_dir}/_pickle.%{SOABI_optimized}.so
%{dynload_dir}/_posixsubprocess.%{SOABI_optimized}.so
%{dynload_dir}/_queue.%{SOABI_optimized}.so
%{dynload_dir}/_random.%{SOABI_optimized}.so
%{dynload_dir}/_socket.%{SOABI_optimized}.so
%{dynload_dir}/_sqlite3.%{SOABI_optimized}.so
%{dynload_dir}/_ssl.%{SOABI_optimized}.so
%{dynload_dir}/_statistics.%{SOABI_optimized}.so
%{dynload_dir}/_struct.%{SOABI_optimized}.so
%{dynload_dir}/array.%{SOABI_optimized}.so
%{dynload_dir}/audioop.%{SOABI_optimized}.so
%{dynload_dir}/binascii.%{SOABI_optimized}.so
%{dynload_dir}/cmath.%{SOABI_optimized}.so
%{dynload_dir}/_datetime.%{SOABI_optimized}.so
%{dynload_dir}/fcntl.%{SOABI_optimized}.so
%{dynload_dir}/grp.%{SOABI_optimized}.so
%{dynload_dir}/math.%{SOABI_optimized}.so
%{dynload_dir}/mmap.%{SOABI_optimized}.so
%{dynload_dir}/nis.%{SOABI_optimized}.so
%{dynload_dir}/ossaudiodev.%{SOABI_optimized}.so
%{dynload_dir}/parser.%{SOABI_optimized}.so
%{dynload_dir}/_posixshmem.%{SOABI_optimized}.so
%{dynload_dir}/pyexpat.%{SOABI_optimized}.so
%{dynload_dir}/readline.%{SOABI_optimized}.so
%{dynload_dir}/resource.%{SOABI_optimized}.so
%{dynload_dir}/select.%{SOABI_optimized}.so
%{dynload_dir}/spwd.%{SOABI_optimized}.so
%{dynload_dir}/syslog.%{SOABI_optimized}.so
%{dynload_dir}/termios.%{SOABI_optimized}.so
%{dynload_dir}/unicodedata.%{SOABI_optimized}.so
%{dynload_dir}/_uuid.%{SOABI_optimized}.so
%{dynload_dir}/xxlimited.%{SOABI_optimized}.so
%{dynload_dir}/_xxsubinterpreters.%{SOABI_optimized}.so
%{dynload_dir}/zlib.%{SOABI_optimized}.so

%dir %{pylibdir}/site-packages/
%dir %{pylibdir}/site-packages/__pycache__/
%{pylibdir}/site-packages/README.txt
%{pylibdir}/*.py
%dir %{pylibdir}/__pycache__/
%{pylibdir}/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/collections/
%dir %{pylibdir}/collections/__pycache__/
%{pylibdir}/collections/*.py
%{pylibdir}/collections/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/ctypes/
%dir %{pylibdir}/ctypes/__pycache__/
%{pylibdir}/ctypes/*.py
%{pylibdir}/ctypes/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/ctypes/macholib

%{pylibdir}/curses

%dir %{pylibdir}/dbm/
%dir %{pylibdir}/dbm/__pycache__/
%{pylibdir}/dbm/*.py
%{pylibdir}/dbm/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/distutils/
%dir %{pylibdir}/distutils/__pycache__/
%{pylibdir}/distutils/*.py
%{pylibdir}/distutils/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/distutils/README
%{pylibdir}/distutils/command

%dir %{pylibdir}/email/
%dir %{pylibdir}/email/__pycache__/
%{pylibdir}/email/*.py
%{pylibdir}/email/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/email/mime
%doc %{pylibdir}/email/architecture.rst

%{pylibdir}/encodings

%{pylibdir}/html
%{pylibdir}/http

%dir %{pylibdir}/importlib/
%dir %{pylibdir}/importlib/__pycache__/
%{pylibdir}/importlib/*.py
%{pylibdir}/importlib/__pycache__/*%{bytecode_suffixes}

%dir %{pylibdir}/json/
%dir %{pylibdir}/json/__pycache__/
%{pylibdir}/json/*.py
%{pylibdir}/json/__pycache__/*%{bytecode_suffixes}

%{pylibdir}/logging
%{pylibdir}/multiprocessing

%dir %{pylibdir}/sqlite3/
%dir %{pylibdir}/sqlite3/__pycache__/
%{pylibdir}/sqlite3/*.py
%{pylibdir}/sqlite3/__pycache__/*%{bytecode_suffixes}

%if %{without flatpackage}
%exclude %{pylibdir}/turtle.py
%exclude %{pylibdir}/__pycache__/turtle*%{bytecode_suffixes}
%endif

%{pylibdir}/urllib
%{pylibdir}/xml

%if "%{_lib}" == "lib64"
%attr(0755,root,root) %dir %{_prefix}/lib/python%{pybasever}
%attr(0755,root,root) %dir %{_prefix}/lib/python%{pybasever}/site-packages
%attr(0755,root,root) %dir %{_prefix}/lib/python%{pybasever}/site-packages/__pycache__/
%endif

# "Makefile" and the config-32/64.h file are needed by
# distutils/sysconfig.py:_init_posix(), so we include them in the core
# package, along with their parent directories (bug 531901):
%dir %{pylibdir}/config-%{LDVERSION_optimized}-%{platform_triplet}/
%{pylibdir}/config-%{LDVERSION_optimized}-%{platform_triplet}/Makefile
%dir %{_includedir}/python%{LDVERSION_optimized}/
%{_includedir}/python%{LDVERSION_optimized}/%{_pyconfig_h}

%{_libdir}/%{py_INSTSONAME_optimized}
%if %{with main_python}
%{_libdir}/libpython3.so
%endif


%if %{without flatpackage}
%files devel
%endif

%if %{with main_python}
%{_bindir}/2to3
%endif

%{pylibdir}/config-%{LDVERSION_optimized}-%{platform_triplet}/*
%if %{without flatpackage}
%exclude %{pylibdir}/config-%{LDVERSION_optimized}-%{platform_triplet}/Makefile
%exclude %{_includedir}/python%{LDVERSION_optimized}/%{_pyconfig_h}
%endif
%{_includedir}/python%{LDVERSION_optimized}/*.h
%{_includedir}/python%{LDVERSION_optimized}/internal/
%{_includedir}/python%{LDVERSION_optimized}/cpython/
%doc Misc/README.valgrind Misc/valgrind-python.supp Misc/gdbinit

%if %{with main_python}
%{_bindir}/python3-config
%{_bindir}/python-config
%{_libdir}/pkgconfig/python3.pc
%{_libdir}/pkgconfig/python.pc
%{_libdir}/pkgconfig/python3-embed.pc
%{_bindir}/pathfix.py
%{_bindir}/pygettext3.py
%{_bindir}/pygettext.py
%{_bindir}/msgfmt3.py
%{_bindir}/msgfmt.py
%endif

%{_bindir}/2to3-%{pybasever}
%{_bindir}/pathfix%{pybasever}.py
%{_bindir}/pygettext%{pybasever}.py
%{_bindir}/msgfmt%{pybasever}.py

%{_bindir}/python%{pybasever}-config
%{_bindir}/python%{LDVERSION_optimized}-config
%{_bindir}/python%{LDVERSION_optimized}-*-config
# Alternatives
%ghost %{_bindir}/python3-config

%{_libdir}/libpython%{LDVERSION_optimized}.so
%{_libdir}/pkgconfig/python-%{LDVERSION_optimized}.pc
%{_libdir}/pkgconfig/python-%{LDVERSION_optimized}-embed.pc
%{_libdir}/pkgconfig/python-%{pybasever}.pc
%{_libdir}/pkgconfig/python-%{pybasever}-embed.pc


%if %{without flatpackage}
%files idle
%endif

%if %{with main_python}
%{_bindir}/idle*
%else
%{_bindir}/idle%{pybasever}
# Alternatives
%ghost %{_bindir}/idle3
%endif

%{pylibdir}/idlelib

%if %{with main_python}
%{_metainfodir}/idle3.appdata.xml
%{_datadir}/applications/idle3.desktop
%{_datadir}/icons/hicolor/*/apps/idle3.*
%endif

%if %{without flatpackage}
%files tkinter
%endif

%{pylibdir}/tkinter
%if %{without flatpackage}
%exclude %{pylibdir}/tkinter/test
%endif
%{dynload_dir}/_tkinter.%{SOABI_optimized}.so
%{pylibdir}/turtle.py
%{pylibdir}/__pycache__/turtle*%{bytecode_suffixes}
%dir %{pylibdir}/turtledemo
%{pylibdir}/turtledemo/*.py
%{pylibdir}/turtledemo/*.cfg
%dir %{pylibdir}/turtledemo/__pycache__/
%{pylibdir}/turtledemo/__pycache__/*%{bytecode_suffixes}


%if %{without flatpackage}
%files test
%endif

%{pylibdir}/ctypes/test
%{pylibdir}/distutils/tests
%{pylibdir}/sqlite3/test
%{pylibdir}/test
%{dynload_dir}/_ctypes_test.%{SOABI_optimized}.so
%{dynload_dir}/_testbuffer.%{SOABI_optimized}.so
%{dynload_dir}/_testcapi.%{SOABI_optimized}.so
%{dynload_dir}/_testimportmultiple.%{SOABI_optimized}.so
%{dynload_dir}/_testinternalcapi.%{SOABI_optimized}.so
%{dynload_dir}/_testmultiphase.%{SOABI_optimized}.so
%{dynload_dir}/_xxtestfuzz.%{SOABI_optimized}.so
%{pylibdir}/lib2to3/tests
%{pylibdir}/tkinter/test
%{pylibdir}/unittest/test

# We don't bother splitting the debug build out into further subpackages:
# if you need it, you're probably a developer.

# Hence the manifest is the combination of analogous files in the manifests of
# all of the other subpackages

%if %{with debug_build}
%if %{without flatpackage}
%files debug
%endif

%if %{with main_python}
%{_bindir}/python3-debug
%{_bindir}/python-debug
%endif

# Analog of the core subpackage's files:
%{_bindir}/python%{LDVERSION_debug}
# Alternatives
%ghost %{_bindir}/python3-debug

# Analog of the -libs subpackage's files:
# ...with debug builds of the built-in "extension" modules:

%{dynload_dir}/_blake2.%{SOABI_debug}.so
%{dynload_dir}/_sha3.%{SOABI_debug}.so
%{dynload_dir}/_hmacopenssl.%{SOABI_debug}.so

%{dynload_dir}/_asyncio.%{SOABI_debug}.so
%{dynload_dir}/_bisect.%{SOABI_debug}.so
%{dynload_dir}/_bz2.%{SOABI_debug}.so
%{dynload_dir}/_codecs_cn.%{SOABI_debug}.so
%{dynload_dir}/_codecs_hk.%{SOABI_debug}.so
%{dynload_dir}/_codecs_iso2022.%{SOABI_debug}.so
%{dynload_dir}/_codecs_jp.%{SOABI_debug}.so
%{dynload_dir}/_codecs_kr.%{SOABI_debug}.so
%{dynload_dir}/_codecs_tw.%{SOABI_debug}.so
%{dynload_dir}/_contextvars.%{SOABI_debug}.so
%{dynload_dir}/_crypt.%{SOABI_debug}.so
%{dynload_dir}/_csv.%{SOABI_debug}.so
%{dynload_dir}/_ctypes.%{SOABI_debug}.so
%{dynload_dir}/_curses.%{SOABI_debug}.so
%{dynload_dir}/_curses_panel.%{SOABI_debug}.so
%{dynload_dir}/_dbm.%{SOABI_debug}.so
%{dynload_dir}/_decimal.%{SOABI_debug}.so
%{dynload_dir}/_elementtree.%{SOABI_debug}.so
%if %{with gdbm}
%{dynload_dir}/_gdbm.%{SOABI_debug}.so
%endif
%{dynload_dir}/_hashlib.%{SOABI_debug}.so
%{dynload_dir}/_heapq.%{SOABI_debug}.so
%{dynload_dir}/_json.%{SOABI_debug}.so
%{dynload_dir}/_lsprof.%{SOABI_debug}.so
%{dynload_dir}/_lzma.%{SOABI_debug}.so
%{dynload_dir}/_multibytecodec.%{SOABI_debug}.so
%{dynload_dir}/_multiprocessing.%{SOABI_debug}.so
%{dynload_dir}/_opcode.%{SOABI_debug}.so
%{dynload_dir}/_pickle.%{SOABI_debug}.so
%{dynload_dir}/_posixsubprocess.%{SOABI_debug}.so
%{dynload_dir}/_queue.%{SOABI_debug}.so
%{dynload_dir}/_random.%{SOABI_debug}.so
%{dynload_dir}/_socket.%{SOABI_debug}.so
%{dynload_dir}/_sqlite3.%{SOABI_debug}.so
%{dynload_dir}/_ssl.%{SOABI_debug}.so
%{dynload_dir}/_statistics.%{SOABI_debug}.so
%{dynload_dir}/_struct.%{SOABI_debug}.so
%{dynload_dir}/array.%{SOABI_debug}.so
%{dynload_dir}/audioop.%{SOABI_debug}.so
%{dynload_dir}/binascii.%{SOABI_debug}.so
%{dynload_dir}/cmath.%{SOABI_debug}.so
%{dynload_dir}/_datetime.%{SOABI_debug}.so
%{dynload_dir}/fcntl.%{SOABI_debug}.so
%{dynload_dir}/grp.%{SOABI_debug}.so
%{dynload_dir}/math.%{SOABI_debug}.so
%{dynload_dir}/mmap.%{SOABI_debug}.so
%{dynload_dir}/nis.%{SOABI_debug}.so
%{dynload_dir}/ossaudiodev.%{SOABI_debug}.so
%{dynload_dir}/parser.%{SOABI_debug}.so
%{dynload_dir}/_posixshmem.%{SOABI_debug}.so
%{dynload_dir}/pyexpat.%{SOABI_debug}.so
%{dynload_dir}/readline.%{SOABI_debug}.so
%{dynload_dir}/resource.%{SOABI_debug}.so
%{dynload_dir}/select.%{SOABI_debug}.so
%{dynload_dir}/spwd.%{SOABI_debug}.so
%{dynload_dir}/syslog.%{SOABI_debug}.so
%{dynload_dir}/termios.%{SOABI_debug}.so
%{dynload_dir}/unicodedata.%{SOABI_debug}.so
%{dynload_dir}/_uuid.%{SOABI_debug}.so
%{dynload_dir}/_xxsubinterpreters.%{SOABI_debug}.so
%{dynload_dir}/_xxtestfuzz.%{SOABI_debug}.so
%{dynload_dir}/zlib.%{SOABI_debug}.so

# No need to split things out the "Makefile" and the config-32/64.h file as we
# do for the regular build above (bug 531901), since they're all in one package
# now; they're listed below, under "-devel":

%{_libdir}/%{py_INSTSONAME_debug}

# Analog of the -devel subpackage's files:
%{pylibdir}/config-%{LDVERSION_debug}-%{platform_triplet}
%{_includedir}/python%{LDVERSION_debug}
%{_bindir}/python%{LDVERSION_debug}-config
%{_bindir}/python%{LDVERSION_debug}-*-config
%ghost %{_bindir}/python3-debug-config

%{_libdir}/libpython%{LDVERSION_debug}.so
%{_libdir}/libpython%{LDVERSION_debug}.so.%{py_SOVERSION}
%{_libdir}/pkgconfig/python-%{LDVERSION_debug}.pc
%{_libdir}/pkgconfig/python-%{LDVERSION_debug}-embed.pc

# Analog of the -tools subpackage's files:
#  None for now; we could build precanned versions that have the appropriate
# shebang if needed

# Analog  of the tkinter subpackage's files:
%{dynload_dir}/_tkinter.%{SOABI_debug}.so

# Analog  of the -test subpackage's files:
%{dynload_dir}/_ctypes_test.%{SOABI_debug}.so
%{dynload_dir}/_testbuffer.%{SOABI_debug}.so
%{dynload_dir}/_testcapi.%{SOABI_debug}.so
%{dynload_dir}/_testimportmultiple.%{SOABI_debug}.so
%{dynload_dir}/_testinternalcapi.%{SOABI_debug}.so
%{dynload_dir}/_testmultiphase.%{SOABI_debug}.so

%endif # with debug_build

# We put the debug-gdb.py file inside /usr/lib/debug to avoid noise from ldconfig
# See https://bugzilla.redhat.com/show_bug.cgi?id=562980
#
# The /usr/lib/rpm/redhat/macros defines %%__debug_package to use
# debugfiles.list, and it appears that everything below /usr/lib/debug and
# (/usr/src/debug) gets added to this file (via LISTFILES) in
# /usr/lib/rpm/find-debuginfo.sh
#
# Hence by installing it below /usr/lib/debug we ensure it is added to the
# -debuginfo subpackage
# (if it doesn't, then the rpmbuild ought to fail since the debug-gdb.py
# payload file would be unpackaged)

# Workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1476593
%undefine _debuginfo_subpackages

# ======================================================
# Finally, the changelog:
# ======================================================

%changelog
* Wed Aug 09 2023 Petr Viktorin <pviktori@redhat.com> - 3.8.17-2
- Fix symlink handling in the fix for CVE-2023-24329
Resolves: rhbz#263261

* Mon Aug 07 2023 Charalampos Stratakis <cstratak@redhat.com> - 3.8.17-1
- Update to 3.8.17
- Security fix for CVE-2023-24329
- Add filters for tarfile extraction (CVE-2007-4559, PEP-706)
Resolves: rhbz#2173917, rhbz#263261

* Tue Jul 18 2023 Charalampos Stratakis <cstratak@redhat.com> - 3.8.16-2
- Strip the LTO bytecode from python.o
Resolves: rhbz#2213526

* Tue Dec 13 2022 Charalampos Stratakis <cstratak@redhat.com> - 3.8.16-1
- Update to 3.8.16
- Security fix for CVE-2022-45061
Resolves: rhbz#2144072

* Mon Sep 12 2022 Charalampos Stratakis <cstratak@redhat.com> - 3.8.14-1
- Rebase to 3.8.14
- Security fixes for CVE-2020-10735 and CVE-2021-28861
Resolves: rhbz#1834423, rhbz#2120642

* Tue Jun 14 2022 Charalampos Stratakis <cstratak@redhat.com> - 3.8.13-1
- Rebase to 3.8.13
- Security fix for CVE-2015-20107
- Fix the test suite support for Expat >= 2.4.5
Resolves: rhbz#2075390

* Wed Sep 15 2021 Charalampos Stratakis <cstratak@redhat.com> - 3.8.12-1
- Update to 3.8.12
Resolves: rhbz#2004587

* Tue Sep 07 2021 Charalampos Stratakis <cstratak@redhat.com> - 3.8.11-1
- Update to 3.8.11
- Fix for CVE-2021-3733 and CVE-2021-3737
Resolves: rhbz#1995234, rhbz#1995162

* Mon Aug 02 2021 Tomas Orsava <torsava@redhat.com> - 3.8.8-4
- Adjusted the postun scriptlets to enable upgrading to RHEL 9
- Resolves: rhbz#1933055

* Tue Jul 27 2021 Charalampos Stratakis <cstratak@redhat.com> - 3.8.8-3
- Security fix for CVE-2021-29921: Leading zeros in IPv4 addresses are no longer tolerated
Resolves: rhbz#1957458

* Fri Apr 30 2021 Charalampos Stratakis <cstratak@redhat.com> - 3.8.8-2
- Security fix for CVE-2021-3426: information disclosure via pydoc
Resolves: rhbz#1935913

* Mon Mar 15 2021 Lumír Balhar <lbalhar@redhat.com> - 3.8.8-1
- Update to 3.8.8 and fix CVE-2021-23336
Resolves: rhbz#1928904

* Fri Jan 22 2021 Charalampos Stratakis <cstratak@redhat.com> - 3.8.6-3
- Security fix for CVE-2021-3177
Resolves: rhbz#1919161

* Fri Oct 23 2020 Lumír Balhar <lbalhar@redhat.com> - 3.8.6-2
- Add support for upstream architecture names
https://fedoraproject.org/wiki/Changes/Python_Upstream_Architecture_Names
Resolves: rhbz#1868006

* Fri Oct 09 2020 Charalampos Stratakis <cstratak@redhat.com> - 3.8.6-1
- Update to 3.8.6
- Security fix for CVE-2020-26116
Resolves: rhbz#1886755, rhbz#1883259

* Mon Aug 17 2020 Tomas Orsava <torsava@redhat.com> - 3.8.3-3
- Avoid infinite loop when reading specially crafted TAR files (CVE-2019-20907)
Resolves: rhbz#1856481
- Resolve hash collisions for Pv4Interface and IPv6Interface (CVE-2020-14422)
Resolves: rhbz#1854926

* Wed Jun 24 2020 Tomas Orsava <torsava@redhat.com> - 3.8.3-2
- Fix sqlite3 deterministic test
Related: rhbz#1847416

* Wed Jun 24 2020 Tomas Orsava <torsava@redhat.com> - 3.8.3-1
- Rebased to 3.8.3 final
- Backported changes from Fedora
  - Recommend python3-tkinter when tk is installed
  - Add bcond for no_semantic_interposition (enabled by default)
  - Update the ensurepip module to work with setuptools >= 45
Resolves: rhbz#1847416

* Thu May 07 2020 Charalampos Stratakis <cstratak@redhat.com> - 3.8.0-10
- Fix test_hashlib and test_hmac under FIPS mode
Resolves: rhbz#1812477

* Thu Apr 23 2020 Lumír Balhar <lbalhar@redhat.com> - 3.8.0-9
- Fix ensurepip to run pip via runpy to fix compatibility with pip 19.3.1
Resolves: rhbz#1827623

* Wed Apr 22 2020 Charalampos Stratakis <cstratak@redhat.com> - 3.8.0-8
- Skip test_startup_imports from test_site if we have a .pth file in sys.path
Resolves: rhbz#1815643

* Fri Apr 03 2020 Charalampos Stratakis <cstratak@redhat.com> - 3.8.0-7
- Security fix for CVE-2020-8492
Resolves: rhbz#1810622

* Mon Feb 24 2020 Tomas Orsava <torsava@redhat.com> - 3.8.0-6
- Implement alternatives for /usr/bin/python, python3 and related executables
- Resolves: rhbz#1807041

* Fri Jan 10 2020 Charalampos Stratakis <cstratak@redhat.com> - 3.8.0-5
- Add support for FIPS mode
- Resolves: rhbz#1793589

* Thu Dec 12 2019 Tomas Orsava <torsava@redhat.com> - 3.8.0-4
- Exclude unsupported i686 arch

* Mon Nov 25 2019 Tomas Orsava <torsava@redhat.com> - 3.8.0-3
- Build Python with -fno-semantic-interposition for better performance
  https://fedoraproject.org/wiki/Changes/PythonNoSemanticInterpositionSpeedup

* Wed Nov 13 2019 Tomas Orsava <torsava@redhat.com> - 3.8.0-2
- Converting to RHEL8
- Changes from Fedora
  - Removed gpgverifycation as the tool used in Fedora is not present in RHEL8
  - Added versioned pathfix.py and 2to3 scripts into bindir
  - Depend on python3-rpm-generators always, because they run on Python 3.6
- Added python38-rpm-macros subpackage
  - Fixed py3_install_wheel macro because python38-pip does not have
    the --strip-prefix patch

* Mon Oct 14 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0-1
- Update to Python 3.8.0 final

* Tue Oct 01 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~rc1-1
- Rebased to Python 3.8.0rc1

* Fri Aug 30 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~b4-1
- Rebased to Python 3.8.0b4

* Thu Aug 15 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~b3-4
- Enable Profile-guided optimization for all arches, not just x86 (#1741015)

* Wed Aug 14 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~b3-3
- Rebuilt for Python 3.8

* Wed Aug 14 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~b3-2
- Bootstrap for Python 3.8

* Tue Aug 13 2019 Miro Hrončok <mhroncok@redhat.com> - 3.8.0~b3-1
- Update to 3.8.0b3

* Sun Aug 11 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.4-5
- Conditionalize python3-devel runtime dependencies on RPM packages and setuptools

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 3.7.4-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Mon Jul 15 2019 Lumír Balhar <lbalhar@redhat.com> - 3.7.4-3
- Move test.support module to python3-test subpackage
  https://fedoraproject.org/wiki/Changes/Move_test.support_module_to_python3-test_subpackage
- Restore pyc to TIMESTAMP invalidation mode as default in rpmbubild

* Fri Jul 12 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.4-2
- https://fedoraproject.org/wiki/Changes/Python_means_Python3
- The python-unversioned-command package is no longer Python 2, but 3
- The python, pydoc, python-config, python-debug, idle, pygettext.py and
  msgfmt.py commands are now in python3

* Tue Jul 09 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.4-1
- Update to 3.7.4

* Tue Jul 02 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.4~rc2-1
- Update to 3.7.4rc2

* Tue Jun 25 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.4~rc1-1
- Update to 3.7.4rc1

* Tue May 07 2019 Charalampos Stratakis <cstratak@redhat.com> - 3.7.3-3
- Fix handling of pre-normalization characters in urlsplit
- Disallow control chars in http URLs (#1695572, #1700684, #1688169, #1706851)

* Wed Apr 17 2019 Patrik Kopkan <pkopkan@redhat.com> - 3.7.3-2
- Makes man python3.7m show python3.7 man pages (#1612241)

* Wed Mar 27 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.3-1
- Update to 3.7.3

* Thu Mar 21 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.3~rc1-1
- Update to 3.7.3rc1

* Thu Mar 14 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.2-8
- Security fix for CVE-2019-9636 (#1688543, #1688546)

* Sun Feb 17 2019 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 3.7.2-7
- Rebuild for readline 8.0

* Tue Feb 12 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.2-6
- Reduced default build flags used to build extension modules
  https://fedoraproject.org/wiki/Changes/Python_Extension_Flags

* Sat Feb 02 2019 Fedora Release Engineering <releng@fedoraproject.org> - 3.7.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Wed Jan 16 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.2-4
- Security fix for CVE-2019-5010 (#1666519, #1666522)

* Mon Jan 14 2019 Björn Esser <besser82@fedoraproject.org> - 3.7.2-3
- Rebuilt for libcrypt.so.2 (#1666033)

* Fri Jan 04 2019 Miro Hrončok <mhroncok@redhat.com> - 3.7.2-2
- No longer revert upstream commit 3b699932e5ac3e7
- This was a dirty workaround for (#1644936)

* Tue Dec 25 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.2-1
- Update to 3.7.2

* Fri Dec 07 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.1-5
- Make sure we don't ship any exe files (not needed an prebuilt)

* Wed Nov 21 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.1-4
- Make sure the entire test.support module is in python3-libs (#1651245)

* Tue Nov 06 2018 Victor Stinner <vstinner@redhat.com> - 3.7.1-3
- Verify the value of '-s' when execute the CLI of cProfile (rhbz#1160640)

* Sun Nov 04 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.1-2
- Temporarily revert upstream commit 3b699932e5ac3e7
- This is dirty workaround for (#1644936)

* Mon Oct 22 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.1-1
- Update to 3.7.1

* Thu Sep 27 2018 Petr Viktorin <pviktori@redhat.com> - 3.7.0-10
- Compile the debug build with -Og rather than -O0

* Thu Aug 30 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-9
- Require python3-setuptools from python3-devel to prevent packaging errors (#1623914)

* Fri Aug 17 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-8
- Add /usr/bin/pygettext3.py and msgfmt3.py to python3-devel
Resolves: rhbz#1571474

* Fri Aug 17 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-7
- Backport TLS 1.3 related fixes to fix FTBFS
Resolves: rhbz#1609291

* Wed Aug 15 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-6
- Use RPM built wheels of pip and setuptools in ensurepip instead of our rewheel patch

* Fri Aug 10 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 3.7.0-5
- Fix wrong requirement on gdbm

* Fri Jul 20 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-4
- Allow to call Py_Main() after Py_Initialize()
Resolves: rhbz#1595421

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 3.7.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Thu Jul 12 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 3.7.0-2
- Rebuild for new gdbm

* Wed Jun 27 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-1
- Update to 3.7.0 final

* Wed Jun 13 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-0.21.rc1
- Finish bootstrapping, enable rewheel, tests, optimizations

* Tue Jun 12 2018 Miro Hrončok <mhroncok@redhat.com> - 3.7.0-0.20.rc1
- Update to 3.7.0rc1
- Bootstrap, disable rewheel, tests, optimizations

* Mon Apr 23 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.5-4
- Fix multiprocessing regression on newer glibcs
- Enable test_multiprocessing_fork(server) and _spawn again
Resolves: rhbz#1569933

* Thu Apr 19 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.5-3
- Skip test_multiprocessing_fork(server) and _spawn for now

* Wed Apr 18 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.5-2
- Add flatpackage conditionals

* Thu Mar 29 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.5-1
- Update to 3.6.5

* Sat Mar 24 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.4-20
- Fix broken macro invocation and broken building of C Python extensions
Resolves: rhbz#1560103

* Fri Mar 16 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.4-19
- Add -n option for pathfix.py
Resolves: rhbz#1546990

* Thu Mar 15 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.4-18
- Fix the py_byte_compile macro to work on Python 2
- Remove the pybytecompile macro file from the flat package
Resolves: rhbz#1484993

* Tue Mar 13 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-17
- Do not send IP addresses in SNI TLS extension

* Sat Feb 24 2018 Florian Weimer <fweimer@redhat.com> - 3.6.4-16
- Rebuild with new LDFLAGS from redhat-rpm-config

* Wed Feb 21 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.4-15
- Filter out automatic /usr/bin/python3.X requirement,
  recommend the main package from libs instead
Resolves: rhbz#1547131

* Thu Feb 15 2018 Iryna Shcherbina <ishcherb@redhat.com> - 3.6.4-14
- Remove the python3-tools package (#rhbz 1312030)
- Move /usr/bin/2to3 to python3-devel
- Move /usr/bin/idle and idlelib to python3-idle
- Provide python3-tools from python3-idle

* Fri Feb 09 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 3.6.4-13
- Escape macros in %%changelog

* Fri Feb 02 2018 Michal Cyprian <mcyprian@redhat.com> - 3.6.4-12
- Remove sys.executable check from change-user-install-location patch
Resolves: rhbz#1532287

* Thu Feb 01 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-11
- Define TLS cipher suite on build time.

* Wed Jan 31 2018 Tomas Orsava <torsava@redhat.com> - 3.6.4-10
- Disable test_gdb for all arches and test_buffer for ppc64le in anticipation
  of the F28 mass rebuild
- Re-enable these tests after the mass rebuild when they can be properly
  addressed

* Tue Jan 23 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-9
- Restore the PyExc_RecursionErrorInst public symbol

* Tue Jan 23 2018 Björn Esser <besser82@fedoraproject.org> - 3.6.4-8
- Add patch to explicitly link _ctypes module with -ldl (#1537489)
- Refactored patch for libxcrypt
- Re-enable strict symbol checks in the link editor

* Mon Jan 22 2018 Björn Esser <besser82@fedoraproject.org> - 3.6.4-7
- Add patch for libxcrypt
- Disable strict symbol checks in the link editor

* Sat Jan 20 2018 Björn Esser <besser82@fedoraproject.org> - 3.6.4-6
- Rebuilt for switch to libxcrypt

* Fri Jan 19 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-5
- Fix localeconv() encoding for LC_NUMERIC

* Thu Jan 18 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 3.6.4-4
- R: gdbm-devel → R: gdbm for python3-libs

* Wed Jan 17 2018 Miro Hrončok <mhroncok@redhat.com> - 3.6.4-3
- Require large enough gdbm (fixup for previous bump)

* Tue Jan 16 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-2
- Rebuild for reverted gdbm 1.13 on Fedora 27

* Mon Jan 15 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.4-1
- Update to version 3.6.4

* Fri Jan 12 2018 Charalampos Stratakis <cstratak@redhat.com> - 3.6.3-5
- Fix the compilation of the nis module.

* Tue Nov 21 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.3-4
- Raise the release of platform-python obsoletes for better maintainability

* Wed Nov 15 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.3-3
- Obsolete platform-python and it's subpackages

* Mon Oct 09 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.3-2
- Fix memory corruption due to allocator mix
Resolves: rhbz#1498207

* Fri Oct 06 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.3-1
- Update to Python 3.6.3

* Fri Sep 29 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.2-19
- Move pathfix.py to bindir, https://github.com/fedora-python/python-rpm-porting/issues/24
- Make the -devel package require redhat-rpm-config
Resolves: rhbz#1496757

* Wed Sep 13 2017 Iryna Shcherbina <ishcherb@redhat.com> - 3.6.2-18
- Fix /usr/bin/env dependency from python3-tools
Resolves: rhbz#1482118

* Wed Sep 06 2017 Iryna Shcherbina <ishcherb@redhat.com> - 3.6.2-17
- Include `-g` in the flags sent to the linker (LDFLAGS)
Resolves: rhbz#1483222

* Tue Sep 05 2017 Petr Viktorin <pviktori@redhat.com> - 3.6.2-16
- Specfile cleanup
- Make the main description also applicable to the SRPM
- Add audiotest.au to the test package

* Fri Sep 01 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.2-15
- Remove %%{pylibdir}/Tools/scripts/2to3

* Fri Sep 01 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.2-14
- Expat >= 2.1.0 is everywhere, remove explicit requires
- Conditionalize systemtap-devel BuildRequires
- For consistency, require /usr/sbin/ifconfig instead of net-tools

* Mon Aug 28 2017 Petr Viktorin <pviktori@redhat.com> - 3.6.2-13
- Rename patch files to be consistent
- Run autotools to generate the configure script before building
- Merge lib64 patches (104 into 102)
- Skip test_bdist_rpm using test config rather than a patch (removes patch 137)
- Remove patches 157 and 186, which had test changes left over after upstreaming
- Remove patch 188, a temporary workaround for hashlib tests
- Merge patches 180, 206, 243, 5001 (architecture naming) into new patch 274
- Move python2-tools conflicts to tools subpackage (it was wrongly in tkinter)

* Mon Aug 28 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.2-12
- Use python3 style of calling super() without arguments in rpath
  patch to prevent recursion in UnixCCompiler subclasses
Resolves: rhbz#1458122

* Mon Aug 21 2017 Petr Viktorin <pviktori@redhat.com> - 3.6.2-11
- Add bcond for --without optimizations
- Reword package descriptions
- Remove Group declarations
- Skip failing test_float_with_comma

* Mon Aug 21 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.2-10
- Remove system-python, see https://fedoraproject.org/wiki/Changes/Platform_Python_Stack

* Wed Aug 16 2017 Petr Viktorin <pviktori@redhat.com> - 3.6.2-9
- Use bconds for configuring the build
- Reorganize the initial sections

* Wed Aug 16 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.2-8
- Have /usr/bin/2to3 (rhbz#1111275)
- Provide 2to3 and idle3, list them in summary and description (rhbz#1076401)

* Fri Aug 11 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.2-7
- Revert "Add --executable option to install.py command"
  This enhancement is currently not needed and it can possibly
  collide with `pip --editable`option

* Mon Aug 07 2017 Iryna Shcherbina <ishcherb@redhat.com> - 3.6.2-6
- Fix the "urllib FTP protocol stream injection" vulnerability
Resolves: rhbz#1478916

* Tue Aug 01 2017 Tomas Orsava <torsava@redhat.com> - 3.6.2-5
- Dropped BuildRequires on db4-devel which was useful for Python 2 (module
  bsddb), however, no longer needod for Python 3
- Tested building Python 3 with and without the dependency, all tests pass and
  filelists of resulting RPMs are identical

* Sun Jul 30 2017 Florian Weimer <fweimer@redhat.com> - 3.6.2-4
- Do not generate debuginfo subpackages (#1476593)
- Rebuild with binutils fix for ppc64le (#1475636)

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.6.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Tue Jul 25 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.2-2
- Make test_asyncio to not depend on the current SIGHUP signal handler.

* Tue Jul 18 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.2-1
- Update to Python 3.6.2

* Tue Jun 27 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-10
- Update to the latest upstream implementation of PEP 538

* Mon Jun 26 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.1-9
- Make pip and distutils in user environment install into separate location

* Fri Jun 23 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-8
- Fix test_alpn_protocols from test_ssl
- Do not require rebundled setuptools dependencies

* Tue May 16 2017 Tomas Orsava <torsava@redhat.com> - 3.6.1-7
- Added a dependency to the devel subpackage on python3-rpm-generators which
  have been excised out of rpm-build
- Updated notes on bootstrapping Python on top of this specfile accordingly
- Involves: rhbz#1410631, rhbz#1444925

* Tue May 09 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-6
- Enable profile guided optimizations for x86_64 and i686 architectures
- Update to a newer implementation of PEP 538
- Update description to reflect that Python 3 is now the default Python

* Fri May 05 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-5
- Update PEP 538 to the latest upstream implementation

* Tue Apr 18 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-4
- Enable link time optimizations
- Move windows executables to the devel subpackage (rhbz#1426257)

* Thu Apr 13 2017 Tomas Orsava <torsava@redhat.com> - 3.6.1-3
- Rename python3.Xdm-config script from -debug to be arch specific
Resolves: rhbz#1179073

* Wed Apr 05 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.1-2
- Install the Makefile in its proper location (rhbz#1438219)

* Wed Mar 22 2017 Iryna Shcherbina <ishcherb@redhat.com> - 3.6.1-1
- Update to version 3.6.1 final

* Tue Mar 21 2017 Tomas Orsava <torsava@redhat.com> - 3.6.1-0.2.rc1
- Fix syntax error in %%py_byte_compile macro (rhbz#1433569)

* Thu Mar 16 2017 Iryna Shcherbina <ishcherb@redaht.com> - 3.6.1-0.1.rc1
- Update to Python 3.6.1 release candidate 1
- Add patch 264 to skip a known test failure on aarch64

* Fri Mar 10 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-21
- Use proper command line parsing in _testembed
- Backport of PEP 538: Coercing the legacy C locale to a UTF-8 based locale
  https://fedoraproject.org/wiki/Changes/python3_c.utf-8_locale

* Mon Feb 27 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-20
- Add desktop entry and appdata.xml file for IDLE 3 (rhbz#1392049)

* Fri Feb 24 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.0-19
- Revert "Set values of prefix and exec_prefix to /usr/local for
  /usr/bin/python* executables..." to prevent build failures
  of packages using alternate build tools

* Tue Feb 21 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.0-18
- Set values of prefix and exec_prefix to /usr/local for
  /usr/bin/python* executables
- Use new %%_module_build macro

* Fri Feb 17 2017 Michal Cyprian <mcyprian@redhat.com> - 3.6.0-13
- Add --executable option to install.py command

* Wed Feb 15 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-12
- BuildRequire the new dependencies of setuptools when rewheel mode is enabled
in order for the virtualenvs to work properly

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.6.0-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Feb 01 2017 Stephen Gallagher <sgallagh@redhat.com> - 3.6.0-10
- Add missing %%license macro

* Thu Jan 26 2017 Tomas Orsava <torsava@redhat.com> - 3.6.0-9
- Modify the runtime dependency of python3-libs on system-python-libs again,
  because previous attempt didn't work properly with dnf resolving mechanism

* Wed Jan 25 2017 Tomas Orsava <torsava@redhat.com> - 3.6.0-8
- Modify the runtime dependency of python3-libs on system-python-libs to use
  just the version and release number, but not the dist tag due to Modularity

* Mon Jan 16 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-7
- Fix error check, so that Random.seed actually uses OS randomness (rhbz#1412275)
- Skip test_aead_aes_gcm during rpmbuild

* Thu Jan 12 2017 Igor Gnatenko <ignatenko@redhat.com> - 3.6.0-6
- Rebuild for readline 7.x

* Tue Jan 10 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-5
- Require glibc >= 2.24.90-26 for system-python-libs (rhbz#1410644)

* Mon Jan 09 2017 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-4
- Define HAVE_LONG_LONG as 1 for backwards compatibility

* Thu Jan 05 2017 Miro Hrončok <mhroncok@redhat.com> - 3.6.0-3
- Don't blow up on EL7 kernel (random generator) (rhbz#1410175)

* Tue Dec 27 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-1
- Update to Python 3.6.0 final

* Fri Dec 09 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-0.6.rc1
- Enable rewheel

* Wed Dec 07 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-0.5.rc1
- Update to Python 3.6.0 release candidate 1

* Mon Dec 05 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.6.0-0.4.b4
- Update to Python 3.6.0 beta 4

* Mon Dec 05 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.2-7
- Set to work with pip version 9.0.1

* Wed Oct 12 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.2-6
- Use proper patch numbering and base upstream branch for
porting ssl and hashlib modules to OpenSSL 1.1.0
- Drop hashlib patch for now
- Add riscv64 arch to 64bit and no-valgrind arches

* Tue Oct 11 2016 Tomáš Mráz <tmraz@redhat.com> - 3.5.2-5
- Make it build with OpenSSL-1.1.0 based on upstream patch

* Wed Sep 14 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.2-4
- Obsolete and Provide python35 package

* Mon Sep 12 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.2-3
- Update %%py_byte_compile macro
- Remove unused configure flags (rhbz#1374357)

* Fri Sep 09 2016 Tomas Orsava <torsava@redhat.com> - 3.5.2-2
- Updated .pyc 'bytecompilation with the newly installed interpreter' to also
  recompile optimized .pyc files
- Removed .pyo 'bytecompilation with the newly installed interpreter', as .pyo
  files are no more
- Resolves rhbz#1373635

* Mon Aug 15 2016 Tomas Orsava <torsava@redhat.com> - 3.5.2-1
- Rebased to version 3.5.2
- Set to work with pip version 8.1.2
- Removed patches 207, 237, 241 as fixes are already contained in Python 3.5.2
- Removed arch or environment specific patches 194, 196, 203, and 208
  as test builds indicate they are no longer needed
- Updated patches 102, 146, and 242 to work with the new Python codebase
- Removed patches 200, 201, 5000 which weren't even being applied

* Tue Aug 09 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.1-15
- Fix for CVE-2016-1000110 HTTPoxy attack
- SPEC file cleanup

* Mon Aug 01 2016 Michal Toman <mtoman@fedoraproject.org> - 3.5.1-14
- Build properly on MIPS

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.5.1-13
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Fri Jul 08 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.1-12
- Refactor patch for properly fixing CVE-2016-5636

* Fri Jul 08 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.1-11
- Fix test_pyexpat failure with Expat version of 2.2.0

* Fri Jul 08 2016 Miro Hrončok <mhroncok@redhat.com> - 3.5.1-10
- Move xml module to system-python-libs

* Thu Jun 16 2016 Tomas Orsava <torsava@redhat.com> - 3.5.1-9
- Fix for: CVE-2016-0772 python: smtplib StartTLS stripping attack
- Raise an error when STARTTLS fails
- rhbz#1303647: https://bugzilla.redhat.com/show_bug.cgi?id=1303647
- rhbz#1346345: https://bugzilla.redhat.com/show_bug.cgi?id=1346345
- Fixed upstream: https://hg.python.org/cpython/rev/d590114c2394

* Mon Jun 13 2016 Charalampos Stratakis <cstratak@redhat.com> - 3.5.1-8
- Added patch for fixing possible integer overflow and heap corruption in zipimporter.get_data()

* Fri Mar 04 2016 Miro Hrončok <mhroncok@redhat.com> - 3.5.1-7
- Move distutils to system-python-libs

* Wed Feb 24 2016 Robert Kuska <rkuska@redhat.com> - 3.5.1-6
- Provide python3-enum34

* Fri Feb 19 2016 Miro Hrončok <mhroncok@redhat.com> - 3.5.1-5
- Provide System Python packages and macros

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.5.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Wed Jan 13 2016 Orion Poplwski <orion@cora.nwra.com> - 3.5.1-2
- Drop python3 macros, require python/python3-rpm-macros

* Mon Dec 14 2015 Robert Kuska <rkuska@redhat.com> - 3.5.1-1
- Update to 3.5.1
- Removed patch 199 and 207 (upstream)

* Sun Nov 15 2015 Robert Kuska <rkuska@redhat.com> - 3.5.0-5
- Remove versioned libpython from devel package

* Fri Nov 13 2015 Than Ngo <than@redhat.com> 3.5.0-4
- add correct arch for ppc64/ppc64le to fix build failure

* Wed Nov 11 2015 Robert Kuska <rkuska@redhat.com> - 3.5.0-3
- Hide the private _Py_atomic_xxx symbols from public header

* Wed Oct 14 2015 Robert Kuska <rkuska@redhat.com> - 3.5.0-2
- Rebuild with wheel set to 1

* Tue Sep 15 2015 Matej Stuchlik <mstuchli@redhat.com> - 3.5.0-1
- Update to 3.5.0

* Mon Jun 29 2015 Thomas Spura <tomspur@fedoraproject.org> - 3.4.3-4
- python3-devel: Require python-macros for version independant macros such as
  python_provide. See fpc#281 and fpc#534.

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.4.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed Jun 17 2015 Matej Stuchlik <mstuchli@redhat.com> - 3.4.3-4
- Use 1024bit DH key in test_ssl
- Use -O0 when compiling -debug build
- Update pip version variable to the version we actually ship

* Wed Jun 17 2015 Matej Stuchlik <mstuchli@redhat.com> - 3.4.3-3
- Make relocating Python by changing _prefix actually work
Resolves: rhbz#1231801

* Mon May  4 2015 Peter Robinson <pbrobinson@fedoraproject.org> 3.4.3-2
- Disable test_gdb on aarch64 (rhbz#1196181), it joins all other non x86 arches

* Thu Mar 12 2015 Matej Stuchlik <mstuchli@redhat.com> - 3.4.3-1
- Updated to 3.4.3
- BuildPython now accepts additional build options
- Temporarily disabled test_gdb on arm (rhbz#1196181)

* Wed Feb 25 2015 Matej Stuchlik <mstuchli@redhat.com> - 3.4.2-7
- Fixed undefined behaviour in faulthandler which caused test to hang on x86_64
  (http://bugs.python.org/issue23433)

* Sat Feb 21 2015 Till Maas <opensource@till.name> - 3.4.2-6
- Rebuilt for Fedora 23 Change
  https://fedoraproject.org/wiki/Changes/Harden_all_packages_with_position-independent_code

* Tue Feb 17 2015 Ville Skyttä <ville.skytta@iki.fi> - 3.4.2-5
- Own systemtap dirs (#710733)

* Mon Jan 12 2015 Dan Horák <dan[at]danny.cz> - 3.4.2-4
- build with valgrind on ppc64le
- disable test_gdb on s390(x) until rhbz#1181034 is resolved

* Tue Dec 16 2014 Robert Kuska <rkuska@redhat.com> - 3.4.2-3
- New patches: 170 (gc asserts), 200 (gettext headers),
  201 (gdbm memory leak)

* Thu Dec 11 2014 Robert Kuska <rkuska@redhat.com> - 3.4.2-2
- OpenSSL disabled SSLv3 in SSLv23 method

* Thu Nov 13 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.2-1
- Update to 3.4.2
- Refreshed patches: 156 (gdb autoload)
- Removed: 195 (Werror declaration), 197 (CVE-2014-4650)

* Mon Nov 03 2014 Slavek Kabrda <bkabrda@redhat.com> - 3.4.1-16
- Fix CVE-2014-4650 - CGIHTTPServer URL handling
Resolves: rhbz#1113529

* Sun Sep 07 2014 Karsten Hopp <karsten@redhat.com> 3.4.1-15
- exclude test_gdb on ppc* (rhbz#1132488)

* Thu Aug 21 2014 Slavek Kabrda <bkabrda@redhat.com> - 3.4.1-14
- Update rewheel patch with fix from https://github.com/bkabrda/rewheel/pull/1

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.4.1-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sun Jun  8 2014 Peter Robinson <pbrobinson@fedoraproject.org> 3.4.1-12
- aarch64 has valgrind, just list those that don't support it

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.4.1-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed Jun 04 2014 Karsten Hopp <karsten@redhat.com> 3.4.1-10
- bump release and rebuild to link with the correct tcl/tk libs on ppcle

* Tue Jun 03 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.1-9
- Change paths to bundled projects in rewheel patch

* Fri May 30 2014 Miro Hrončok <mhroncok@redhat.com> - 3.4.1-8
- In config script, use uname -m to write the arch

* Thu May 29 2014 Dan Horák <dan[at]danny.cz> - 3.4.1-7
- update the arch list where valgrind exists - %%power64 includes also
    ppc64le which is not supported yet

* Thu May 29 2014 Miro Hrončok <mhroncok@redhat.com> - 3.4.1-6
- Forward arguments to the arch specific config script
Resolves: rhbz#1102683

* Wed May 28 2014 Miro Hrončok <mhroncok@redhat.com> - 3.4.1-5
- Rename python3.Xm-config script to arch specific.
Resolves: rhbz#1091815

* Tue May 27 2014 Bohuslav Kabrda <bkabrda@redhat.com> - 3.4.1-4
- Use python3-*, not python-* runtime requires on setuptools and pip
- rebuild for tcl-8.6

* Tue May 27 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.1-3
- Update the rewheel module

* Mon May 26 2014 Miro Hrončok <mhroncok@redhat.com> - 3.4.1-2
- Fix multilib dependencies.
Resolves: rhbz#1091815

* Sun May 25 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.1-1
- Update to Python 3.4.1

* Sun May 25 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-8
- Fix test_gdb failure on ppc64le
Resolves: rhbz#1095355

* Thu May 22 2014 Miro Hrončok <mhroncok@redhat.com> - 3.4.0-7
- Add macro %%python3_version_nodots

* Sun May 18 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-6
- Disable test_faulthandler, test_gdb on aarch64
Resolves: rhbz#1045193

* Fri May 16 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-5
- Don't add Werror=declaration-after-statement for extension
  modules through setup.py (PyBT#21121)

* Mon May 12 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-4
- Add setuptools and pip to Requires

* Tue Apr 29 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-3
- Point __os_install_post to correct brp-* files

* Tue Apr 15 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-2
- Temporarily disable tests requiring SIGHUP (rhbz#1088233)

* Tue Apr 15 2014 Matej Stuchlik <mstuchli@redhat.com> - 3.4.0-1
- Update to Python 3.4 final
- Add patch adding the rewheel module
- Merge patches from master

* Wed Jan 08 2014 Bohuslav Kabrda <bkabrda@redhat.com> - 3.4.0-0.1.b2
- Update to Python 3.4 beta 2.
- Refreshed patches: 55 (systemtap), 146 (hashlib-fips), 154 (test_gdb noise)
- Dropped patches: 114 (statvfs constants), 177 (platform unicode)

* Mon Nov 25 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.4.0-0.1.b1
- Update to Python 3.4 beta 1.
- Refreshed patches: 102 (lib64), 111 (no static lib), 125 (less verbose COUNT
ALLOCS), 141 (fix COUNT_ALLOCS in test_module), 146 (hashlib fips),
157 (UID+GID overflows), 173 (ENOPROTOOPT in bind_port)
- Removed patch 00187 (remove pthread atfork; upstreamed)

* Mon Nov 04 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.4.0-0.1.a4
- Update to Python 3.4 alpha 4.
- Refreshed patches: 55 (systemtap), 102 (lib64), 111 (no static lib),
114 (statvfs flags), 132 (unittest rpmbuild hooks), 134 (fix COUNT_ALLOCS in
test_sys), 143 (tsc on ppc64), 146 (hashlib fips), 153 (test gdb noise),
157 (UID+GID overflows), 173 (ENOPROTOOPT in bind_port), 186 (dont raise
from py_compile)
- Removed patches: 129 (test_subprocess nonreadable dir - no longer fails in
Koji), 142 (the mock issue that caused this is fixed)
- Added patch 187 (remove thread atfork) - will be in next version
- Refreshed script for checking pyc and pyo timestamps with new ignored files.
- The fips patch is disabled for now until upstream makes a final decision
what to do with sha3 implementation for 3.4.0.

* Wed Oct 30 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.2-7
- Bytecompile all *.py files properly during build (rhbz#1023607)

* Fri Aug 23 2013 Matej Stuchlik <mstuchli@redhat.com> - 3.3.2-6
- Added fix for CVE-2013-4238 (rhbz#996399)

* Fri Jul 26 2013 Dennis Gilmore <dennis@ausil.us> - 3.3.2-5
- fix up indentation in arm patch

* Fri Jul 26 2013 Dennis Gilmore <dennis@ausil.us> - 3.3.2-4
- disable a test that fails on arm
- enable valgrind support on arm arches

* Tue Jul 02 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.2-3
- Fix build with libffi containing multilib wrapper for ffi.h (rhbz#979696).

* Mon May 20 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.2-2
- Add patch for CVE-2013-2099 (rhbz#963261).

* Thu May 16 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.2-1
- Updated to Python 3.3.2.
- Refreshed patches: 153 (gdb test noise)
- Dropped patches: 175 (configure -Wformat, fixed upstream), 182 (gdb
test threads)
- Synced patch numbers with python.spec.

* Thu May  9 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.1-4
- fix test.test_gdb.PyBtTests.test_threads on ppc64 (patch 181; rhbz#960010)

* Thu May 02 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.1-3
- Add patch that enables building on ppc64p7 (replace the sed, so that
we get consistent with python2 spec and it's more obvious that we're doing it.

* Wed Apr 24 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.1-2
- Add fix for gdb tests failing on arm, rhbz#951802.

* Tue Apr 09 2013 Bohuslav Kabrda <bkabrda@redhat.com> - 3.3.1-1
- Updated to Python 3.3.1.
- Refreshed patches: 55 (systemtap), 111 (no static lib), 146 (hashlib fips),
153 (fix test_gdb noise), 157 (uid, gid overflow - fixed upstream, just
keeping few more downstream tests)
- Removed patches: 3 (audiotest.au made it to upstream tarball)
- Removed workaround for http://bugs.python.org/issue14774, discussed in
http://bugs.python.org/issue15298 and fixed in revision 24d52d3060e8.

* Mon Mar 25 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.0-10
- fix gcc 4.8 incompatibility (rhbz#927358); regenerate autotool intermediates

* Mon Mar 25 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.0-9
- renumber patches to keep them in sync with python.spec

* Fri Mar 15 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 3.3.0-8
- Fix error in platform.platform() when non-ascii byte strings are decoded to
  unicode (rhbz#922149)

* Thu Mar 14 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 3.3.0-7
- Fix up shared library extension (rhbz#889784)

* Thu Mar 07 2013 Karsten Hopp <karsten@redhat.com> 3.3.0-6
- add ppc64p7 build target, optimized for Power7

* Mon Mar  4 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.0-5
- add workaround for ENOPROTOOPT seen running selftests in Koji
(rhbz#913732)

* Mon Mar  4 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.0-4
- remove config flag from /etc/rpm/macros.{python3|pybytecompile}

* Mon Feb 11 2013 David Malcolm <dmalcolm@redhat.com> - 3.3.0-3
- add aarch64 (rhbz#909783)

* Thu Nov 29 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-2
- add BR on bluez-libs-devel (rhbz#879720)

* Sat Sep 29 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-1
- 3.3.0rc3 -> 3.3.0; drop alphatag

* Mon Sep 24 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.6.rc3
- 3.3.0rc2 -> 3.3.0rc3

* Mon Sep 10 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.5.rc2
- 3.3.0rc1 -> 3.3.0rc2; refresh patch 55

* Mon Aug 27 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.4.rc1
- 3.3.0b2 -> 3.3.0rc1; refresh patches 3, 55

* Mon Aug 13 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.3.b2
- 3.3b1 -> 3.3b2; drop upstreamed patch 152; refresh patches 3, 102, 111,
134, 153, 160; regenenerate autotools patch; rework systemtap patch to work
correctly when LANG=C (patch 55); importlib.test was moved to
test.test_importlib upstream

* Mon Aug 13 2012 Karsten Hopp <karsten@redhat.com> 3.3.0-0.2.b1
- disable some failing checks on PPC* (rhbz#846849)

* Fri Aug  3 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.1.b1
- 3.2 -> 3.3: https://fedoraproject.org/wiki/Features/Python_3.3
- 3.3.0b1: refresh patches 3, 55, 102, 111, 113, 114, 134, 157; drop upstream
patch 147; regenenerate autotools patch; drop "--with-wide-unicode" from
configure (PEP 393); "plat-linux2" -> "plat-linux" (upstream issue 12326);
"bz2" -> "_bz2" and "crypt" -> "_crypt"; egg-info files are no longer shipped
for stdlib (upstream issues 10645 and 12218); email/test moved to
test/test_email; add /usr/bin/pyvenv[-3.3] and venv module (PEP 405); add
_decimal and _lzma modules; make collections modules explicit in payload again
(upstream issue 11085); add _testbuffer module to tests subpackage (added in
upstream commit 3f9b3b6f7ff0); fix test failures (patches 160 and 161);
workaround erroneously shared _sysconfigdata.py upstream issue #14774; fix
distutils.sysconfig traceback (patch 162); add BuildRequires: xz-devel (for
_lzma module); skip some tests within test_socket (patch 163)

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.2.3-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Fri Jul 20 2012 David Malcolm <dmalcolm@redhat.com> - 3.3.0-0.1.b1

* Fri Jun 22 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-10
- use macro for power64 (rhbz#834653)

* Mon Jun 18 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-9
- fix missing include in uid/gid handling patch (patch 157; rhbz#830405)

* Wed May 30 2012 Bohuslav Kabrda <bkabrda@redhat.com> - 3.2.3-8
- fix tapset for debug build

* Tue May 15 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-7
- update uid/gid handling to avoid int overflows seen with uid/gid
values >= 2^31 on 32-bit architectures (patch 157; rhbz#697470)

* Fri May  4 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-6
- renumber autotools patch from 300 to 5000
- specfile cleanups

* Mon Apr 30 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-5
- fix test_gdb.py (patch 156; rhbz#817072)

* Fri Apr 20 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-4
- avoid allocating thunks in ctypes unless absolutely necessary, to avoid
generating SELinux denials on "import ctypes" and "import uuid" when embedding
Python within httpd (patch 155; rhbz#814391)

* Fri Apr 20 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-3
- add explicit version requirements on expat to avoid linkage problems with
XML_SetHashSalt

* Thu Apr 12 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-2
- fix test_gdb (patch 153)

* Wed Apr 11 2012 David Malcolm <dmalcolm@redhat.com> - 3.2.3-1
- 3.2.3; refresh patch 102 (lib64); drop upstream patches 148 (gdbm magic
values), 149 (__pycache__ fix); add patch 152 (test_gdb regex)

* Thu Feb  9 2012 Thomas Spura <tomspur@fedoraproject.org> - 3.2.2-13
- use newly installed python for byte compiling (now for real)

* Sun Feb  5 2012 Thomas Spura <tomspur@fedoraproject.org> - 3.2.2-12
- use newly installed python for byte compiling (#787498)

* Wed Jan  4 2012 Ville Skyttä <ville.skytta@iki.fi> - 3.2.2-11
- Build with $RPM_LD_FLAGS (#756863).
- Use xz-compressed source tarball.

* Wed Dec 07 2011 Karsten Hopp <karsten@redhat.com> 3.2.2-10
- disable rAssertAlmostEqual in test_cmath on PPC (#750811)

* Mon Oct 17 2011 Rex Dieter <rdieter@fedoraproject.org> - 3.2.2-9
- python3-devel missing autogenerated pkgconfig() provides (#746751)

* Mon Oct 10 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-8
- cherrypick fix for distutils not using __pycache__ when byte-compiling
files (rhbz#722578)

* Fri Sep 30 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-7
- re-enable gdbm (patch 148; rhbz#742242)

* Fri Sep 16 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-6
- add a sys._debugmallocstats() function (patch 147)

* Wed Sep 14 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-5
- support OpenSSL FIPS mode in _hashlib and hashlib; don't build the _md5 and
_sha* modules, relying on _hashlib in hashlib (rhbz#563986; patch 146)

* Tue Sep 13 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-4
- disable gdbm module to prepare for gdbm soname bump

* Mon Sep 12 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-3
- renumber and rename patches for consistency with python.spec (8 to 55, 106
to 104, 6 to 111, 104 to 113, 105 to 114, 125, 131, 130 to 143)

* Sat Sep 10 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-2
- rewrite of "check", introducing downstream-only hooks for skipping specific
cases in an rpmbuild (patch 132), and fixing/skipping failing tests in a more
fine-grained manner than before; (patches 106, 133-142 sparsely, moving
patches for consistency with python.spec: 128 to 134, 126 to 135, 127 to 141)

* Tue Sep  6 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.2-1
- 3.2.2

* Thu Sep  1 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-7
- run selftests with "--verbose"
- disable parts of test_io on ppc (rhbz#732998)

* Wed Aug 31 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-6
- use "--findleaks --verbose3" when running test suite

* Tue Aug 23 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-5
- re-enable and fix the --with-tsc option on ppc64, and rework it on 32-bit
ppc to avoid aliasing violations (patch 130; rhbz#698726)

* Tue Aug 23 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-4
- don't use --with-tsc on ppc64 debug builds (rhbz#698726)

* Thu Aug 18 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-3
- add %%python3_version to the rpm macros (rhbz#719082)

* Mon Jul 11 2011 Dennis Gilmore <dennis@ausil.us> - 3.2.1-2
- disable some tests on sparc arches

* Mon Jul 11 2011 David Malcolm <dmalcolm@redhat.com> - 3.2.1-1
- 3.2.1; refresh lib64 patch (102), subprocess unit test patch (129), disabling
of static library build (due to Modules/_testembed; patch 6), autotool
intermediates (patch 300)

* Fri Jul  8 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-5
- use the gdb hooks from the upstream tarball, rather than keeping our own copy

* Fri Jul  8 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-4
- don't run test_openpty and test_pty in %%check

* Fri Jul  8 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-3
- cleanup of BuildRequires; add comment headings to specfile sections

* Tue Apr 19 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-2
- fix the libpython.stp systemtap tapset (rhbz#697730)

* Mon Feb 21 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-1
- 3.2
- drop alphatag
- regenerate autotool patch

* Mon Feb 14 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.13.rc3
- add a /usr/bin/python3-debug symlink within the debug subpackage

* Mon Feb 14 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.12.rc3
- 3.2rc3
- regenerate autotool patch

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.2-0.11.rc2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Jan 31 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.10.rc2
- 3.2rc2

* Mon Jan 17 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.9.rc1
- 3.2rc1
- rework patch 6 (static lib removal)
- remove upstreamed patch 130 (ppc debug build)
- regenerate patch 300 (autotool intermediates)
- updated packaging to reflect upstream rewrite of "Demo" (issue 7962)
- added libpython3.so and 2to3-3.2

* Wed Jan  5 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.8.b2
- set EXTRA_CFLAGS to our CFLAGS, rather than overriding OPT, fixing a linker
error with dynamic annotations (when configured using --with-valgrind)
- fix the ppc build of the debug configuration (patch 130; rhbz#661510)

* Tue Jan  4 2011 David Malcolm <dmalcolm@redhat.com> - 3.2-0.7.b2
- add --with-valgrind to configuration (on architectures that support this)

* Wed Dec 29 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.6.b2
- work around test_subprocess failure seen in koji (patch 129)

* Tue Dec 28 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.5.b2
- 3.2b2
- rework patch 3 (removal of mimeaudio tests), patch 6 (no static libs),
patch 8 (systemtap), patch 102 (lib64)
- remove patch 4 (rendered redundant by upstream r85537), patch 103 (PEP 3149),
patch 110 (upstreamed expat fix), patch 111 (parallel build fix for grammar
fixed upstream)
- regenerate patch 300 (autotool intermediates)
- workaround COUNT_ALLOCS weakref issues in test suite (patch 126, patch 127,
patch 128)
- stop using runtest.sh in %%check (dropped by upstream), replacing with
regrtest; fixup list of failing tests
- introduce "pyshortver", "SOABI_optimized" and "SOABI_debug" macros
- rework manifests of shared libraries to use "SOABI_" macros, reflecting
PEP 3149
- drop itertools, operator and _collections modules from the manifests as py3k
commit r84058 moved these inside libpython; json/tests moved to test/json_tests
- move turtle code into the tkinter subpackage

* Wed Nov 17 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.5.a1
- fix sysconfig to not rely on the -devel subpackage (rhbz#653058)

* Thu Sep  9 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.4.a1
- move most of the content of the core package to the libs subpackage, given
that the libs aren't meaningfully usable without the standard libraries

* Wed Sep  8 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.3.a1
- Move test.support to core package (rhbz#596258)
- Add various missing __pycache__ directories to payload

* Sun Aug 22 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 3.2-0.2.a1
- Add __pycache__ directory for site-packages

* Sun Aug 22 2010 Thomas Spura <tomspur@fedoraproject.org> - 3.2-0.1.a1
- on 64bit "stdlib" was still "/usr/lib/python*" (modify *lib64.patch)
- make find-provides-without-python-sonames.sh 64bit aware

* Sat Aug 21 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.0.a1
- 3.2a1; add alphatag
- rework %%files in the light of PEP 3147 (__pycache__)
- drop our configuration patch to Setup.dist (patch 0): setup.py should do a
better job of things, and the %%files explicitly lists our modules (r82746
appears to break the old way of doing things).  This leads to various modules
changing from "foomodule.so" to "foo.so".  It also leads to the optimized build
dropping the _sha1, _sha256 and _sha512 modules, but these are provided by
_hashlib; _weakref becomes a builtin module; xxsubtype goes away (it's only for
testing/devel purposes)
- fixup patches 3, 4, 6, 8, 102, 103, 105, 111 for the rebase
- remove upstream patches: 7 (system expat), 106, 107, 108 (audioop reformat
plus CVE-2010-1634 and CVE-2010-2089), 109 (CVE-2008-5983)
- add machinery for rebuilding "configure" and friends, using the correct
version of autoconf (patch 300)
- patch the debug build's usage of COUNT_ALLOCS to be less verbose (patch 125)
- "modulator" was removed upstream
- drop "-b" from patch applications affecting .py files to avoid littering the
installation tree

* Thu Aug 19 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 3.1.2-13
- Turn on computed-gotos.
- Fix for parallel make and graminit.c

* Fri Jul  2 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-12
- rebuild

* Fri Jul  2 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-11
- Fix an incompatibility between pyexpat and the system expat-2.0.1 that led to
a segfault running test_pyexpat.py (patch 110; upstream issue 9054; rhbz#610312)

* Fri Jun  4 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-10
- ensure that the compiler is invoked with "-fwrapv" (rhbz#594819)
- reformat whitespace in audioop.c (patch 106)
- CVE-2010-1634: fix various integer overflow checks in the audioop
module (patch 107)
- CVE-2010-2089: further checks within the audioop module (patch 108)
- CVE-2008-5983: the new PySys_SetArgvEx entry point from r81399 (patch 109)

* Thu May 27 2010 Dan Horák <dan[at]danny.cz> - 3.1.2-9
- reading the timestamp counter is available only on some arches (see Python/ceval.c)

* Wed May 26 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-8
- add flags for statvfs.f_flag to the constant list in posixmodule (i.e. "os")
(patch 105)

* Tue May 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-7
- add configure-time support for COUNT_ALLOCS and CALL_PROFILE debug options
(patch 104); enable them and the WITH_TSC option within the debug build

* Mon May 24 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-6
- build and install two different configurations of Python 3: debug and
standard, packaging the debug build in a new "python3-debug" subpackage
(patch 103)

* Tue Apr 13 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-5
- exclude test_http_cookies when running selftests, due to hang seen on
http://koji.fedoraproject.org/koji/taskinfo?taskID=2088463 (cancelled after
11 hours)
- update python-gdb.py from v5 to py3k version submitted upstream

* Wed Mar 31 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-4
- update python-gdb.py from v4 to v5 (improving performance and stability,
adding commands)

* Thu Mar 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-3
- update python-gdb.py from v3 to v4 (fixing infinite recursion on reference
cycles and tracebacks on bytes 0x80-0xff in strings, adding handlers for sets
and exceptions)

* Wed Mar 24 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-2
- refresh gdb hooks to v3 (reworking how they are packaged)

* Sun Mar 21 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-1
- update to 3.1.2: http://www.python.org/download/releases/3.1.2/
- drop upstreamed patch 2 (.pyc permissions handling)
- drop upstream patch 5 (fix for the test_tk and test_ttk_* selftests)
- drop upstreamed patch 200 (path-fixing script)

* Sat Mar 20 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-28
- fix typo in libpython.stp (rhbz:575336)

* Fri Mar 12 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-27
- add pyfuntop.stp example (source 7)
- convert usage of $$RPM_BUILD_ROOT to %%{buildroot} throughout, for
consistency with python.spec

* Mon Feb 15 2010 Thomas Spura <tomspur@fedoraproject.org> - 3.1.1-26
- rebuild for new package of redhat-rpm-config (rhbz:564527)
- use 'install -p' when running 'make install'

* Fri Feb 12 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-25
- split configure options into multiple lines for easy of editing
- add systemtap static markers (wcohen, mjw, dmalcolm; patch 8), a systemtap
tapset defining "python.function.entry" and "python.function.return" to make
the markers easy to use (dmalcolm; source 5), and an example of using the
tapset to the docs (dmalcolm; source 6) (rhbz:545179)

* Mon Feb  8 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-24
- move the -gdb.py file from %%{_libdir}/INSTSONAME-gdb.py to
%%{_prefix}/lib/debug/%%{_libdir}/INSTSONAME.debug-gdb.py to avoid noise from
ldconfig (bug 562980), and which should also ensure it becomes part of the
debuginfo subpackage, rather than the libs subpackage
- introduce %%{py_SOVERSION} and %%{py_INSTSONAME} to reflect the upstream
configure script, and to avoid fragile scripts that try to figure this out
dynamically (e.g. for the -gdb.py change)

* Mon Feb  8 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-23
- add gdb hooks for easier debugging (Source 4)

* Thu Jan 28 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-22
- update python-3.1.1-config.patch to remove downstream customization of build
of pyexpat and elementtree modules
- add patch adapted from upstream (patch 7) to add support for building against
system expat; add --with-system-expat to "configure" invocation
- remove embedded copies of expat and zlib from source tree during "prep"

* Mon Jan 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-21
- introduce %%{dynload_dir} macro
- explicitly list all lib-dynload files, rather than dynamically gathering the
payload into a temporary text file, so that we can be sure what we are
shipping
- introduce a macros.pybytecompile source file, to help with packaging python3
modules (Source3; written by Toshio)
- rename "2to3-3" to "python3-2to3" to better reflect python 3 module packaging
plans

* Mon Jan 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-20
- change python-3.1.1-config.patch to remove our downstream change to curses
configuration in Modules/Setup.dist, so that the curses modules are built using
setup.py with the downstream default (linking against libncursesw.so, rather
than libncurses.so), rather than within the Makefile; add a test to %%install
to verify the dso files that the curses module is linked against the correct
DSO (bug 539917; changes _cursesmodule.so -> _curses.so)

* Fri Jan 22 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-19
- add %%py3dir macro to macros.python3 (to be used during unified python 2/3
builds for setting up the python3 copy of the source tree)

* Wed Jan 20 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-18
- move lib2to3 from -tools subpackage to main package (bug 556667)

* Sun Jan 17 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-17
- patch Makefile.pre.in to avoid building static library (patch 6, bug 556092)

* Fri Jan 15 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-16
- use the %%{_isa} macro to ensure that the python-devel dependency on python
is for the correct multilib arch (#555943)
- delete bundled copy of libffi to make sure we use the system one

* Fri Jan 15 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-15
- fix the URLs output by pydoc so they point at python.org's 3.1 build of the
docs, rather than the 2.6 build

* Wed Jan 13 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-14
- replace references to /usr with %%{_prefix}; replace references to
/usr/include with %%{_includedir} (Toshio)

* Mon Jan 11 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-13
- fix permission on find-provides-without-python-sonames.sh from 775 to 755

* Mon Jan 11 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-12
- remove build-time requirements on tix and tk, since we already have
build-time requirements on the -devel subpackages for each of these (Thomas
Spura)
- replace usage of %%define with %%global (Thomas Spura)
- remove forcing of CC=gcc as this old workaround for bug 109268 appears to
longer be necessary
- move various test files from the "tools"/"tkinter" subpackages to the "test"
subpackage

* Thu Jan  7 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-11
- add %%check section (thanks to Thomas Spura)
- update patch 4 to use correct shebang line
- get rid of stray patch file from buildroot

* Tue Nov 17 2009 Andrew McNabb <amcnabb@mcnabbs.org> - 3.1.1-10
- switched a few instances of "find |xargs" to "find -exec" for consistency.
- made the description of __os_install_post more accurate.

* Wed Nov  4 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-9
- add macros.python3 to the -devel subpackage, containing common macros for use
when packaging python3 modules

* Tue Nov  3 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-8
- add a provides of "python(abi)" (see bug 532118)
- fix issues identified by a.badger in package review (bug 526126, comment 39):
  - use "3" thoughout metadata, rather than "3.*"
  - remove conditional around "pkg-config openssl"
  - use standard cleanup of RPM_BUILD_ROOT
  - replace hardcoded references to /usr with _prefix macro
  - stop removing egg-info files
  - use /usr/bin/python3.1 rather than /use/bin/env python3.1 when fixing
up shebang lines
  - stop attempting to remove no-longer-present .cvsignore files
  - move the post/postun sections above the "files" sections

* Thu Oct 29 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-7
- remove commented-away patch 51 (python-2.6-distutils_rpm.patch): the -O1
flag is used by default in the upstream code
- "Makefile" and the config-32/64.h file are needed by distutils/sysconfig.py
_init_posix(), so we include them in the core package, along with their parent
directories (bug 531901)

* Tue Oct 27 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-6
- reword description, based on suggestion by amcnabb
- fix the test_email and test_imp selftests (patch 3 and patch 4 respectively)
- fix the test_tk and test_ttk_* selftests (patch 5)
- fix up the specfile's handling of shebang/perms to avoid corrupting
test_httpservers.py (sed command suggested by amcnabb)

* Thu Oct 22 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-5
- fixup importlib/_bootstrap.py so that it correctly handles being unable to
open .pyc files for writing (patch 2, upstream issue 7187)
- actually apply the rpath patch (patch 1)

* Thu Oct 22 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-4
- update patch0's setup of the crypt module to link it against libcrypt
- update patch0 to comment "datetimemodule" back out, so that it is built
using setup.py (see Setup, option 3), thus linking it statically against
timemodule.c and thus avoiding a run-time "undefined symbol:
_PyTime_DoubleToTimet" failure on "import datetime"

* Wed Oct 21 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-3
- remove executable flag from various files that shouldn't have it
- fix end-of-line encodings
- fix a character encoding

* Tue Oct 20 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-2
- disable invocation of brp-python-bytecompile in postprocessing, since
it would be with the wrong version of python (adapted from ivazquez'
python3000 specfile)
- use a custom implementation of __find_provides in order to filter out bogus
provides lines for the various .so modules
- fixup distutils/unixccompiler.py to remove standard library path from rpath
(patch 1, was Patch0 in ivazquez' python3000 specfile)
- split out libraries into a -libs subpackage
- update summaries and descriptions, basing content on ivazquez' specfile
- fixup executable permissions on .py, .xpm and .xbm files, based on work in
ivazquez's specfile
- get rid of DOS batch files
- fixup permissions for shared libraries from non-standard 555 to standard 755
- move /usr/bin/python*-config to the -devel subpackage
- mark various directories as being documentation

* Thu Sep 24 2009 Andrew McNabb <amcnabb@mcnabbs.org> 3.1.1-1
- Initial package for Python 3.
