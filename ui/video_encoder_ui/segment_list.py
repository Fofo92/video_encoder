from PySide6 import QtCore, QtGui, QtWidgets


class SegmentListWidget(QtWidgets.QTableWidget):
    segment_selected = QtCore.Signal(int)
    delete_requested = QtCore.Signal(int)

    HEADERS = (
        "Segment",
        "Source",
        "IN",
        "OUT",
        "Durée",
        ""
    )

    def __init__(self):
        super().__init__(0, len(self.HEADERS))

        self.setHorizontalHeaderLabels(
            self.HEADERS
        )
        self.verticalHeader().setVisible(False)

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setAlternatingRowColors(True)
        self.setMaximumHeight(150)

        header = self.horizontalHeader()

        header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            4,
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            5,
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )
        self.setColumnWidth(5, 36)

        self.cellClicked.connect(
            self.emit_selected_segment
        )

    def set_rows(
        self,
        rows,
        source_colors=None
    ):
        source_colors = source_colors or {}

        self.blockSignals(True)

        try:
            self.clearContents()
            self.setRowCount(len(rows))

            for row_index, values in enumerate(rows):
                for column_index, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(
                        str(value)
                    )

                    if column_index == 1:
                        color = source_colors.get(value)

                        if color:
                            item.setForeground(
                                QtGui.QColor(color)
                            )
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)

                    self.setItem(
                        row_index,
                        column_index,
                        item
                    )

                delete_button = QtWidgets.QToolButton()
                delete_button.setIcon(
                    self.style().standardIcon(
                        QtWidgets.QStyle.StandardPixmap.SP_TrashIcon
                    )
                )
                delete_button.setToolTip(
                    f"Supprimer le segment {row_index + 1}"
                )
                delete_button.setAccessibleName(
                    f"Supprimer le segment {row_index + 1}"
                )
                delete_button.setAutoRaise(True)
                delete_button.clicked.connect(
                    lambda _checked=False, index=row_index: (
                        self.delete_requested.emit(index)
                    )
                )

                self.setCellWidget(
                    row_index,
                    5,
                    delete_button
                )
        finally:
            self.blockSignals(False)

    def emit_selected_segment(
        self,
        row,
        _column
    ):
        self.segment_selected.emit(row)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        event.accept()

    def keyPressEvent(self, event):
        if (
            event.key()
            == QtCore.Qt.Key.Key_Delete
        ):
            row = self.currentRow()

            if row >= 0:
                self.delete_requested.emit(row)
                event.accept()
                return

        super().keyPressEvent(event)
