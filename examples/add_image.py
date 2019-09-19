"""
Display one image using the add_image API.
"""

from skimage import data
import napari


with napari.gui_qt():
    # create the viewer with an image
    viewer = napari.add_image(data.astronaut())
