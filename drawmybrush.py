# -*- coding: utf-8 -*-
"""
Brush drawing functionality adapted from:
Draw-By-Brush (https://github.com/josephburkhart/Draw-By-Brush)
Originally authored by Joseph Burkhart.

Modifications for integration into QGIS Class Labeler by Aman Bagrecha:
- Bug fixes for QGIS 3.x compatibility
- Extended error handling and validation
- Seamless lifecycle management within QGIS plugin
- Enhanced integration with dynamic class labeling workflow

/***************************************************************************
 Brush (Class Labeler Integration)
                                 A QGIS plugin
 This plugin provides a tool for drawing polygons with a brush-style workflow,
 similar to Photoshop or GIMP, integrated with hotkey-driven class labeling.

 Adapted from the original Draw-By-Brush plugin by Joseph Burkhart.
 Generated initially by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2025-01-01
        git sha              : $Format:%H$
        copyright            : (C) 2023 Joseph Burkhart
                               (C) 2025 Aman Bagrecha
        email                : josephburkhart.public@gmail.com
                               amanbagrecha.blr@gmail.com
 ***************************************************************************/

 /***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import QGIS Qt libraries
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon, QColor, QPixmap, QCursor, QGuiApplication
from qgis.PyQt.QtWidgets import QAction

# Import necessary QGIS classes
from qgis.core import QgsFeature, QgsProject, QgsGeometry, QgsVectorLayer,\
    QgsRenderContext, QgsLayerTreeGroup, QgsWkbTypes, QgsMapLayer, QgsExpressionContextUtils

# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
import os.path

# Import the brush tool code
from .brushtools import BrushTool

class DrawByBrush:
    """QGIS Plugin Implementation of Draw by Brush.
    
    Attributes:
        iface: The QgsInterface of the current project instance.
        tool: The BrushTool or other currently active plugin map tool.
        previous_tool: The QgsMapTool that was active when the plugin was first
            activated.
        active_layer: The currently active map layer (can be any subclass of
            QgsMapLayer).
        sb: The QgsStatusBar of the current project instance.
        plugin_dir: The path to the folder containing the plugin's data.
        translator: The QTranslator to be used in translating documentation to
            match the user's locale.
        actions: A list of the QActions containing the plugin's core
            functionality, including the brush tool.
        menu: A string containing the text to display in the plugin's menu
            listing.
        toolbar: The QToolBar containing the buttons for the plugin's actions.
        tool_tip: Multi-line string explaining the plugin's controls.
        status_tip: Single-line string explaining the plugin's controls.
        pluginIsActive: A boolean indicating whether the plugin is active.
            This is useful for controlling behavior of accessory widgets
            such as Dock Widgets when the plugin is activated and 
            deactivated.
        brush_action: The QAction responsible for activating the brush tool.

    Methods:
        initGui: Create the menu entries and toolbar icons inside the QGIS GUI.
        tr: Translate a string using Qt translation API.
        activate_brush_tool: Activate the brush tool.
        onClosePlugin: Clean up necessary items when dockwidget is closed.
        unload: Clean up necessary items when the plugin is unloaded.
        add_action: Add a button bound to an action onto the plugin toolbar.
        disable_action: Reset necessary settings and restore active map tool
            when disabling an action.
        brush_action_requirements_check: Check that requirements for brush
            action activation are met, and disable the action if not.
        draw: Take the geometry and drawing flags from self.tool and modify
            self.active_layer accordingly.
        set_previous_tool: Reset self.previous_tool to the currently active
            map tool.
        features_overlapping_with: Determine which features in self.active_layer
            overlap with a given feature, and organize them into a dict
            by type of overlap.
        get_active_layer: Reset the reference to the currently active layer and
             reconnect editing signals with brush_action_requirements_check
             accordingly.
    """

    #------------------------------ INITIALIZATION ----------------------------
    def __init__(self, iface, class_value_getter=None, class_field_getter=None):
        """Constructor for the Draw by Brush plugin.

        Args:
            iface: A QgsInterface instance which provides the hook by which the
                class can manipulate the QGIS application at run time.
            class_value_getter: Optional callable that returns current class value
            class_field_getter: Optional callable that returns current class field name
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # Save reference to the QGIS status bar
        self.iface.statusBarIface()

        # Store class labeler integration callbacks
        self._get_class_value = class_value_getter
        self._get_class_field = class_field_getter

        # Save additional references
        self.tool = None
        self.previous_tool = None
        self.active_layer = None

        self.sb = self.iface.statusBarIface()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'drawbybrush_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'Draw by Brush')
        # No toolbar creation - brush tool accessed through Class Labeler dock widget only

        self.tool_tip = self.tr(u'Brush Tool\n\n'+
                                u'- Left-click to draw\n'+
                        	    u'- Right-click to erase\n'+
                                u'- Shift + scroll to re-scale the brush\n'+
                                u'- Shift + Ctrl + Scroll to rotate the brush\n'+
                                u'- Tab to change the brush shape\n'+
                                u'- Ctrl while drawing to merge\n'+
                                u'  (Note: attributes are lost on merge)')

        self.status_tip = self.tr(u'Brush Tool:\t'+
                                  u'Left-click to draw, '+
                        	      u'Right-click to erase, '+
                                  u'Shift + scroll to re-scale, '+
                                  u'Shift + Ctrl + Scroll to rotate, '+
                                  u'Tab to change shape, '+
                                  u'Ctrl while drawing to merge')

        self.pluginIsActive = False

    def initGui(self):
        """Create the menu entries and toolbar buttons inside the QGIS GUI, 
        and connect the signals and slots that pertain to them."""
        # Create Brush Action
        icon_path = ':/plugins/brush/resources/paintbrush.png'
        self.brush_action = self.add_action(
            icon_path,
            text=self.tr(u'Brush Tool'),
            checkable=True,
            callback=self.activate_brush_tool,
            enabled_flag=False,
            status_tip=self.status_tip,
            tool_tip=self.tool_tip,
            parent=self.iface.mainWindow())
        
        # Connect necessary signals and slots
        # Get necessary info whenever active layer changes
        self.iface.currentLayerChanged.connect(self.get_active_layer)

        # Save reference to previous map tool whenever brush action is activated -- TODO: check that toggled is the correct signal here
        self.brush_action.toggled.connect(lambda x: self.set_previous_tool(self.brush_action))

        # Only enable brush action if a Polygon or MultiPolygon Vector layer is selected
        self.iface.currentLayerChanged.connect(self.brush_action_requirements_check)

    #------------------------------ COMMUNICATION -----------------------------
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        Args:
            message: The string or QString for translation.

        Returns: 
            A QString containing the translated message.
        """
        return QCoreApplication.translate('DrawByBrush', message)

    #------------------------------- ACTIVATION -------------------------------
    def activate_brush_tool(self):
        """Set up the brush tool, connect it to the GUI, and connect its 
        signals with the proper slots."""
        # Load and start the plugin
        if not self.pluginIsActive:
            self.pluginIsActive = True

        # Initialize and configure self.tool
        self.tool = BrushTool(self.iface)
        self.tool.setAction(self.actions[0])
        self.tool.rb_finished.connect(lambda g: self.draw(g))
        
        # Select the tool in the current interface
        self.iface.mapCanvas().setMapTool(self.tool)

        # Update tool attribute
        self.tool.active_layer = self.active_layer

        # Show controls in the status bar
        self.sb.showMessage(self.status_tip)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        self.pluginIsActive = False

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'Draw by Brush'),
                action)
            self.iface.removeToolBarIcon(action)
        # No toolbar to remove since we don't create one

    #------------------------------ UPPDATE STATE -----------------------------
    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        checkable=False,
        add_to_toolbar=False,
        status_tip=None,
        tool_tip=None,
        parent=None):
        """Add a button bound to an action onto the plugin toolbar. 

        Args:
            icon_path: A string containing the path to the icon for the action.
                This can be a resource path (e.g. ':/plugins/foo/bar.png') or a
                normal file system path.
            text: A string that should be shown in menu items for this action.
            callback: The function to be called when the action is triggered.
            enabled_flag: A boolean indicating if the action should be enabled
                by default. Defaults to True.
            checkable: A boolean indicating whether the action can be toggled
                on or off.
            add_to_toolbar: A boolean indicating whether the action should also
                be added to the toolbar. Defaults to True.
            status_tip: An optional string to show in the status bar upon mouse
                hover. Defaults to None.
            tool_tip: An optional string to show in a tooltip upon mouse hover.
                Defaults to None.
            parent: The parent QWidget for the new action. Defaults to None.

        Returns:
            The QAction that was created. Note that the action is also added to
            self.actions.
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        
        if tool_tip is not None:
            action.setToolTip(tool_tip)

        if add_to_toolbar and hasattr(self, 'toolbar') and self.toolbar:
            self.toolbar.addAction(action)

        self.actions.append(action)

        return action

    def disable_action(self, action):
        """Reset necessary settings and restore active map tool when disabling
        an action."""
        # Toggle off
        action.setChecked(False)

        # Disable the tool
        action.setEnabled(False)

        # Restore previous map tool (if any)
        # TODO: account for selected layer type
        if self.previous_tool != None:
            self.iface.mapCanvas().setMapTool(self.previous_tool)

    def brush_action_requirements_check(self):
        """Enable/Disable brush action as necessary when different types of
        layers are selected. Tool can only be activated when editing is on."""
        # No layer is selected
        if self.active_layer == None:
            self.disable_action(self.brush_action)

        # Polygon Layer is selected
        elif ((self.active_layer.type() == QgsMapLayer.VectorLayer) and
            (self.active_layer.geometryType() == QgsWkbTypes.PolygonGeometry) and
            self.active_layer.isEditable()):
                self.brush_action.setEnabled(True)
        
        # Non-polygon layer is selected
        else:
            self.disable_action(self.brush_action)

    def draw(self, emmitted_geometry):
        """Take the emitted geometry and drawing flags from self.tool and
        modify self.active_layer accordingly."""
        # Get current active layer used in the drawing tool
        self.active_layer = self.tool.active_layer

        # Create new feature
        new_feature = QgsFeature(self.active_layer.fields())
        new_feature.setGeometry(emmitted_geometry)
        
        # Set class attribute if integration is available
        class_field_name = self._get_class_field() if self._get_class_field else "class"
        class_idx = self.active_layer.fields().indexFromName(class_field_name)
        if class_idx != -1:
            if self._get_class_value:
                # Use current class from labeler plugin
                new_feature.setAttribute(class_idx, self._get_class_value())
            else:
                # Fall back to layer's default value
                ctx = QgsExpressionContextUtils.globalProjectLayerScopes(self.active_layer)
                new_feature.setAttribute(class_idx, self.active_layer.defaultValue(class_idx, ctx))

        # If drawing, add new feature
        if self.tool.drawing_mode == 'drawing':
            # If merging, recalculate the geometry of new_feature and delete
            # all overlapping features
            # TODO: if attributes are present, prompt user to select which
            #       overlapping feature to take attribute data from
            if self.tool.merging:
                overlapping_features = self.features_overlapping_with(new_feature)    
                for f in overlapping_features['any_overlap']:
                    new_feature.setGeometry(new_feature.geometry().combine(f.geometry()))
                    self.active_layer.deleteFeature(f.id())
            
            # Wrap in edit command for proper undo/redo support
            if not self.active_layer.isEditable():
                self.active_layer.startEditing()
            self.active_layer.beginEditCommand("Brush add")
            ok = self.active_layer.addFeature(new_feature)
            if not ok:
                self.active_layer.destroyEditCommand()
                self.iface.messageBar().pushCritical("Brush", f"Add failed: {self.active_layer.lastError()}")
                return
            self.active_layer.endEditCommand()

        # If erasing, modify existing features
        elif self.tool.drawing_mode == 'erasing':
            # Calculate overlapping features
            overlapping_features = self.features_overlapping_with(new_feature)
            
            # Cut a hole through all features that new_feature is contained by
            contained_by_features = overlapping_features['contained_by']
            for f in contained_by_features:
                # Get current and previous geometries
                current_geometry = new_feature.geometry()
                current_geometry.convertToMultiType() #sometimes there is only one part
                current_polygon = current_geometry.asMultiPolygon()[0]
                current_exterior = current_polygon[0]
                current_holes = current_polygon[1:] 
                
                previous_geometry = f.geometry()
                previous_geometry.convertToMultiType() #sometimes previous feature is not multitype
                previous_polygon = previous_geometry.asMultiPolygon()[0]
                previous_exterior = previous_polygon[0]
                previous_holes = previous_polygon[1:]

                # Calculate new holes
                previous_holes_geometry = QgsGeometry().fromMultiPolygonXY([previous_holes])
                new_holes_geometry = QgsGeometry().fromMultiPolygonXY([[current_exterior]])
                new_holes_geometry.combine(previous_holes_geometry)
                new_holes = new_holes_geometry.asMultiPolygon()

                # Calculate new island parts, if any
                if current_holes != []:
                    print(current_holes)
                    current_holes_geometry = QgsGeometry().fromMultiPolygonXY([current_holes])
                    new_parts_geometry = current_holes_geometry.intersection(previous_geometry)
                    new_parts_geometry.convertToMultiType()  #sometimes there is only one part
                    new_parts = new_parts_geometry.asMultiPolygon()

                # Add calculated holes and parts
                new_geometry = QgsGeometry(previous_geometry)   # copy the previous geometry
                for hole in new_holes:
                    new_geometry.addRing(hole[0])
                if current_holes != []:
                    for part in new_parts_geometry.constParts():
                        new_geometry.addPart(part.boundary())
                
                # Change feature geometry to what was calculated above
                f.setGeometry(new_geometry)
                self.active_layer.updateFeature(f)

            # Delete all features that new_feature contains
            contains_features = overlapping_features['contains']
            for f in contains_features:
                self.active_layer.deleteFeature(f.id())

            # For all other features, modify their geometry
            for f in overlapping_features['partial_overlap']:
                previous_geometry = f.geometry()
                new_geometry = previous_geometry.difference(new_feature.geometry())
                f.setGeometry(new_geometry)
                self.active_layer.updateFeature(f)

            #self.active_layer.commitChanges(stopEditing=False)

        # Delete the instance of new_feature to free up memory
        # TODO: delete other expensive variables as well
        del new_feature

        # Refresh the interface
        self.iface.layerTreeView().refreshLayerSymbology(self.active_layer.id())
        self.iface.mapCanvas().refresh()

        # Clean up at the end
        self.tool.reset()

    def set_previous_tool(self, action):
        """Reset self.previous_tool to the current active map tool. To be 
        called whenever the action is toggled."""
        if action.isChecked():
            self.previous_tool = self.iface.mapCanvas().mapTool()

    #------------------------------- CALCULATION ------------------------------
    def features_overlapping_with(self, feature):
        """Determine which features in self.active_layer overlap with a given
        feature, and organize them into a dict by type of overlap.
        
        Args:
            feature: A QgsFeature to be checked against self.active_layer. Must
                be in the same CRS as self.active_layer.
        
        Returns:
            A dict of features in self.active_layer that overlap with feature.
        
        The returned dict is of the following form:
            {
                'contains':        `feature` contains these features
                'contained_by':    `feature` is contained by these features
                'partial_overlap': `feature` only partially overlaps these features
                'any_overlap':     `feature` has partial or total overlap with these
                                   features
            }

        If the two features have equivalent geometries, the feature from
        self.active_layer is added to 'contained_by'.

        Note: If this method causes performance issues, QgsGeometryEngine
        may provide a more efficient approach.
        """
        overlapping_features = {
            'contains': [],
            'contained_by': [],
            'partial_overlap': [],
            'any_overlap': []
        }
        for f in self.active_layer.getFeatures():
            if feature.geometry().contains(f.geometry()):
                overlapping_features['contains'].append(f)
                overlapping_features['any_overlap'].append(f)
            
            elif (feature.geometry().within(f.geometry()) or
                  QgsGeometry.compare(feature.geometry(), f.geometry())):
                overlapping_features['contained_by'].append(f)
                overlapping_features['any_overlap'].append(f)            
            
            elif feature.geometry().overlaps(f.geometry()):
                overlapping_features['partial_overlap'].append(f)
                overlapping_features['any_overlap'].append(f)
        
        return overlapping_features

    def get_active_layer(self):
        """Reset the reference to the current active layer and reconnect 
        signals to slots as necessary. To be called whenever the active layer
        changes."""
        self.active_layer = self.iface.activeLayer()
        if ((self.active_layer != None) and
            (self.active_layer.type() == QgsMapLayer.VectorLayer)):
            self.active_layer.editingStarted.connect(self.brush_action_requirements_check)
            self.active_layer.editingStopped.connect(self.brush_action_requirements_check)