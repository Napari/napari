import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QComboBox, QDoubleSpinBox
from .qt_base_layer import QtLayerControls
from ..qt_color_dialog import QColorSwatchEdit
from ..utils import qt_signals_blocked
from ...layers.vectors._vectors_constants import ColorMode


class QtVectorsControls(QtLayerControls):
    """Qt view and controls for the napari Vectors layer.

    Parameters
    ----------
    layer : napari.layers.Vectors
        An instance of a napari Vectors layer.

    Attributes
    ----------
    edgeColorSwatch : qtpy.QtWidgets.QFrame
        Color swatch showing display color of vectors.
    edgeComboBox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select display color for vectors.
    grid_layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Vectors
        An instance of a napari Vectors layer.
    lengthSpinBox : qtpy.QtWidgets.QDoubleSpinBox
        Spin box widget controlling line length of vectors.
        Multiplicative factor on projections for length of all vectors.
    widthSpinBox : qtpy.QtWidgets.QDoubleSpinBox
        Spin box widget controlling edge line width of vectors.
    """

    def __init__(self, layer):
        super().__init__(layer)

        self.layer.events.edge_width.connect(self._on_width_change)
        self.layer.events.length.connect(self._on_len_change)
        self.layer.events.current_edge_color.connect(
            self._on_edge_color_change
        )
        self.layer.events.edge_color_mode.connect(
            self._on_edge_color_mode_change
        )

        color_properties = self._get_property_values()
        color_prop_box = QComboBox(self)
        color_prop_box.activated[str].connect(self.change_edge_color_property)
        color_prop_box.addItems(color_properties)
        self.color_prop_box = color_prop_box

        # vector color adjustment and widget
        self.edgeColorEdit = QColorSwatchEdit(
            initial_color=self.layer.edge_color,
            tooltip='click to set current edge color',
        )
        self.edgeColorEdit.color_changed.connect(self.change_edge_color)
        self.edge_color_label = QLabel('edge color:')
        self._on_edge_color_change()

        colorModeComboBox = QComboBox(self)
        colorModeComboBox.addItems(ColorMode.keys())
        colorModeComboBox.activated[str].connect(self.change_edge_color_mode)
        self.color_mode_comboBox = colorModeComboBox
        self._on_edge_color_mode_change()

        # line width in pixels
        self.widthSpinBox = QDoubleSpinBox()
        self.widthSpinBox.setKeyboardTracking(False)
        self.widthSpinBox.setSingleStep(0.1)
        self.widthSpinBox.setMinimum(0.1)
        self.widthSpinBox.setValue(self.layer.edge_width)
        self.widthSpinBox.valueChanged.connect(self.change_width)

        # line length
        self.lengthSpinBox = QDoubleSpinBox()
        self.lengthSpinBox.setKeyboardTracking(False)
        self.lengthSpinBox.setSingleStep(0.1)
        self.lengthSpinBox.setValue(self.layer.length)
        self.lengthSpinBox.setMinimum(0.1)
        self.lengthSpinBox.valueChanged.connect(self.change_length)

        # grid_layout created in QtLayerControls
        # addWidget(widget, row, column, [row_span, column_span])
        self.grid_layout.addWidget(QLabel('opacity:'), 0, 0)
        self.grid_layout.addWidget(self.opacitySlider, 0, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('width:'), 1, 0)
        self.grid_layout.addWidget(self.widthSpinBox, 1, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('length:'), 2, 0)
        self.grid_layout.addWidget(self.lengthSpinBox, 2, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('blending:'), 3, 0)
        self.grid_layout.addWidget(self.blendComboBox, 3, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('edge color mode:'), 4, 0)
        self.grid_layout.addWidget(self.color_mode_comboBox, 4, 1, 1, 2)
        self.grid_layout.addWidget(self.edge_color_label, 5, 0)
        self.grid_layout.addWidget(self.edgeColorEdit, 5, 1, 1, 2)
        self.grid_layout.setRowStretch(6, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setSpacing(4)

    def change_edge_color_property(self, property: str):
        """Change edge_color_property of vectors on the layer model.
        This property is the property the edge color is mapped to.

        Parameters
        ----------
        property : str
            property to map the edge color to
        """
        mode = self.layer.edge_color_mode
        try:
            self.layer.edge_color = property
            self.layer.edge_color_mode = mode
        except TypeError:
            self._on_edge_color_mode_change()
            raise

    def change_edge_color_mode(self, mode: str):
        """Change edge color mode of vectors on the layer model.

        Parameters
        ----------
        mode : str
            Edge color for vectors. Must be: 'direct', 'cycle', or 'colormap'
        """
        old_mode = self.layer.edge_color_mode
        with self.layer.events.edge_color_mode.blocker():
            try:
                self.layer.edge_color_mode = mode

                self._update_edge_color_gui(mode)

            except ValueError:
                self.layer.edge_color_mode = old_mode
                raise

    def change_edge_color(self, color: np.ndarray):
        """Change edge color of vectors on the layer model.

        Parameters
        ----------
        color : np.ndarray
            Edge color for vectors, in an RGBA array
        """
        with self.layer.events.current_edge_color.blocker():
            self.layer.current_edge_color = color

    def change_width(self, value):
        """Change edge line width of vectors on the layer model.

        Parameters
        ----------
        value : float
            Line width of vectors.
        """
        self.layer.edge_width = value
        self.widthSpinBox.clearFocus()
        self.setFocus()

    def change_length(self, value):
        """Change length of vectors on the layer model.

        Multiplicative factor on projections for length of all vectors.

        Parameters
        ----------
        value : float
            Length of vectors.
        """
        self.layer.length = value
        self.lengthSpinBox.clearFocus()
        self.setFocus()

    def _update_edge_color_gui(self, mode: str):
        """ Update the GUI element associated with edge_color.
        This is typically used when edge_color_mode changes

        Parameters
        ----------
        mode : str
            The new edge_color mode the GUI needs to be updated for.
            Should be: 'direct', 'cycle', 'colormap'
        """
        if mode in ('cycle', 'colormap'):
            if self.grid_layout.indexOf(self.color_prop_box) == -1:
                self.grid_layout.replaceWidget(
                    self.edgeColorEdit, self.color_prop_box
                )
                self.edgeColorEdit.setHidden(True)
                self.color_prop_box.setHidden(False)
        elif mode == 'direct':
            if self.grid_layout.indexOf(self.edgeColorEdit) == -1:
                self.grid_layout.replaceWidget(
                    self.color_prop_box, self.edgeColorEdit
                )
                self.edgeColorEdit.setHidden(False)
                self.color_prop_box.setHidden(True)

    def _get_property_values(self):
        """Get the current property values from the Vectors layer

        Returns
        -------
        property_values : np.ndarray
            array of all of the union of the property names (keys)
            in Vectors.properties and Vectors._property_choices

        """
        property_choices = [*self.layer._property_choices]
        properties = [*self.layer.properties]
        property_values = np.union1d(property_choices, properties)

        return property_values

    def _on_len_change(self, event=None):
        """Change length of vectors.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.length.blocker():
            self.lengthSpinBox.setValue(self.layer.length)

    def _on_width_change(self, event=None):
        """"Receive layer model width change event and update width spinbox.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.edge_width.blocker():
            self.widthSpinBox.setValue(self.layer.edge_width)

    def _on_edge_color_change(self, event=None):
        """"Receive layer model edge color change event & update color swatch.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        """Receive layer.current_edge_color() change event and update view."""
        with qt_signals_blocked(self.edgeColorEdit):
            self.edgeColorEdit.setColor(self.layer.current_edge_color)

    def _on_edge_color_mode_change(self, event=None):
        """"Receive layer model edge color mode change event & update dropdown.

                Parameters
                ----------
                event : qtpy.QtCore.QEvent, optional.
                    Event from the Qt context, by default None.
                """
        with qt_signals_blocked(self.color_mode_comboBox):
            mode = self.layer.edge_color_mode
            index = self.color_mode_comboBox.findText(
                mode, Qt.MatchFixedString
            )
            self.color_mode_comboBox.setCurrentIndex(index)

            self._update_edge_color_gui(mode)
