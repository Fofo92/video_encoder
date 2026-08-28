from evdev import InputDevice, ecodes
from PySide6 import QtCore


class ShuttleXpressReader(QtCore.QObject):
    jogged = QtCore.Signal(int)
    shuttle_changed = QtCore.Signal(int)

    def __init__(self, device_path):
        super().__init__()

        self.device = InputDevice(device_path)

        try:
            self.device.grab()
        except OSError:
            self.device.close()
            self.device = None
            raise

        self.previous_dial = None
        self.shuttle_position = 0

        self.report_contains_dial = False
        self.report_contains_shuttle = False
        self.pending_shuttle_position = 0

        self.notifier = QtCore.QSocketNotifier(
            self.device.fd,
            QtCore.QSocketNotifier.Type.Read,
            self
        )
        self.notifier.activated.connect(
            self.read_available_events
        )

    def read_available_events(self, *_):
        while True:
            event = self.device.read_one()

            if event is None:
                break

            self.process_event(event)

    def process_event(self, event):
        if event.type == ecodes.EV_REL:
            self.process_relative_event(event)
            return

        if (
            event.type == ecodes.EV_SYN
            and event.code == ecodes.SYN_REPORT
        ):
            self.finish_report()

    def process_relative_event(self, event):
        if event.code == ecodes.REL_DIAL:
            self.report_contains_dial = True
            self.process_dial(event.value)
            return

        if event.code == ecodes.REL_WHEEL:
            self.report_contains_shuttle = True
            self.pending_shuttle_position = event.value

    def process_dial(self, current_dial):
        if self.previous_dial is None:
            self.previous_dial = current_dial
            return

        delta = (
            current_dial
            - self.previous_dial
            + 128
        ) % 256 - 128

        self.previous_dial = current_dial

        if delta:
            self.jogged.emit(delta)

    def finish_report(self):
        if self.report_contains_shuttle:
            new_position = self.pending_shuttle_position
        elif self.report_contains_dial:
            new_position = 0
        else:
            new_position = self.shuttle_position

        if new_position != self.shuttle_position:
            self.shuttle_position = new_position
            self.shuttle_changed.emit(new_position)

        self.report_contains_dial = False
        self.report_contains_shuttle = False

    def close(self):
        if self.device is None:
            return

        self.notifier.setEnabled(False)
        self.device.ungrab()
        self.device.close()
        self.device = None
