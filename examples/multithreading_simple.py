from qtpy.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel
import time
from napari._qt.threading import thread_worker


@thread_worker
def long_running_function():
    """Just a long running function, most like viewer.update."""
    time.sleep(2)  # long function
    return 'finished!'


def create_widget():
    widget = QWidget()
    layout = QHBoxLayout()
    widget.setLayout(layout)
    widget.status = QLabel('ready...')
    layout.addWidget(widget.status)
    widget.show()
    return widget


if __name__ == "__main__":
    app = QApplication([])
    wdg = create_widget()

    # call decorated function
    worker = long_running_function(_start_thread=False)

    # Note that signals/slots are best connected *before* starting the worker.
    worker.started.connect(lambda: wdg.status.setText("worker is running..."))
    worker.returned.connect(
        lambda x: wdg.status.setText(f"worker returned {x}")
    )
    worker.start()

    # # The above syntax is equivalent to:
    # worker = long_running_function(
    #     connections={
    #         'started': lambda: wdg.status.setText("worker is running..."),
    #         'returned': lambda x: wdg.status.setText(f"worker returned {x!r}"),
    #     }
    # )

    app.exec_()
