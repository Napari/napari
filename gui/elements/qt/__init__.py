"""
Qt backend.
"""
from PyQt5.QtWidgets import QApplication as QtApplication

from ._viewer import QtViewer
from ._layer import QtLayer


from vispy import app
app.use_app('pyqt5')
del app
