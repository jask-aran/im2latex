"""Pytest configuration and compatibility helpers for the im2latex test suite."""

import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

# Ensure Qt uses an offscreen backend during tests to avoid GUI requirements.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Make the project root importable for test modules.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Normalise ``sys.argv[0]`` so that importing ``main`` does not change the
# working directory to the pytest executable's location.
sys.argv[0] = str(PROJECT_ROOT / "pytest_runner")


def _install_pyqt_stubs() -> None:
    """Install lightweight PyQt5 stand-ins when Qt libraries are unavailable."""

    # Remove partially imported PyQt modules to avoid inconsistent state.
    for name in list(sys.modules):
        if name.startswith("PyQt5"):
            del sys.modules[name]

    pyqt5 = types.ModuleType("PyQt5")
    pyqt5.__is_stub__ = True
    sys.modules["PyQt5"] = pyqt5

    class _BoundSignal:
        def __init__(self):
            self._slots = []

        def connect(self, slot):
            self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                slot(*args, **kwargs)

        def disconnect(self, slot=None):
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

    class _SignalDescriptor:
        def __set_name__(self, owner, name):
            self._name = f"__signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = getattr(instance, self._name, None)
            if signal is None:
                signal = _BoundSignal()
                setattr(instance, self._name, signal)
            return signal

    def pyqtSignal(*_args, **_kwargs):
        return _SignalDescriptor()

    def pyqtSlot(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    class QObject:
        def __init__(self, *args, **kwargs):
            super().__setattr__("_qt_attributes", {})

        def deleteLater(self):
            return None

    class QThread(QObject):
        def __init__(self):
            super().__init__()
            self.started = _BoundSignal()
            self._running = False

        def start(self):
            self._running = True
            self.started.emit()

        def isRunning(self):
            return self._running

        def quit(self):
            self._running = False

        def wait(self):
            return None

    class QAbstractNativeEventFilter:
        def __init__(self, *args, **kwargs):
            pass

    class Qt:
        AA_DisableHighDpiScaling = 0
        AA_EnableHighDpiScaling = 1
        FramelessWindowHint = 0
        WindowStaysOnTopHint = 0
        Tool = 0
        Window = 0
        CrossCursor = 0
        StrongFocus = 0
        NoPen = 0
        Key_Escape = 27
        AlignCenter = 0
        ScrollBarAlwaysOff = 0
        ScrollBarAsNeeded = 0
        PointingHandCursor = 0

    class QRect:
        def __init__(self, left, top, width, height):
            self._left = left
            self._top = top
            self._width = width
            self._height = height

        def left(self):
            return self._left

        def top(self):
            return self._top

        def right(self):
            return self._left + self._width

        def bottom(self):
            return self._top + self._height

        def width(self):
            return self._width

        def height(self):
            return self._height

    class QEvent:
        pass

    class QTimer(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.timeout = _BoundSignal()

        def start(self, *args, **kwargs):
            return None

        def stop(self):
            return None

        @staticmethod
        def singleShot(*args, **kwargs):
            return None

    qtcore = types.ModuleType("PyQt5.QtCore")
    qtcore.QObject = QObject
    qtcore.QThread = QThread
    qtcore.QAbstractNativeEventFilter = QAbstractNativeEventFilter
    qtcore.pyqtSignal = pyqtSignal
    qtcore.pyqtSlot = pyqtSlot
    qtcore.Qt = Qt
    qtcore.QRect = QRect
    qtcore.QEvent = QEvent
    qtcore.QTimer = QTimer
    sys.modules["PyQt5.QtCore"] = qtcore
    pyqt5.QtCore = qtcore

    class QIcon:
        def __init__(self, *_args, **_kwargs):
            pass

    class QImage:
        def __init__(self, *_args, **_kwargs):
            pass

    class QPainter:
        def __init__(self, *_args, **_kwargs):
            pass

        def setPen(self, *_args, **_kwargs):
            return None

        def setBrush(self, *_args, **_kwargs):
            return None

        def drawRect(self, *_args, **_kwargs):
            return None

        def drawImage(self, *_args, **_kwargs):
            return None

    class QColor:
        def __init__(self, *_args, **_kwargs):
            pass

    class QPen:
        def __init__(self, *_args, **_kwargs):
            pass

    class QCursor:
        def __init__(self, *_args, **_kwargs):
            pass

    qtgui = types.ModuleType("PyQt5.QtGui")
    qtgui.QIcon = QIcon
    qtgui.QImage = QImage
    qtgui.QPainter = QPainter
    qtgui.QColor = QColor
    qtgui.QPen = QPen
    qtgui.QCursor = QCursor
    sys.modules["PyQt5.QtGui"] = qtgui
    pyqt5.QtGui = qtgui

    class QWidget(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._visible = False

        def show(self):
            self._visible = True

        def hide(self):
            self._visible = False

        def isVisible(self):
            return self._visible

        def raise_(self):
            return None

        def activateWindow(self):
            return None

        def setLayout(self, *_args, **_kwargs):
            return None

    class QMainWindow(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    class QApplication(QObject):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self.aboutToQuit = _BoundSignal()
            self._quit_on_last_window_closed = True

        def setQuitOnLastWindowClosed(self, value):
            self._quit_on_last_window_closed = value

        def exec_(self):
            return 0

        def clipboard(self):
            return SimpleNamespace(setText=lambda *_: None)

        @staticmethod
        def setAttribute(*_args, **_kwargs):
            return None

    class QMenu(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._actions = []

        def addAction(self, action):
            self._actions.append(action)
            return action

    class QAction(QObject):
        def __init__(self, text, parent=None, triggered=None):
            super().__init__()
            self.text = text
            self.triggered = _BoundSignal()
            if triggered is not None:
                self.triggered.connect(triggered)

    class QSystemTrayIcon(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.activated = _BoundSignal()

        def setIcon(self, *_args, **_kwargs):
            return None

        def setToolTip(self, *_args, **_kwargs):
            return None

        def setContextMenu(self, *_args, **_kwargs):
            return None

        def show(self):
            return None

    class QRubberBand(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__(*args, **kwargs)
            self._geometry = QRect(0, 0, 0, 0)

        def setGeometry(self, rect):
            self._geometry = rect

        def geometry(self):
            return self._geometry

    class QMessageBox(QWidget):
        Critical = 0
        ActionRole = 0
        Ok = object()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._buttons = []

        def setIcon(self, *_args, **_kwargs):
            return None

        def setWindowTitle(self, *_args, **_kwargs):
            return None

        def setText(self, *_args, **_kwargs):
            return None

        def addButton(self, *args):
            button = object()
            self._buttons.append((args, button))
            return button

        def exec_(self):
            return 0

        def clickedButton(self):
            return None

    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    qtwidgets.QApplication = QApplication
    qtwidgets.QMainWindow = QMainWindow
    qtwidgets.QWidget = QWidget
    qtwidgets.QSystemTrayIcon = QSystemTrayIcon
    qtwidgets.QMenu = QMenu
    qtwidgets.QAction = QAction
    qtwidgets.QMessageBox = QMessageBox
    qtwidgets.QRubberBand = QRubberBand
    qtwidgets.__all__ = [
        "QApplication",
        "QMainWindow",
        "QWidget",
        "QSystemTrayIcon",
        "QMenu",
        "QAction",
        "QMessageBox",
        "QRubberBand",
    ]
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
    pyqt5.QtWidgets = qtwidgets

    class QSound:
        @staticmethod
        def play(*_args, **_kwargs):
            return None

    qtmultimedia = types.ModuleType("PyQt5.QtMultimedia")
    qtmultimedia.QSound = QSound
    sys.modules["PyQt5.QtMultimedia"] = qtmultimedia
    pyqt5.QtMultimedia = qtmultimedia

    if "gui" not in sys.modules:
        gui_stub = types.ModuleType("gui")

        class MainWindow:
            def __init__(self, storage_manager):
                self.storage_manager = storage_manager
                self._visible = False

            def show(self):
                self._visible = True

            def raise_(self):
                return None

            def activateWindow(self):
                return None

            def isVisible(self):
                return self._visible

        gui_stub.MainWindow = MainWindow
        sys.modules["gui"] = gui_stub

    if "chat_gui" not in sys.modules:
        chat_stub = types.ModuleType("chat_gui")

        class ChatApp:
            def __init__(self, chat_manager):
                if chat_manager is None:
                    raise ValueError("chat_manager is required")
                self.chat_manager = chat_manager
                self.destroyed = _BoundSignal()
                self._visible = False

            def show(self):
                self._visible = True

            def raise_(self):
                return None

            def activateWindow(self):
                return None

            def setFocus(self):
                return None

            def isVisible(self):
                return self._visible

        chat_stub.ChatApp = ChatApp
        sys.modules["chat_gui"] = chat_stub


try:
    import PyQt5.QtWidgets  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - only executed in headless CI
    _install_pyqt_stubs()
