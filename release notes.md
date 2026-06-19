# ApolloTab v0.4.1 - Release Notes

**Release Date**: June 19, 2026
**Commit**: `2f742dd` (based on `123a05c`)
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v0.4.1 introduces **cross-platform FluidSynth library auto-discovery**, enabling the audio synthesis engine to work seamlessly on Linux distributions without manual configuration.

---

## New Feature: Linux FluidSynth `.so` Auto-Discovery

### Problem

Previous versions only supported Windows (DLL auto-discovery). On Linux, users had to manually configure `LD_LIBRARY_PATH` or rely on system-default library paths, which often failed due to distribution-specific directory layouts.

### Solution

Added a comprehensive Linux `.so` file search mechanism that covers all major Linux distributions and architectures.

### New Method: `_find_so_path()` ([synth_engine.py:353](file:///e:/Projects/ApolloTab/ApolloTab/audio/synth_engine.py#L353))

A static method that searches for `libfluidsynth.so.x` across common Linux installation paths:

| Distribution | Search Path | Architecture |
|--------------|-------------|-------------|
| Ubuntu/Debian | `/usr/lib/x86_64-linux-gnu` | x64 |
| Ubuntu/Debian | `/usr/lib/aarch64-linux-gnu` | ARM64 |
| Ubuntu/Debian | `/usr/lib/i386-linux-gnu` | i386 |
| Fedora/RHEL/CentOS | `/usr/lib64` | RPM-based |
| Arch Linux/openSUSE/Alpine | `/usr/lib` | Generic |
| Local builds | `/usr/local/lib` | Source compile |
| Linuxbrew | `/home/linuxbrew/.linuxbrew/lib` | Homebrew |

**File name search order (by version priority):**
1. `libfluidsynth.so.3` — FluidSynth v2.x/v3.x (recommended)
2. `libfluidsynth.so.2` — FluidSynth v1.x/v2.x
3. `libfluidsynth.so.1` — FluidSynth v1.x
4. `libfluidsynth.so` — Unversioned symlink (some distros)

### Enhanced `initialize()` Method ([synth_engine.py:226](file:///e:/Projects/ApolloTab/ApolloTab/audio/synth_engine.py#L226))

The initialization flow now has a dedicated Linux branch:

```
platform.system() == 'Linux'
    ↓
_find_so_path() → locate .so file
    ↓ (found)
Set LD_LIBRARY_PATH → ctypes.CDLL(RTLD_GLOBAL) pre-load
    ↓
import fluidsynth → create Synth instance → start audio driver
    ↓ (not found)
Print installation instructions per distro
```

**When .so is not found, helpful output:**
```
[SynthEngine] Warning: libfluidsynth.so not found (please install fluidsynth)
  Ubuntu/Debian: sudo apt-get install libfluidsynth3
  Fedora/RHEL:   sudo dnf install fluidsynth-libs
  Arch Linux:    sudo pacman -S fluidsynth
```

---

## Refactoring Changes

### Platform Detection Consolidation

**Before**: `platform.system()` was called inside each branch (Windows/Linux) separately.
**After**: Called once at the top of `initialize()`, stored in `_system`, reused for both library detection and audio driver selection.

```python
# [v0.4.1] Platform detection moved to method top
_system = platform.system()

if _system == 'Windows':
    # ... DLL logic ...

elif _system == 'Linux':
    # ... .so logic ...

# Reuse _system for driver selection
driver = driver_map.get(_system, 'default')
```

### Method Documentation Clarification

- `_find_dll_path()` now explicitly documented as Windows-only
- `_find_so_path()` now explicitly documented as Linux-only
- Both methods include detailed docstrings with path tables, version priority, and installation commands

---

## Changed Files Summary

| File | Changes | Lines |
|------|---------|-------|
| `ApolloTab/audio/synth_engine.py` | **Major**: New `_find_so_path()` + Linux branch in `initialize()` + platform refactoring + updated header doc | **+124 / -23 lines** |
| `pyproject.toml` | Version bump 0.4.0 → 0.4.1 | +1 line |
| `README.md` | Version/date update (EN + CN sections) | +2 lines |
| `readme/功能更新.md` | v0.4.1 changelog entry | +26 lines |
| `dist/` | v0.4.1 packages (wheel + source) | New |

**Total Net Change**: ~+153 lines of production code

---

## Backward Compatibility

Fully Backward Compatible
- All new code is inside platform-specific branches (`elif _system == 'Linux'`)
- Windows behavior completely unchanged
- macOS behavior unchanged (falls through to default fluidsynth import)
- New method is `@staticmethod`, doesn't affect instance state

---

## Testing Recommendations

To validate v0.4.1 cross-platform support:

1. **Linux Basic Test**: Run on Ubuntu with `libfluidsynth3` installed via apt, verify auto-discovery works
2. **Linux Multi-Distro Test**: Test on Fedora/RHEL (dnf), Arch (pacman), Alpine (apk)
3. **Linux ARM64 Test**: Test on aarch64 architecture (Raspberry Pi, cloud VMs)
4. **Linux Not Installed Test**: Run without fluidsynth installed, verify helpful error message with distro-specific commands
5. **Windows Regression Test**: Verify Windows DLL loading still works as before
6. **macOS Regression Test**: Verify macOS coreaudio driver still initializes correctly
7. **So Version Priority Test**: Install an older FluidSynth (.so.1/.so.2), verify fallback finds it
8. **LD_LIBRARY_PATH Test**: Verify LD_LIBRARY_PATH is set correctly before ctypes import
9. **Audio Playback Test**: Full parse→render→play workflow on Linux
10. **Driver Selection Test**: Verify correct driver (pulseaudio/pipewire) selected on Linux

---

## Installation

```bash
# Upgrade to latest version
pip install --upgrade ApolloTab

# Or install from source
git clone https://github.com/Zhuwenqian/ApolloTab.git
cd ApolloTab
pip install .
```

**Platform-Specific Dependencies**:

| Platform | Library | Installation |
|----------|---------|-------------|
| Windows | `libfluidsynth-3.dll` | Place in project root (auto-detected) |
| Linux | `libfluidsynth.so.x` | Via package manager (auto-detected) |
| macOS | `libfluidsynth.dylib` | Via Homebrew: `brew install fluidsynth` |

**Python Requirements** (unchanged):
- Python >= 3.8
- pyguitarpro >= 0.11
- PyQt5 >= 5.15
- pyfluidsynth >= 1.4.0

---

**Full Changelog**: View Commit Diff (commit `123a05c`)

---

*End of Release Notes*
