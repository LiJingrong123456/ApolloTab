# ApolloTab v1.3.1 - Release Notes

**Release Date**: July 1, 2026
**Commit**: (Playback Bar / MIDI Sync Fix)
**Author**: Zhu Wenqian
**License**: LGPL-2.1

---

## Overview

ApolloTab v1.3.1 fixes a synchronization issue between the visual playback bar and the generated MIDI audio. The timeline now advances according to the actual note duration of each beat, matching the timing used by `MidiConverter`.

### Bug Fix: Playback Bar / MIDI Audio Synchronization

**Problem**: `GTPPlayer.build_timeline()` previously advanced time using `measure_ticks // n_beats`, giving every beat inside a measure the same duration. This caused the playback bar to run at a constant speed per beat while the MIDI audio followed real note durations, producing visible drift on rhythms with mixed note values, dotted notes, or tuplets.

**Fix**: `build_timeline()` now advances `current_time_ticks` by `int(ticks_per_beat * beat.duration_value)`, where `duration_value` already accounts for note duration, dotted notes, and tuplets. This makes the timeline identical to the tick calculation in `MidiConverter._beat_duration_to_ticks()`.

**Files Changed**:
- `ApolloTab/player.py` - `build_timeline()` timing logic and file header
- `ApolloTab/__init__.py` - version bump to `1.3.1`
- `pyproject.toml` - version bump to `1.3.1`
- `readme/功能更新.md` - changelog entry for v1.3.1

---

# ApolloTab v1.3.0 - Release Notes

**Release Date**: June 30, 2026
**Commit**: `461dc0f` (Theme Runtime Registration + Metronome Improvements)
**Author**: Zhu Wenqian
**License**: LGPL-2.1

---

## Overview

ApolloTab v1.3.0 adds **dynamic theme registration** for runtime customization and improves metronome volume control, with a fix for GP7/GP8 string mapping direction.

### New Feature: Dynamic Theme Registration

**Purpose**: Enable TAB Score Viewer's user theme extension features to sync with ApolloTab's rendering engine.

**New APIs in `ThemeConfig`**:
- `register_theme(name, colors)`: Register a custom theme at runtime
  - Built-in themes ("dark", "light") are protected and cannot be overwritten
  - Missing color keys are auto-filled with dark theme defaults
- `unregister_theme(name)`: Unregister a previously registered custom theme

**Usage Example**:
```python
from ApolloTab import ThemeConfig

custom_colors = {"COLOR_BG": "#FFFDE7", "COLOR_TEXT": "#212121"}
ThemeConfig.register_theme("sepia", custom_colors)

renderer = TabRenderer()
renderer.set_theme("sepia")  # Use custom theme by name
```

### Metronome Improvements

**Default Gain Increase**: Changed from default to 1.5 to solve the issue where woodblock sounds were too quiet when mixed with other instruments.

**Channel Volume CC Event**: Added CC#7 volume event for metronome channel (15) to prevent metronome clicks from being covered by other instruments.

### Bug Fix: GP7/GP8 String Mapping

**Problem**: GP7/GP8 GPIF `<String>` node string indices were mapped in the wrong direction.

**Fix**: Corrected string index mapping to ensure correct parsing of GP7/GP8 file string data.

---

