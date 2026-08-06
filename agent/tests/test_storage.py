from urllib.parse import urlparse, parse_qs

import pytest
from botocore.exceptions import ClientError

from followup_agent import storage
from followup_agent.config import Settings


def _settings(**over) -> Settings:
    base = dict(
        database_url="", openrouter_api_key="", openrouter_model="",
        jwt_signing_key="", jwt_issuer="", jwt_audience="",
        smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
        smtp_from="", followup_age_days=7, client_origin="",
        s3_endpoint_url="https://accountid.r2.cloudflarestorage.com",
        s3_bucket="prospect-resumes",
        s3_access_key_id="test-key-id",
        s3_secret_access_key="test-secret",
        s3_region="auto",
    )
    base.update(over)
    return Settings(**base)


def test_is_configured_true_when_all_values_present():
    assert storage.is_configured(_settings()) is True


def test_is_configured_false_when_bucket_missing():
    assert storage.is_configured(_settings(s3_bucket="")) is False


def test_is_configured_false_when_credentials_missing():
    assert storage.is_configured(_settings(s3_secret_access_key="")) is False


def test_presign_put_builds_a_signed_url_for_the_key():
    # generate_presigned_url signs locally; no network call happens here.
    url = storage.presign_put(_settings(), "resumes/42/abc.pdf", "application/pdf")
    parsed = urlparse(url)
    assert "prospect-resumes" in url
    assert "resumes/42/abc.pdf" in url
    query = parse_qs(parsed.query)
    assert query["X-Amz-Expires"] == ["300"]
    assert "X-Amz-Signature" in query


def test_presign_put_honours_a_custom_expiry():
    url = storage.presign_put(_settings(), "resumes/42/abc.pdf",
                              "application/pdf", expires_in=60)
    assert parse_qs(urlparse(url).query)["X-Amz-Expires"] == ["60"]


def test_operations_raise_when_storage_is_unconfigured():
    unconfigured = _settings(s3_bucket="")
    with pytest.raises(storage.StorageNotConfigured):
        storage.presign_put(unconfigured, "k", "application/pdf")
    with pytest.raises(storage.StorageNotConfigured):
        storage.get_object(unconfigured, "k")
    with pytest.raises(storage.StorageNotConfigured):
        storage.delete_object(unconfigured, "k")


class _Body:
    def __init__(self, data): self._data = data
    def read(self): return self._data


class FakeS3:
    def __init__(self, *, data=b"", error_code=None, content_length=None):
        self._data = data
        self._error_code = error_code
        self._content_length = content_length
        self.deleted = []

    def get_object(self, Bucket, Key):
        if self._error_code:
            raise ClientError({"Error": {"Code": self._error_code}}, "GetObject")
        return {"Body": _Body(self._data)}

    def head_object(self, Bucket, Key):
        if self._error_code:
            raise ClientError({"Error": {"Code": self._error_code}}, "HeadObject")
        return {"ContentLength": self._content_length}

    def delete_object(self, Bucket, Key):
        self.deleted.append(Key)


def test_get_object_returns_the_bytes(monkeypatch):
    monkeypatch.setattr(storage, "_client", lambda s: FakeS3(data=b"%PDF-1.4"))
    assert storage.get_object(_settings(), "resumes/42/a.pdf") == b"%PDF-1.4"


def test_get_object_translates_a_missing_key(monkeypatch):
    monkeypatch.setattr(storage, "_client", lambda s: FakeS3(error_code="NoSuchKey"))
    with pytest.raises(storage.ObjectNotFound):
        storage.get_object(_settings(), "resumes/42/gone.pdf")


def test_get_object_propagates_other_client_errors(monkeypatch):
    monkeypatch.setattr(storage, "_client", lambda s: FakeS3(error_code="AccessDenied"))
    with pytest.raises(ClientError):
        storage.get_object(_settings(), "resumes/42/a.pdf")


def test_delete_object_calls_through(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "_client", lambda s: fake)
    storage.delete_object(_settings(), "resumes/42/old.pdf")
    assert fake.deleted == ["resumes/42/old.pdf"]


def test_object_size_returns_the_content_length(monkeypatch):
    monkeypatch.setattr(storage, "_client",
                        lambda s: FakeS3(content_length=4096))
    assert storage.object_size(_settings(), "resumes/42/a.pdf") == 4096


def test_object_size_translates_a_missing_key(monkeypatch):
    monkeypatch.setattr(storage, "_client", lambda s: FakeS3(error_code="404"))
    with pytest.raises(storage.ObjectNotFound):
        storage.object_size(_settings(), "resumes/42/gone.pdf")
