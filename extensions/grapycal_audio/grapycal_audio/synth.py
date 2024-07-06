from typing import TYPE_CHECKING

from grapycal.extension_api.trait import ClockTrait
from grapycal.sobjects.controls.optionControl import OptionControl
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import background_task
from grapycal.sobjects.port import InputPort
from grapycal.utils.resource import get_resource
from grapycal_audio.utils import Instrument, midi2Freq


if TYPE_CHECKING:
    from grapycal_audio import GrapycalAudio

from grapycal import Node

import numpy as np
import math


class SynthNode(Node):
    ext: "GrapycalAudio"
    category = "audio/synth"
    need_mod_t = True
    need_pitch_port = True

    def define_traits(self):
        return [
            ClockTrait(self.tick, 0.01, pass_time=True),
        ]

    def build_node(self):
        if self.need_pitch_port:
            self.pitch_port = self.add_in_port("pitch")
        self.out_port = self.add_out_port("samples")

    def init_node(self):
        self.sample_t = 0
        self.timeout = 0.5  # seconds

        if self.need_pitch_port:
            self.pitch = 60
            self.freq = midi2Freq(self.pitch)
            self.t_mod = 1000 / self.freq if self.need_mod_t else 100000000
        else:
            self.t_mod = 100000000000000000000000

    def port_activated(self, port: InputPort):
        super().port_activated(port)
        if self.need_pitch_port and port == self.pitch_port:
            self.pitch = self.pitch_port.get()
            self.freq = midi2Freq(self.pitch)
            self.t_mod = 1000 / self.freq if self.need_mod_t else 100000000

    def tick(self, t: float):
        if len(self.out_port.edges) == 0:
            return
        if (
            t - self.sample_t > self.timeout
        ):  # Too much time has passed since last sample. Skip to current time
            self.print(f"Timeout: {t - self.sample_t} seconds")
            self.sample_t = t
            return
        while self.sample_t < t:  # Generate samples until current time
            n = int((self.sample_t % self.t_mod) * self.ext.sample_rate)
            try:
                samples = self.sample(n, self.ext.chunk_size)
            except Exception as e:
                self.print_exception(e)
                samples = np.zeros(self.ext.chunk_size, dtype="float32")
            self.out_port.push(samples)
            self.sample_t += self.ext.chunk_duration

        self.flash_running_indicator()  # If performance is an issue, remove this line

    def sample(self, n: int, l: int):
        pass

    def destroy(self):
        return super().destroy()


class BasicSynthNode(SynthNode):
    ext: "GrapycalAudio"

    def build_node(self):
        super().build_node()
        self.waveform = self.add_control(
            name="waveform",
            label="waveform",
            control_type=OptionControl,
            options=["sine", "square", "sawtooth", "triangle"],
            value="sine",
        )

    def sample(self, n: int, l: int):
        sample_rate = self.ext.sample_rate
        if self.waveform.get() == "sine":
            return np.sin(
                2 * math.pi * self.freq * np.arange(n, n + l) / sample_rate,
                dtype="float32",
            )
        elif self.waveform.get() == "square":
            return (
                np.sign(
                    np.sin(2 * math.pi * self.freq * np.arange(n, n + l) / sample_rate),
                    dtype="float32",
                )
                * 0.1
            )
        elif self.waveform.get() == "sawtooth":
            return (
                2
                * (
                    self.freq * np.arange(n, n + l, dtype="float32") / sample_rate
                    - np.floor(
                        0.5
                        + self.freq * np.arange(n, n + l, dtype="float32") / sample_rate
                    )
                )
                * 0.1
            )
        elif self.waveform.get() == "triangle":
            return (
                2
                * np.abs(
                    2
                    * (
                        self.freq * np.arange(n, n + l, dtype="float32") / sample_rate
                        - np.floor(
                            0.5
                            + self.freq
                            * np.arange(n, n + l, dtype="float32")
                            / sample_rate
                        )
                    )
                )
                - 1
            )


class ADSRNode(SynthNode):
    ext: "GrapycalAudio"
    mod_t = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("ADSR")
        self.on_port = self.add_in_port("on", 1)
        self.off_port = self.add_in_port("off", 1)
        self.attack = self.add_control(
            name="attack", label="attack", control_type=TextControl, text="1"
        )
        self.decay = self.add_control(
            name="decay", label="decay", control_type=TextControl, text="0.8"
        )
        self.sustain = self.add_control(
            name="sustain", label="sustain", control_type=TextControl, text="0.5"
        )
        self.attack_time = self.add_control(
            name="attack_time",
            label="attack time",
            control_type=TextControl,
            text="0.1",
        )
        self.decay_time = self.add_control(
            name="decay_time", label="decay time", control_type=TextControl, text="0.1"
        )
        self.sustain_time = self.add_control(
            name="sustain_time",
            label="sustain time",
            control_type=TextControl,
            text="0.5",
        )
        self.release_time = self.add_control(
            name="release_time",
            label="release time",
            control_type=TextControl,
            text="0.1",
        )

    def init_node(self):
        super().init_node()
        self.envelope = None
        self.start_n = 0
        self.last_n = 0
        self.positive_edge = False

    def port_activated(self, port: InputPort):
        super().port_activated(port)
        if port == self.on_port:
            self.envelope = self.get_on_envelope()
            self.positive_edge = True

    def get_on_envelope(self):
        attack = float(self.attack.get())
        decay = float(self.decay.get())
        sustain = float(self.sustain.get())
        attack_time = float(self.attack_time.get())
        decay_time = float(self.decay_time.get())
        sustain_time = float(self.sustain_time.get())

        attack_samples = np.linspace(0, attack, int(attack_time * self.ext.sample_rate))
        decay_samples = np.linspace(
            attack, decay, int(decay_time * self.ext.sample_rate)
        )
        # sustain is exponential decay
        sustain_samples = (
            np.exp(
                np.linspace(
                    0, np.log(sustain / decay), int(sustain_time * self.ext.sample_rate)
                )
            )
            * decay
        )

        return np.concatenate((attack_samples, decay_samples, sustain_samples))

    def sample(self, n: float, l: int):
        if self.positive_edge:
            self.start_n = self.last_n
            self.positive_edge = False
        self.last_n = n + l
        rel_n = n - self.start_n
        if self.envelope is None:
            return np.zeros(l, dtype="float32")
        if rel_n + l > len(self.envelope):
            return np.ones(l, dtype="float32") * float(self.sustain.get())
        return self.envelope[int(rel_n) : int(rel_n + l)]


