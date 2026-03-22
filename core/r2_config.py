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

print("R2_ENDPOINT =", repr(R2_ENDPOINT))
print("BUCKET_NAME =", repr(BUCKET_NAME))
print("BASE_URL =", repr(BASE_URL))
print("ACCESS_KEY_LEN =", len(ACCESS_KEY) if ACCESS_KEY else None)

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

try:
    s3.head_bucket(Bucket=BUCKET_NAME)
    print("head_bucket OK")
except Exception as e:
    print("head_bucket failed:", str(e))


def upload_file(file, path: str, content_type: str | None = None):
    print("Uploading to bucket =", repr(BUCKET_NAME))
    print("Uploading key =", repr(path))
    print("Content-Type =", repr(content_type))

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
    print("Deleting from bucket =", repr(BUCKET_NAME))
    print("Deleting key =", repr(path))
    s3.delete_object(Bucket=BUCKET_NAME, Key=path)


def build_file_url(path: str) -> str:
    return f"{BASE_URL}/{path}"


def debug_r2():
    data = {
        "R2_ENDPOINT": R2_ENDPOINT,
        "BUCKET_NAME": BUCKET_NAME,
        "BASE_URL": BASE_URL,
        "ACCESS_KEY_LEN": len(ACCESS_KEY) if ACCESS_KEY else None,
    }

    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        data["head_bucket"] = "OK"
    except Exception as e:
        data["head_bucket"] = str(e)

    try:
        res = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=5)
        data["list_objects"] = "OK"
        data["sample_keys"] = [x["Key"] for x in res.get("Contents", [])]
    except Exception as e:
        data["list_objects"] = str(e)

    return data