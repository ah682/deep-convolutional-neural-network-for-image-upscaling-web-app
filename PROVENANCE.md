# Pretrained model and upstream code

This project integrates a pretrained ESRGAN into Flask. It does not implement a
new super-resolution architecture, train the bundled model or reproduce the
upstream paper's benchmarks.

The architecture in `RRDBNet_arch.py`, interpolation/conversion helpers and the
original tensor preprocessing follow [Xintao Wang and collaborators' ESRGAN
repository](https://github.com/xinntao/ESRGAN). Upstream identifies the work as
*ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks* (ECCV Workshops,
2018), with training code maintained in BasicSR. See the
[upstream inference example](https://github.com/xinntao/ESRGAN/blob/master/test.py)
and [architecture](https://github.com/xinntao/ESRGAN/blob/master/RRDBNet_arch.py).

The bundled `RRDB_ESRGAN_x4.pth` was already present in this repository. It remains
unchanged in this repair; its SHA-256 is
`65fece06e1ccb48853242aa972bdf00ad07a7dd8938d2dcbdf4221b59f6372ce`.
That identifies these bytes; it does not independently authenticate the original
checkpoint download. Upstream links pretrained model downloads in its README.
Only the trusted bundled checksum is accepted by the local app.
`RRDBNet_arch.py` also remains unchanged (SHA-256
`0ef92981019fe1527e2570faebaee29c28bdee14094603bd963cd6651a456153`).

Upstream publishes its repository under
[Apache-2.0](https://github.com/xinntao/ESRGAN/blob/master/LICENSE); a copy is retained
in [licenses/ESRGAN-Apache-2.0.txt](licenses/ESRGAN-Apache-2.0.txt). This attribution
covers upstream-derived material; it does not grant a new project-wide license
for separately authored application/UI files. No project-wide license was present
at the repair baseline. Existing image assets and footer credits are retained;
their provenance has not been independently established by this repair.

The web integration changes in this repair are generated job storage, bounded
Pillow decoding, lazy CPU inference loading and explicit error handling. RGB
normalization, the 23-block RRDB architecture and 4× scale remain the existing
model path. Generated texture can be plausible but incorrect; output is not
recovered ground truth. Neither synthetic tests nor a tiny CPU smoke establish
quality on user photos, OCR evidence, faces or scientific/forensic material.
