# ApolloTab v1.0.1 - Release Notes

**Release Date**: June 28, 2026
**Commits**: `fa4d8f3` (GP7/GP8 support) + `588a72c` (Bank/Program Change)
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v1.0.1 is a **major milestone release** (Phase 5) that introduces **native GP7/GP8 (.gp) file support** and **MIDI bank/program change support** for professional audio playback.

### New Feature 1: GP7/GP8 (.gp) Native Support

Guitar Pro 7/8 introduced a completely new file format (`.gp`) based on ZIP packaging with GPIF XML content. ApolloTab now supports this format natively:

- **Parser chain** (based on alphaTab algorithm):
  - `gp7_parser.py`: ZIP unpacking, file stream reading, Score.gpif extraction
  - `gpif_parser.py`: Full GPIF XML parser (~1500 lines) covering Tracks, Measures, Beats, Notes, Effects, Automation, etc.
  - `binary_stylesheet.py`: Binary stylesheet parsing for visual layout
  - `part_configuration.py`: Part configuration parsing
- **Smart dispatch**: `parse_score(filepath)` automatically selects the correct parser based on file extension (.gp3/.gp4/.gp5/.gpx/.gp)
- **Extended data models**: Track/Measure/Beat/Note/Song all gain GP7/GP8-specific fields (clef, key signature, marker, stroke direction, grace notes, harmonic, dead note, etc.)
- **RenderMode enum**: Added in `utils/constants.py` for multi-staff rendering mode (reserved for future GP7/GP8 multi-staff support)

### New Feature 2: MIDI Bank Select & Program Change

Professional playback now supports proper sound bank selection:

- **Bank Select (CC0 + CC32)**: Automatically sent before Program Change to select the correct sound bank
- **Program Change**: Changes instrument/program for each track
- **Event ordering**: CC/Program Change events are sorted to occur **before** note events, ensuring correct tone loading
- **Parser integration**: `gpif_parser.py` parses `master_banks` and `tracks_banks` from GP7/GP8 files
- **Synth engine**: `synth_engine.py` `_play_event()` now handles `control_change` and `program_change` event types

### Modified Files
| File | Change |
|------|--------|
| `__init__.py` | Expose GP7/GP8 new API |
| `parser/gp7_parser.py` | New: ZIP unpack + file stream reader |
| `parser/gpif_parser.py` | New: Full GPIF XML parser |
| `parser/binary_stylesheet.py` | New: Binary stylesheet parser |
| `parser/part_configuration.py` | New: Part configuration parser |
| `parser/__init__.py` | New: Smart dispatch `parse_score()` |
| `models/*.py` | Extended: GP7/GP8-specific fields |
| `utils/constants.py` | New: `RenderMode` enum |
| `audio/midi_converter.py` | New: Bank Select + Program Change event generation & sorting |
| `audio/synth_engine.py` | Extended: CC/Program Change playback support |

---

# ApolloTab v0.5.0 - Release Notes

**Release Date**: June 20, 2026
**Commit**: `01be990` (based on `61c80eb`)
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v0.5.0 is a **major feature release** that introduces complete **Repeat Sign (反复记号) expansion support** for Guitar Pro files. This solves the long-standing issue where songs with repeat sections (`||:` and `:||`) would play incorrectly — either skipping repeats entirely or having the playhead cursor desynchronized from the audio playback.

---

## New Feature: Repeat Sign Expansion

### Problem

Guitar Pro files commonly contain **repeat signs** (`||:` = repeat start, `:||n` = repeat end with count n). When playing such files:

1. **Without expansion**: MIDI events played measures in file order only, ignoring repeats
2. **With expansion but no timeline sync**: Audio plays correctly (repeats work), but the visual playhead cursor stays at the original position, causing **audio-visual desynchronization**

### Solution

A two-part implementation:

#### Part 1: Stack-Based Repeat Expansion Algorithm ([midi_converter.py:132](file:///e:/Projects/ApolloTab/ApolloTab/audio/midi_converter.py#L132))

New static method `MidiConverter.expand_measure_indices(measures)` uses a **stack data structure** to handle nested repeats:

```
Algorithm:
  result = []          # Expanded index sequence
  stack = []           # Repeat start positions

  For each measure i:
    1. Append i to result (always include current measure)
    2. If measure.is_repeat_open:
       → Push len(result)-1 onto stack (record start position)
    3. If measure.repeat_close > 0 and stack not empty:
       → Pop start_pos from stack
       → Extract segment = result[start_pos:]
       → Extend result with segment × (repeat_close - 1) times
```

**Key property**: The stack naturally handles nesting because inner closes pop inner opens first.

**Examples**:

