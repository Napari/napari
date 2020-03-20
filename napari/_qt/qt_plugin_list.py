"""Provides a QtPluginSorter that allows the user to change plugin call order.
"""
from typing import Optional

from pluggy.manager import HookImpl, PluginManager, _HookCaller
from qtpy.QtCore import QEvent, Qt, Signal, Slot
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .utils import drag_with_pixmap
from ..plugins import plugin_manager as napari_plugin_manager
from ..plugins.utils import HookOrderType, permute_hook_implementations


class ImplementationListItem(QFrame):
    """A Widget to render each hook implementation in a QtHookImplListWidget.

    Parameters
    ----------
    item : QListWidgetItem
        An item instance from a QListWidget. This will most likely come from
        :meth:`QtHookImplListWidget.add_hook_implementation_to_list`.
    parent : QWidget, optional
        The parent widget, by default None

    Attributes
    ----------
    plugin_name_label : QLabel
        The name of the plugin providing the hook implementation.
    enabled_checkbox : QCheckBox
        Checkbox to set the ``enabled`` status of the corresponding hook
        implementation.
    opacity : QGraphicsOpacityEffect
        The opacity of the whole widget.  When self.enabled_checkbox is
        unchecked, the opacity of the item is decreased.
    """

    def __init__(self, item: QListWidgetItem, parent: QWidget = None):
        super().__init__(parent)
        self.setToolTip("Click and drag to change call order")
        self.item = item
        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.position_label = QLabel()
        self.update_position_label()

        self.plugin_name_label = QLabel(item.hookimpl.plugin_name)
        self.enabled_checkbox = QCheckBox(self)
        self.enabled_checkbox.setToolTip("Uncheck to disable this plugin")
        self.enabled_checkbox.stateChanged.connect(self._set_enabled)
        self.enabled_checkbox.setChecked(
            getattr(item.hookimpl, 'enabled', True)
        )
        layout.addWidget(self.position_label)
        layout.addWidget(self.enabled_checkbox)
        layout.addWidget(self.plugin_name_label)
        layout.setStretch(2, 1)
        layout.setContentsMargins(0, 0, 0, 0)

    def _set_enabled(self, state: bool):
        """Set the enabled state of this hook implementation to ``state``."""
        # "hookimpl.enabled" is NOT a pluggy attribute... we are adding that to
        # allow skipping of hook_implementations.
        # see plugins.io.read_data_with_plugins() for an example
        setattr(self.item.hookimpl, 'enabled', bool(state))
        self.opacity.setOpacity(1 if state else 0.5)

    def update_position_label(self, order=None):
        """Update the label showing the position of this item in the list.

        Parameters
        ----------
        order : list, optional
            A HookOrderType list ... unused by this function, but here for ease
            of signal connection, by default None.
        """
        position = self.item.listWidget().indexFromItem(self.item).row() + 1
        self.position_label.setText(str(position))


class QtHookImplListWidget(QListWidget):
    """A ListWidget to display & sort the call order of a hook implementation.

    This class will usually be instantiated by a
    :class:`~napari._qt.qt_plugin_list.QtPluginSorter`.  Each item in the list
    will be rendered as a :class:`ImplementationListItem`.

    Parameters
    ----------
    parent : QWidget, optional
        Optional parent widget, by default None
    hook : pluggy.manager._HookCaller, optional
        The pluggy ``_HookCaller`` for which to show implementations.
        by default None (i.e. no hooks shown)
    """

    order_changed = Signal(list)  # emitted when the user changes the order.

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        hook: Optional[_HookCaller] = None,
    ):
        super().__init__(parent)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True)
        self.setDragDropMode(self.InternalMove)
        self.setSelectionMode(self.SingleSelection)
        self.setAcceptDrops(True)
        self.setSpacing(1)
        self.setMinimumHeight(1)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        self.order_changed.connect(self.permute_hook)
        self.set_hook(hook)

    def set_hook(self, hook: Optional[_HookCaller]):
        """Set the list widget to show hook implementations for ``hook``.

        Parameters
        ----------
        hook : _HookCaller, optional
            A pluggy HookCaller to show implementations for. by default None
            (i.e. no hooks shown)
        """
        self.clear()
        self.hook = hook
        if not hook:
            return
        for hookimpl in reversed(hook.get_hookimpls()):
            self.add_hook_implementation_to_list(hookimpl)

    def add_hook_implementation_to_list(self, hookimpl: HookImpl):
        """Add a list item for ``hookimpl`` with a custom widget.

        Parameters
        ----------
        hookimpl : HookImpl
            The hook implementation object to add to the list.
        """
        # don't want users to be able to resort builtin plugins.
        # this may change in the future, and might require hook-specific rules
        if hookimpl.plugin_name == 'builtins':
            return
        item = QListWidgetItem(parent=self)
        item.hookimpl = hookimpl
        self.addItem(item)
        widg = ImplementationListItem(item, parent=self)
        item.setSizeHint(widg.sizeHint())
        self.order_changed.connect(widg.update_position_label)
        self.setItemWidget(item, widg)

    def dropEvent(self, event: QEvent):
        """Triggered when the user moves & drops one of the items in the list.

        Parameters
        ----------
        event : QEvent
            The event that triggered the dropEvent.
        """
        super().dropEvent(event)
        order = [self.item(r).hookimpl for r in range(self.count())]
        self.order_changed.emit(order)

    def startDrag(self, supportedActions: Qt.DropActions):
        drag = drag_with_pixmap(self)
        drag.exec_(supportedActions, Qt.MoveAction)

    @Slot(list)
    def permute_hook(self, order: HookOrderType):
        """Rearrage the call order of the hooks for the current hook impl.

        Parameters
        ----------
        order : list
            A list of str, hookimpls, or module_or_class, with the desired
            CALL ORDER of the hook implementations.
        """
        if not self.hook:
            return
        permute_hook_implementations(self.hook, order)


