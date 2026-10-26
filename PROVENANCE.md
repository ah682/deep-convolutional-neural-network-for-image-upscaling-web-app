# Pretrained model and upstream code

This project adds a Flask upload and comparison interface to a pretrained ESRGAN
model. It uses the upstream architecture and checkpoint for 4× inference.

The architecture in `RRDBNet_arch.py`, interpolation/conversion helpers and the
original tensor preprocessing follow [Xintao Wang and collaborators' ESRGAN
repository](https://github.com/xinntao/ESRGAN). Upstream identifies the work as
*ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks* (ECCV Workshops,
2018), with training code maintained in BasicSR. See the
[upstream inference example](https://github.com/xinntao/ESRGAN/blob/master/test.py)
and [architecture](https://github.com/xinntao/ESRGAN/blob/master/RRDBNet_arch.py).

The bundled `RRDB_ESRGAN_x4.pth` is unchanged from the original repository. Its SHA-256 is
`65fece06e1ccb48853242aa972bdf00ad07a7dd8938d2dcbdf4221b59f6372ce`.
The original download source was not recorded. Upstream links pretrained models
in its README; the app accepts only the bundled checksum above.
`RRDBNet_arch.py` is also unchanged (SHA-256
`0ef92981019fe1527e2570faebaee29c28bdee14094603bd963cd6651a456153`).

Upstream publishes its repository under
[Apache-2.0](https://github.com/xinntao/ESRGAN/blob/master/LICENSE); a copy is retained
in [licenses/ESRGAN-Apache-2.0.txt](licenses/ESRGAN-Apache-2.0.txt). This attribution
covers the upstream-derived code. Separately authored application/UI files have
no project-wide licence. Existing image assets and footer credits are retained,
but their source and reuse terms have not been established.

The web app uses generated job directories, input-size checks, lazy CPU model
loading and per-request error handling. RGB normalization, the 23-block RRDB
architecture and 4× scale follow the existing inference path. The tests check
integration and output shape; this project has not measured image quality or
reproduced the paper's benchmarks.
