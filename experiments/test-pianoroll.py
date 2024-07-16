# %%
from grapycal_audio_torch.dataset import PianoRollDataset
from torch.utils.data import DataLoader, Dataset
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

# %%
from grapycal_audio.pianoroll import PianoRoll


def tokenize(
    pr: PianoRoll,
    n_velocity=128,
    duration: int | None = None,
    seq_len: int | None = None,
):
    tokens = []
    frame = 0
    if duration is None:
        duration = pr.duration

    tokens.append({"type": "start", "frame": frame})
    for note in pr.notes:
        while note.onset > frame:
            tokens.append({"type": "next_frame", "frame": frame})
            frame += 1

        tokens.append({"type": "pitch", "frame": frame, "value": note.pitch - 21})
        tokens.append(
            {
                "type": "velocity",
                "frame": frame,
                "value": int(note.velocity * (n_velocity / 128)),
            }
        )

    while duration > frame:
        tokens.append({"type": "next_frame", "frame": frame})
        frame += 1

    # fill in the next_frame
    for i in range(len(tokens) - 1):
        tokens[i]["next_frame"] = tokens[i + 1]["frame"]

    tokens.pop()  # remove the last next_frame 128

    # we're using seq_len+1 because start token doesn't count
    if seq_len is not None:
        tokens = tokens[: seq_len + 1]

        if len(tokens) < seq_len + 1:
            tokens += [{"type": "pad"}] * (seq_len + 1 - len(tokens))

    return tokens


# %%
def binary_positional_encoding(length: int, dim: int):
    res = []
    for i in range(length):
        res.append([int(x) for x in f"{i:0{dim}b}"])
        # pad
        res[-1] += [0] * (dim - len(res[-1]))

    return torch.tensor(res, dtype=torch.float32)


