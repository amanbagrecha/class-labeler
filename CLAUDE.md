# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a QGIS plugin called "Class Labeler" that provides dynamic class management with hotkeys for labeling vector features. The plugin allows users to create toolbars with numbered hotkeys (1-9) for quickly setting class values on polygon features, with optional brush tool integration for drawing.

## Recent Improvements

### Robust Class Management (2025)
- **Fixed class deletion bug**: Classes can now be deleted regardless of field name changes or toolbar state
- **Decoupled operations**: Class management is independent of field/toolbar validation
- **Better error handling**: Field operations only occur when actually needed

### Clean UI Integration (2025)
- **Removed redundant toolbar**: Brush tool no longer creates its own toolbar in main QGIS interface
- **Streamlined access**: Brush functionality only available through dock widget button
- **Proper cleanup**: Fixed memory leaks and duplicate icon accumulation during plugin reloads

## Architecture

### Core Components

**class_labeler.py** - Main plugin implementation
- `ClassLabelerPlugin`: Core plugin class handling toolbar creation, hotkey management, and layer integration
- `ClassLabelerDockWidget`: UI dock widget for configuration and class management
- Manages class field creation, default value setting, and hotkey assignments

**drawmybrush.py** - Brush tool integration
- `DrawByBrush`: Integrates brush drawing functionality with class labeling
- Takes optional callbacks for getting current class value and field name
- Handles feature creation with automatic class attribute assignment
- No longer creates standalone toolbar - accessed only through dock widget

**brushtools.py** - Low-level brush drawing tool
- `BrushTool`: Custom QgsMapTool for brush-based polygon drawing
- Supports multiple brush shapes (circle, wedge, rectangle)
- Provides drawing and erasing modes with customizable brush size

**__init__.py** - Plugin factory function
**metadata.txt** - Plugin metadata (name, version, description, etc.)
**resources.py** - Qt resource file (auto-generated, large binary content)

### Plugin Integration Points

The plugin integrates with QGIS through:
- Dock widget for configuration (right panel by default)
- Dynamic toolbar creation with numbered hotkey actions (1-9)
- Layer field manipulation for class attribute management
- MapTool integration for brush drawing functionality

### Class Management Workflow

1. Select target vector layer (polygon geometry required)
2. Configure class field name (defaults to "class")
3. Add class values through the dock widget
4. Create toolbar - automatically creates field if missing
5. Use numbered hotkeys (1-9) to switch active class
6. Draw features normally - they inherit the active class value

## Development Commands

### Testing the Plugin
```bash
# Plugin is installed in QGIS profile directory
# Reload plugin in QGIS: Plugins -> Plugin Reloader -> Class Labeler
```

### Git Workflow
```bash
git add <files>
git commit -m "descriptive message"
# Plugin follows simple commit workflow with descriptive messages
```

## Key Implementation Details

### Layer Requirements
- Supports polygon vector layers only
- Requires layer to be in editing mode for brush tool functionality
- Automatically creates class field if missing during toolbar creation

### Hotkey System
- Maximum 9 classes (hotkeys 1-9)
- Active class highlighted in toolbar
- Hotkeys update layer's default field value for new features

### Brush Tool Integration
- Optional feature - gracefully handles import failures
- Integrates with class labeler through callback functions
- Supports drawing, erasing, and merging operations
- Brush properties: size (scroll+shift), rotation (scroll+ctrl+shift), shape (tab)
- Accessed exclusively through dock widget button (no main toolbar integration)
- Proper lifecycle management prevents duplicate instances

### Field Management
- Creates text fields for class attributes
- Sets default values using QgsDefaultValue expressions
- Configures edit form to suppress attribute dialog for streamlined workflow

## Plugin Installation Structure

The plugin resides in the QGIS3 profile plugins directory:
`C:\Users\Admin\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\class_labeler\`

Files must be present for proper plugin loading:
- `__init__.py` (plugin factory)
- `metadata.txt` (plugin metadata)
- `class_labeler.py` (main implementation)
- Optional: `drawmybrush.py`, `brushtools.py`, `resources.py` (brush features)