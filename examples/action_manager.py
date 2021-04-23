from random import shuffle

import numpy as np
from skimage import data

import napari
from napari._qt.widgets.qt_viewer_buttons import QtViewerPushButton
from napari.components import ViewerModel
from napari.utils.action_manager import action_manager


def rotate45(viewer):
    """
    Rotate layer 0 of the viewer by 45º

    Parameters
    ----------
    viewer
        active (unique) instance of the naparia viewer

    Notes
    -----
    The `viewer` parameter needs to be named `viewer`, the action manager will
    infer that we need an instance of viewer.
    """
    angle = np.pi / 4
    from numpy import cos, sin

    r = np.array([[cos(angle), -sin(angle)], [sin(angle), cos(angle)]])
    layer = viewer.layers[0]
    layer.rotate = layer.rotate @ r


# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)

layer_buttons = viewer.window.qt_viewer.layerButtons

# Button do not need to do anything, just need to be pretty; all the action
# binding and (un) binding will be done with the action manager, idem for
# setting the tooltip.
rot_button = QtViewerPushButton(None, 'warning')
layer_buttons.layout().insertWidget(3, rot_button)


def register_action():
    # Here we pass ViewerModel as the KeymapProvider as we want it to handle the shortcuts.
    # we could also pass none and bind the shortcuts at the window level – though we
    # are trying to not change the KeymapProvider API too much for now.
    # we give an action name to the action for configuration purposes as we need
    # it to be storable in json.
    action_manager.register_action(
        'rotate45', rotate45, 'Rotate layer 0 by 45deg', ViewerModel
    )


def bind_shortcut():
    # note that the tooltip of the corresponding button will be updated to
    # remove the shortcut.
    action_manager.unbind_shortcut('reset_view')  # Control-R
    action_manager.bind_shortcut('rotate45', 'Control-R')

def bind_button():
    action_manager.bind_button('rotate45', rot_button)

# we can all bind_shortcut or register_action or bind_button in any order;
# this let us configure shortcuts even if plugins are loaded / unloaded.
callbacks = [register_action, bind_shortcut, bind_button]

shuffle(callbacks)
for c in callbacks:
    print('calling', c)
    c()

napari.run()