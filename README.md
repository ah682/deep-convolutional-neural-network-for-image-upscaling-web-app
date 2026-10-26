# ESRGAN Image Upscaler

A Flask web app for upscaling images with the pretrained ESRGAN/RRDB model.
Upload a PNG, JPEG or WebP image and compare it with a result at four times the
width and height. The model and architecture come from
[Xintao Wang and collaborators' ESRGAN project](https://github.com/xinntao/ESRGAN);
see [model provenance and terms](PROVENANCE.md) for the bundled files.

## Run locally

Use **Python 3.12 on Linux x86_64** for the pinned CPU environment:

```bash
git clone https://github.com/ah682/deep-convolutional-neural-network-for-image-upscaling-web-app.git
cd deep-convolutional-neural-network-for-image-upscaling-web-app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-model.txt
.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`. PyTorch is a large download; the CPU wheel comes from
its [official index](https://pytorch.org/get-started/previous-versions/).
The repository includes the original 67 MB checkpoint. Inference checks its
recorded checksum and loads tensor weights with `weights_only=True` on the CPU.

## Storage and limits

Each successful request publishes a server-generated job under `instance/jobs/`.
Client filenames never select paths. Refreshing the page or uploading another
image keeps earlier jobs intact. The app re-encodes decoded inputs as RGB PNGs;
it does not preserve uploaded metadata, animation or transparency.

Defaults: 4 MiB file bytes, 256 pixels per side, 65,536 input pixels, one inference
at a time and 32 retained jobs. Output is 4× per side. Extra multipart bytes and
fields have separate request/form limits. Oversized inputs return 413; bad or
truncated images return 400; concurrent inference returns 429; a missing/broken
model or full job directory returns 503. Failed jobs are discarded independently.
These limits control input size and concurrency; decoding and inference still
run in the application process without a hard memory limit or timeout.

Set `UPSCALER_JOB_ROOT` before startup to choose another directory. To reclaim
space, **stop the app**, then remove only unneeded generated job directories in
that root. An interrupted process can leave `.pending-*` directories; inspect
and remove them while stopped. The application never globally clears files on
page load. Old `uploads/` and `results/` folders are not imported or deleted.

Run this as a single-user app on loopback with one serving process. Job URLs have
no authentication, and the lock and storage quota apply to that process only.
The page loads remote style/font assets; image inference runs locally on the CPU.
ESRGAN can generate plausible but incorrect texture, so a sharper result should
not be treated as recovered detail.

## Development checks

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app.py inference.py RRDBNet_arch.py tests
node --check static/uploads.js
```

Request tests replace inference with a test function while exercising multipart
parsing, Pillow decoding, storage, HTTP responses and PNG output. A separate
smoke test loads the bundled model, upscales a 2×2 image and checks the 8×8 RGB
result; it skips if PyTorch is unavailable.

`POST /upload` returns JSON with `job_id`, `input` and `result` URLs. Listing
routes return arrays of generated job paths. Images are served at
`/uploads/<job>/input.png` and `/results/<job>/output.png`.
