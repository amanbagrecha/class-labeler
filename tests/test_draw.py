import sys
import os
import types

# Stub out QGIS modules required for importing drawmybrush
qgis = types.ModuleType("qgis")
PyQt = types.ModuleType("qgis.PyQt")
QtCore = types.ModuleType("qgis.PyQt.QtCore")
QtGui = types.ModuleType("qgis.PyQt.QtGui")
QtWidgets = types.ModuleType("qgis.PyQt.QtWidgets")
core = types.ModuleType("qgis.core")

class Dummy:
    pass

for mod, names in [
    (QtCore, ["QSettings", "QTranslator", "QCoreApplication", "Qt"]),
    (QtGui, ["QIcon", "QColor", "QPixmap", "QCursor", "QGuiApplication"]),
    (QtWidgets, ["QAction"]),
]:
    for name in names:
        setattr(mod, name, Dummy)

for name in [
    "QgsFeature",
    "QgsProject",
    "QgsGeometry",
    "QgsVectorLayer",
    "QgsRenderContext",
    "QgsLayerTreeGroup",
    "QgsWkbTypes",
    "QgsMapLayer",
]:
    setattr(core, name, type(name, (), {}))

class QgsExpressionContextUtils:
    @staticmethod
    def globalProjectLayerScopes(layer):
        return None

core.QgsExpressionContextUtils = QgsExpressionContextUtils

qgis.PyQt = PyQt
qgis.core = core

sys.modules.setdefault("qgis", qgis)
sys.modules.setdefault("qgis.PyQt", PyQt)
sys.modules.setdefault("qgis.PyQt.QtCore", QtCore)
sys.modules.setdefault("qgis.PyQt.QtGui", QtGui)
sys.modules.setdefault("qgis.PyQt.QtWidgets", QtWidgets)
sys.modules.setdefault("qgis.core", core)

# Now import the module under test within a fake package to satisfy relative imports
root = os.path.dirname(os.path.dirname(__file__))
plugin_root = os.path.join(root, "class_labeler")
sys.path.insert(0, root)

pkg = types.ModuleType("class_labeler")
pkg.__path__ = [plugin_root]
sys.modules.setdefault("class_labeler", pkg)
sys.modules.setdefault("class_labeler.resources", types.ModuleType("resources"))
brushtools_mod = types.ModuleType("brushtools")
brushtools_mod.BrushTool = type("BrushTool", (), {})
sys.modules.setdefault("class_labeler.brushtools", brushtools_mod)

import importlib.util
spec = importlib.util.spec_from_file_location(
    "class_labeler.drawmybrush", os.path.join(plugin_root, "drawmybrush.py")
)
drawmybrush = importlib.util.module_from_spec(spec)
sys.modules.setdefault("class_labeler.drawmybrush", drawmybrush)
spec.loader.exec_module(drawmybrush)


def test_draw_requires_edit_mode():
    warnings = []

    class MessageBar:
        def pushWarning(self, title, message):
            warnings.append((title, message))

    class Iface:
        def messageBar(self):
            return MessageBar()

    class Layer:
        def __init__(self):
            self.editable = False
            self.start_called = False

        def isEditable(self):
            return self.editable

        def startEditing(self):
            self.start_called = True

    iface = Iface()
    layer = Layer()
    tool = types.SimpleNamespace(active_layer=layer, drawing_mode="drawing", merging=False)

    plugin = types.SimpleNamespace(iface=iface, tool=tool)

    drawmybrush.DrawByBrush.draw(plugin, None)

    assert warnings, "Expected warning when layer is not editable"
    assert not layer.start_called, "startEditing should not be invoked"
