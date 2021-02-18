from copy import deepcopy
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from pydantic import root_validator, validator

from ...utils.colormaps import Colormap
from ...utils.colormaps.categorical_colormap import CategoricalColormap
from ...utils.colormaps.colormap_utils import ensure_colormap
from ...utils.events import EventedModel
from ...utils.events.custom_types import Array
from ._color_manager_constants import ColorMode
from .color_manager_utils import (
    guess_continuous,
    is_color_mapped,
    map_property,
)
from .color_transformations import (
    ColorType,
    normalize_and_broadcast_colors,
    transform_color,
    transform_color_with_defaults,
)


class ColorProperties(EventedModel):
    name: str
    values: np.ndarray
    current_value: Optional[Any] = None


def compare_colormap(cmap_1, cmap_2):
    names_eq = cmap_1.name == cmap_2.name
    colors_eq = np.array_equal(cmap_1.colors, cmap_2.colors)

    return np.all([names_eq, colors_eq])


def compare_categorical_colormap(cmap_1, cmap_2):
    # todo: add real equivalence test
    if np.array_equal(
        cmap_1.fallback_color.values, cmap_2.fallback_color.values
    ):
        return True
    else:
        return False


def compare_color_properties(c_prop_1, c_prop_2):
    if (c_prop_1 is None) and (c_prop_2 is None):
        return True
    elif (c_prop_1 is None) != (c_prop_2 is None):
        return False
    else:
        names_eq = c_prop_1.name == c_prop_2.name
        values_eq = np.array_equal(c_prop_1.values, c_prop_2.values)

        eq = names_eq & values_eq

    return eq


def compare_colors(color_1, color_2):
    return np.allclose(color_1, color_2)


def compare_contrast_limits(clim_1, clim_2):
    if (clim_1 is None) and (clim_2 is None):
        return True
    elif (clim_1 is None) != (clim_2 is None):
        return False
    else:
        return np.allclose(clim_1, clim_2)


