import numpy as np
from xml.etree.ElementTree import Element
from .shape import Shape
from ..shape_utils import create_box


class Path(Shape):
    """Class for a single path, which is a sequence of line segments.

    Parameters
    ----------
    data : np.ndarray
        NxD array of vertices specifying the path.
    edge_width : float
        thickness of lines and edges.
    edge_color : str or array-like
        Color of the shape marker border. Strings can be color names or hex
        values (starting with `#`). Array-like should have 3 or 4 elements
        per row in an RGB(A) format, and can either be of length 1 or the
        exact length of `data`.
    face_color : str or array-like
        Color of the shape marker body. Strings can be color names or hex
        values (starting with `#`). Array-like should have 3 or 4 elements
        per row in an RGB(A) format, and can either be of length 1 or the
        exact length of `data`.
    opacity : float
        Opacity of the shape, must be between 0 and 1.
    z_index : int
        Specifier of z order priority. Shapes with higher z order are displayed
        ontop of others.
    dims_order : (D,) list
        Order that the dimensions are to be rendered in.
    """

    def __init__(
        self,
        data,
        *,
        edge_width=1,
        edge_color='black',
        face_color='white',
        opacity=1,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):

        super().__init__(
            edge_width=edge_width,
            edge_color=edge_color,
            face_color=face_color,
            opacity=opacity,
            z_index=z_index,
            dims_order=dims_order,
            ndisplay=ndisplay,
        )
        self._filled = False
        self.data = data
        self.name = 'path'

    @property
    def data(self):
        """np.ndarray: NxD array of vertices."""
        return self._data

    @data.setter
    def data(self, data):
        data = np.array(data).astype(float)

        if len(self.dims_order) != data.shape[1]:
            self._dims_order = list(range(data.shape[1]))

        if len(data) < 2:
            raise ValueError(
                f"""Data shape does not match a path. A
                             Path expects at least two vertices,
                             {len(data)} provided."""
            )

        self._data = data
        self._update_displayed_data()

    def _update_displayed_data(self):
        """Update the data that is to be displayed."""
        # For path connect every all data
        self._set_meshes(self.data_displayed, face=False, closed=False)
        self._box = create_box(self.data_displayed)

        data_not_displayed = self.data[:, self.dims_not_displayed]
        self.slice_key = np.round(
            [
                np.min(data_not_displayed, axis=0),
                np.max(data_not_displayed, axis=0),
            ]
        ).astype('int')

    def to_xml(self):
        """Generates an xml element that defintes the shape according to the
        svg specification.

        Returns
        ----------
        element : xml.etree.ElementTree.Element
            xml element specifying the shape according to svg.
        """
        data = self.data[:, self.dims_displayed]
        points = ' '.join([f'{d[1]},{d[0]}' for d in data])

        props = self.svg_props
        props['fill'] = 'none'

        element = Element('polyline', points=points, **props)

        return element
