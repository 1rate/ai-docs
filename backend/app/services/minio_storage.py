from functools import lru_cache
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


@lru_cache
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio_client()
    bucket = settings.minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(
    *,
    storage_key: str,
    data: BinaryIO,
    length: int,
    content_type: Optional[str],
) -> None:
    ensure_bucket()
    get_minio_client().put_object(
        settings.minio_bucket,
        storage_key,
        data,
        length=length,
        content_type=content_type or "application/octet-stream",
    )


def delete_file(storage_key: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(settings.minio_bucket, storage_key)
    except S3Error:
        pass


def download_file(storage_key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, storage_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()

