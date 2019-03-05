"""
This example generates an image of vectors
Vector data is an array of shape (N, 4)
Each vector position is defined by an (x, y, x-proj, y-proj) element
    where x and y are the center points
    where x-proj and y-proj are the vector projections at each center

"""

import sys
from PyQt5.QtWidgets import QApplication
from napari_gui import Window, Viewer

import numpy as np


# starting
application = QApplication(sys.argv)

# create the viewer and window
viewer = Viewer()
win = Window(viewer)

# sample vector coord-like data
n = 1000
pos = np.zeros((n, 4), dtype=np.float32)
phi_space = np.linspace(0, 4*np.pi, n)
radius_space = np.linspace(0, 100, n)

# assign x-y position
pos[:, 0] = radius_space*np.cos(phi_space)
pos[:, 1] = radius_space*np.sin(phi_space)

# assign x-y projection
pos[:, 2] = radius_space*np.cos(phi_space)
pos[:, 3] = radius_space*np.sin(phi_space)

# add the vectors
viewer.add_vectors(pos)

sys.exit(application.exec_())
