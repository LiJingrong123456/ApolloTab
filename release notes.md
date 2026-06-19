# ApolloTab v0.4.0 - Release Notes

**Release Date**: June 19, 2026
**Commit**: `763b021`
**Author**: Zhu Wenqian

---

## Overview

ApolloTab v0.4.0 is a style-focused release that improves the visual presentation of rendered tablature and internationalizes tuning names for broader audience reach.

---

## Changes

### Title Centering & Spacing Improvement

**File**: [tab_renderer.py:306-320](file:///e:/Projects/ApolloTab/ApolloTab/renderer/tab_renderer.py#L306-L320)

The page header title has been redesigned for a more professional, balanced appearance:

| Property | Before | After |
|----------|--------|-------|
| Alignment | `Qt.AlignLeft` (left-aligned) | `Qt.AlignCenter` (centered) |
| Title rect height | 25px | 30px |
| Post-title spacing | 26px | 35px |

**Before**: Title was left-aligned against the page margin, creating visual imbalance.
**After**: Title sits centered in the page header area with increased breathing room before the track info line.

```python
# Before
painter.drawText(QRect(10, y, page_width - 200, 25), Qt.AlignLeft, title_text)
y += 26

# After
painter.drawText(QRect(10, y, page_width - 200, 30), Qt.AlignCenter, title_text)
y += 35  # Increased spacing for better visual breathing room
```

### English Tuning Names (Internationalization)

**File**: [track.py:63-95](file:///e:/Projects/ApolloTab/ApolloTab/models/track.py#L63-L95)

`GTPTrack.get_tuning_name()` now returns English names instead of Chinese:

| Tuning | Before (Chinese) | After (English) |
|--------|------------------|-----------------|
| Standard EADGBE | "标准调弦(EADGBE)" | "Standard" |
| Drop D | "Drop D" | "Drop D" |
| Open G | "Open G" | "Open G" |
| Open D | "Open D" | "Open D" |
| DADGAD | "DADGAD" | "DADGAD" |
| Half Step Down | "降半调" | "Half Step Down" |
| Custom/Unknown | "自定义调弦(N弦)" | "Custom (N strings)" |

**Rationale**: English is the universal language of music. Guitarists worldwide recognize "Standard", "Drop D", "Open G" etc. This eliminates the need for i18n translation and makes the library more accessible to the global community.

---

## Changed Files Summary

| File | Changes | Lines |
|------|---------|-------|
| `ApolloTab/renderer/tab_renderer.py` | Title center alignment + spacing increase; header comment updated | **+4 / -4 lines** |
| `ApolloTab/models/track.py` | Tuning names English refactor; detailed docstring; header comment updated | **+18 / -7 lines** |
| `pyproject.toml` | Version bump 0.3.9 → 0.4.0 | +1 line |
| `README.md` | Version/date update (EN + CN sections) | +2 lines |
| `readme/功能更新.md` | v0.4.0 changelog entry | +24 lines |
| `dist/` | v0.4.0 packages (wheel + source) | New |

**Total Net Change**: ~+49 lines (net)

---

## Backward Compatibility

**Breaking Change (Minor)**: The return value of `get_tuning_name()` has changed from Chinese to English strings. Any code that depends on exact string matching (e.g., `if name == "标准调弦(EADGBE)"`) will need to be updated to use the new English equivalents.

**Non-Breaking**: All rendering output remains visually compatible; only display text content has changed.

---

## Testing Recommendations

1. **Title Centering Test**: Render any song, verify title appears centered in the header area
2. **Spacing Test**: Verify adequate space between title line and track info line
3. **Tuning Name Test**: Load songs with various tunings (Standard, Drop D, Open G, custom), verify English names appear in info line
4. **Custom Tuning Test**: Load a non-standard tuning, verify it shows as "Custom (N strings)"
5. **Backward Compatibility Test**: If any UI code matches tuning name strings, update to English equivalents
6. **Multi-page Test**: Render a multi-page song, verify centering works consistently across all pages
7. **Long Title Test**: Render a song with title >50 chars, verify truncation + centering still work
8. **Dark Theme Test**: Render with dark theme, verify centered title is readable
9. **Light Theme Test**: Render with light theme, verify centered title is readable
10. **Info Line Consistency Test**: Verify "Track Name | Tuning | BPM" format displays correctly with new tuning names

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

**Full Changelog**: View Commit Diff (commit `763b021`, based on parent `0ad7e67`)

---

*End of Release Notes*
