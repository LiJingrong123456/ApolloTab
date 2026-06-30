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

