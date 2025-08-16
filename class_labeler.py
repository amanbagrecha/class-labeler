from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QHBoxLayout, 
                                  QPushButton, QLineEdit, QLabel, QListWidget, 
                                  QListWidgetItem, QFileDialog, QMessageBox)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.core import QgsProject, QgsDefaultValue, QgsSettings, QgsVectorLayer, QgsEditFormConfig
from qgis.utils import iface
import os

class ClassLabelerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.classes = []
        self.actions = []
        
    def refresh_toolbar(self):
        if getattr(self, "toolbar", None):
            # adjust & rebuild
            if self.active_class_index >= len(self.classes):
                self.active_class_index = max(0, len(self.classes) - 1)
            self.create_toolbar()
            if self.classes and self.active_class_index < len(self.classes):
                self.set_default_class(self.classes[self.active_class_index])
            return

        # If there is no toolbar, do NOT clear self.dialog here.
        # Optionally keep indices sane:
        self.active_class_index = min(self.active_class_index, max(0, len(self.classes) - 1))

        
    def initGui(self):
        icon = QIcon()
        self.action = QAction(icon, "Class Labeler", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        
    def unload(self):
        # Disconnect signals
        try:
            QgsProject.instance().layersRemoved.disconnect(self.on_layers_removed)
        except:
            pass
        self.cleanup_toolbar()
        if hasattr(self, 'action') and self.action:
            self.iface.removeToolBarIcon(self.action)
            
    def cleanup_toolbar(self):
        if hasattr(self, 'toolbar') and self.toolbar:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar = None
        if hasattr(self, 'actions'):
            self.actions = []
        
    def run(self):
        # Ensure attributes exist
        if not hasattr(self, 'classes'):
            self.classes = []
        if not hasattr(self, 'class_field'):
            self.class_field = "class"
        if not hasattr(self, 'active_class_index'):
            self.active_class_index = 0
            
        self.dialog = ClassConfigDialog(self)
        self.dialog.show()
        
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
            
    def set_default_class_by_index(self, index):
        if 0 <= index < len(self.classes):
            self.active_class_index = index
            self.set_default_class(self.classes[index])
            self.update_active_button()
            
    def update_active_button(self):
        for i, action in enumerate(self.actions):
            action.setChecked(i == self.active_class_index)
            
    def set_default_class(self, value):
        layer = self.get_active_layer()
        if not layer:
            # Layer no longer exists, cleanup toolbar
            self.cleanup_toolbar()
            self.current_layer = None
            self.iface.messageBar().pushWarning("Class Labeler", "No valid layer - toolbar cleared")
            return
            
        idx = layer.fields().indexFromName(self.class_field)
        if idx == -1:
            self.iface.messageBar().pushCritical("Class Labeler", 
                f"Field '{self.class_field}' not found")
            return
            
        expr = f"'{value}'"
        layer.setDefaultValueDefinition(idx, QgsDefaultValue(expr))
        
        # Force layer-specific form suppression
        form_config = layer.editFormConfig()
        form_config.setSuppress(QgsEditFormConfig.SuppressOn)
        layer.setEditFormConfig(form_config)
        
        layer.triggerRepaint()
        self.iface.messageBar().pushInfo("Class Labeler", 
            f"Active class: {value}")
            
    def get_active_layer(self):
        layer = self.iface.activeLayer()
        if not layer or not hasattr(layer, 'fields'):
            self.iface.messageBar().pushWarning("Class Labeler", 
                "Select a vector layer")
            return None
        return layer

    def set_target_layer(self, layer):
        # disconnect old hook
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

        # Clear classes + selection state
        self.classes.clear()
        self.active_class_index = 0

        # If the config dialog is open, clear its UI list too
        if getattr(self, "dialog", None):
            try:
                self.dialog.class_list.clear()
            except Exception:
                pass

        self.iface.messageBar().pushInfo("Class Labeler", "Layer removed — toolbar & classes cleared")


    def apply_settings(self):
        s = QgsSettings()
        s.setValue("/qgis/digitizing/disable_enter_attribute_values_dialog", True)
        s.setValue("/Map/identifyAutoFeatureForm", False)
        s.setValue("/qgis/digitizing/reuseLastValue", True)
        
    def on_layers_removed(self, layer_ids):
        """Called when layers are removed from project"""
        # If we have a toolbar and any layer is removed, check if we still have a valid target
        if self.toolbar:
            layer = self.get_active_layer()
            if not layer:
                self.cleanup_toolbar()
                self.current_layer = None
                self.iface.messageBar().pushInfo("Class Labeler", "Target layer removed - toolbar cleared")

class ClassConfigDialog(QDialog):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Class Labeler Configuration")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        
        # Class list
        layout.addWidget(QLabel("Classes:"))
        self.class_list = QListWidget()
        layout.addWidget(self.class_list)
        
        # Load existing classes into the dialog
        for class_name in self.plugin.classes:
            self.class_list.addItem(class_name)
        
        # Add class section
        add_layout = QHBoxLayout()
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("Enter class name")
        self.add_btn = QPushButton("Add Class")
        self.add_btn.clicked.connect(self.add_class)
        add_layout.addWidget(self.class_input)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        
        # Remove class
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_class)
        layout.addWidget(self.remove_btn)
        
        # Layer selection
        layout.addWidget(QLabel("Target Layer:"))
        layer_layout = QHBoxLayout()
        self.layer_btn = QPushButton("Select Layer File...")
        self.layer_btn.clicked.connect(self.select_layer_file)
        self.active_layer_btn = QPushButton("Use Active Layer")
        self.active_layer_btn.clicked.connect(self.use_active_layer)
        layer_layout.addWidget(self.layer_btn)
        layer_layout.addWidget(self.active_layer_btn)
        layout.addLayout(layer_layout)
        
        self.layer_label = QLabel("No layer selected")
        layout.addWidget(self.layer_label)
        
        # Apply button
        self.apply_btn = QPushButton("Create Toolbar")
        self.apply_btn.clicked.connect(self.apply_config)
        layout.addWidget(self.apply_btn)
        
        # Clear toolbar button
        self.clear_btn = QPushButton("Clear Toolbar")
        self.clear_btn.clicked.connect(self.clear_toolbar)
        layout.addWidget(self.clear_btn)
        
        self.setLayout(layout)
        self.class_input.returnPressed.connect(self.add_class)
        
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
            self.plugin.refresh_toolbar()
            
    def select_layer_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Vector File", "", 
            "Vector files (*.shp *.gpkg *.geojson *.kml);;All files (*.*)")
        if file_path:
            layer = QgsVectorLayer(file_path, os.path.basename(file_path), "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.iface.setActiveLayer(layer)
                self.plugin.current_layer = layer
                self.plugin.set_target_layer(layer)
                self.layer_label.setText(f"Selected: {layer.name()}")
            else:
                QMessageBox.critical(self, "Error", "Invalid layer file")
                
    def use_active_layer(self):
        layer = self.plugin.get_active_layer()
        if layer:
            self.plugin.current_layer = layer
            self.plugin.set_target_layer(layer) 
            self.layer_label.setText(f"Using: {layer.name()}")
        else:
            QMessageBox.warning(self, "Warning", "No active vector layer")
            
            
    def apply_config(self):
        if not self.plugin.classes:
            QMessageBox.warning(self, "Warning", "Add at least one class")
            return
            
        layer = self.plugin.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Warning", "Select a target layer")
            return
            
        # Check if class field exists, create if needed
        if layer.fields().indexFromName(self.plugin.class_field) == -1:
            reply = QMessageBox.question(self, "Field Missing", 
                f"Field '{self.plugin.class_field}' not found. Create it?")
            if reply == QMessageBox.Yes:
                from qgis.core import QgsField
                from qgis.PyQt.QtCore import QVariant
                layer.dataProvider().addAttributes([QgsField(self.plugin.class_field, QVariant.String)])
                layer.updateFields()
            else:
                return
                
        self.plugin.apply_settings()
        self.plugin.create_toolbar()
        
        if self.plugin.classes:
            self.plugin.active_class_index = 0
            self.plugin.set_default_class(self.plugin.classes[0])
            
        QMessageBox.information(self, "Success", "Toolbar created successfully!")
        self.close()
        
    def clear_toolbar(self):
        self.plugin.cleanup_toolbar()
        self.plugin.current_layer = None
        self.plugin.classes = []  # Clear the classes list
        self.class_list.clear()   # Clear the UI list
        QMessageBox.information(self, "Info", "Toolbar and classes cleared!")