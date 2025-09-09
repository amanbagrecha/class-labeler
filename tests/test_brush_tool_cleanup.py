import sys
import types


def stub_qgis_modules():
    qgis = types.ModuleType('qgis')
    PyQt = types.ModuleType('qgis.PyQt')
    QtWidgets = types.ModuleType('qgis.PyQt.QtWidgets')
    for name in ['QAction','QWidget','QVBoxLayout','QHBoxLayout','QPushButton','QLineEdit','QLabel',
                 'QListWidget','QListWidgetItem','QComboBox','QMessageBox','QToolButton','QSizePolicy','QFrame']:
        setattr(QtWidgets, name, type(name, (), {}))
    QtCore = types.ModuleType('qgis.PyQt.QtCore')
    QtCore.Qt = type('Qt', (), {})
    def pyqtSignal(*args, **kwargs):
        return None
    QtCore.pyqtSignal = pyqtSignal
    QtGui = types.ModuleType('qgis.PyQt.QtGui')
    QtGui.QIcon = type('QIcon', (), {})
    QtGui.QKeySequence = type('QKeySequence', (), {})
    PyQt.QtWidgets = QtWidgets
    PyQt.QtCore = QtCore
    PyQt.QtGui = QtGui
    qgis.PyQt = PyQt

    core = types.ModuleType('qgis.core')
    for name in ['QgsProject','QgsDefaultValue','QgsSettings','QgsVectorLayer',
                 'QgsEditFormConfig','QgsField','QgsMapLayerProxyModel']:
        setattr(core, name, type(name, (), {}))
    core.QgsEditFormConfig.SuppressOn = 0
    gui = types.ModuleType('qgis.gui')
    gui.QgsMapLayerComboBox = type('QgsMapLayerComboBox', (), {})
    gui.QgsDockWidget = type('QgsDockWidget', (), {})
    utils = types.ModuleType('qgis.utils')
    utils.iface = None

    sys.modules['qgis'] = qgis
    sys.modules['qgis.PyQt'] = PyQt
    sys.modules['qgis.PyQt.QtWidgets'] = QtWidgets
    sys.modules['qgis.PyQt.QtCore'] = QtCore
    sys.modules['qgis.PyQt.QtGui'] = QtGui
    sys.modules['qgis.core'] = core
    sys.modules['qgis.gui'] = gui
    sys.modules['qgis.utils'] = utils


def test_cleanup_toolbar_restores_map_tool():
    stub_qgis_modules()
    # stub drawmybrush to avoid heavy imports
    stub_draw = types.ModuleType('class_labeler.drawmybrush')
    class DummyDraw: pass
    stub_draw.DrawByBrush = DummyDraw
    sys.modules['class_labeler.drawmybrush'] = stub_draw
    import pathlib
    package = types.ModuleType('class_labeler')
    package.__path__ = [str(pathlib.Path(__file__).resolve().parents[1])]
    sys.modules['class_labeler'] = package
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

    from class_labeler import class_labeler as plugin_module
    ClassLabelerPlugin = plugin_module.ClassLabelerPlugin

    class MockCanvas:
        def __init__(self):
            self._tool = None
        def mapTool(self):
            return self._tool
        def setMapTool(self, tool):
            self._tool = tool

    class MockIface:
        def __init__(self):
            self.canvas = MockCanvas()
        def mapCanvas(self):
            return self.canvas
        def mainWindow(self):
            return self
        def removeToolBar(self, tb):
            self.removed = tb
        def removeDockWidget(self, dw):
            pass
        def addToolBarIcon(self, action):
            pass
        def removeToolBarIcon(self, action):
            pass

    iface = MockIface()
    plugin = ClassLabelerPlugin(iface)

    class MockBrush:
        def __init__(self):
            self.tool = object()
            self.previous_tool = object()
            self.unloaded = False
        def unload(self):
            self.unloaded = True

    brush = MockBrush()
    plugin.brush_tool = brush
    iface.mapCanvas().setMapTool(brush.tool)

    plugin.cleanup_toolbar()

    assert iface.mapCanvas().mapTool() == brush.previous_tool
    assert brush.unloaded
    assert plugin.brush_tool is None
