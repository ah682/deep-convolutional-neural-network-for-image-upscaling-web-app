"""Request/storage regressions; only the costly learned inference is substituted."""

import importlib.util
import io
import json
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def picture(color="red", size=(3, 2), kind="PNG"):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, format=kind)
    return stream.getvalue()


def upscaled(image):
    return image.resize((image.width * 4, image.height * 4))


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    import app

    calls = []

    def measured(image):
        calls.append(image.size)
        return upscaled(image)

    instance = app.create_app({"JOB_ROOT": tmp_path / "jobs"}, inference=measured)
    instance.extensions["inference_calls"] = calls
    instance.config.update(TESTING=True)
    return instance


def upload(app, data=None, name="same.png"):
    return app.test_client().post(
        "/upload",
        data={"file": (io.BytesIO(data if data is not None else picture()), name)},
    )


def results(app):
    return json.loads(app.test_client().get("/get_images").data)


def test_two_same_name_jobs_and_home_keep_both_results(application):
    assert upload(application, picture("red")).status_code == 200
    first = results(application)[0]
    original = application.test_client().get("/results/" + first).data
    assert upload(application, picture("blue")).status_code == 200
    assert len(results(application)) == 2
    assert application.test_client().get("/results/" + first).data == original
    assert application.test_client().get("/").status_code == 200
    assert len(results(application)) == 2
    assert application.test_client().get("/results/" + first).data == original


@pytest.mark.parametrize(
    "name", ["../outside.png", "absolute", r"..\outside.png", "same.png"]
)
def test_client_filename_never_becomes_storage_path(application, tmp_path, name):
    if name == "absolute":
        name = str(tmp_path / "outside-absolute.png")
    assert upload(application, name=name).status_code == 200
    assert not (tmp_path / "outside-absolute.png").exists()
    assert not (tmp_path / "outside.png").exists()
    assert not (tmp_path / "uploads" / name).is_file()
    assert results(application)[0].endswith("/output.png")


@pytest.mark.parametrize("data", [b"not an image", b"", picture()[:30]])
def test_bad_or_truncated_image_is_a_client_error(application, data):
    assert upload(application, data).status_code == 400
    assert application.extensions["inference_calls"] == []
    assert results(application) == []


def test_upload_bytes_are_checked_before_inference(application):
    application.config["MAX_UPLOAD_BYTES"] = 100
    assert upload(application, picture() + b"x" * 101).status_code == 413
    assert application.extensions["inference_calls"] == []
    assert results(application) == []


@pytest.mark.parametrize("size", [(5, 2), (3, 3)])
def test_header_dimensions_and_pixel_budget_are_checked_before_decode(
    application, size
):
    application.config.update(MAX_IMAGE_SIDE=4, MAX_IMAGE_PIXELS=8)
    assert upload(application, picture(size=size)).status_code == 413
    assert application.extensions["inference_calls"] == []
    assert results(application) == []


def test_home_does_not_delete_a_completed_job(application):
    assert upload(application).status_code == 200
    first = results(application)[0]
    before = application.test_client().get("/results/" + first).data
    assert application.test_client().get("/").status_code == 200
    assert results(application) == [first]
    assert application.test_client().get("/results/" + first).data == before


def test_failed_job_preserves_success_and_can_retry(application):
    assert upload(application).status_code == 200
    first = results(application)[0]
    original = application.test_client().get("/results/" + first).data
    from app import create_app

    calls = 0

    def unreliable(image):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("inference failed")
        return upscaled(image)

    app = create_app({"JOB_ROOT": application.config["JOB_ROOT"]}, inference=unreliable)
    assert upload(app).status_code == 500
    assert results(app) == [first]
    assert not list(Path(app.config["JOB_ROOT"]).glob(".pending-*"))
    assert app.test_client().get("/results/" + first).data == original
    assert upload(app).status_code == 200
    assert len(results(app)) == 2


def test_busy_job_is_rejected_without_touching_another_job(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app import create_app

    entered, release = Event(), Event()

    def slow(image):
        entered.set()
        assert release.wait(3)
        return upscaled(image)

    app = create_app({"JOB_ROOT": tmp_path / "jobs"}, inference=slow)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(upload, app)
        try:
            assert entered.wait(3)
            assert upload(app).status_code == 429
        finally:
            release.set()
        assert first.result(timeout=3).status_code == 200
    assert len(results(app)) == 1


def test_job_quota_preserves_existing_outputs(application):
    application.config["MAX_JOBS"] = 2
    assert upload(application).status_code == 200
    assert upload(application, picture("blue")).status_code == 200
    before = {
        p: application.test_client().get("/results/" + p).data
        for p in results(application)
    }
    assert upload(application).status_code == 503
    assert {
        p: application.test_client().get("/results/" + p).data
        for p in results(application)
    } == before


def test_dimension_header_is_rejected_without_loading_pixels(application, monkeypatch):
    data = picture(size=(9, 9))
    application.config["MAX_IMAGE_SIDE"] = 8
    monkeypatch.setattr(
        Image.Image, "load", lambda self: pytest.fail("oversized image was decoded")
    )
    assert upload(application, data).status_code == 413


@pytest.mark.parametrize(
    "path",
    ["/results/../../app.py", "/uploads/../app.py", "/results/not-a-job/output.png"],
)
def test_non_job_paths_are_not_served(application, path):
    assert application.test_client().get(path).status_code == 404


def test_missing_file_and_oversized_multipart_have_predictable_errors(application):
    client = application.test_client()
    assert client.post("/upload").status_code == 400
    application.config["MAX_CONTENT_LENGTH"] = 100
    response = upload(application)
    assert response.status_code == 413
    assert response.is_json


def test_model_unavailable_does_not_publish_partial_job(tmp_path):
    from app import create_app
    from inference import ModelUnavailable

    def missing(image):
        raise ModelUnavailable("missing dependency")

    app = create_app({"JOB_ROOT": tmp_path / "jobs"}, inference=missing)
    assert upload(app).status_code == 503
    assert results(app) == []
    assert list((tmp_path / "jobs").iterdir()) == []


def test_real_bundled_checkpoint_smoke(tmp_path):
    if importlib.util.find_spec("torch") is None:
        pytest.skip("install requirements-model.txt for the real CPU smoke")
    from app import create_app

    app = create_app({"JOB_ROOT": tmp_path / "jobs"})
    response = upload(app, picture(size=(2, 2)))
    assert response.status_code == 200
    output = app.test_client().get(response.json["result"])
    assert output.status_code == 200
    with Image.open(io.BytesIO(output.data)) as image:
        assert image.size == (8, 8)
        assert image.mode == "RGB"


def test_normalized_input_does_not_retain_uploaded_profile(application):
    source = io.BytesIO()
    Image.new("RGB", (2, 2)).save(
        source, format="PNG", icc_profile=b"private-upload-profile"
    )
    response = upload(application, source.getvalue())
    assert response.status_code == 200
    stored = application.test_client().get(response.json["input"])
    with Image.open(io.BytesIO(stored.data)) as image:
        assert "icc_profile" not in image.info


def test_cleanup_io_failure_does_not_leave_processing_locked(tmp_path, monkeypatch):
    import app as module

    calls = 0

    def once_broken(image):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("model failure")
        return upscaled(image)

    def cannot_remove(path):
        raise OSError("temporary filesystem failure")

    monkeypatch.setattr(module.shutil, "rmtree", cannot_remove)
    app = module.create_app({"JOB_ROOT": tmp_path / "jobs"}, inference=once_broken)
    assert upload(app).is_json
    assert upload(app).status_code == 200
