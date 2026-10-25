import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor, SHUTTLE_SPEED_BY_POSITION
    from video_encoder_ui.window_placement import place_initial_window
    from video_encoder_ui.start_window import StartWindow


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class ApplicationWorkspaceLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_geometry_uses_the_upper_left_third_and_half_height(self):
        window = QtWidgets.QWidget()
        place_initial_window(window)
        area = window.screen().availableGeometry()
        self.assertEqual(window.width(), area.width() // 3)
        self.assertEqual(window.height(), area.height() // 2)
        self.assertEqual(window.pos(), area.topLeft())
        window.close()

    def test_home_keeps_queue_controls_and_menus(self):
        window = StartWindow()
        self.assertEqual(window.tabs.count(), 8)
        self.assertEqual([action.text() for action in window.menu_bar.actions()],
                         ["&Sources", "&Projets", "&Montage"])
        self.assertFalse(hasattr(window, "queue_button"))
        window.set_running(True)
        self.assertTrue(window.stop_button.isEnabled())
        self.assertFalse(window.start_button.isEnabled())
        self.assertFalse(window.start_button.property("home_action").isEnabled())
        window.set_running(False)
        window.close()

    def test_editor_reserves_timeline_and_removes_redundant_controls(self):
        source = SimpleNamespace(frames_per_second=25, length=10000, close=Mock())
        with patch("video_encoder_ui.application.MltFrameSource", return_value=source), \
                patch("video_encoder_ui.application.MltAudioPlayer"):
            window = MltFrameMonitor("/source.m2t")
            window.show()
            self.app.processEvents()
            self.assertTrue(window.segment_list.isVisible())
            self.assertFalse(hasattr(window, "previous_button"))
            self.assertFalse(hasattr(window, "next_button"))
            self.assertFalse(window.nudge_marker_selector.isVisible())
            self.assertFalse(window.nudge_backward_button.isVisible())
            self.assertEqual([action.text() for action in window.menuBar().actions()],
                             ["&Sources", "&Projets", "&Montage"])
            toolbar = window.findChild(QtWidgets.QToolBar, "main_toolbar")
            self.assertNotIn(window.show_export_queue_action, toolbar.actions())
            buttons = [window.backward_button, window.pause_button,
                       window.forward_button, window.boundary_start_button,
                       window.boundary_end_button, window.in_button,
                       window.out_button, window.add_segment_button]
            positions = [button.mapTo(window, button.rect().center()).y()
                         for button in buttons]
            self.assertLessEqual(max(positions) - min(positions), 1)
            self.assertTrue(all(button.isVisible() for button in buttons))
            window.shutdown()
            window.close()

    def test_home_can_close_when_idle_but_not_during_queue_processing(self):
        window = StartWindow()
        window.show()
        self.app.processEvents()
        self.assertTrue(window.refresh_timer.isActive())
        window.set_running(True)
        with patch("video_encoder_ui.start_window.QtWidgets.QMessageBox.information"):
            self.assertFalse(window.close())
        self.assertTrue(window.isVisible())
        window.set_running(False)
        self.assertTrue(window.close())
        self.assertFalse(window.isVisible())
        self.assertFalse(window.refresh_timer.isActive())

    def test_only_mouse_acceleration_changes_and_shuttle_keeps_original_speeds(self):
        self.assertEqual(SHUTTLE_SPEED_BY_POSITION,
                         {1: 1.0, 2: 2.0, 3: 3.0, 4: 5.0, 5: 10.0, 6: 20.0, 7: 50.0})
        monitor = SimpleNamespace(previous_wheel_event_timestamp=None)
        steps = [MltFrameMonitor.coarse_wheel_step(monitor, timestamp)
                 for timestamp in (1000, 1001, 1050, 1130, 1310, 1400)]
        self.assertTrue(all(1 <= step <= 3 for step in steps))
