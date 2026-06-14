# ApolloTab v0.3.9 - Release Notes

**Release Date**: June 14, 2026
**Commit**: `057d8f4`
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v0.3.9 focuses on fixing critical playhead timeline accuracy issues for songs containing empty/rest measures, and introduces a global unique measure identification system that enables precise cross-page measure lookup.

---

## Bug Fixes

### Critical Fix: Empty Measure Click Positioning Inaccuracy

**Issue**: When a Guitar Pro song contains empty measures (measures with only rests or no notes/beats), clicking on these areas in the UI would cause the playhead cursor to jump to an adjacent non-empty measure, resulting in significant positioning errors.

**Root Cause**: The `build_timeline()` method in `GTPPlayer` used `continue` to skip empty measures (where `m_layout.beats` is empty/falsy). This meant those measures had no corresponding timeline entries, so the binary search in click handlers would land on the nearest populated entry instead.

**Fix Implemented** ([player.py:1246-1282](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1246-L1282)):

```python
# [v0.3.9] Empty measure placeholder generation:
# Instead of skipping empty measures with 'continue',
# generate a placeholder timeline entry with correct scroll_y and time_ms
if not beats_in_measure:
    n_measures_in_system = len(system.measures)
    rel_pos = meas_idx / max(n_measures_in_system, 1)
    sys_h_render = max(system.y_tab_bottom - system.y_tab_top, 1)

    scroll_y = (
        page_base_y
        + (system.y_tab_top + rel_pos * sys_h_render) * page_scale_ratio
    )

    placeholder = {
        'time_ms': current_time_ms,
        'scroll_y': scroll_y,
        # ... page/sys/meas indices ...
        'beat_idx': -1,  # Marks this as an empty measure placeholder
        # ... coordinate fields ...
    }
    self._playhead_timeline.append(placeholder)
```

**Impact**:
- Clicks on empty/rest measures now position the playhead correctly
- No more "jumping" to adjacent measures when clicking silent sections
- Accurate A/B loop point placement even in rest-heavy passages

### Fix: Sentinel Point Measure Index Inheritance

**Issue**: The sentinel (end-of-timeline) entry had hardcoded `meas_idx=0`, which caused `_find_measure_at_time()` to return measure 0 when the B-loop-point was set at the end of the song.

**Fix** ([player.py:1357](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1357)): Sentinel now inherits all measure indices from the last real timeline entry:

```python
sentinel = {
    # ...
    'sys_idx': last_entry.get('sys_idx', 0),
    'meas_idx': last_entry.get('meas_idx', 0),
    'global_meas_idx': last_entry.get('global_meas_idx', 0),  # New: global ID
    'beat_idx': last_entry.get('beat_idx', 0),
    # ...
}
```

---

## New Features

### Global Unique Measure ID (`global_meas_idx`)

**Problem**: The existing `meas_idx` was local to each system (row), meaning measure 0 could appear multiple times across different systems/pages. This made it impossible to uniquely identify a measure when implementing features like "click to jump to measure N" or cross-referencing between audio time and visual position.

**Solution**: Introduced `global_meas_idx` - a monotonically increasing integer that increments once per processed measure, guaranteed unique across all systems and pages.

**Implementation Details** ([player.py:1217](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1217), [player.py:1304](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1304), [player.py:1317](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1317)):

1. Initialized as `global_meas_idx = 0` before page iteration
2. Incremented after processing each measure (both empty and populated)
3. Included in every timeline entry (real beats + placeholders + sentinel)

### `find_measure_at_time()` Method

**New API Method** ([player.py:1174-1206](file:///e:/Projects/ApolloTab/ApolloTab/player.py#L1174-L1206)):

| Method | Description |
|--------|-------------|
| `find_measure_at_time(time_ms=None, scroll_y=None)` | Find measure info at given time or scroll position |

**Returns**:
```python
{
    'global_meas_idx': int,   # Global unique measure ID
    'meas_idx': int,          # Local index within system (for UI display)
    'start_time_ms': float,   # Start time of this measure (ms)
    'start_scroll_y': float,  # Start scroll Y position of this measure
}
```

**Usage Example**:

```python
from ApolloTab.player import GTPPlayer

player = GTPPlayer()
player.load("song.gp5")

# Build timeline first
layouts = player.last_layouts  # or from renderer
images = player.render_track(0)
timeline = player.build_timeline(layouts, images, display_width=1200)

# Find measure at specific time (e.g., user clicked at 5000ms)
info = player.find_measure_at_time(time_ms=5000.0)
print(f"Global measure: {info['global_meas_idx']}")
print(f"Local measure: {info['meas_idx']}")
print(f"Start time: {info['start_time_ms']}ms")

# Or find by scroll position
info = player.find_measure_at_time(scroll_y=1500.0)
```

---

## Architecture Highlights

### Design Pattern: Timeline Index with Global Namespace

This release demonstrates the **Global Unique Identifier** pattern applied to timeline data structures:

1. **Namespace Isolation**: Each measure gets a globally unique ID independent of its local system context
2. **Bidirectional Lookup**: The `find_measure_at_time()` method uses `global_meas_idx` for backward scanning within the same measure boundary
3. **Placeholder Strategy**: Empty measures are represented as first-class timeline citizens (not skipped), ensuring complete coverage of the musical score

### Data Flow

```
GTPSong → build_timeline() → List[dict] with global_meas_idx
                                    ↓
                    find_measure_at_time() → Measure info dict
                                    ↓
                    UI click handler → Precise measure定位
```

---

## Changed Files Summary

| File | Changes | Lines |
|------|---------|-------|
| `ApolloTab/player.py` | **Major**: find_measure_at_time() + empty measure placeholders + global_meas_idx + sentinel fix | **+269 lines** |
| `pyproject.toml` | Version bump 0.3.8 → 0.3.9 | +1 line |
| `README.md` | Version/date update | +2 lines |
| `readme/功能更新.md` | v0.3.9 changelog entry | +27 lines |
| `release notes.md` | This file | Rewritten |
| `dist/` | v0.3.9 packages (wheel + source) | Replaced |

**Total Net Change**: ~+299 lines of production code

---

## Backward Compatibility

Fully Backward Compatible
- All new fields (`global_meas_idx`) are additive only
- Existing timeline entries retain all original keys
- `find_measure_at_time()` is a new method, no existing APIs changed
- Placeholder entries use `beat_idx: -1` to distinguish from real beat entries

---

## Testing Recommendations

To validate the v0.3.9 changes:

1. **Empty Measure Test**: Load a song with rest-only measures, verify clicks on those areas position correctly
2. **Global ID Uniqueness Test**: Verify `global_meas_idx` is strictly increasing with no duplicates across pages
3. **find_measure_at_time Test**: Call with various `time_ms` values, verify returned measure matches expected location
4. **Scroll Position Test**: Call with `scroll_y`, verify returned info corresponds to visual position
5. **Sentinel Test**: Set B loop point at song end, verify it maps to last real measure (not measure 0)
6. **Cross-Page Measure Test**: Verify measures spanning page boundaries have correct sequential global IDs
7. **Mixed Content Test**: Song with alternating populated and empty measures, verify all are addressable
8. **A/B Loop + Empty Measures Test**: Set loop region spanning empty measures, verify correct behavior
9. **Timeline Completeness Test**: Verify total timeline entry count = sum of all measures (including empty ones)
10. **Backward Compatibility Test**: Existing code using timeline entries without `global_meas_idx` still works

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

**Full Changelog**: View Commit Diff (commit `057d8f4`)

---

*End of Release Notes*
