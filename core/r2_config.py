"""Provides the R2 Config shared infrastructure module for the backend application."""

import os
import logging
from dotenv import load_dotenv
import boto3
from botocore.client import Config

load_dotenv()
logger = logging.getLogger(__name__)

R2_ENDPOINT = os.getenv("R2_ENDPOINT")
BUCKET_NAME = os.getenv("R2_BUCKET")
ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
SECRET_KEY = os.getenv("R2_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(
        signature_version="s3v4",
        connect_timeout=5,
        read_timeout=15,
    ),
    region_name="auto",
)


def upload_file(file, path: str, content_type: str | None = None):
    logger.info(
        "R2 upload started",
        extra={
            "event": "r2_upload_started",
            "storage_provider": "cloudflare_r2",
            "content_type": content_type,
        },
    )

    kwargs = {
        "Fileobj": file,
        "Bucket": BUCKET_NAME,
        "Key": path,
    }

    if content_type:
        kwargs["ExtraArgs"] = {"ContentType": content_type}

    try:
        s3.upload_fileobj(**kwargs)
    except Exception:
        logger.exception(
            "R2 upload failed",
            extra={
                "event": "r2_upload_failed",
                "storage_provider": "cloudflare_r2",
                "content_type": content_type,
            },
        )
        raise

    logger.info(
        "R2 upload completed",
        extra={
            "event": "r2_upload_completed",
            "storage_provider": "cloudflare_r2",
            "content_type": content_type,
        },
    )
    return path


def delete_file(path: str):
    logger.info(
        "R2 delete started",
        extra={
            "event": "r2_delete_started",
            "storage_provider": "cloudflare_r2",
        },
    )
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=path)
    except Exception:
        logger.exception(
            "R2 delete failed",
            extra={
                "event": "r2_delete_failed",
                "storage_provider": "cloudflare_r2",
            },
        )
        raise

    logger.info(
        "R2 delete completed",
        extra={
            "event": "r2_delete_completed",
            "storage_provider": "cloudflare_r2",
        },
    )


def build_file_url(path: str) -> str:
    return f"{BASE_URL}/{path}"


def debug_r2():
    data = {
        "r2_endpoint_configured": bool(R2_ENDPOINT),
        "r2_bucket_configured": bool(BUCKET_NAME),
        "base_url_configured": bool(BASE_URL),
        "access_key_configured": bool(ACCESS_KEY),
    }

    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        data["head_bucket"] = "OK"
    except Exception as e:
        data["head_bucket"] = str(e)

    try:
        res = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=5)
        data["list_objects"] = "OK"
        data["sample_key_count"] = len(res.get("Contents", []))
    except Exception as e:
        data["list_objects"] = str(e)

    return data
