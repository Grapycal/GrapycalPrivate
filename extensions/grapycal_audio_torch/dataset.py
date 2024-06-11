from math import ceil
import os
import glob
from grapycal.sobjects.controls.sliderControl import SliderControl
import torch
from torch.utils.data import Dataset

from grapycal import Node, background_task, get_resource
from grapycal.extension_api.trait import Chain, OutputsTrait, TriggerTrait
from grapycal_audio import PianoRoll


class PianoRollDataset(Dataset):
    def __init__(
        self,
        data_dir,
        segment_len=0,
        hop_len=32,
        max_duration=32 * 180,
        shard=0,
        num_shards=1,
        max_pieces=None,
        metadata_file=None,
    ):
        print(f"Creating dataset segment_len = {segment_len}")
        if metadata_file is not None:
            try:
                import pandas
            except ImportError:
                raise ImportError(
                    "Pandas is required to load metadata. Please install it using `pip install pandas`"
                )
            metadata = pandas.read_csv(metadata_file)
        else:
            metadata = None
        self.pianorolls: list[PianoRoll] = []

        file_list = list(glob.glob(os.path.join(data_dir, "*.json")))
        file_list = file_list[:max_pieces]
        for file_path in file_list:
            new_pr = PianoRoll.load(file_path)
            if metadata is not None:
                song_id = int(file_path.split("/")[-1].split(".json")[0])
                meta = metadata[metadata["id"] == song_id].iloc[0]
                new_pr.set_metadata(name=meta["title"])

            self.pianorolls.append(new_pr)

        self.segment_length = segment_len
        if segment_len:
            num_segments = [
                ceil(pianoroll.duration / hop_len) for pianoroll in self.pianorolls
            ]

            self.segment_id_to_piece = []
            for pianoroll, num_seg in zip(self.pianorolls, num_segments):
                self.segment_id_to_piece += [
                    (pianoroll, hop_len * i, hop_len * i + segment_len)
                    for i in range(num_seg)
                ]
            # slice shard
            self.segment_id_to_piece = self.segment_id_to_piece[shard:][::num_shards]
            self.length = len(self.segment_id_to_piece)
        else:
            self.length = len(self.pianorolls)
            self.max_duration = min(
                max_duration, max([pianoroll.duration for pianoroll in self.pianorolls])
            )

        print(
            f"Created dataset with {self.length} data points from {len(self.pianorolls)} pieces"
        )

    def __len__(self):
        return self.length

    def __getitem__(self, idx) -> torch.Tensor:
        if self.segment_length:
            piece, start, end = self.segment_id_to_piece[idx]
            return piece.to_tensor(start, end, padding=True, normalized=False)  # [-1,1)
        else:
            return self.pianorolls[idx].to_tensor(
                0, self.max_duration, padding=True, normalized=False
            )  # [-1,1)

    def get_piano_roll(self, idx) -> PianoRoll:
        if self.segment_length:
            piece, start, end = self.segment_id_to_piece[idx]
            return piece.slice(start, end)
        else:
            return self.pianorolls[idx].slice(0, self.max_duration)

    def get_all_piano_rolls(self) -> list[PianoRoll]:
        return [self.get_piano_roll(i) for i in range(len(self))]


class PianoRollDatasetNode(Node):
    """
    A dataset of piano rolls
    """

    def define_traits(self):
        return [
            Chain(
                TriggerTrait(),
                self.get_dataset,
                OutputsTrait(),
            )
        ]

    def build_node(self):
        self.segment_len = self.add_in_port(
            "segment_len",
            control_type=SliderControl,
            value=0,
            min=0,
            max=512,
            step=1,
            int_mode=True,
        )

    @background_task
    def get_dataset(self):
        self.print("Loading dataset...")
        path = get_resource("download/music/pop_piano", is_dir=True)
        dataset = PianoRollDataset(path, segment_len=self.segment_len.get())
        self.print("Dataset loaded")
        return dataset
