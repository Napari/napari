"""
Example plugin for testing plugin discovery and loading
"""
import pluggy

hookimpl = pluggy.HookimplMarker("napari")


def reader_function():
    pass


@hookimpl
def napari_get_reader(path):
    if path.endswith('true'):
        return reader_function
