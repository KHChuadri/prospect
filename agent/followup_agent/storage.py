"""S3-compatible object storage for uploaded résumé PDFs.

Configured against Cloudflare R2 in practice, but the endpoint is an
environment variable, so AWS S3 or a local MinIO need no code change.
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from followup_agent.config import Settings


class StorageNotConfigured(Exception):
    """No bucket or credentials — callers should surface this as a 503."""


class ObjectNotFound(Exception):
    """The key does not exist in the bucket."""


def is_configured(settings: Settings) -> bool:
    return bool(settings.s3_bucket and settings.s3_endpoint_url
                and settings.s3_access_key_id and settings.s3_secret_access_key)


def _client(settings: Settings):
    if not is_configured(settings):
        raise StorageNotConfigured("object storage is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        # R2 only accepts SigV4. Being explicit also keeps presigned URLs
        # stable if botocore changes its default for custom endpoints.
        config=Config(signature_version="s3v4"),
    )


def presign_put(settings: Settings, key: str, content_type: str,
                expires_in: int = 300) -> str:
    """A URL the browser can PUT one specific object to, and nothing else.

    ContentType is part of the signature, so the URL cannot be reused to
    store something that is not a PDF.
    """
    return _client(settings).generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key,
                "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def get_object(settings: Settings, key: str) -> bytes:
    try:
        response = _client(settings).get_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            raise ObjectNotFound(key) from e
        raise
    return response["Body"].read()


def object_size(settings: Settings, key: str) -> int:
    """The object's byte size via HEAD, without reading its body.

    Lets an oversized upload be rejected before it is ever pulled into memory.
    """
    try:
        response = _client(settings).head_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            raise ObjectNotFound(key) from e
        raise
    return response["ContentLength"]


def delete_object(settings: Settings, key: str) -> None:
    _client(settings).delete_object(Bucket=settings.s3_bucket, Key=key)
