from napari.components import Dims
from napari.components._dims.dims import DimsMode


def test_range():
    """
    Tests mode initialisation:
    """
    dims = Dims(2)


    dims.set_range(3, (0,1000,0.1))

    print(dims.range)

    assert dims.ndims == 4

    assert dims.range[0] == (None,None,None)
    assert dims.range[1] == (None,None,None)
    assert dims.range[2] == (None,None,None)
    assert dims.range[3] == (0,1000,0.1)

def test_mode():
    """
    Tests mode initialisation:
    """
    dims = Dims(2)

    dims.set_mode(3, DimsMode.Interval)

    print(dims.mode)

    assert dims.ndims == 4

    assert dims.mode[0] is None
    assert dims.mode[1] is None
    assert dims.mode[2] is None
    assert dims.mode[3] == DimsMode.Interval


def test_point():
    """
    Tests point initialisation
    """
    dims = Dims(2)

    dims.set_point(3, 2.5)

    print(dims.point)

    assert dims.ndims == 4

    assert dims.point[0] == 0.0
    assert dims.point[1] == 0.0
    assert dims.point[2] == 0.0
    assert dims.point[3] == 2.5


def test_interval():
    """
    Tests interval initialisation
    """
    dims = Dims(2)

    dims.set_interval(3, (0, 10))

    print(dims.interval)

    assert dims.ndims == 4

    assert dims.interval[0] == None
    assert dims.interval[1] == None
    assert dims.interval[2] == None
    assert dims.interval[3] == (0, 10)


def test_display():
    """
    Tests display initialisation
    """
    dims = Dims(2)

    dims.set_display(0, False)
    dims.set_display(1, False)
    dims.set_display(2, True)
    dims.set_display(3, True)

    print(dims.interval)

    assert dims.ndims == 4

    assert not dims.display[0]
    assert not dims.display[1]
    assert dims.display[2]
    assert dims.display[3]

    assert (dims.displayed_dimensions == [2,3]).all()




def test_slice_and_project():
    dims = Dims(2)

    dims.set_mode(0, DimsMode.Point)
    dims.set_mode(1, DimsMode.Point)
    dims.set_mode(2, DimsMode.Interval)
    dims.set_mode(3, DimsMode.Interval)

    dims.set_display(1, True)
    dims.set_display(3, True)

    dims.set_point(0, 1.234)
    dims.set_point(3, 2.5)
    dims.set_interval(2, (1,2))
    dims.set_interval(3, (3,6))

    print(dims.slice_and_project)

    (sliceit, projectit) = dims.slice_and_project

    assert sliceit[0] == 1
    assert sliceit[1] == None
    assert sliceit[2] == slice(1, 2)
    assert sliceit[3] == slice(3, 6)

    assert projectit[0] == False
    assert projectit[1] == False
    assert projectit[2] == True
    assert projectit[3] == False

def test_add_remove_dims():
    dims = Dims(2)
    assert dims.ndims == 2

    dims.ndims = 10
    assert dims.ndims == 10

    dims.ndims = 5
    assert dims.ndims == 5

    dims.set_mode(5, DimsMode.Point)
    assert dims.ndims == 6

_axis_change_counter =0
_ndims_change_counter =0

def test_listeners():
    global _axis_change_counter
    global _ndims_change_counter

    dims = Dims(2)

    def axischange(event):
        print("Change in axis %d " % event.axis)
        global _axis_change_counter

        _axis_change_counter=_axis_change_counter+1

    dims.events.axis.connect(axischange)

    def ndimschange(event):
        print("Change in number of dimensions %d " % event.source.ndims)
        global _ndims_change_counter

        _ndims_change_counter=_ndims_change_counter+1

    dims.events.ndims.connect(ndimschange)

    assert _axis_change_counter == 0
    assert _ndims_change_counter == 0

    dims.ndims = 10
    print("acc=%d ncc=%d" % (_axis_change_counter, _ndims_change_counter))
    assert _ndims_change_counter==1

    dims.ndims = 5
    print("acc=%d ncc=%d" % (_axis_change_counter, _ndims_change_counter))
    assert _ndims_change_counter == 2

    dims.set_point(0,0)
    print("acc=%d ncc=%d" % (_axis_change_counter, _ndims_change_counter))
    assert _axis_change_counter == 9
