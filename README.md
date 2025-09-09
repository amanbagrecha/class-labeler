<p align="center">
  <img src="class_labeler.png" alt="Class Labeler Logo" width="150"/>
</p>



# Class Labeler for QGIS

**A QGIS plugin that lets you classify and label vector features with dynamic hotkeys and integrated brush tools.**

---

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)


## The Challenge of Manual Feature Labeling

Geographic data analysis often requires classifying thousands of vector features—parcels, land use areas, vegetation zones, or building types. Traditional QGIS workflows involve repetitive clicking through attribute dialogs, manually typing class values, and constantly switching between drawing tools and data entry forms. This process is not only time-consuming but prone to inconsistencies and errors.

## Introducing Class Labeler

Class Labeler transforms this tedious workflow into an efficient, keyboard-driven process. With numbered hotkeys (1-9), users can instantly switch between class values while drawing or editing features, dramatically reducing the time spent on data classification tasks.

### Key Features

** Dynamic Hotkey System**
- Assign class values to number keys 1-9
- Instantly switch active class while drawing
- Visual feedback shows current active class
- Automatic field creation and management

**🖌️ Integrated Brush Tool**
- Paint polygon features like in Photoshop or GIMP
- Multiple brush shapes (circle, wedge, rectangle)
- Drawing and erasing modes with merge support
- Customizable brush size and rotation

**Smart Field Management**
- Automatic class field creation
- Configurable field names
- Robust error handling and validation
- Seamless integration with existing layers

## How It Works

### 1. Setup and Configuration

Launch the Class Labeler dock widget and configure your workflow:

```
1. Select target polygon layer
2. Configure class field name (defaults to "class") 
3. Add your class values (e.g., "residential", "commercial", "industrial")
4. Create toolbar to activate hotkey system
```

### 2. Streamlined Classification Workflow

With your toolbar active, classification becomes effortless:

- **Press 1**: Switches to first class (e.g., "residential")
- **Press 2**: Switches to second class (e.g., "commercial")  
- **Press 3**: Switches to third class (e.g., "industrial")
- **Draw features**: Automatically inherit the active class value

### 3. Advanced Brush Drawing

Activate the brush tool for photoshop-style polygon creation:

**Note:** The brush tool requires the target layer to be in editing mode. If the layer isn't editable, drawing will warn and abort.

- **Left-click + drag**: Paint polygons
- **Right-click + drag**: Erase areas
- **Shift + scroll**: Adjust brush size
- **Ctrl + Shift + scroll**: Rotate brush
- **Tab**: Cycle through brush shapes
- **Ctrl while drawing**: Merge with existing features

## Technical Architecture

### Core Components

**ClassLabelerPlugin**
- Main orchestration class managing hotkeys and toolbar creation
- Handles layer integration and field management
- Provides clean API for class value switching

**ClassLabelerDockWidget** 
- User interface for configuration and class management
- Real-time updates and validation
- Intuitive controls for adding/removing classes

**DrawByBrush Integration**
- Optional brush tool with seamless class labeler integration
- Callback-based architecture for extensibility  
- Proper lifecycle management and cleanup

### Smart Design Decisions

**Decoupled Architecture**: Class management operates independently of field validation, allowing users to modify field names without breaking existing workflows.

**Graceful Degradation**: Brush tool features gracefully handle import failures, ensuring core functionality remains available even in constrained environments.

**Memory Management**: Proper cleanup prevents resource leaks and UI element accumulation during plugin reloads.

## Installation and Requirements

**System Requirements**
- QGIS 3.x
- Python 3.6+
- Write access to QGIS plugin directory

**Installation**
1. Copy plugin files to QGIS profile plugins directory
2. Enable "Class Labeler" in QGIS Plugin Manager
3. Access via dock widget or toolbar icon

**Plugin Structure**
```
class_labeler/
├── __init__.py              # Plugin factory
├── metadata.txt             # Plugin metadata
├── class_labeler.py         # Core implementation
├── drawmybrush.py           # Brush tool integration
├── brushtools.py            # Low-level brush functionality
├── resources.py             # Qt resources
├── CLAUDE.md                # Development guidance
└── README.md                # This documentation
```

## Best Practices

**Layer Preparation**
- Enable editing mode before using brush tools
- Backup data before bulk classification operations

**Workflow Optimization**  
- Start with most common classes on lower-numbered hotkeys
- Use descriptive class names for clarity
- Test field names before large-scale operations

**Quality Control**
- Review class assignments before committing changes
- Use QGIS's undo/redo functionality for corrections
- Validate data integrity after classification sessions

## Future Enhancements

The Class Labeler plugin continues to evolve based on user feedback and emerging workflows. Planned enhancements include:

- **Extended Hotkey Support**: Beyond the current 1-9 limitation
- **Class Hierarchies**: Support for nested classification systems
- **Batch Operations**: Bulk reclassification tools
- **Integration APIs**: Enhanced connectivity with other QGIS plugins




## Acknowledgements

This plugin incorporates and extends the **Draw-By-Brush** tool originally created by [Joseph Burkhart](https://github.com/josephburkhart/Draw-By-Brush).  
We thank the original author for making the code available under an open license, which allowed us to adapt it into this workflow-oriented QGIS plugin.
