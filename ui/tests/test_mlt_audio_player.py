import unittest
from unittest.mock import Mock

try:
    import mlt7
except ModuleNotFoundError:
    mlt7 = None

if mlt7 is not None:
    from video_encoder_ui.mlt_audio_player import (
        MltAudioPlayer,
    )

@unittest.skipIf(
    mlt7 is None,
    "MLT Python bindings are unavailable",
)

class MltAudioPlayerTest(unittest.TestCase):
    def build_player(
        self,
        producer_position=15899,
        consumer_position=15888,
        playback_start_position=15884,
    ):
        player = MltAudioPlayer.__new__(
            MltAudioPlayer
        )

        player.producer = Mock()
        player.producer.position.return_value = (
            producer_position
        )

        player.consumer = Mock()
        player.consumer.position.return_value = (
            consumer_position
        )

        player.playback_start_position = (
            playback_start_position
        )
        player.is_playing = True

        return player

    def test_reports_the_audio_consumer_position(self):
        player = self.build_player()

        self.assertEqual(
            player.position,
            15888,
        )

    def test_does_not_report_a_position_before_playback_start(
        self
    ):
        player = self.build_player(
            consumer_position=0,
        )

        self.assertEqual(
            player.position,
            15884,
        )

    def test_stops_at_the_audio_consumer_position(self):
        player = self.build_player()

        position = player.stop()

        self.assertEqual(position, 15888)
        player.producer.set_speed.assert_called_once_with(
            0
        )
        player.consumer.stop.assert_called_once_with()

    def test_records_the_playback_start_position(self):
        player = self.build_player(
            playback_start_position=12000,
        )
        player.is_playing = False

        player.start(15884)

        self.assertEqual(
            player.playback_start_position,
            15884,
        )

    def test_ignores_a_stale_consumer_position(self):
        player = self.build_player(
            producer_position=15899,
            consumer_position=20000,
            playback_start_position=15884,
        )

        self.assertEqual(
            player.position,
            15884,
        )

if __name__ == "__main__":
    unittest.main()
