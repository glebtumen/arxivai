"""Yandex Object Storage (S3-compatible) client and upload/delete helpers."""

import logging
import mimetypes
from functools import lru_cache

import boto3

from ..config import settings

logger = logging.getLogger(__name__)


class S3Error(Exception):
    pass


@lru_cache(maxsize=1)
def _get_client():
    session = boto3.session.Session()
    return session.client(
        service_name="s3",
        endpoint_url=settings.s3_yandex_endpoint,
        region_name=settings.s3_yandex_region,
        aws_access_key_id=settings.s3_yandex_ident_key,
        aws_secret_access_key=settings.s3_yandex_secret_key,
    )


def public_url(key: str) -> str:
    """Build the public URL for an object, assuming a public-read bucket."""
    bucket = settings.s3_yandex_bucket
    return f"https://{bucket}.storage.yandexcloud.net/{key}"


def upload_file(local_path: str, key: str, content_type: str | None = None) -> str:
    """
    Uploads `local_path` to the configured bucket under `key`, marks the
    object public-read, and returns its public URL.
    """
    if content_type is None:
        content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    client = _get_client()
    try:
        client.upload_file(
            Filename=local_path,
            Bucket=settings.s3_yandex_bucket,
            Key=key,
            ExtraArgs={"ACL": "public-read", "ContentType": content_type},
        )
    except Exception as e:
        raise S3Error(f"Failed to upload {local_path!r} to key {key!r}: {e}") from e

    return public_url(key)


def delete_object(key: str) -> None:
    """Best-effort delete of an object; logs but does not raise on failure."""
    client = _get_client()
    try:
        client.delete_object(Bucket=settings.s3_yandex_bucket, Key=key)
    except Exception as e:
        logger.warning("Could not delete S3 object %r: %s", key, e)