def sinusoidal_positional_encoding(length: int, dim: int):
    res = []
    for d in range(dim // 2):
        res.append(torch.sin(torch.arange(length) / 10000 ** (2 * d / dim)))
    for d in range(dim // 2):
        res.append(torch.cos(torch.arange(length) / 10000 ** (2 * d / dim)))
    return torch.stack(res, dim=1)


def construct_input_frame(token: dict, pos_encoding: torch.Tensor, n_pitch, n_velocity):
    if token["type"] == "pad":
        return torch.zeros(n_pitch + n_velocity + 2 + pos_encoding.shape[1] * 2)

    # pitch
    pitch = torch.zeros(n_pitch)
    if token["type"] == "pitch":
        pitch[token["value"]] = 1

    # velocity
    velocity = torch.zeros(n_velocity)
    if token["type"] == "velocity":
        velocity[token["value"]] = 1

    # next_frame
    next_frame = torch.zeros(1)
    if token["type"] == "next_frame":
        next_frame[0] = 1

    # start
    start = torch.zeros(1)
    if token["type"] == "start":
        start[0] = 1

    # pos
    pos = pos_encoding[token["frame"]]

    # target pos
    target_pos = pos_encoding[token["next_frame"]]

    return torch.cat([pitch, velocity, next_frame, start, pos, target_pos], dim=0)


def construct_input_tensor(tokens, pos_encoding: torch.Tensor, n_pitch, n_velocity):
    frame_axis = []

    for token in tokens:
        frame_axis.append(
            construct_input_frame(token, pos_encoding, n_pitch, n_velocity)
        )

    return torch.stack(frame_axis, dim=0)


def construct_output_mask(tokens, n_pitch, n_velocity):
    """
    An additive mask for the model's output (logits) to prevent the model from predicting invalid tokens.

    The first token must be pitch or next_frame.
    The next token of pitch must be velocity.
    The next token of next_frame can be pitch or next_frame.
    The next token of velocity must be pitch or next_frame.

    Accroding to the above rule, we can construct a mask as a prior on the model's prediction.
    """

    mask = torch.zeros(len(tokens), n_pitch + n_velocity + 1)
    # fill with -inf
    mask = mask - 1e7

    mask[0, :n_pitch] = 0
    mask[0, n_pitch + n_velocity] = 0

    for i in range(len(tokens) - 1):
        # output shape: Output: [pitch(n_pitch), velocity(n_velocity), next_frame(1)]
        token = tokens[i]

        if token["type"] == "pitch":
            # enable velocity
            mask[i + 1, n_pitch : n_pitch + n_velocity] = 0
        if token["type"] == "velocity":
            # enable pitch or next_frame
            mask[i + 1, :n_pitch] = 0
            mask[i + 1, n_pitch + n_velocity] = 0
        if token["type"] == "next_frame":
            # enable pitch or next_frame
            mask[i + 1, :n_pitch] = 0
            mask[i + 1, n_pitch + n_velocity] = 0

    return mask


def construct_target(tokens, n_pitch, n_velocity):
    res = []
    for i, token in enumerate(tokens):
        if token["type"] == "pitch":
            res.append(token["value"])
        elif token["type"] == "velocity":
            res.append(n_pitch + token["value"])
        elif token["type"] == "next_frame":
            res.append(n_pitch + n_velocity)
        elif token["type"] == "pad":
            res.append(-100)  # -100 is the ignore index
        else:
            raise ValueError(f"Unknown token type: {token['type']}")

    return torch.tensor(res, dtype=torch.long)


pos_encoding = torch.cat(
    [binary_positional_encoding(512, 9), sinusoidal_positional_encoding(512, 31)],
    dim=1,
)


class TokenizedPianoRollDataset(Dataset):
    """
    Input: [pitch(n_pitch), velocity(n_velocity), next_frame(1), start(1), pos, target_pos]
    Output: [pitch(n_pitch), velocity(n_velocity), next_frame(1)]
    """

    def __init__(
        self,
        path: str,
        pos_encoding: torch.Tensor,
        segment_length: int,
        hop_len: int,
        seq_len: int,
        n_pitch: int,
        n_velocity: int,
    ):
        self.ds = PianoRollDataset(path, segment_len=segment_length, hop_len=hop_len)
        self.pos_encoding = pos_encoding
        self.seq_len = seq_len
        self.n_pitch = n_pitch
        self.n_velocity = n_velocity
        self.segment_length = segment_length

        # self.tokens = []
        # for idx in range(len(self.ds)):
        #    self.tokens.append(tokenize(self.ds.get_piano_roll(idx), n_velocity=self.n_velocity, duration=self.segment_length, seq_len=self.seq_len))

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, idx):
        # tokens = self.tokens[idx]

        pr = self.ds.get_piano_roll(idx)
        tokens = tokenize(
            pr,
            n_velocity=self.n_velocity,
            duration=self.segment_length,
            seq_len=self.seq_len,
        )

        tokens_without_start = tokens[1:]

        # the last token is not needed to be an input
        input = construct_input_tensor(
            tokens[:-1],
            pos_encoding=self.pos_encoding,
            n_pitch=self.n_pitch,
            n_velocity=self.n_velocity,
        )
        target = construct_target(
            tokens_without_start, n_pitch=self.n_pitch, n_velocity=self.n_velocity
        )
        output_mask = construct_output_mask(
            tokens_without_start, n_pitch=self.n_pitch, n_velocity=self.n_velocity
        )
        return {"input": input, "target": target, "output_mask": output_mask}

    def get_loss_weight(self):
        """
        The loss weight for each token.
        """
        res = torch.ones(self.n_pitch + self.n_velocity + 1)
        res[self.n_pitch + self.n_velocity] = (
            0.05  # next_frame is too common so we need to reduce its weight
        )


if __name__ == "__main__":
    # %%
    ds = TokenizedPianoRollDataset(
        "dev_cwd/_data/gr_resource/download/music/a", pos_encoding, 5, 500, 14, 88, 32
    )
    dl = DataLoader(ds, batch_size=8, shuffle=True, num_workers=1)

    # %%
    next(iter(dl))

    # %%
    from torch import nn
    from torch.optim import Adam
    # input: B, 350, 202
    # output: B, 350, 121

    class PianoRollGenerator(nn.Module):
        def __init__(self):
            super().__init__()
            self.in_linear = nn.Linear(200, 256)
            self.transformer = nn.TransformerEncoder(
                nn.TransformerEncoderLayer(
                    d_model=256, nhead=8, dim_feedforward=1024, batch_first=True
                ),
                num_layers=6,
            )
            self.out_linear = nn.Linear(256, 121)

        def forward(self, x):
            x = self.in_linear(x)
            x = self.transformer(
                x,
                mask=nn.Transformer.generate_square_subsequent_mask(x.shape[1]).to(
                    x.device
                ),
                is_causal=True,
            )
            x = self.out_linear(x)
            return x

    model = PianoRollGenerator()

    crit = nn.CrossEntropyLoss(weight=ds.get_loss_weight())

    opt = Adam(model.parameters(), lr=1e-4)

    # %%

    from grapycal_audio.pianoroll import Note

    def top_k(logits: torch.Tensor, k):
        values, indices = logits.topk(k)
        probs = torch.softmax(values, dim=0)
        selected = torch.multinomial(probs, 1)
        return indices[selected]

    def decode(logits, last_token, n_pitch, n_velocity):
        frame = last_token["next_frame"]

        if last_token["type"] in ["start", "velocity", "next_frame"]:
            logits[n_pitch : n_pitch + n_velocity] = -torch.inf
            max_idx = top_k(logits, 15).item()
            if max_idx < n_pitch:
                return {
                    "type": "pitch",
                    "value": max_idx,
                    "frame": frame,
                    "next_frame": frame,
                }
            elif max_idx == n_pitch + n_velocity:
                return {"type": "next_frame", "frame": frame, "next_frame": frame + 1}
            else:
                raise ValueError(f"Invalid index: {max_idx}")

        elif last_token["type"] == "pitch":
            logits[:n_pitch] = -torch.inf
            logits[n_pitch + n_velocity] = -torch.inf
            max_idx = top_k(logits, 15).item()
            return {
                "type": "velocity",
                "value": max_idx - n_pitch,
                "frame": frame,
                "next_frame": frame,
            }
        else:
            raise ValueError(f"Unknown token type: {last_token['type']}")

    def token_to_pianoroll(tokens):
        notes = []
        frame = 0
        last_pitch = None
        for token in tokens:
            if token["type"] == "start":
                continue
            if token["type"] == "pitch":
                last_pitch = token["value"]
            if token["type"] == "velocity":
                notes.append(
                    Note(
                        onset=frame,
                        pitch=last_pitch + 21,
                        velocity=int(token["value"] * (128 / 32)),
                    )
                )
            if token["type"] == "next_frame":
                frame += 1
        return PianoRoll(notes)

    # logits = out[0].detach().cpu()

    # n_pitch = 88
    # n_velocity = 32
    # last_token = {'type':'start', 'frame':0, 'next_frame':0}
    # tokens = []
    # for frame_logits in logits:
    #     decoded = decode(frame_logits, last_token, n_pitch, n_velocity)
    #     tokens.append(decoded)
    #     last_token = decoded
    def inference(file_path: str):
        model.eval()
        n_pitch = 88
        n_velocity = 32
        tokens = [{"type": "start", "frame": 0, "next_frame": 0}]
        # tokens = ds.tokens[64][:20]
        last_token = tokens[-1]
        while tokens[-1]["next_frame"] < 512:
            input = construct_input_tensor(
                tokens,
                pos_encoding=pos_encoding,
                n_pitch=n_pitch,
                n_velocity=n_velocity,
            ).unsqueeze(0)
            input = input.to(device)
            logits = model(input).squeeze(0)[-1].detach().cpu()
            decoded = decode(logits, last_token, n_pitch, n_velocity)
            tokens.append(decoded)
            last_token = decoded

        token_to_pianoroll(tokens).to_midi(file_path)

    # %%
    # train
    import time
    from tqdm import tqdm

    model.to(device)
    crit.to(device)

    model.train()

    for epoch in range(100):
        tq = tqdm(dl)
        for i, batch in enumerate(tq):
            batch = {k: v.to(device) for k, v in batch.items()}
            opt.zero_grad()
            out = model(batch["input"])
            loss = crit((out + batch["output_mask"]).transpose(1, 2), batch["target"])
            loss.backward()
            opt.step()
            if i % 100 == 0:
                # print the loss to tqdm
                # temp = torch.cuda.temperature()
                temp = 0
                tq.set_postfix(batch=i, loss=loss.item(), gpu_temp=temp)

                if temp > 65:
                    print("GPU temperature is too high. Slowin down.", temp)
                    time.sleep(0.1)

            if torch.isnan(loss):
                raise ValueError("Loss is NaN")

        inference(f"./output_{epoch}_{i}.mid")
        torch.save(model.state_dict(), f"./model_{epoch}.pth")
        torch.save(opt.state_dict(), f"./opt_{epoch}.pth")

    # %%
    inference("a.mid")

    # %%
    print(torch.version.cuda)

    # %%
    for i, batch in enumerate(tq):
        break

    # %%
    device

    # %%
    import torch

    torch.cuda.is_available()

    # %%
    from torch.utils.data import DataLoader, Dataset

    ds = [1, 2, 3, 4, 5, 36, 4, 1]
    dl = DataLoader(ds, batch_size=2, shuffle=True, num_workers=2)
    for b in dl:
        print(b)

    # %%
