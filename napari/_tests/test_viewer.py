import os

import numpy as np
import pytest
from qtpy.QtCore import QPoint

from napari import layers
from napari._tests.utils import (
    add_layer_by_type,
    check_view_transform_consistency,
    check_viewer_functioning,
    layer_test_data,
)
from napari.utils._tests.test_naming import eval_with_filename


def test_viewer(make_test_viewer):
    """Test instantiating viewer."""
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    assert viewer.title == 'napari'
    assert view.viewer == viewer

    assert len(viewer.layers) == 0
    assert view.layers.vbox_layout.count() == 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0

    # Switch to 3D rendering mode and back to 2D rendering mode
    viewer.dims.ndisplay = 3
    assert viewer.dims.ndisplay == 3
    viewer.dims.ndisplay = 2
    assert viewer.dims.ndisplay == 2

    # Run all class key bindings
    for func in viewer.class_keymap.values():
        # skip fullscreen test locally
        if func.__name__ == 'toggle_fullscreen' and not os.getenv("CI"):
            continue
        if func.__name__ == 'play':
            continue
        func(viewer)


@pytest.mark.parametrize('layer_class, data, ndim', layer_test_data)
@pytest.mark.parametrize('visible', [True, False])
def test_add_layer(make_test_viewer, layer_class, data, ndim, visible):
    viewer = make_test_viewer()
    layer = add_layer_by_type(viewer, layer_class, data, visible=visible)
    check_viewer_functioning(viewer, viewer.window.qt_viewer, data, ndim)

    # Run all class key bindings
    for func in layer.class_keymap.values():
        func(layer)


@pytest.mark.parametrize('layer_class, a_unique_name, ndim', layer_test_data)
def test_add_layer_magic_name(
    make_test_viewer, layer_class, a_unique_name, ndim
):
    """Test magic_name works when using add_* for layers"""
    # Tests for issue #1709
    viewer = make_test_viewer()  # noqa: F841
    layer = eval_with_filename(
        "add_layer_by_type(viewer, layer_class, a_unique_name)",
        "somefile.py",
    )
    assert layer.name == "a_unique_name"


def test_screenshot(make_test_viewer):
    """Test taking a screenshot."""
    viewer = make_test_viewer()

    np.random.seed(0)
    # Add image
    data = np.random.random((10, 15))
    viewer.add_image(data)

    # Add labels
    data = np.random.randint(20, size=(10, 15))
    viewer.add_labels(data)

    # Add points
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)

    # Add vectors
    data = 20 * np.random.random((10, 2, 2))
    viewer.add_vectors(data)

    # Add shapes
    data = 20 * np.random.random((10, 4, 2))
    viewer.add_shapes(data)

    # Take screenshot of the image canvas only
    screenshot = viewer.screenshot(canvas_only=True)
    assert screenshot.ndim == 3

    # Take screenshot with the viewer included
    screenshot = viewer.screenshot(canvas_only=False)
    assert screenshot.ndim == 3


def test_changing_theme(make_test_viewer):
    """Test changing the theme updates the full window."""
    viewer = make_test_viewer()
    viewer.add_points(data=None)
    assert viewer.theme == 'dark'

    screenshot_dark = viewer.screenshot(canvas_only=False)

    viewer.theme = 'light'
    assert viewer.theme == 'light'

    screenshot_light = viewer.screenshot(canvas_only=False)
    equal = (screenshot_dark == screenshot_light).min(-1)

    # As canvas is main part of window (about 60%) so its area must be masked in these comparison.
    size = viewer.window.qt_viewer.canvas.native.size()
    coord = viewer.window.qt_viewer.canvas.native.mapTo(
        viewer.window._qt_window, QPoint(0, 0)
    )
    equal[
        coord.y() : coord.y() + size.height(),
        coord.x() : coord.x() + size.width(),
    ] = False

    # more than 99.5% of the pixels have changed
    assert (np.count_nonzero(equal) / equal.size) < 0.05, "Themes too similar"

    with pytest.raises(ValueError):
        viewer.theme = 'nonexistent_theme'


@pytest.mark.parametrize('layer_class, data, ndim', layer_test_data)
def test_roll_traspose_update(make_test_viewer, layer_class, data, ndim):
    """Check that transpose and roll preserve correct transform sequence."""

    viewer = make_test_viewer()

    np.random.seed(0)

    layer = add_layer_by_type(viewer, layer_class, data)

    # Set translations and scalings (match type of visual layer storing):
    transf_dict = {
        'translate': np.random.randint(0, 10, ndim).astype(np.float32),
        'scale': np.random.rand(ndim).astype(np.float32),
    }
    for k, val in transf_dict.items():
        setattr(layer, k, val)

    if layer_class in [layers.Image, layers.Labels]:
        transf_dict['translate'] -= transf_dict['scale'] / 2

    # Check consistency:
    check_view_transform_consistency(layer, viewer, transf_dict)

    # Roll dims and check again:
    viewer.dims._roll()
    check_view_transform_consistency(layer, viewer, transf_dict)

    # Transpose and check again:
    viewer.dims._transpose()
    check_view_transform_consistency(layer, viewer, transf_dict)


def test_toggling_axes(make_test_viewer):
    """Test toggling axes."""
    viewer = make_test_viewer()

    # Check axes are not visible
    assert not viewer.axes.visible

    # Make axes visible
    viewer.axes.visible = True
    assert viewer.axes.visible

    # Enter 3D rendering and check axes still visible
    viewer.dims.ndisplay = 3
    assert viewer.axes.visible

    # Make axes not visible
    viewer.axes.visible = False
    assert not viewer.axes.visible


def test_toggling_scale_bar(make_test_viewer):
    """Test toggling scale bar."""
    viewer = make_test_viewer()

    # Check scale bar is not visible
    assert not viewer.scale_bar.visible

    # Make scale bar visible
    viewer.scale_bar.visible = True
    assert viewer.scale_bar.visible

    # Enter 3D rendering and check scale bar is still visible
    viewer.dims.ndisplay = 3
    assert viewer.scale_bar.visible

    # Make scale bar not visible
    viewer.scale_bar.visible = False
    assert not viewer.scale_bar.visible
