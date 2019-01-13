from PyQt5.QtWidgets import QHBoxLayout, QWidget
from PyQt5.QtCore import QSize

from ._range_slider import QVRangeSlider


class QtControlBars(QWidget):
    def __init__(self, control_bars):
        super().__init__()

        self.control_bars = control_bars

        layout = QHBoxLayout()

        # Clim Slider
        self.climSlider = QVRangeSlider(slider_range=[0, 1, 0.0001],
                                        values=[0, 1], parent=self)
        self.climSlider.setEmitWhileMoving(True)
        self.climSlider.collapsable = False
        layout.addWidget(self.climSlider)

        self.setLayout(layout)
        self.setMouseTracking(True)
        self.setMinimumSize(QSize(40, 40))

        self.climSlider.rangeChanged.connect(self.clim_slider_changed)
        self.control_bars.events.update_slider.connect(self.update)

    def update(self, event):
        if event.enabled:
            self.climSlider.setEnabled(True)
            self.climSlider.setValues(event.values)
        else:
            self.climSlider.setEnabled(False)

    def clim_slider_changed(self, slidermin, slidermax):
        self.control_bars.values = (slidermin, slidermax)
        msg = None
        for layer in self.control_bars.viewer.layers:
            if hasattr(layer, 'visual') and layer.selected:
                valmin, valmax = layer._clim_range
                cmin = valmin+self.control_bars.values[0]*(valmax-valmin)
                cmax = valmin+self.control_bars.values[1]*(valmax-valmin)
                layer.clim = [cmin, cmax]
                msg = '(%.3f, %.3f)' % (cmin, cmax)
        if msg is None:
            msg = 'Ready'

        self.control_bars.viewer.status = msg

    def mouseMoveEvent(self, event):
        for layer in self.control_bars.viewer.layers[::-1]:
            if hasattr(layer, 'visual') and layer.selected:
                cmin, cmax = layer.clim
                msg = '(%.3f, %.3f)' % (cmin, cmax)
                self.control_bars.viewer.status = msg
                break
        else:
            self.control_bars.viewer.status = 'Ready'
