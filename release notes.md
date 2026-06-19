# ApolloTab v0.4.2 - Release Notes

**Release Date**: June 19, 2026
**Commit**: `dc3c195` (based on `61601fb`)
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v0.4.2 introduces **multi audio driver auto-try mechanism** for the FluidSynth synthesis engine. This solves the "no sound" issue on Linux systems where different distributions and desktop environments use different audio backends (PulseAudio, PipeWire, ALSA, JACK).

---

## New Feature: Multi Audio Driver Auto-Try

### Problem

Previous versions used a two-step approach:
1. Try `driver=None` (FluidSynth's default auto-detect)
2. If that fails, try a single platform-specific driver (`pulseaudio` for Linux)

This failed in many scenarios:
- **Ubuntu 22.04+ / Fedora 34+**: Default is **PipeWire**, not PulseAudio
- **Docker containers**: No PulseAudio/PipeWire, only **ALSA** available
- **Headless servers**: No desktop audio stack at all
- **Professional workstations**: Using **JACK** instead of system default

### Solution

Replaced the single-fallback approach with a **priority-based driver list loop** that tries each driver until one succeeds.

### Driver Priority Lists ([synth_engine.py:288-300](file:///e:/Projects/ApolloTab/ApolloTab/audio/synth_engine.py#L288-L300))

| Platform | Priority Order | Rationale |
|----------|---------------|-----------|
| **Windows** | `dsound` → `waveout` → `default` | DirectSound most reliable; WaveOut as legacy fallback |
| **macOS** | `coreaudio` → `default` | CoreAudio is the only practical option |
| **Linux** | `pulseaudio` → `pipewire` → `alsa` → `jack` → `default` | Covers all common Linux audio backends |

### Implementation Details ([synth_engine.py:302-321](file:///e:/Projects/ApolloTab/ApolloTab/audio/synth_engine.py#L302-L321))

```python
self._audio_driver = None
for _drv in _driver_list:
    try:
        print(f"[SynthEngine] Trying audio driver: {_drv}")
        self._audio_driver = self._synth.start(driver=_drv)
        if self._audio_driver is not None:
            print(f"[SynthEngine] Audio driver started successfully: {_drv}")
            break
        else:
            print(f"[SynthEngine] Driver {_drv} unavailable, trying next...")
    except Exception as _drv_err:
        print(f"[SynthEngine] Driver {_drv} failed: {_drv_err}")
```

### Enhanced Failure Diagnostics ([synth_engine.py:323-333](file:///e:/Projects/ApolloTab/ApolloTab/audio/synth_engine.py#L323-L333))

When ALL drivers fail, detailed diagnostic output helps users troubleshoot:

```
[SynthEngine] Warning: All audio drivers failed to start, no sound output
  Possible causes:
   1. Audio service not installed (PulseAudio/PipeWire/ALSA)
   2. Docker container without /dev/snd device mounted
   3. SSH remote connection without audio forwarding configured

  Installation commands:
    Ubuntu/Debian: sudo apt-get install pulseaudio-utils libasound2
    Fedora/RHEL:   sudo dnf install pulseaudio-libs alsa-lib
    Docker:        Add --device /dev/snd parameter
```

---

## Changed Files Summary

| File | Changes | Lines |
|------|---------|-------|
| `ApolloTab/audio/synth_engine.py` | **Major**: Multi-driver priority loop + enhanced diagnostics + updated header doc | **+43 / -12 lines** |
| `pyproject.toml` | Version bump 0.4.1 → 0.4.2 | +1 line |
| `README.md` | Version/date update (EN + CN sections) | +2 lines |
| `readme/功能更新.md` | v0.4.2 changelog entry | +27 lines |
| `dist/` | v0.4.2 packages (wheel + source) | New |

**Total Net Change**: ~+73 lines of production code

---

## Backward Compatibility

Fully Backward Compatible
- The new driver list includes all previously-used drivers (`pulseaudio`, `dsound`, `coreaudio`, `default`)
- On Windows/macOS, behavior is effectively identical (same first-priority driver)
- On Linux, behavior is strictly better (more drivers tried before giving up)
- No API changes, no new public methods

---

## Testing Recommendations

To validate v0.4.2 multi-driver support:

1. **PipeWire System Test**: Run on Ubuntu 22.04+ with PipeWire, verify `pipewire` driver succeeds
2. **PulseAudio System Test**: Run on Ubuntu 20.04 with PulseAudio, verify `pulseaudio` driver succeeds
3. **Docker/ALSA Test**: Run in Docker without desktop, verify `alsa` driver succeeds
4. **JACK Test**: Run with JACK audio server running, verify `jack` driver succeeds
5. **Windows Regression Test**: Verify `dsound` driver still works on Windows
6. **macOS Regression Test**: Verify `coreaudio` driver still works on macOS
7. **All Drivers Fail Test**: Simulate failure scenario, verify helpful error message
8. **Driver Fallback Chain Test**: Block primary driver, verify automatic fallback to secondary
9. **Log Output Test**: Verify each driver attempt produces clear console output
10. **Full Workflow Test**: Complete parse→render→play workflow on each platform

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

**Platform-Specific Audio Requirements**:

| Platform | Required Audio Stack |
|----------|---------------------|
| Windows | DirectSound (built-in to Windows) |
| macOS | CoreAudio (built-in to macOS) |
| Linux | PulseAudio / PipeWire / ALSA / JACK (auto-detected) |

**Python Requirements** (unchanged):
- Python >= 3.8
- pyguitarpro >= 0.11
- PyQt5 >= 5.15
- pyfluidsynth >= 1.4.0

---

**Full Changelog**: View Commit Diff (commit `61601fb`)

---

*End of Release Notes*
