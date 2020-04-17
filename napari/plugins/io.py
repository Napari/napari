from logging import getLogger
from typing import Optional, Sequence, Union

from ..types import LayerData
from . import PluginError
from . import plugin_manager as napari_plugin_manager


logger = getLogger(__name__)


def read_data_with_plugins(
    path: Union[str, Sequence[str]], plugin_manager=napari_plugin_manager
) -> Optional[LayerData]:
    """Iterate reader hooks and return first non-None LayerData or None.

    This function returns as soon as the path has been read successfully,
    while catching any plugin exceptions, storing them for later retrievial,
    providing useful error messages, and relooping until either layer data is
    returned, or no readers are found.

    Exceptions will be caught and stored as PluginErrors
    (in plugins.exceptions.PLUGIN_ERRORS)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to open
    plugin_manager : plugins.PluginManager, optional
        Instance of a napari PluginManager.  by default the main napari
        plugin_manager will be used.

    Returns
    -------
    LayerData : list of tuples, or None
        LayerData that can be passed to :func:`Viewer._add_layer_from_data()
        <napari.components.add_layers_mixin.AddLayersMixin._add_layer_from_data>`.
        ``LayerData`` is a list tuples, where each tuple is one of
        ``(data,)``, ``(data, meta)``, or ``(data, meta, layer_type)`` .

        If no reader plugins are (or they all error), returns ``None``
    """
    plugin_manager = plugin_manager or napari_plugin_manager
    skip_impls = []
    while True:
        (reader, implementation) = plugin_manager.hook.napari_get_reader(
            path=path, _return_impl=True, _skip_impls=skip_impls
        )
        if not reader:
            # we're all out of reader plugins
            return None
        try:
            return reader(path)  # try to read data
        except Exception as exc:
            # If the hook did return a reader, but the reader then failed
            # while trying to read the path, we store the traceback for later
            # retrieval, warn the user, and continue looking for readers
            # (skipping this one)
            msg = (
                f"Error in plugin '{implementation.plugin_name}', "
                f"hook 'napari_get_reader': {exc}"
            )
            # instantiating this PluginError stores it in
            # plugins.exceptions.PLUGIN_ERRORS, where it can be retrieved later
            err = PluginError(
                msg, implementation.plugin_name, implementation.plugin.__name__
            )
            err.__cause__ = exc  # like ``raise PluginError() from exc``

            skip_impls.append(implementation)  # don't try this impl again
            if implementation.plugin_name != 'builtins':
                # If builtins doesn't work, they will get a "no reader" found
                # error anyway, so it looks a bit weird to show them that the
                # "builtin plugin" didn't work.
                logger.error(err.format_with_contact_info())