| Input Pattern | Measures | Output (Expanded Indices) |
|--------------|----------|--------------------------|
| Simple repeat | `\|\|: A B :\|\|2 C` | `[0, 1, 0, 1, 3]` |
| Nested repeat | `A \|\|: B C :\|\|2 D :\|\|2 E` | `[0, 1, 2, 3, 2, 3, 4, 1, 2, 3, 2, 3, 4, 5]` |

#### Part 2: Timeline-MIDI Synchronization ([player.py:1388](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1388))

After building the base timeline (one entry per original measure), the timeline is **re-expanded** to match the MIDI event sequence:

```
Step 1: Build idx → global_meas_idx mapping from track.measures
Step 2: Group timeline entries by global_meas_idx
Step 3: Calculate duration per measure (ms)
Step 4: Rebuild timeline following expanded_measure_indices order:
        - Copy entries with same scroll_y (visual position unchanged)
        - Recalculate time_ms = running_time + relative_position × duration
        - Advance running_time by measure duration
Step 5: Replace _playhead_timeline and update _total_audio_duration_ms
```

**Result during repeat playback**:
- `scroll_y`: Jumps back to previous visual position (**correct** — same sheet location)
- `time_ms`: Continues to increase monotonically (**correct** — reflects actual audio progress)
- Playhead cursor: Visually "loops back" on the score while audio continues forward

---

## Integration Points

### MidiConverter Changes

| Method | Change |
|--------|--------|
| `expand_measure_indices()` | **NEW** — Static method for repeat expansion |
| `convert()` | Calls `expand_measure_indices()` before iterating measures |
| `convert_all_tracks()` | Also calls expansion for multi-track mode |

### GTPPlayer Changes

| Location | Change |
|----------|--------|
| `__init__()` | New field `_expanded_measure_indices: List[int] = []` |
| `init_audio()` | Computes and caches expanded sequence via `_midi_converter.expand_measure_indices()` |
| `build_timeline()` | After base timeline construction, applies repeat-aware expansion to sync with MIDI events |

---

## Changed Files Summary

| File | Changes | Lines |
|------|---------|-------|
| `ApolloTab/audio/midi_converter.py` | **Major**: New `expand_measure_indices()` method; integrated into `convert()`/`convert_all_tracks()`; updated header doc with detailed algorithm explanation | **+164 / -25 lines** |
| `ApolloTab/player.py` | **Major**: New `_expanded_measure_indices` cache; `init_audio()` computes expansion; `build_timeline()` syncs timeline with expanded sequence; updated header doc | **+124 / -14 lines** |
| `pyproject.toml` | Version bump 0.4.2 → 0.5.0 | +1 line |
| `README.md` | Version/date update (EN + CN sections) | +2 lines |
| `readme/功能更新.md` | v0.5.0 changelog entry | +35 lines |
| `dist/` | v0.5.0 packages (wheel + source) | New |

**Total Net Change**: ~+326 lines of production code

---

## Backward Compatibility

Fully Backward Compatible
- Songs without repeat signs: expansion produces identical sequence (no-op)
- Existing API unchanged: `MidiConverter.convert()` still returns `List[MidiEvent]`
- `GTPPlayer.build_timeline()` still returns `List[dict]` timeline entries
- Timeline entries gain correct `time_ms` values for repeat sections (improvement, not breaking change)

---

## Testing Recommendations

To validate v0.5.0 repeat sign support:

1. **Simple Repeat Test**: Load song with `||: A B :||2`, verify A-B-A-B-C playback order
2. **Nested Repeat Test**: Load song with nested repeats, verify correct expansion depth
3. **No Repeat Test**: Load song without any repeat signs, verify identical behavior to before
4. **Timeline Sync Test**: During repeat playback, verify playhead cursor jumps back visually while audio continues
5. **Time Accuracy Test**: Verify `current_time_ms` increases monotonically even during repeat jumps
6. **Scroll Position Test**: Verify `scroll_y` returns to original position during repeat (not advancing)
7. **A/B Loop + Repeat Test**: Set A/B loop region within a repeated section, verify correct behavior
8. **Multi-Track Repeat Test**: Use `MODE_ALL`, verify all tracks expand consistently
9. **Triple+ Repeat Test**: Test `:||3` or higher counts, verify correct number of repetitions
10. **Edge Case Test**: Open-only without close, close without open — verify graceful handling

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

**Requirements** (unchanged):
- Python >= 3.8
- pyguitarpro >= 0.11
- PyQt5 >= 5.15
- pyfluidsynth >= 1.4.0

---

**Full Changelog**: View Commit Diff (commit `61c80eb`)

---

*End of Release Notes*