class InstrumentNode(SynthNode):
    """
    A polyphonic synth for any instrument
    """

    class Note:
        def __init__(self, onset: int, pitch: int, velocity: int, offset: int):
            self.onset = onset
            self.pitch = pitch
            self.velocity = velocity
            self.offset = offset

    ext: "GrapycalAudio"
    category = "audio/synth"
    need_pitch_port = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("Instrument")
        self.note_on_port = self.add_in_port("note_on")
        self.note_off_port = self.add_in_port("note_off")

    def init_node(self):
        super().init_node()
        self.playing_notes: dict[int, InstrumentNode.Note] = {}
        self.releasing_notes: dict[int, InstrumentNode.Note] = {}
        self.instrument: Instrument | None = None
        self.release_time = 0.05  # seconds
        self.relase_envelope = np.concatenate(
            [
                np.linspace(
                    1, 0, int(self.release_time * self.ext.sample_rate), dtype="float32"
                ),
                np.zeros(self.ext.chunk_size, dtype="float32"),
            ]
        )

    def edge_activated(self, edge: Edge, port: InputPort):
        super().edge_activated(edge, port)

        if self.instrument is None:
            if hasattr(self, "getting_instrument"):
                return
            self.getting_instrument = True
            self.init_instrument()
            return

        if port == self.note_on_port:
            note_info: dict = edge.get()
            note = InstrumentNode.Note(
                note_info.get("onset", int(self.sample_t * self.ext.sample_rate)),
                note_info["pitch"],
                note_info["velocity"],
                note_info.get(
                    "offset", int((self.sample_t + 6) * self.ext.sample_rate)
                ),
            )
            # move currently playing note to releasing notes if it is played again
            if note.pitch in self.playing_notes:
                old_note = self.playing_notes[note.pitch]
                old_note.offset = int(self.sample_t * self.ext.sample_rate)
                self.releasing_notes[note.pitch] = old_note
            self.playing_notes[note.pitch] = note
        elif port == self.note_off_port:
            note_info: dict = edge.get()
            pitch = note_info["pitch"]
            if pitch in self.playing_notes:
                self.playing_notes[pitch].offset = note_info.get(
                    "offset", int(self.sample_t * self.ext.sample_rate)
                )

    @background_task
    def init_instrument(self):
        self.instrument = Instrument(
            get_resource("download/audio/instrument/grand_piano", is_dir=True)
        )

    def sample(self, n: int, l: int):
        # stack all playing notes
        samples = np.zeros(self.ext.chunk_size, dtype="float32")
        if self.instrument is None:
            return samples
        to_delete = []
        for note in self.playing_notes.values():
            samples_since_onset = n - note.onset
            samples_since_offset = n - note.offset

            # note has not started yet
            if samples_since_onset < 0:
                continue

            note.velocity = 1  # TODO implement velocity
            # note is still playing
            if samples_since_offset < 0:
                try:
                    samples += self.instrument.get_frames(
                        note.pitch,
                        note.velocity,
                        samples_since_onset,
                        self.ext.chunk_size,
                    )
                except Exception as e:
                    self.print_exception(e)
                    to_delete.append(note.pitch)
                    continue

            # note is releasing. move to releasing notes
            else:
                self.releasing_notes[note.pitch] = note
                to_delete.append(note.pitch)
                continue

        for pitch in to_delete:
            del self.playing_notes[pitch]

        # stack all releasing notes
        to_delete = []
        for note in self.releasing_notes.values():
            samples_since_offset = n - note.offset
            samples_since_onset = n - note.onset
            if samples_since_offset + l > len(self.relase_envelope):
                to_delete.append(note.pitch)
                continue
            try:
                note.velocity = 1  # TODO implement velocity
                samples += (
                    self.instrument.get_frames(
                        note.pitch,
                        note.velocity,
                        samples_since_onset,
                        self.ext.chunk_size,
                    )
                    * self.relase_envelope[
                        samples_since_offset : samples_since_offset + l
                    ]
                )

            except Exception as e:
                self.print_exception(e)
                to_delete.append(note.pitch)
                continue
        for pitch in to_delete:
            del self.releasing_notes[pitch]

        return samples


del SynthNode
