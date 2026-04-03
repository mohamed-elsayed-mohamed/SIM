"""Windows SDK / vcpkg overlay triplet helpers for manifest installs."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from .constants import REPO_ROOT, log


def short_windows_path(path: Path) -> str:
    """8.3 path for CMake/vcpkg when paths contain spaces (Windows only)."""
    try:
        p = path.resolve()
        if not p.exists():
            return p.as_posix()
        buf = ctypes.create_unicode_buffer(4096)
        n = ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, ctypes.sizeof(buf) // 2)
        if n and n < ctypes.sizeof(buf) // 2:
            return buf.value.replace("\\", "/")
    except OSError:
        pass
    return path.resolve().as_posix()


def find_windows_kits_x64_bin() -> Path | None:
    """
    Directory containing rc.exe / mt.exe (e.g. ...\\10\\bin\\10.0.xxxxx.0\\x64).
    CMake+Ninja often invokes bare `rc`; prepending this to PATH also helps.
    """
    base = (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Windows Kits"
        / "10"
        / "bin"
    )
    if not base.is_dir():
        return None
    for ver_dir in sorted(
        (p for p in base.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    ):
        x64 = ver_dir / "x64"
        if (x64 / "rc.exe").is_file():
            return x64
    return None


def write_vcpkg_overlay_triplet_dir() -> Path | None:
    """
    Writes vcpkg-triplets/x64-windows.cmake so CMake/Ninja find rc.exe, mt.exe,
    and Windows import libs (kernel32.lib) during vcpkg port builds (e.g. fmt).
    Required when not using a full VS Developer shell for every tool invocation.
    """
    x64_bin = find_windows_kits_x64_bin()
    if x64_bin is None:
        return None
    rc = x64_bin / "rc.exe"
    mt = x64_bin / "mt.exe"
    if not rc.is_file() or not mt.is_file():
        return None
    ver = x64_bin.parent.name
    kits_base = x64_bin.parent.parent.parent
    include_root = kits_base / "Include" / ver
    lib_root = kits_base / "Lib" / ver
    inc_ucrt = include_root / "ucrt"
    inc_shared = include_root / "shared"
    inc_um = include_root / "um"
    lib_um = lib_root / "um" / "x64"
    lib_ucrt = lib_root / "ucrt" / "x64"
    for d in (inc_ucrt, inc_shared, inc_um, lib_um, lib_ucrt):
        if not d.is_dir():
            log.warning("[resolve_deps] Windows SDK path missing: %s", d)
            return None

    overlay = REPO_ROOT / "vcpkg-triplets"
    overlay.mkdir(exist_ok=True)
    rc_s = short_windows_path(rc)
    mt_s = short_windows_path(mt)
    iu = short_windows_path(inc_ucrt)
    ish = short_windows_path(inc_shared)
    ium = short_windows_path(inc_um)
    lum = short_windows_path(lib_um)
    luct = short_windows_path(lib_ucrt)
    sdk_inc = f"/I{iu} /I{ish} /I{ium}"
    sdk_link = f"/LIBPATH:{lum} /LIBPATH:{luct}"
    text = f"""set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
set(VCPKG_PLATFORM_TOOLSET v143)
set(VCPKG_C_FLAGS "{sdk_inc}")
set(VCPKG_CXX_FLAGS "{sdk_inc}")
set(VCPKG_LINKER_FLAGS "{sdk_link}")
set(VCPKG_CMAKE_CONFIGURE_OPTIONS
    "-DCMAKE_RC_COMPILER={rc_s}"
    "-DCMAKE_MT={mt_s}"
)
"""
    (overlay / "x64-windows.cmake").write_text(text, encoding="utf-8")
    log.info("[resolve_deps] Wrote overlay triplet → %s", overlay / "x64-windows.cmake")
    return overlay
