import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from video_encoder_ui.application import MltFrameMonitor
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    MltFrameMonitor = None

from video_encoder_ui.trim_session import TrimSession, SourceReference


@unittest.skipIf(MltFrameMonitor is None, 'MLT or Qt unavailable')
class ApplicationRepeatedSequencesTest(unittest.TestCase):
    def monitor(self):
        session = TrimSession()
        session.add_source(SourceReference('source', Path('/source.m2t')))
        return SimpleNamespace(export_status='idle', trim_session=session, source_id='source',
                               source_path=Path('/source.m2t'), in_position=100, out_position=1900,
                               frame_source=SimpleNamespace(length=2000, frame_rate_numerator=25,
                                                            frame_rate_denominator=1),
                               set_transport_position=Mock(), export_status_changed=Mock(),
                               ad_trim_proposal_succeeded=Mock(), show_frame=Mock(), current_position=123)

    def test_cancel_keeps_existing_montage_and_restores_preview(self):
        monitor = self.monitor()
        with patch('video_encoder_ui.repeated_sequence_dialog.RepeatedSequenceDialog') as dialog:
            dialog.return_value.exec.return_value = QtWidgets.QDialog.DialogCode.Rejected
            MltFrameMonitor.review_repeated_sequences(monitor)
        monitor.ad_trim_proposal_succeeded.assert_not_called()
        monitor.set_transport_position.assert_called_once_with(0)
        monitor.show_frame.assert_called_once_with(123)
        self.assertEqual(monitor.export_status_changed.call_args.args, ('idle',))

    def test_accept_uses_existing_proposal_loading_and_never_enqueues(self):
        monitor = self.monitor()
        with patch('video_encoder_ui.repeated_sequence_dialog.RepeatedSequenceDialog') as dialog:
            dialog.return_value.exec.return_value = QtWidgets.QDialog.DialogCode.Accepted
            session = dialog.return_value.session
            MltFrameMonitor.review_repeated_sequences(monitor)
        monitor.ad_trim_proposal_succeeded.assert_called_once_with({'session': session})

    def test_busy_editor_does_not_open_a_second_task(self):
        monitor = self.monitor()
        monitor.export_status = 'running'
        with patch('video_encoder_ui.repeated_sequence_dialog.RepeatedSequenceDialog') as dialog:
            MltFrameMonitor.review_repeated_sequences(monitor)
        dialog.assert_not_called()
