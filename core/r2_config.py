import os
from dotenv import load_dotenv
import boto3
from botocore.client import Config

load_dotenv()

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
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def upload_file(file, path: str, content_type: str | None = None):
    """
    Upload a file object to R2.
    """
    kwargs = {
        "Fileobj": file,
        "Bucket": BUCKET_NAME,
        "Key": path,
    }

    if content_type:
        kwargs["ExtraArgs"] = {"ContentType": content_type}

    s3.upload_fileobj(**kwargs)
    return path


def delete_file(path: str):
    """
    Delete a file from R2 by object key/path.
    """
    s3.delete_object(Bucket=BUCKET_NAME, Key=path)


def build_file_url(path: str) -> str:
    return f"{BASE_URL}/{path}"