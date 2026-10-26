# Local ESRGAN image upscaler

A legacy Flask integration of the pretrained ESRGAN/RRDB 4× model. Upload a small
PNG, JPEG or WebP image, then open its generated result. The contribution here is
the web integration; the model and architecture are upstream work. See
[provenance and terms](PROVENANCE.md). No training or new model is included.

## Run locally

The verified recipe uses **Python 3.12 on Linux x86_64**, CPU only:

```bash
git clone https://github.com/ah682/deep-convolutional-neural-network-for-image-upscaling-web-app.git
cd deep-convolutional-neural-network-for-image-upscaling-web-app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-model.txt
.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`. PyTorch is a large download; the CPU wheel comes from
its [official index](https://pytorch.org/get-started/previous-versions/). The pinned
dependency combination was verified from cached public packages; a fresh network installation
and live browser workflow were not executed in the maintenance environment.
The repository includes its original 67 MB checkpoint. Inference checks its
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
This bounds individual workloads; it is not a hard memory/CPU timeout or a
hostile-decoder sandbox.

Set `UPSCALER_JOB_ROOT` before startup to choose another directory. To reclaim
space, **stop the app**, then remove only unneeded generated job directories in
that root. An interrupted process can leave `.pending-*` directories; inspect
and remove them while stopped. The application never globally clears files on
page load. Old `uploads/` and `results/` folders are not imported or deleted.

This remains a local single-user demo. Job URLs/listing have no authentication,
all local users share retained jobs, and the lock/quota apply to one serving
process. Use one process and loopback only. There is no production deployment,
GPU validation, rate-limited shared hosting or perceptual-quality claim. The page
still uses remote style/font assets; these are separate from local image inference.
Generated textures may be wrong even when the image looks sharper.

## Verify

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app.py inference.py RRDBNet_arch.py tests
node --check static/uploads.js
```

The request tests inject only the costly inference boundary. They exercise real
multipart parsing, Pillow decoding, storage, HTTP responses and PNG output. The
real-model smoke uses the unchanged checkpoint on a 2×2 input and checks an 8×8
RGB result; it skips explicitly if PyTorch is not installed. The maintenance run
also verified the actual CPU model. This is a compatibility check, not a model
accuracy benchmark or live browser test.

`POST /upload` now returns JSON with `job_id`, `input` and `result` URLs. Existing
listing routes return JSON arrays of generated job paths. Raw client-filename
URLs are replaced by `/uploads/<job>/input.png` and `/results/<job>/output.png`.
The page uses these APIs; no credentials or external model service are needed.
