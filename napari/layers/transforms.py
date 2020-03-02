from __future__ import annotations  # noqa: F407

import toolz as tz
from typing import Sequence
import numpy as np

# from ..utils.list import ListModel


class Transform:
    """Base transform class.

    Defaults to the identity transform.

    Parameters
    ----------
    func : callable, Coords -> Coords
        A function converting an NxD array of coordinates to NxD'.
    """

    def __init__(self, func=tz.identity, inverse=None, name=None):
        self.func = func
        self._inverse_func = inverse
        self.name = name

        if func is tz.identity:
            self._inverse_func = tz.identity

    def __call__(self, coords):
        """Transform input coordinates to output."""
        return self.func(coords)

    def set_slice(self, axes: Sequence[int]) -> Transform:
        """Return a transform subset to the visible dimensions."""
        raise NotImplementedError('Cannot subset arbitrary transforms.')

    def set_pad(self, axes: Sequence[int]) -> Transform:
        """Return a transform with added axes for non-visible dimensions."""
        raise NotImplementedError('Cannot subset arbitrary transforms.')

    @property
    def inverse(self):
        if self._inverse_func is not None:
            return Transform(self._inverse_func, self.func)
        else:
            raise ValueError('Inverse function was not provided.')


# class TransformChain(ListModel, Transform):
#     def __init__(self, transforms=[]):
#         super().__init__(
#             basetype=Transform,
#             iterable=transforms,
#             lookup={str: lambda q, e: q == e.name},
#         )
#
#     def __call__(self, coords):
#         return tz.pipe(coords, *self)
#
#     def __newlike__(self, iterable):
#         return ListModel(self._basetype, iterable, self._lookup)
#
#     def set_slice(self, axes: Sequence[int]) -> TransformChain:
#         return TransformChain([tf.set_slice(axes) for tf in self])


class STTransform(Transform):
    """n-dimensional scale and translation (shift) class.

    Scaling is always applied before translation.

    An empty translation vector implies no translation, and an empty scale
    implies no scaling.

    Translation is broadcast to 0 in leading dimensions, so that, for example,
    a translation of [4, 18, 34] in 3D can be used as a translation of
    [0, 4, 18, 34] in 4D without modification.

    Translation is broadcast to 1 in leading dimensions, so that, for example,
    a scale of [4, 18, 34] in 3D can be used as a scale of
    [1, 4, 18, 34] in 4D without modification.
    """

    def __init__(self, scale=(1.0,), translate=(0.0,), name=None):
        super().__init__(name=name)
        self.scale = np.array(scale)
        self.translate = np.array(translate)

    def __call__(self, coords):
        coords = np.atleast_2d(coords)
        scale = np.concatenate(
            ([1.0] * (coords.shape[1] - len(self.scale)), self.scale)
        )
        translate = np.concatenate(
            ([0.0] * (coords.shape[1] - len(self.translate)), self.translate)
        )
        return np.squeeze(scale * coords + translate)

    @property
    def inverse(self):
        return STTransform(1 / self.scale, -self.translate)

    def set_slice(self, axes: Sequence[int]) -> STTransform:
        return STTransform(self.scale[axes], self.translate[axes])

    def set_pad(self, axes: Sequence[int]) -> STTransform:
        n = len(axes) + len(self.scale)
        not_axes = [i for i in range(n) if i not in axes]
        scale = np.ones(n)
        scale[not_axes] = self.scale
        translate = np.zeros(n)
        translate[not_axes] = self.translate
        return STTransform(scale, translate)

    def compose(self, transform: STTransform) -> STTransform:
        scale = self.scale * transform.scale
        translate = self.translate + self.scale * transform.translate
        return STTransform(scale, translate)


# class Translate(Transform):
#     """n-dimensional translation (shift) class.
#
#     An empty translation vector implies no translation.
#
#     Translation is broadcast to 0 in leading dimensions, so that, for example,
#     a translation of [4, 18, 34] in 3D can be used as a translation of
#     [0, 4, 18, 34] in 4D without modification.
#     """
#
#     def __init__(self, translate=(0.0,), name='translate'):
#         super().__init__(name=name)
#         self.translate = np.array(translate)
#
#     def __call__(self, coords):
#         coords = np.atleast_2d(coords)
#         translate = np.concatenate(
#             ([0.0] * (coords.shape[1] - len(self.translate)), self.translate)
#         )
#         return coords + translate
#
#     @property
#     def inverse(self):
#         return Translate(-self.translate)
#
#     def set_slice(self, axes: Sequence[int]) -> Translate:
#         return Translate(self.translate[axes])
#
#
# class Scale(Transform):
#     """n-dimensional scale class.
#
#     An empty scale class implies a scale of 1.
#     """
#
#     def __init__(self, scale=(1.0,), name='scale'):
#         super().__init__(name=name)
#         self.scale = np.array(scale)
#
#     def __call__(self, coords):
#         coords = np.atleast_2d(coords)
#         if coords.shape[1] > len(self.scale):
#             scale = np.concatenate(
#                 ([1.0] * (coords.shape[1] - len(self.scale)), self.scale)
#             )
#         return coords * scale
#
#     @property
#     def inverse(self):
#         return Scale(1 / self.scale)
#
#     def set_slice(self, axes: Sequence[int]) -> Scale:
#         return Scale(self.scale[axes])
