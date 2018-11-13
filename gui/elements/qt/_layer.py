from PyQt5.QtWidgets import QSlider, QLineEdit, QHBoxLayout, QFrame, QVBoxLayout, QCheckBox, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from os.path import dirname, join, realpath
import weakref

dir_path = dirname(realpath(__file__))
path_on = join(dir_path,'icons','eye_on.png')
path_off = join(dir_path,'icons','eye_off.png')

class QtLayer(QFrame):
    def __init__(self, layer):
        super().__init__()
        self.layer = weakref.proxy(layer)
        self.unselectedStyleSheet = "QFrame {border: 3px solid lightGray; background-color:lightGray; border-radius: 3px;}"
        self.selectedStyleSheet = "QFrame {border: 3px solid rgb(71,143,205); background-color:lightGray; border-radius: 3px;}"

        layout = QHBoxLayout()

        cb = QCheckBox(self)
        cb.setStyleSheet("QCheckBox::indicator {width: 18px; height: 18px;}"
                         #{}"QCheckBox::indicator:unchecked {image: url(" + path_off + ");}"
                         "QCheckBox::indicator:checked {image: url(" + path_on + ");}")
        cb.setToolTip('Layer visibility')
        cb.setChecked(self.layer.visible)
        cb.stateChanged.connect(lambda state=cb: self.changeVisible(state))
        layout.addWidget(cb)

        layout.insertSpacing(1, 5)

        sld = QSlider(Qt.Horizontal, self)
        sld.setToolTip('Layer opacity')
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setInvertedAppearance(True)
        sld.setFixedWidth(75)
        sld.setMinimum(0)
        sld.setMaximum(100)
        sld.setSingleStep(1)
        sld.setValue(self.layer.opacity*100)
        sld.valueChanged[int].connect(lambda value=sld: self.changeOpacity(value))
        layout.addWidget(sld)

        textbox = QLineEdit(self)
        textbox.setStyleSheet('background-color:lightGray; border:none')
        textbox.setText(layer.name)
        textbox.setToolTip('Layer name')
        textbox.setFixedWidth(80)
        textbox.editingFinished.connect(lambda text=textbox: self.changeText(text))
        layout.addWidget(textbox)

        self.setLayout(layout)
        self.setFixedHeight(55)
        self.setStyleSheet(self.selectedStyleSheet)
        self.layer.selected = True

#        self.setDragEnabled(True)
        #self.setAcceptDrops(True)

    def changeOpacity(self, value):
        self.layer.opacity = value/100

    def changeVisible(self, state):
        if state == Qt.Checked:
            self.layer.visible = True
        else:
            self.layer.visible = False

    def changeText(self, text):
        self.layer.name = text.text()

    def mouseReleaseEvent(self, event):
        modifiers = event.modifiers()
        if modifiers != Qt.ShiftModifier:
            self.unselectAll()
        self.layer.selected = True
        self.setStyleSheet(self.selectedStyleSheet)

    def unselectAll(self):
        if self.layer.viewer is not None:
            for layer in self.layer.viewer.layers:
                if layer.selected:
                    layer._qt.setStyleSheet(self.unselectedStyleSheet)
                    layer.selected = False

    def dragMoveEvent(self, event):
        print('drag leave!!!')
        self.layer.name = 'asdfa'

    def dropEvent(self, event):
        print('drop event!!!')
        self.layer.name = 'qqqq'

    def update(self):
        print('hello!!!')
        #print(self.layout().children())
        #sld.setValue(self.layer.opacity*100)
        #cb.setChecked(self.layer.visible)