class QtPluginSorter(QDialog):
    """Dialog that allows a user to change the call order of plugin hooks.

    A main QComboBox lets the user pick which hook specification they would
    like to reorder.  Then a :class:`QtHookImplListWidget` shows the current
    call order for all implementations of the current hook specification.  The
    user may then reorder them, or disable them by checking the checkbox next
    to each hook implementation name.

    Parameters
    ----------
    plugin_manager : pluggy.PluginManager, optional
        An instance of a pluggy PluginManager, by default, the main
        :class:`~napari.plugins.manager.NapariPluginManager` instance
    parent : QWidget, optional
        Optional parent widget, by default None
    initial_hook : str, optional
        If provided the QComboBox at the top of the dialog will be set to
        this hook, by default None
    firstresult_only : bool, optional
        If True, only hook specifications that declare the "firstresult"
        option will be included.  (these are hooks for which only the first
        non None result is returned).  by default True (because it makes
        less sense to sort hooks where we just collect all results anyway)
        https://pluggy.readthedocs.io/en/latest/#first-result-only

    Attributes
    ----------
    hook_combo_box : QComboBox
        A dropdown menu to select the current hook.
    hook_list : QtHookImplListWidget
        The list widget that displays (and allows sorting of) all of the hook
        implementations for the currently selected hook.
    """

    NULL_OPTION = 'select hook... '

    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        *,
        parent: Optional[QWidget] = None,
        initial_hook: Optional[str] = None,
        firstresult_only: bool = True,
    ):
        plugin_manager = plugin_manager or napari_plugin_manager
        super().__init__(parent)
        self.setWindowModality(Qt.NonModal)
        self.plugin_manager = plugin_manager
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.hook_combo_box = QComboBox()
        self.hook_combo_box.addItem(self.NULL_OPTION)

        # populate the combo box with all of the hooks known by the plugin mngr
        hooks = []
        for name, hook_caller in vars(plugin_manager.hook).items():
            if firstresult_only:
                # if the firstresult_only option is set
                # we only want to include hook_specifications that declare the
                # "firstresult" option as True.
                if not hook_caller.spec.opts.get('firstresult', False):
                    continue
            hooks.append(name)
        self.hook_combo_box.addItems(hooks)
        self.hook_combo_box.setToolTip(
            "select the hook specification to reorder"
        )
        self.hook_combo_box.activated[str].connect(self.set_current_hook)
        self.hook_list = QtHookImplListWidget(parent=self)

        title = QLabel('Plugin Sorter')
        title.setObjectName("h2")
        self.layout.addWidget(title)

        instructions = QLabel(
            'Select a hook to rearrange, then drag and '
            'drop plugins into the desired call order. '
            '\nDisable plugins by unchecking their checkbox.'
        )
        instructions.setWordWrap(True)
        self.layout.addWidget(instructions)

        self.layout.addWidget(self.hook_combo_box)
        self.layout.addWidget(self.hook_list)
        if initial_hook is not None:
            self.hook_combo_box.setCurrentText(initial_hook)
            self.set_current_hook(initial_hook)

    def set_current_hook(self, hook: str):
        """Change the hook specification shown in the list widget.

        Parameters
        ----------
        hook : str
            Name of the new hook specification to show.
        """
        if hook == self.NULL_OPTION:
            hook_caller = None
        else:
            hook_caller = getattr(self.plugin_manager.hook, hook)
        self.hook_list.set_hook(hook_caller)
