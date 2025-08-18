from qgis.PyQt.QtWidgets import (QAction, QWidget, QVBoxLayout, QHBoxLayout, 
                                  QPushButton, QLineEdit, QLabel, QListWidget, 
                                  QListWidgetItem, QComboBox, QMessageBox, QToolButton,
                                  QSizePolicy, QFrame)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.core import (QgsProject, QgsDefaultValue, QgsSettings, QgsVectorLayer, 
                      QgsEditFormConfig, QgsField, QgsMapLayerProxyModel)
from qgis.gui import QgsMapLayerComboBox, QgsDockWidget
from qgis.utils import iface
import os

# Import brush tool classes
try:
    from .drawmybrush import DrawByBrush
    BRUSH_AVAILABLE = True
    
except ImportError as e:
    BRUSH_AVAILABLE = False
    


class ClassLabelerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.classes = []
        self.actions = []
        self.class_field = "class"
        self.active_class_index = 0
        self.dock_widget = None
        self.current_layer = None
        self.brush_tool = None

        # self.iface.messageBar().pushWarning("Class Labeler", f"{BRUSH_AVAILABLE=}")
        
    def refresh_toolbar(self):
        if getattr(self, "toolbar", None):
            if self.active_class_index >= len(self.classes):
                self.active_class_index = max(0, len(self.classes) - 1)
            self.create_toolbar()
            # Only set default class if we have a valid layer and field
            if (self.classes and self.active_class_index < len(self.classes) and 
                self.get_target_layer() and 
                self.get_target_layer().fields().indexFromName(self.class_field) != -1):
                self.set_default_class(self.classes[self.active_class_index])
            return

        self.active_class_index = min(self.active_class_index, max(0, len(self.classes) - 1))
        
    def current_class_value(self):
        """Get the current active class value."""
        if self.classes and 0 <= self.active_class_index < len(self.classes):
            return self.classes[self.active_class_index]
        return None
        
    def current_class_field(self):
        """Get the current class field name."""
        return self.class_field

    def initGui(self):
        icon = QIcon()
        self.action = QAction(icon, "Class Labeler", self.iface.mainWindow())
        self.action.triggered.connect(self.show_dock)
        self.iface.addToolBarIcon(self.action)
        
    def unload(self):
        try:
            QgsProject.instance().layersRemoved.disconnect(self.on_layers_removed)
        except:
            pass
        self.cleanup_toolbar()
        if hasattr(self, 'action') and self.action:
            self.iface.removeToolBarIcon(self.action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            
    def cleanup_toolbar(self):
        if hasattr(self, 'toolbar') and self.toolbar:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar = None
        if hasattr(self, 'actions'):
            self.actions = []
        # Clean up brush tool properly
        if hasattr(self, 'brush_tool') and self.brush_tool:
            self.brush_tool.unload()
            self.brush_tool = None
            
    def show_dock(self):
        if not self.dock_widget:
            self.dock_widget = ClassLabelerDockWidget(self)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        else:
            self.dock_widget.show()
        
    def create_toolbar(self):
        self.cleanup_toolbar()
        if not self.classes:
            return
            
        self.toolbar = self.iface.addToolBar("Class Labels")
        self.actions = []
        
        for i, class_name in enumerate(self.classes):
            hotkey = str(i + 1)
            action = QAction(f"{class_name} ({hotkey})", self.iface.mainWindow())
            action.triggered.connect(lambda checked, idx=i: self.set_default_class_by_index(idx))
            action.setShortcut(QKeySequence(hotkey))
            action.setToolTip(f"Set {self.class_field}={class_name} (Hotkey: {hotkey})")
            action.setCheckable(True)
            
            self.toolbar.addAction(action)
            self.actions.append(action)
            
        self.update_active_button()
        
        # Initialize brush tool with class labeler integration
        if BRUSH_AVAILABLE:
            self.brush_tool = DrawByBrush(
                self.iface,
                class_value_getter=self.current_class_value,
                class_field_getter=self.current_class_field
            )
            self.brush_tool.initGui()
            
    def set_default_class_by_index(self, index):
        if 0 <= index < len(self.classes):
            self.active_class_index = index
            self.set_default_class(self.classes[index])
            self.update_active_button()
            if self.dock_widget:
                self.dock_widget.update_class_selection()
            
    def update_active_button(self):
        for i, action in enumerate(self.actions):
            action.setChecked(i == self.active_class_index)
            
    def set_default_class(self, value):
        layer = self.get_target_layer()
        if not layer:
            self.iface.messageBar().pushWarning("Class Labeler", "No valid layer selected")
            return
            
        idx = layer.fields().indexFromName(self.class_field)
        if idx == -1:
            self.iface.messageBar().pushCritical("Class Labeler", 
                f"Field '{self.class_field}' not found. Create toolbar first.")
            return
            
        expr = f"'{value}'"
        layer.setDefaultValueDefinition(idx, QgsDefaultValue(expr))
        
        form_config = layer.editFormConfig()
        form_config.setSuppress(QgsEditFormConfig.SuppressOn)
        layer.setEditFormConfig(form_config)
        
        layer.triggerRepaint()
        self.iface.messageBar().pushInfo("Class Labeler", 
            f"Active class: {value}")
            
    def get_target_layer(self):
        if self.current_layer and self.current_layer.isValid():
            return self.current_layer
        return None

    def set_target_layer(self, layer):
        if getattr(self, "current_layer", None):
            try:
                self.current_layer.willBeDeleted.disconnect(self.on_current_layer_deleted)
            except Exception:
                pass

        self.current_layer = layer
        if layer:
            layer.willBeDeleted.connect(self.on_current_layer_deleted)

    def on_current_layer_deleted(self):
        self.cleanup_toolbar()
        self.current_layer = None
        self.classes.clear()
        self.active_class_index = 0

        if self.dock_widget:
            self.dock_widget.class_list.clear()  # Clear the UI list too

        self.iface.messageBar().pushInfo("Class Labeler", "Layer removed — toolbar & classes cleared")

    def apply_settings(self):
        s = QgsSettings()
        s.setValue("/qgis/digitizing/disable_enter_attribute_values_dialog", True)
        s.setValue("/Map/identifyAutoFeatureForm", False)
        s.setValue("/qgis/digitizing/reuseLastValue", True)
        
    def on_layers_removed(self, layer_ids):
        if self.toolbar and self.current_layer and self.current_layer.id() in layer_ids:
            self.cleanup_toolbar()
            self.current_layer = None
            self.classes.clear()
            self.active_class_index = 0
            if self.dock_widget:
                self.dock_widget.class_list.clear()
            self.iface.messageBar().pushInfo("Class Labeler", "Target layer removed - toolbar cleared")

class ClassLabelerDockWidget(QgsDockWidget):
    def __init__(self, plugin):
        super().__init__("Class Labeler", plugin.iface.mainWindow())
        self.plugin = plugin
        self.setup_ui()
        
    def setup_ui(self):
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        # Layer selection
        layer_frame = QFrame()
        layer_frame.setFrameStyle(QFrame.StyledPanel)
        layer_layout = QVBoxLayout()
        
        layer_layout.addWidget(QLabel("Target Layer:"))
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer_combo.layerChanged.connect(self.on_layer_changed)
        layer_layout.addWidget(self.layer_combo)
        
        layer_frame.setLayout(layer_layout)
        layout.addWidget(layer_frame)
        
        # Field name input
        field_frame = QFrame()
        field_frame.setFrameStyle(QFrame.StyledPanel)
        field_layout = QVBoxLayout()
        
        field_layout.addWidget(QLabel("Class Field Name:"))
        self.field_input = QLineEdit()
        self.field_input.setText(self.plugin.class_field)
        self.field_input.textChanged.connect(self.on_field_changed)
        field_layout.addWidget(self.field_input)
        
        field_frame.setLayout(field_layout)
        layout.addWidget(field_frame)
        
        # Classes section
        classes_frame = QFrame()
        classes_frame.setFrameStyle(QFrame.StyledPanel)
        classes_layout = QVBoxLayout()
        
        # Header with buttons
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Classes:"))
        header_layout.addStretch()
        
        self.add_btn = QToolButton()
        self.add_btn.setText("+")
        self.add_btn.setToolTip("Add class")
        self.add_btn.clicked.connect(self.add_class)
        
        self.remove_btn = QToolButton()
        self.remove_btn.setText("-")
        self.remove_btn.setToolTip("Remove selected class")
        self.remove_btn.clicked.connect(self.remove_class)
        
        header_layout.addWidget(self.add_btn)
        header_layout.addWidget(self.remove_btn)
        classes_layout.addLayout(header_layout)
        
        # Class input
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("Enter class name")
        self.class_input.returnPressed.connect(self.add_class)
        classes_layout.addWidget(self.class_input)
        
        # Class list
        self.class_list = QListWidget()
        self.class_list.itemClicked.connect(self.on_class_selected)
        classes_layout.addWidget(self.class_list)
        
        classes_frame.setLayout(classes_layout)
        layout.addWidget(classes_frame)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Create Toolbar")
        self.apply_btn.clicked.connect(self.apply_config)
        
        self.clear_btn = QPushButton("Clear Toolbar")
        self.clear_btn.clicked.connect(self.clear_toolbar)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)
        
        # Brush tool button (only show if available)
        if BRUSH_AVAILABLE:
            brush_layout = QHBoxLayout()
            self.brush_btn = QPushButton("🖌️ Brush Tool")
            self.brush_btn.setToolTip("Activate brush tool for drawing features with current class")
            self.brush_btn.clicked.connect(self.activate_brush_tool)
            self.brush_btn.setEnabled(False)  # Disabled until toolbar is created
            brush_layout.addWidget(self.brush_btn)
            layout.addLayout(brush_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        self.setWidget(widget)
        
        self.refresh_ui()
        
    def activate_brush_tool(self):
        """Activate the brush tool with class labeler integration."""
        if hasattr(self.plugin, 'brush_tool') and self.plugin.brush_tool:
            # Activate the brush tool
            self.plugin.brush_tool.activate_brush_tool()
        else:
            QMessageBox.warning(self, "Warning", "Brush tool not available. Create toolbar first.")
        
    def refresh_ui(self):
        self.class_list.clear()
        for class_name in self.plugin.classes:
            self.class_list.addItem(class_name)
        self.update_class_selection()
        
    def update_class_selection(self):
        for i in range(self.class_list.count()):
            item = self.class_list.item(i)
            item.setSelected(i == self.plugin.active_class_index)
            
    def on_layer_changed(self, layer):
        if layer and layer.isValid():
            self.plugin.set_target_layer(layer)
        else:
            self.plugin.current_layer = None
            
    def on_field_changed(self, text):
        self.plugin.class_field = text.strip() or "class"
        
    def add_class(self):
        class_name = self.class_input.text().strip()
        if not class_name:
            return
        if class_name in self.plugin.classes:
            QMessageBox.warning(self, "Warning", "Class already exists")
            return
        if len(self.plugin.classes) >= 9:
            QMessageBox.warning(self, "Warning", "Maximum 9 classes (hotkeys 1-9)")
            return
            
        self.plugin.classes.append(class_name)
        self.class_list.addItem(class_name)
        self.class_input.clear()
        
    def remove_class(self):
        current_row = self.class_list.currentRow()
        if current_row >= 0:
            self.plugin.classes.pop(current_row)
            self.class_list.takeItem(current_row)
            # Only refresh toolbar if it exists
            if hasattr(self.plugin, 'toolbar') and self.plugin.toolbar:
                self.plugin.refresh_toolbar()
            
    def on_class_selected(self, item):
        row = self.class_list.row(item)
        if 0 <= row < len(self.plugin.classes):
            self.plugin.active_class_index = row
            # Only update UI selection, don't set default values
            self.update_class_selection()
            
    def apply_config(self):
        if not self.plugin.classes:
            QMessageBox.warning(self, "Warning", "Add at least one class")
            return
            
        layer = self.plugin.get_target_layer()
        if not layer:
            QMessageBox.warning(self, "Warning", "Select a target layer")
            return
            
        # Check if class field exists, create if needed
        if layer.fields().indexFromName(self.plugin.class_field) == -1:
            reply = QMessageBox.question(self, "Field Missing", 
                f"Field '{self.plugin.class_field}' not found. Create it?")
            if reply == QMessageBox.Yes:
                from qgis.PyQt.QtCore import QVariant
                field = QgsField(self.plugin.class_field, QVariant.String)
                if not layer.dataProvider().addAttributes([field]):
                    QMessageBox.critical(self, "Error", "Failed to add field. Layer may be read-only.")
                    return
                layer.updateFields()
                
                # Verify field was created
                if layer.fields().indexFromName(self.plugin.class_field) == -1:
                    QMessageBox.critical(self, "Error", f"Field '{self.plugin.class_field}' could not be created.")
                    return
            else:
                return
                
        self.plugin.apply_settings()
        self.plugin.create_toolbar()
        
        if self.plugin.classes:
            self.plugin.active_class_index = 0
            self.plugin.set_default_class(self.plugin.classes[0])
            self.update_class_selection()
            
        # Enable brush tool button
        if hasattr(self, 'brush_btn'):
            self.brush_btn.setEnabled(True)
            
        QMessageBox.information(self, "Success", "Toolbar created successfully!")
        
    def clear_toolbar(self):
        self.plugin.cleanup_toolbar()
        self.plugin.current_layer = None
        self.plugin.classes.clear()
        self.plugin.active_class_index = 0
        self.class_list.clear()
        # Disable brush tool button
        if hasattr(self, 'brush_btn'):
            self.brush_btn.setEnabled(False)
        QMessageBox.information(self, "Info", "Toolbar and classes cleared!")