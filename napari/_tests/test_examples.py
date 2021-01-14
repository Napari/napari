from pathlib import Path
import napari
import pytest
import runpy

# import os


# not testing these examples
skip = [
    'surface_timeseries.py',  # needs nilearn
    '3d_kymograph.py',  # needs tqdm
    'live_tiffs.py',  # requires files
    'live_tiffs_generator.py',
]
EXAMPLE_DIR = Path(napari.__file__).parent.parent / 'examples'
# using f.name here and re-joining at `run_path()` for test key presentation
# (works even if the examples list is empty, as opposed to using an ids lambda)
examples = [f.name for f in EXAMPLE_DIR.glob("*.py") if f.name not in skip]


@pytest.fixture
def qapp():
    from napari._qt.qt_event_loop import get_app
    from qtpy.QtCore import QTimer

    # it's important that we use get_app so that it connects to the
    # app.aboutToQuit.connect(wait_for_workers_to_quit)
    app = get_app()

    # quit examples that explicitly start the event loop with `napari.run()`
    # so that tests aren't waiting on a manual exit
    QTimer.singleShot(100, app.quit)

    yield app


# @pytest.mark.skipif(bool(os.getenv("CI")), reason="Need to debug segfaults.")
@pytest.mark.skipif(bool(not examples), reason="Examples directory not found.")
@pytest.mark.parametrize("fname", examples)
def test_examples(qapp, fname, monkeypatch, capsys):
    """Test that all of our examples are still working without warnings."""

    from napari._qt.qt_main_window import Window
    from napari._qt.exceptions import ExceptionHandler

    # hide viewer window
    monkeypatch.setattr(Window, 'show', lambda *a: None)

    # make sure our sys.excepthook override in gui_qt doesn't hide errors
    def raise_errors(self, etype, value, tb):
        raise value

    monkeypatch.setattr(ExceptionHandler, 'handle', raise_errors)

    # run the example!
    assert runpy.run_path(str(EXAMPLE_DIR / fname))
