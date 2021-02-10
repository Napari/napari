import numpy as np
import pytest

from napari.components.cursor_event import CursorEvent
from napari.layers import Labels
from napari.utils.interactions import (
    ReadOnlyWrapper,
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
)


@pytest.mark.parametrize(
    "brush_shape, expected_sum", [("circle", 244), ("square", 274)]
)
def test_paint(brush_shape, expected_sum):
    """Test painting labels with circle/square brush."""
    data = np.ones((20, 20))
    layer = Labels(data)
    layer.brush_size = 10
    assert layer.cursor_size == 10
    layer.brush_shape = brush_shape
    layer.mode = 'paint'
    layer.selected_label = 3
    position = (0, 0)

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)

    position = (19, 19)

    # Simulate drag
    event = ReadOnlyWrapper(
        CursorEvent(
            data_position=position, type='mouse_move', is_dragging=True
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_release')
    )
    mouse_release_callbacks(layer, event)

    # Painting goes from (0, 0) to (19, 19) with a brush size of 10, changing
    # all pixels along that path, but none outside it.
    assert np.unique(layer.data[:8, :8]) == 3
    assert np.unique(layer.data[-8:, -8:]) == 3
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1
    assert np.sum(layer.data == 3) == expected_sum


@pytest.mark.parametrize(
    "brush_shape, expected_sum", [("circle", 244), ("square", 274)]
)
def test_paint_scale(brush_shape, expected_sum):
    """Test painting labels with circle/square brush when scaled."""
    data = np.ones((20, 20))
    layer = Labels(data, scale=(2, 2))
    layer.brush_size = 10
    layer.brush_shape = brush_shape
    layer.mode = 'paint'
    layer.selected_label = 3
    position = (0, 0)

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)

    position = (39, 39)

    # Simulate drag
    event = ReadOnlyWrapper(
        CursorEvent(
            data_position=position, type='mouse_move', is_dragging=True
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_release')
    )
    mouse_release_callbacks(layer, event)

    # Painting goes from (0, 0) to (19, 19) with a brush size of 10, changing
    # all pixels along that path, but none outside it.
    assert np.unique(layer.data[:8, :8]) == 3
    assert np.unique(layer.data[-8:, -8:]) == 3
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1
    assert np.sum(layer.data == 3) == expected_sum


@pytest.mark.parametrize(
    "brush_shape, expected_sum", [("circle", 156), ("square", 126)]
)
def test_erase(brush_shape, expected_sum):
    """Test erasing labels with different brush shapes."""
    data = np.ones((20, 20))
    layer = Labels(data)
    layer.brush_size = 10
    layer.mode = 'erase'
    layer.brush_shape = brush_shape
    layer.selected_label = 3
    position = (0, 0)

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)

    position = (19, 19)

    # Simulate drag
    event = ReadOnlyWrapper(
        CursorEvent(
            data_position=position, type='mouse_move', is_dragging=True
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_release')
    )
    mouse_release_callbacks(layer, event)

    # Painting goes from (0, 0) to (19, 19) with a brush size of 10, changing
    # all pixels along that path, but non outside it.
    assert np.unique(layer.data[:8, :8]) == 0
    assert np.unique(layer.data[-8:, -8:]) == 0
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1
    assert np.sum(layer.data == 1) == expected_sum


def test_pick():
    """Test picking label."""
    data = np.ones((20, 20))
    data[:5, :5] = 2
    data[-5:, -5:] = 3
    layer = Labels(data)
    assert layer.selected_label == 1

    layer.mode = 'pick'
    position = (0, 0)

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert layer.selected_label == 2

    position = (19, 19)

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert layer.selected_label == 3


def test_fill():
    """Test filling label."""
    data = np.ones((20, 20))
    data[:5, :5] = 2
    data[-5:, -5:] = 3
    layer = Labels(data)
    assert np.unique(layer.data[:5, :5]) == 2
    assert np.unique(layer.data[-5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1

    layer.mode = 'fill'
    position = (0, 0)
    layer.selected_label = 4

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[:5, :5]) == 4
    assert np.unique(layer.data[-5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1

    position = (19, 19)
    layer.selected_label = 5

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[:5, :5]) == 4
    assert np.unique(layer.data[-5:, -5:]) == 5
    assert np.unique(layer.data[:5, -5:]) == 1
    assert np.unique(layer.data[-5:, :5]) == 1


def test_fill_nD_plane():
    """Test filling label nD plane."""
    data = np.ones((20, 20, 20))
    data[:5, :5, :5] = 2
    data[0, 8:10, 8:10] = 2
    data[-5:, -5:, -5:] = 3
    layer = Labels(data)
    assert np.unique(layer.data[:5, :5, :5]) == 2
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:, -5:]) == 1
    assert np.unique(layer.data[-5:, :5, -5:]) == 1
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2

    layer.mode = 'fill'
    position = (0, 0, 0)
    layer.selected_label = 4

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[0, :5, :5]) == 4
    assert np.unique(layer.data[1:5, :5, :5]) == 2
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:, -5:]) == 1
    assert np.unique(layer.data[-5:, :5, -5:]) == 1
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2

    position = (0, 19, 19)
    layer.selected_label = 5

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[0, :5, :5]) == 4
    assert np.unique(layer.data[1:5, :5, :5]) == 2
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[1:5, -5:, -5:]) == 1
    assert np.unique(layer.data[-5:, :5, -5:]) == 1
    assert np.unique(layer.data[0, -5:, -5:]) == 5
    assert np.unique(layer.data[0, :5, -5:]) == 5
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2


def test_fill_nD_all():
    """Test filling label nD."""
    data = np.ones((20, 20, 20))
    data[:5, :5, :5] = 2
    data[0, 8:10, 8:10] = 2
    data[-5:, -5:, -5:] = 3
    layer = Labels(data)
    assert np.unique(layer.data[:5, :5, :5]) == 2
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:, -5:]) == 1
    assert np.unique(layer.data[-5:, :5, -5:]) == 1
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2

    layer.n_dimensional = True
    layer.mode = 'fill'
    position = (0, 0, 0)
    layer.selected_label = 4

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[:5, :5, :5]) == 4
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:, -5:]) == 1
    assert np.unique(layer.data[-5:, :5, -5:]) == 1
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2

    position = (0, 19, 19)
    layer.selected_label = 5

    # Simulate click
    event = ReadOnlyWrapper(
        CursorEvent(data_position=position, type='mouse_press')
    )
    mouse_press_callbacks(layer, event)
    assert np.unique(layer.data[:5, :5, :5]) == 4
    assert np.unique(layer.data[-5:, -5:, -5:]) == 3
    assert np.unique(layer.data[:5, -5:, -5:]) == 5
    assert np.unique(layer.data[-5:, :5, -5:]) == 5
    assert np.unique(layer.data[0, 8:10, 8:10]) == 2
