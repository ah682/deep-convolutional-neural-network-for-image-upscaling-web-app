"""CPU inference using the unchanged bundled upstream-style RRDB checkpoint.

Preprocessing follows xinntao/ESRGAN/test.py; model architecture is not retrained.
"""

from hashlib import sha256
from pathlib import Path

from PIL import Image

CHECKPOINT_SHA256 = "65fece06e1ccb48853242aa972bdf00ad07a7dd8938d2dcbdf4221b59f6372ce"


class ModelUnavailable(RuntimeError):
    pass


class ESRGAN:
    def __init__(self, checkpoint: Path):
        self.checkpoint = checkpoint
        self.model = None

    def __call__(self, image: Image.Image) -> Image.Image:
        try:
            import numpy as np
            import torch

            import RRDBNet_arch as arch
        except ImportError as exc:
            raise ModelUnavailable(
                "Install requirements-model.txt for actual inference."
            ) from exc
        if self.model is None:
            try:
                if (
                    sha256(self.checkpoint.read_bytes()).hexdigest()
                    != CHECKPOINT_SHA256
                ):
                    raise ValueError("Bundled checkpoint hash mismatch.")
                torch.set_num_threads(1)
                model = arch.RRDBNet(3, 3, 64, 23, gc=32)
                model.load_state_dict(
                    torch.load(self.checkpoint, map_location="cpu", weights_only=True),
                    strict=True,
                )
                self.model = model.eval()
            except (OSError, ValueError, RuntimeError) as exc:
                raise ModelUnavailable(
                    "Unable to load the trusted bundled checkpoint."
                ) from exc
        array = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array.transpose(2, 0, 1).copy()).unsqueeze(0)
        with torch.inference_mode():
            output = self.model(tensor).squeeze(0).float().cpu().clamp_(0, 1).numpy()
        pixels = (output.transpose(1, 2, 0) * 255.0).round().astype(np.uint8)
        return Image.fromarray(pixels)
