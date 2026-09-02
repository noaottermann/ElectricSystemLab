"""Configuration pytest pour Nodal."""

import os
import sys
import pytest
from PyQt5.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_qapp_instance = None

@pytest.fixture(scope="session", autouse=True)
def qapp():
    global _qapp_instance
    app = QApplication.instance()
    if app is None:
        _qapp_instance = QApplication(sys.argv or ["nodal_tests"])
    else:
        _qapp_instance = app
    return _qapp_instance
