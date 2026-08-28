import mlt7 as mlt


class MltAudioPlayer:
    def __init__(self, source_path):
        self.profile = mlt.Profile()
        self.producer = mlt.Producer(
            self.profile,
            str(source_path)
        )

        if not self.producer.is_valid():
            raise RuntimeError(
                f"Producteur audio MLT invalide : "
                f"{source_path}"
            )

        self.profile.from_producer(
            self.producer
        )

        self.consumer = mlt.Consumer(
            self.profile,
            "sdl2_audio"
        )

        if not self.consumer.is_valid():
            raise RuntimeError(
                "Consommateur MLT sdl2_audio invalide"
            )

        self.consumer.set(
            "terminate_on_pause",
            0
        )
        self.consumer.connect(
            self.producer
        )

        self.is_playing = False

    @property
    def position(self):
        return self.producer.position()

    def start(self, position):
        if self.is_playing:
            return

        self.producer.set_speed(0)
        self.producer.seek(position)

        self.consumer.start()
        self.producer.set_speed(1.0)
        self.is_playing = True

    def stop(self):
        if not self.is_playing:
            return None

        position = self.producer.position()

        self.producer.set_speed(0)
        self.consumer.stop()
        self.is_playing = False

        return position

    def close(self):
        if self.consumer is None:
            return

        self.stop()

        self.consumer = None
        self.producer = None
        self.profile = None
