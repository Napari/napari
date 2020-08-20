import numpy as np

from napari.layers.image._image_slice import ImageSlice


def _converter(array):
    return array * 2


def test_image_slice():
    image1 = np.random.random((32, 16))
    image2 = np.random.random((32, 16))

    # Create a slice and check it was created as expected.
    image_slice = ImageSlice(image1, _converter)
    assert image_slice.rgb is False
    assert id(image_slice.image.view) == id(image1)
    assert id(image_slice.image.raw) == id(image1)

    # Update the slice and see the conversion happened.
    image_slice.image.raw = image2
    assert id(image_slice.image.raw) == id(image2)
    assert np.all(image_slice.image.view == image2 * 2)
