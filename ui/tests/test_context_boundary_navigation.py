"""Exercise the actual navigation methods without requiring a Qt display."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


def navigation_class():
    path = Path(__file__).parents[1] / "video_encoder_ui/application.py"
    tree = ast.parse(path.read_text())
    monitor = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MltFrameMonitor")
    names = {"selected_segment", "go_to_context_start", "go_to_context_end", "update_segment_navigation_actions"}
    methods = [node for node in monitor.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    isolated = ast.ClassDef(name="MltFrameMonitor", bases=[], keywords=[], body=methods, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[]))
    pixmaps = SimpleNamespace(**{name: name for name in ["SP_MediaSeekBackward", "SP_MediaSeekForward", "SP_MediaSkipBackward", "SP_MediaSkipForward"]})
    icon = Mock()
    icon.isNull.return_value = False
    namespace = {"QtWidgets": SimpleNamespace(QStyle=SimpleNamespace(StandardPixmap=pixmaps)),
                 "QtGui": SimpleNamespace(QIcon=SimpleNamespace(fromTheme=Mock(return_value=icon)))}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["MltFrameMonitor"], namespace


class ContextBoundaryNavigationTest(unittest.TestCase):
    def setUp(self):
        self.monitor_class, self.namespace = navigation_class()

    def monitor(self, selected=True, status="idle", source_id="source"):
        return SimpleNamespace(
            export_status=status, frame_source=SimpleNamespace(length=1000), source_id="source",
            segment_list=SimpleNamespace(currentRow=Mock(return_value=0 if selected else -1), selectedItems=Mock(return_value=[object()] if selected else [])),
            trim_session=SimpleNamespace(segments=[SimpleNamespace(source_id=source_id, start_frame=123, end_frame=456)]),
            boundary_start_button=Mock(), boundary_end_button=Mock(), show_frame=Mock(),
            update_marker_edit_controls=Mock(), style=Mock(return_value=Mock()),
        )

    def test_selected_segment_navigates_to_in_and_out(self):
        monitor = self.monitor()
        self.monitor_class.go_to_context_start(monitor)
        self.monitor_class.go_to_context_end(monitor)
        self.assertEqual([call.args[0] for call in monitor.show_frame.call_args_list], [123, 456])

    def test_no_selection_navigates_to_source_extremities(self):
        monitor = self.monitor(selected=False)
        self.monitor_class.go_to_context_start(monitor)
        self.monitor_class.go_to_context_end(monitor)
        self.assertEqual([call.args[0] for call in monitor.show_frame.call_args_list], [0, 999])

    def test_other_source_segment_is_not_used(self):
        monitor = self.monitor(source_id="other")
        self.monitor_class.go_to_context_start(monitor)
        monitor.show_frame.assert_called_once_with(0)

    def test_deselected_current_row_uses_source_boundaries(self):
        monitor = self.monitor(selected=False)
        monitor.segment_list.currentRow.return_value = 0
        self.monitor_class.go_to_context_end(monitor)
        monitor.show_frame.assert_called_once_with(999)

    def test_buttons_labels_and_icons_follow_context(self):
        for selected, labels, icons in [(True, ("IN", "OUT"), ("go-previous", "go-next")),
                                        (False, ("Début source", "Fin source"), ("media-skip-backward", "media-skip-forward"))]:
            with self.subTest(selected=selected):
                monitor = self.monitor(selected=selected)
                self.namespace["QtGui"].QIcon.fromTheme.reset_mock()
                self.monitor_class.update_segment_navigation_actions(monitor)
                for button, label in zip((monitor.boundary_start_button, monitor.boundary_end_button), labels):
                    button.setText.assert_called_once_with(label)
                    button.setEnabled.assert_called_once_with(True)
                self.assertEqual([call.args[0] for call in self.namespace["QtGui"].QIcon.fromTheme.call_args_list], list(icons))

    def test_busy_buttons_are_disabled_and_clicks_do_nothing(self):
        for status in ("running", "preflight", "confirming", "proposing"):
            monitor = self.monitor(status=status)
            self.monitor_class.update_segment_navigation_actions(monitor)
            monitor.boundary_start_button.setEnabled.assert_called_once_with(False)
            monitor.boundary_end_button.setEnabled.assert_called_once_with(False)
            self.monitor_class.go_to_context_start(monitor)
            self.monitor_class.go_to_context_end(monitor)
            monitor.show_frame.assert_not_called()

    def test_falls_back_to_standard_icons_without_theme(self):
        self.namespace["QtGui"].QIcon.fromTheme.return_value.isNull.return_value = True
        monitor = self.monitor(selected=False)
        self.monitor_class.update_segment_navigation_actions(monitor)
        self.assertEqual([call.args[0] for call in monitor.style.return_value.standardIcon.call_args_list],
                         ["SP_MediaSkipBackward", "SP_MediaSkipForward"])


if __name__ == "__main__":
    unittest.main()
