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
        self.in_position = None
        self.out_position = None
        self.setMinimumHeight(34)


    def set_markers(self, in_position, out_position):
        self.in_position = in_position
        self.out_position = out_position
        self.update()

    def pixel_for_value(self, value):
        if self.maximum() == self.minimum():
            return 0

        return QtWidgets.QStyle.sliderPositionFromValue(
            self.minimum(),
            self.maximum(),
            value,
            self.width() - 1,
            self.invertedAppearance()
        )

    def paintEvent(self, event):
        super().paintEvent(event)

        if (
            self.in_position is None
            and self.out_position is None
        ):
            return

        style_option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(style_option)

        groove = self.style().subControlRect(
            QtWidgets.QStyle.ComplexControl.CC_Slider,
            style_option,
            QtWidgets.QStyle.SubControl.SC_SliderGroove,
            self
        )

        painter = QtGui.QPainter(self)
        painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing
        )

        if (
            self.in_position is not None
            and self.out_position is not None
        ):
            in_x = self.pixel_for_value(
                self.in_position
            )
            out_x = self.pixel_for_value(
                self.out_position
            )

            selection_color = QtGui.QColor(
                46,
                160,
                67,
                150
            )

            selection_rectangle = QtCore.QRectF(
                min(in_x, out_x),
                groove.center().y() - 4,
                max(2, abs(out_x - in_x)),
                8
            )

            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(selection_color)
            painter.drawRoundedRect(
                selection_rectangle,
                3,
                3
            )

        def draw_marker(position, color):
            if position is None:
                return

            marker_x = self.pixel_for_value(position)
            marker_tip_y = groove.top()
            marker_base_y = marker_tip_y - 12

            triangle = QtGui.QPolygonF(
                [
                    QtCore.QPointF(
                        marker_x - 6,
                        marker_base_y
                    ),
                    QtCore.QPointF(
                        marker_x + 6,
                        marker_base_y
                    ),
                    QtCore.QPointF(
                        marker_x,
                        marker_tip_y
                    )
                ]
            )

            painter.setPen(
                QtGui.QPen(color, 1)
            )
            painter.setBrush(color)
            painter.drawPolygon(triangle)
        marker_color = QtGui.QColor(
            210,
            70,
            60
        )

        draw_marker(
            self.in_position,
            marker_color
        )
        draw_marker(
            self.out_position,
            marker_color
        )

        handle_option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(handle_option)
        handle_option.subControls = (
            QtWidgets.QStyle.SubControl.SC_SliderHandle
        )

        self.style().drawComplexControl(
            QtWidgets.QStyle.ComplexControl.CC_Slider,
            handle_option,
            painter,
            self
        )

        painter.end()

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
