"""Bounded local Flask integration for the existing pretrained ESRGAN model."""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import uuid
import warnings
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

from inference import ESRGAN, ModelUnavailable

ROOT = Path(__file__).resolve().parent
JOB_ID = re.compile(r"[0-9a-f]{32}\Z")


def decode_image(data: bytes, max_side: int, max_pixels: int) -> Image.Image:
    """Inspect dimensions before pixel allocation, then fully decode one frame."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(
                io.BytesIO(data), formats=["PNG", "JPEG", "WEBP"]
            ) as source:
                if (
                    source.width > max_side
                    or source.height > max_side
                    or source.width * source.height > max_pixels
                ):
                    raise RequestEntityTooLarge(
                        "Image dimensions exceed the configured limit."
                    )
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Animated images are not supported.")
                source.load()
                image = source.convert("RGB")
                image.info.clear()
                return image
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise RequestEntityTooLarge(
                "Image dimensions exceed the configured limit."
            ) from exc
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise ValueError("Upload a complete PNG, JPEG or WebP image.") from exc


def create_app(config=None, *, inference=None):
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.config.from_mapping(
        JOB_ROOT=Path(os.environ.get("UPSCALER_JOB_ROOT", ROOT / "instance" / "jobs")),
        MAX_UPLOAD_BYTES=4 * 1024 * 1024,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 + 64 * 1024,
        MAX_FORM_MEMORY_SIZE=128 * 1024,
        MAX_FORM_PARTS=4,
        MAX_IMAGE_SIDE=256,
        MAX_IMAGE_PIXELS=65_536,
        MAX_JOBS=32,
    )
    if config:
        app.config.update(config)
    infer = inference if inference is not None else ESRGAN(ROOT / "RRDB_ESRGAN_x4.pth")
    processing = Lock()

    def job_root():
        return Path(app.config["JOB_ROOT"]).resolve()

    def completed_jobs():
        root = job_root()
        if not root.exists():
            return []
        return sorted(
            p.name
            for p in root.iterdir()
            if JOB_ID.fullmatch(p.name) and p.is_dir() and (p / "output.png").is_file()
        )

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return jsonify(
            error="Upload exceeds the byte, image dimension or form limit."
        ), 413

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/upload")
    def upload():
        if not processing.acquire(blocking=False):
            return jsonify(
                error="Another image is processing; try again after it completes."
            ), 429
        stage = None
        try:
            if "file" not in request.files or not request.files["file"].filename:
                return jsonify(error="Select an image to upload."), 400
            # Client filenames are never used for storage, model selection or URLs.
            data = request.files["file"].stream.read(app.config["MAX_UPLOAD_BYTES"] + 1)
            if len(data) > app.config["MAX_UPLOAD_BYTES"]:
                raise RequestEntityTooLarge()
            try:
                image = decode_image(
                    data, app.config["MAX_IMAGE_SIDE"], app.config["MAX_IMAGE_PIXELS"]
                )
            except ValueError as exc:
                return jsonify(error=str(exc)), 400
            root = job_root()
            root.mkdir(parents=True, exist_ok=True)
            if sum(p.is_dir() for p in root.iterdir()) >= app.config["MAX_JOBS"]:
                return jsonify(
                    error="Job storage is full. Stop the app and remove unneeded jobs."
                ), 503
            stage = Path(tempfile.mkdtemp(prefix=".pending-", dir=root))
            image.save(stage / "input.png")
            output = infer(image)
            if not isinstance(output, Image.Image) or output.size != (
                image.width * 4,
                image.height * 4,
            ):
                raise RuntimeError("Inference returned an invalid image shape.")
            output.convert("RGB").save(stage / "output.png")
            job_id = uuid.uuid4().hex
            stage.rename(root / job_id)
            stage = None
            return jsonify(
                job_id=job_id,
                input=f"/uploads/{job_id}/input.png",
                result=f"/results/{job_id}/output.png",
            )
        except ModelUnavailable:
            app.logger.exception("The bundled model could not be loaded")
            return jsonify(
                error="Model unavailable; check the local model installation and server log."
            ), 503
        except RequestEntityTooLarge:
            raise
        except Exception:
            app.logger.exception("Image processing failed")
            return jsonify(
                error="Image processing failed; the existing jobs are unchanged."
            ), 500
        finally:
            try:
                if stage is not None:
                    shutil.rmtree(stage)
            except OSError:
                app.logger.exception("Failed to remove the incomplete job directory")
            finally:
                processing.release()

    @app.get("/get_Uploaded_images")
    def get_uploaded_images():
        return jsonify([f"{job}/input.png" for job in completed_jobs()])

    @app.get("/get_images")
    def get_images():
        return jsonify([f"{job}/output.png" for job in completed_jobs()])

    def serve_job(job_id, filename):
        if not JOB_ID.fullmatch(job_id) or job_id not in completed_jobs():
            return jsonify(error="Job not found."), 404
        return send_from_directory(job_root() / job_id, filename, mimetype="image/png")

    @app.get("/uploads/<job_id>/input.png")
    def uploaded_file(job_id):
        return serve_job(job_id, "input.png")

    @app.get("/results/<job_id>/output.png")
    def result_file(job_id):
        return serve_job(job_id, "output.png")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