class ColorManager(EventedModel):
    """A class for controlling the display colors for annotations in napari.

    Attributes
    ----------
    current_color : Optional[np.ndarray]
        A (4,) color array for the color of the next items to be added.
    mode : ColorMode
        The mode for setting colors.

        ColorMode.DIRECT: colors are set by passing color values to ColorManager.colors
        ColorMode.COLORMAP: colors are set via the continuous_colormap applied to the
                            color_properties
        ColorMode.CYCLE: colors are set vie the categorical_colormap appied to the
                         color_properties. This should be used for categorical
                         properties only.
     color_properties : Optional[ColorProperties]
        The property values that are used for setting colors in ColorMode.COLORMAP
        and ColorMode.CYCLE. The ColorProperties dataclass has 3 fields: name,
        values, and current_value. name (str) is the name of the property being used.
        values (np.ndarray) is an array containing the property values.
        current_value contains the value for the next item to be added. color_properties
        can be set as either a ColorProperties object or a dictionary where the keys are
        the field values and the values are the field values (i.e., a dictionary that would
        be valid in ColorProperties(**input_dictionary) ).
    continuous_colormap : Colormap
        The napari colormap object used in ColorMode.COLORMAP mode. This can also be set
        using the name of a known colormap as a string.
    contrast_limits : Tuple[float, float]
        The min and max value for the colormap being applied to the color_properties
        in ColorMonde.COLORMAP mode. Set as a tuple (min, max).
    categorical_colormap : CategoricalColormap
        The napari CategoricalColormap object used in ColorMode.CYCLE mode.
        To set a direct mapping between color_property values and colors,
        pass a dictionary where the keys are the property values and the
        values are colors (either string names or (4,) color arrays).
        To use a color cycle, pass a list or array of colors. You can also
        pass the CategoricalColormap keyword arguments as a dictionary.
    colors : np.ndarray
        The colors in a Nx4 color array, where N is the number of colors.
    """

    # fields
    current_color: Optional[np.ndarray] = None
    mode: ColorMode = ColorMode.DIRECT
    color_properties: Optional[ColorProperties] = None
    continuous_colormap: Colormap = 'viridis'
    contrast_limits: Optional[Tuple[float, float]] = None
    categorical_colormap: CategoricalColormap = [0, 0, 0, 1]
    colors: Array[float, (-1, 4)] = []

    # validators
    @validator('continuous_colormap', pre=True)
    def _ensure_continuous_colormap(cls, v):
        coerced_colormap = ensure_colormap(v)
        return coerced_colormap

    @validator('categorical_colormap', pre=True)
    def _coerce_categorical_colormap(cls, v):
        if isinstance(v, CategoricalColormap):
            return v
        if isinstance(v, list) or isinstance(v, np.ndarray):
            fallback_color = v

            # reset the color mapping
            colormap = {}
        elif isinstance(v, dict):
            if ('colormap' in v) or ('fallback_color' in v):
                if 'colormap' in v:
                    colormap = {
                        k: transform_color(v)[0]
                        for k, v in v['colormap'].items()
                    }
                else:
                    colormap = {}
                if 'fallback_color' in v:
                    fallback_color = v['fallback_color']
                else:
                    fallback_color = 'white'
            else:
                colormap = {k: transform_color(v)[0] for k, v in v.items()}
                fallback_color = 'white'
        else:
            raise TypeError('colormap should be an array or dict')

        return CategoricalColormap(
            colormap=colormap, fallback_color=fallback_color
        )

    @validator('color_properties', pre=True)
    def _coerce_color_properties(cls, v):
        if v is None:
            color_properties = v
        elif isinstance(v, dict):
            if len(v) == 0:
                color_properties = None
            else:
                try:
                    # ensure the values are a numpy array
                    v['values'] = np.asarray(v['values'])
                    color_properties = ColorProperties(**v)
                except ValueError:
                    err_msg = 'color_properties dictionary should have keys: name, value, and optionally current_value'

                    raise ValueError(err_msg)

        elif isinstance(v, ColorProperties):
            color_properties = v
        else:
            raise TypeError(
                'color_properties should be None, a dict, or ColorProperties object'
            )

        return color_properties

    @validator('colors', pre=True)
    def _ensure_color_array(cls, v, values):
        if len(v) > 0:
            return transform_color(v)
        else:
            return np.empty((0, 4))

    @validator('current_color', pre=True)
    def _coerce_current_color(cls, v):
        if v is None:
            return v
        elif len(v) == 0:
            return np.emtpy((0, 4))
        else:
            return transform_color(v)[0]

    @root_validator(skip_on_failure=True)
    def _validate_colors(cls, values):

        color_mode = values['mode']

        if color_mode == ColorMode.CYCLE:
            color_properties = values['color_properties'].values
            cmap = values['categorical_colormap']
            if len(color_properties) == 0:
                colors = np.empty((0, 4))
                current_prop_value = values['color_properties'].current_value
                if current_prop_value is not None:
                    values['current_color'] = cmap.map(current_prop_value)[0]
            else:
                colors = cmap.map(color_properties)
            values['categorical_colormap'] = cmap

        elif color_mode == ColorMode.COLORMAP:
            color_properties = values['color_properties'].values
            cmap = values['continuous_colormap']
            if len(color_properties) > 0:
                if values['contrast_limits'] is None:
                    colors, contrast_limits = map_property(
                        prop=color_properties,
                        colormap=cmap,
                    )
                    values['contrast_limits'] = contrast_limits
                else:
                    colors, _ = map_property(
                        prop=color_properties,
                        colormap=cmap,
                        contrast_limits=values['contrast_limits'],
                    )
            else:
                colors = np.empty((0, 4))
                current_prop_value = values['color_properties'].current_value
                if current_prop_value is not None:
                    values['current_color'] = cmap.map(current_prop_value)[0]

            if len(colors) == 0:
                colors = np.empty((0, 4))
        elif color_mode == ColorMode.DIRECT:
            colors = values['colors']

        # set the current color to the last color/property value
        # if it wasn't already set
        if values['current_color'] is None and len(colors) > 0:
            values['current_color'] = colors[-1]
            if color_mode in [ColorMode.CYCLE, ColorMode.COLORMAP]:
                property_values = values['color_properties']
                property_values.current_value = property_values.values[-1]
                values['color_properties'] = property_values

        values['colors'] = colors
        return values

    def set_color(
        self,
        color: ColorType,
        n_colors: int,
        properties: Dict[str, np.ndarray],
        current_properties: Dict[str, np.ndarray],
    ):
        """Set a color property. This is convenience function

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        n_colors : int
            The number of colors that needs to be set. Typically len(data).
        properties : Dict[str, np.ndarray]
            The layer property values
        current_properties : Dict[str, np.ndarray]
            The layer current property values
        """
        # if the provided color is a string, first check if it is a key in the properties.
        # otherwise, assume it is the name of a color
        if is_color_mapped(color, properties):
            self.color_properties = ColorProperties(
                name=color,
                values=properties[color],
                current_value=np.squeeze(current_properties[color]),
            )
            if guess_continuous(properties[color]):
                self.mode = ColorMode.COLORMAP
            else:
                self.mode = ColorMode.CYCLE
        else:
            transformed_color = transform_color_with_defaults(
                num_entries=n_colors,
                colors=color,
                elem_name="face_color",
                default="white",
            )
            colors = normalize_and_broadcast_colors(
                n_colors, transformed_color
            )
            self.mode = ColorMode.DIRECT
            self.colors = colors

    def refresh_colors(
        self,
        properties: Dict[str, np.ndarray],
        update_color_mapping: bool = False,
    ):
        """Calculate and update colors if using a cycle or color map
        Parameters
        ----------
        properties : Dict[str, np.ndarray]
           The layer properties to use to update the colors.
        update_color_mapping : bool
           If set to True, the function will recalculate the color cycle map
           or colormap (whichever is being used). If set to False, the function
           will use the current color cycle map or color map. For example, if you
           are adding/modifying points and want them to be colored with the same
           mapping as the other points (i.e., the new points shouldn't affect
           the color cycle map or colormap), set update_color_mapping=False.
           Default value is False.
        """
        if self.mode in [ColorMode.CYCLE, ColorMode.COLORMAP]:
            property_name = self.color_properties.name
            current_value = self.color_properties.current_value
            property_values = properties[property_name]
            self.color_properties = ColorProperties(
                name=property_name,
                values=property_values,
                current_value=current_value,
            )

            if update_color_mapping is True:
                self.contrast_limits = None

    def add(
        self,
        color: Optional[ColorType] = None,
        n_colors: int = 1,
        update_clims: bool = False,
    ):
        """Add colors
        Parameters
        ----------
        color : Optional[ColorType]
            The color to add. If set to None, the value of self.current_color will be used.
            The default value is None.
        n_colors : int
            The number of colors to add. The default value is 1.
        update_clims : bool
            If in colormap mode, update the contrast limits when adding the new values
            (i.e., reset the range to 0-new_max_value).
        """
        if self.mode == ColorMode.DIRECT:
            if color is None:
                new_color = self.current_color
            else:
                new_color = color
            transformed_color = transform_color_with_defaults(
                num_entries=n_colors,
                colors=new_color,
                elem_name="color",
                default="white",
            )
            broadcasted_colors = normalize_and_broadcast_colors(
                n_colors, transformed_color
            )
            self.colors = np.concatenate((self.colors, broadcasted_colors))
        else:
            # add the new value color_properties
            color_property_name = self.color_properties.name
            current_value = self.color_properties.current_value
            if color is None:
                color = current_value
            new_color_property_values = np.concatenate(
                (self.color_properties.values, np.repeat(color, n_colors)),
                axis=0,
            )
            self.color_properties = ColorProperties(
                name=color_property_name,
                values=new_color_property_values,
                current_value=current_value,
            )

            if update_clims and self.mode == ColorMode.COLORMAP:
                self.contrast_limits = None

    def remove(self, indices_to_remove: Union[set, list, np.ndarray]):
        """Remove the indicated color elements
        Parameters
        ----------
        indices_to_remove : set, list, np.ndarray
            The indices of the text elements to remove.
        """
        selected_indices = list(indices_to_remove)
        if len(selected_indices) > 0:
            if self.mode == ColorMode.DIRECT:
                self.colors = np.delete(self.colors, selected_indices, axis=0)
            else:
                # remove the color_properties
                color_property_name = self.color_properties.name
                current_value = self.color_properties.current_value
                new_color_property_values = np.delete(
                    self.color_properties.values, selected_indices
                )
                self.color_properties = ColorProperties(
                    name=color_property_name,
                    values=new_color_property_values,
                    current_value=current_value,
                )

    def paste(self, colors: np.ndarray, properties: Dict[str, np.ndarray]):
        """Append colors to the ColorManager. Uses the color values if
        in direct mode and the properties in colormap or cycle mode.

        This method is for compatibility with the paste functionality
        in the layers.

        Parameters
        ----------
        colors : np.ndarray
            The (Nx4) color array of color values to add. These values are
            only used if the color mode is direct.
        properties : Dict[str, np.ndarray]
            The property values to add. These are used if the color mode
            is colormap or cycle.
        """
        if self.mode == ColorMode.DIRECT:
            self.colors = np.concatenate(
                (self.colors, transform_color(colors))
            )
        else:
            color_property_name = self.color_properties.name
            current_value = self.color_properties.current_value
            old_properties = self.color_properties.values
            values_to_add = properties[color_property_name]
            new_color_property_values = np.concatenate(
                (old_properties, values_to_add),
                axis=0,
            )

            self.color_properties = ColorProperties(
                name=color_property_name,
                values=new_color_property_values,
                current_value=current_value,
            )

    def update_current_properties(
        self, current_properties: Dict[str, np.ndarray]
    ):
        """This is updates the current_value of the color_properties when the
        layer current_properties is updated.

        This is a convenience method that is generally only called by the layer.

        Parameters
        ----------
        current_properties : Dict[str, np.ndarray]
            The new current property values
        """
        if self.color_properties is not None:
            current_property_name = self.color_properties.name
            current_property_values = self.color_properties.values
            if current_property_name in current_properties:
                new_current_value = np.squeeze(
                    current_properties[current_property_name]
                )
                if new_current_value != self.color_properties.current_value:
                    self.color_properties = ColorProperties(
                        name=current_property_name,
                        values=current_property_values,
                        current_value=new_current_value,
                    )

    def update_current_color(
        self, current_color: np.ndarray, update_indices: list = []
    ):
        """Update the current color and update the colors if requested.

        This is a convenience method and is generally called by the layer.

        Parameters
        ----------
        current_color : np.ndarray
            The new current color value.
        update_indices : list
            The indices of the color elements to update.
            If the list has length 0, no colors are updated.
            If the ColorManager is not in DIRECT mode, updating the values
            will change the mode to DIRECT.
        """
        self.current_color = transform_color(current_color)[0]
        if len(update_indices) > 0:
            self.mode = ColorMode.DIRECT
            cur_colors = self.colors.copy()
            cur_colors[update_indices] = self.current_color
            self.colors = cur_colors

    @classmethod
    def from_layer_kwargs(
        cls,
        colors: Union[dict, str, np.ndarray],
        properties: Dict[str, np.ndarray],
        n_colors: Optional[int] = None,
        continuous_colormap: Optional[Union[str, Colormap]] = None,
        contrast_limits: Optional[Tuple[float, float]] = None,
        categorical_colormap: Optional[
            Union[CategoricalColormap, list, np.ndarray]
        ] = None,
        mode: Optional[Union[ColorMode, str]] = None,
        current_color: Optional[np.ndarray] = None,
        default_color_cycle: np.ndarray = np.array([1, 1, 1, 1]),
    ):
        """Initialize a ColorManager object from layer kwargs. This is a convenience
        function to coerce possible inputs into ColorManager kwargs

        """
        properties = {k: np.asarray(v) for k, v in properties.items()}
        if isinstance(colors, dict):
            # if the kwargs are passed as a dictionary, unpack them
            color_values = colors.get('colors', None)
            current_color = colors.get('current_color', None)
            mode = colors.get('mode', None)
            color_properties = colors.get('color_properties', None)
            continuous_colormap = colors.get('continuous_colormap', None)
            contrast_limits = colors.get('contrast_limits', None)
            categorical_colormap = colors.get('categorical_colormap', None)

            if isinstance(color_properties, str):
                # if the color properties were given as a property name,
                # coerce into ColorProperties
                try:
                    prop_values = properties[color_properties]
                    prop_name = color_properties
                    color_properties = ColorProperties(
                        name=prop_name, values=prop_values
                    )
                except KeyError:
                    raise KeyError(
                        'if color_properties is a string, it should be a property name'
                    )
        else:
            color_values = colors
            color_properties = None

        if categorical_colormap is None:
            categorical_colormap = deepcopy(default_color_cycle)

        color_kwargs = {
            'categorical_colormap': categorical_colormap,
            'continuous_colormap': continuous_colormap,
            'contrast_limits': contrast_limits,
            'current_color': current_color,
            'n_colors': n_colors,
        }

        if color_properties is None:
            if is_color_mapped(color_values, properties):
                if n_colors == 0:
                    color_properties = ColorProperties(
                        name=color_values,
                        values=np.empty(
                            0, dtype=properties[color_values].dtype
                        ),
                        current_value=properties[color_values][0],
                    )
                else:
                    color_properties = ColorProperties(
                        name=color_values, values=properties[color_values]
                    )
                if mode is None:
                    if guess_continuous(color_properties.values):
                        mode = ColorMode.COLORMAP
                    else:
                        mode = ColorMode.CYCLE

                color_kwargs.update(
                    {'mode': mode, 'color_properties': color_properties}
                )

            else:
                # direct mode
                if n_colors == 0:
                    if current_color is None:
                        current_color = transform_color(color_values)[0]
                    color_kwargs.update(
                        {
                            'mode': ColorMode.DIRECT,
                            'current_color': current_color,
                        }
                    )
                else:
                    transformed_color = transform_color_with_defaults(
                        num_entries=n_colors,
                        colors=color_values,
                        elem_name="colors",
                        default="white",
                    )
                    colors = normalize_and_broadcast_colors(
                        n_colors, transformed_color
                    )
                    color_kwargs.update(
                        {'mode': ColorMode.DIRECT, 'colors': colors}
                    )
        else:
            color_kwargs.update(
                {'mode': mode, 'color_properties': color_properties}
            )

        return cls(**color_kwargs)
