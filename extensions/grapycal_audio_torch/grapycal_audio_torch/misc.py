import time
from grapycal import Node
from grapycal.extension_api.trait import ClockTrait
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.port import InputPort
import torch


class PianoRollPlayerNode(Node):
    category = "audio"

    def define_traits(self):
        return ClockTrait(self.update, 0.01)

    def build_node(self):
        super().build_node()
        self.label_topic.set("Piano Roll Player")
        self.pianoroll_port = self.add_in_port("pianoroll")
        self.note_on = self.add_out_port("note on")
        self.note_off = self.add_out_port("note off")
        self.bpm = self.add_in_port(
            "bpm", control_type=SliderControl, value=120, min=1, max=300
        )

    def init_node(self):
        self.pianoroll: torch.Tensor | None = None
        self.start_time = 0
        self.last_update_frame = 0

    def port_activated(self, port: InputPort):
        if port is self.pianoroll_port:
            self.pianoroll = port.get()
            self.start_time = time.time()
            self.last_update_frame = -1
            self.playing_pitches = set()

    def update(self):
        if self.pianoroll is None:
            return

        fps = self.bpm.get() / 60 * 8  # frame size is 1/8 beat

        current_frame = int((time.time() - self.start_time) * fps)
        if current_frame > self.pianoroll.shape[0]:
            self.pianoroll = None
            return

        if current_frame == self.last_update_frame:
            return

        if (
            current_frame % (8 * 4) == 1
        ):  # release pedal on every bar's first frame so it sounds continuous
            for pitch in self.playing_pitches:
                if self.pianoroll[current_frame, pitch] < 1e-8:
                    self.note_off.push({"pitch": pitch + 21})

        for frame in range(self.last_update_frame, current_frame):
            for pitch in range(88):
                if self.pianoroll[frame, pitch] > 0:
                    self.note_on.push(
                        {"pitch": pitch + 21, "velocity": self.pianoroll[frame, pitch]}
                    )
                    self.playing_pitches.add(pitch)

        self.last_update_frame = current_frame
