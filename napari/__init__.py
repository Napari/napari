try:
    from ._version import version as __version__
except ImportError:
    __version__ = "not-installed"


def __getattr__(name):
    # this unused import is here to fix a very strange bug.
    # there is some mysterious magical goodness in scipy stats that needs
    # to be imported early.
    # see: https://github.com/napari/napari/issues/925
    # see: https://github.com/napari/napari/issues/1347
    from scipy import stats  # noqa: F401

    # register napari object types with magicgui if it is installed
    from .utils import _magicgui, sys_info
    from .utils.notifications import notification_manager
    from .viewer import Viewer

    # This must come before .plugins
    _magicgui.register_types_with_magicgui()

    from ._event_loop import gui_qt, run
    from .plugins.io import save_layers
    from .view_layers import (  # type: ignore
        view_image,
        view_labels,
        view_path,
        view_points,
        view_shapes,
        view_surface,
        view_tracks,
        view_vectors,
    )

    del _magicgui
    del stats
    import os

    os.environ.setdefault('SPARSE_AUTO_DENSIFY', '1')

    return locals()[name]


__all__ = [
    '__version__',
    'gui_qt',
    'notification_manager',
    'run',
    'save_layers',
    'sys_info',
    'view_image',
    'view_labels',
    'view_path',
    'view_points',
    'view_shapes',
    'view_surface',
    'view_tracks',
    'view_vectors',
    'Viewer',
]


def __dir__():
    return __all__
