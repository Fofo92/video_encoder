from PySide6 import QtCore, QtGui, QtWidgets


class VideoLabel(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()

        self.source_pixmap = None

        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.setMinimumSize(640, 360)
        self.setStyleSheet(
            "background: black;"
        )

    def set_image(self, image):
        self.source_pixmap = (
            QtGui.QPixmap.fromImage(image)
        )
        self.update_pixmap()

    def update_pixmap(self):
        if self.source_pixmap is None:
            return

        scaled = self.source_pixmap.scaled(
            self.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )

        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_pixmap()


class ClickableSlider(QtWidgets.QSlider):
    position_requested = QtCore.Signal(int)

    def __init__(self, orientation):
        super().__init__(orientation)
        self.jump_drag_active = False

    def position_from_event(self, event):
        return QtWidgets.QStyle.sliderValueFromPosition(
            self.minimum(),
            self.maximum(),
            round(event.position().x()),
            self.width(),
            self.invertedAppearance()
        )

    def mousePressEvent(self, event):
        if (
            event.button()
            != QtCore.Qt.MouseButton.LeftButton
        ):
            super().mousePressEvent(event)
            return

        style_option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(style_option)

        handle = self.style().subControlRect(
            QtWidgets.QStyle.ComplexControl.CC_Slider,
            style_option,
            QtWidgets.QStyle.SubControl.SC_SliderHandle,
            self
        )

        if handle.contains(event.position().toPoint()):
            super().mousePressEvent(event)
            return

        position = self.position_from_event(event)

        self.jump_drag_active = True
        self.setSliderDown(True)
        self.setSliderPosition(position)
        self.position_requested.emit(position)

        event.accept()

    def mouseMoveEvent(self, event):
        if not self.jump_drag_active:
            super().mouseMoveEvent(event)
            return

        if not (
            event.buttons()
            & QtCore.Qt.MouseButton.LeftButton
        ):
            return

        position = self.position_from_event(event)

        self.setSliderPosition(position)
        self.sliderMoved.emit(position)

        event.accept()

    def mouseReleaseEvent(self, event):
        if (
            not self.jump_drag_active
            or event.button()
            != QtCore.Qt.MouseButton.LeftButton
        ):
            super().mouseReleaseEvent(event)
            return

        position = self.position_from_event(event)

        self.setSliderPosition(position)
        self.sliderMoved.emit(position)

        self.jump_drag_active = False
        self.setSliderDown(False)

        event.accept()

    def wheelEvent(self, event):
        event.ignore()
