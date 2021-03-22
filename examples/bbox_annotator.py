import napari
from magicgui.widgets import ComboBox, Container
import numpy as np


# set up the annotation values and text display properties
box_annotations = ['person', 'sky', 'camera']
text_property = 'box_label'
text_color = 'green'
text_size = 30

# create the GUI for selecting the values
def create_label_menu(shapes_layer, label_property, labels):
    """Create a label menu widget that can be added to the napari viewer dock

    Parameters:
    -----------
    shapes_layer : napari.layers.Shapes
        a napari shapes layer
    label_property : str
        the name of the shapes property to use the displayed text
    labels : List[str]
        list of the possible text labels values.

    Returns:
    --------
    label_widget : magicgui.widgets.Container
        the container widget with the label combobox
    """
    # Create the label selection menu
    label_menu = ComboBox(label='text label', choices=labels)
    label_widget = Container(widgets=[label_menu])

    def update_label_menu(event):
        """This is a callback function that updates the label menu when
        the current properties of the Shapes layer change
        """
        new_label = str(shapes_layer.current_properties[label_property][0])
        if new_label != label_menu.value:
            label_menu.value = new_label

    shapes_layer.events.current_properties.connect(update_label_menu)

    def label_changed(event):
        """This is acallback that update the current properties on the Shapes layer
        when the label menu selection changes
        """
        selected_label = event.value
        current_properties = shapes_layer.current_properties
        current_properties[label_property] = np.asarray([selected_label])
        shapes_layer.current_properties = current_properties

    label_menu.changed.connect(label_changed)

    return label_widget


with napari.gui_qt():
    viewer = napari.view_image(np.random.random((5, 200, 200)))

    text_kwargs = {
        'text': text_property,
        'size': text_size,
        'color': text_color
    }
    shapes = viewer.add_shapes(
        face_color='black',
        properties={text_property: box_annotations},
        text=text_kwargs,
        ndim=3
    )

    # create the label section gui
    label_widget = create_label_menu(
        shapes_layer=shapes,
        label_property=text_property,
        labels=box_annotations
    )
    # add the label selection gui to the viewer as a dock widget
    viewer.window.add_dock_widget(label_widget, area='right')

    # set the shapes layer mode to adding rectangles
    shapes.mode = 'add_rectangle'
