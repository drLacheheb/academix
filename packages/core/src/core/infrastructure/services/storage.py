import os
from pathlib import Path
from uuid import uuid4

import httpx
from core.domain.interfaces.services import BaseStorageService
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-storage")


def _build_safe_storage_name(filename: str) -> str:
    suffix = Path(filename).suffix
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    return f"{uuid4().hex}{suffix}"


class LocalStorageService(BaseStorageService):
    def __init__(self, uploads_dir: str, prefix: str | None = None):
        self._uploads_dir = os.path.abspath(uploads_dir)
        self._prefix = prefix.strip("/") if prefix else ""
        os.makedirs(self._uploads_dir, exist_ok=True)

    def upload(self, filename: str, content: bytes) -> str:
        safe_filename = _build_safe_storage_name(filename)
        saved_file_path = os.path.join(self._uploads_dir, safe_filename)

        with open(saved_file_path, "wb") as f:
            f.write(content)

        key = f"{self._prefix}/{safe_filename}" if self._prefix else safe_filename
        logger.info(
            f"LocalStorageService: Uploaded file saved to local path: {saved_file_path}\n"
            f" (key: {key})"
        )
        return key

    def get_local_path(self, uri: str) -> tuple[str, bool]:
        logger.info(f"LocalStorageService: Retrieving local file path for URI: {uri}")
        if os.path.isabs(uri) and os.path.exists(uri):
            return uri, False
        filename = os.path.basename(uri)
        local_path = os.path.join(self._uploads_dir, filename)
        return local_path, False

    def clean_up(self, local_path: str) -> None:
        # Local files are kept in the uploads folder permanently unless explicitly deleted
        pass

    def delete(self, uri: str) -> None:
        if not uri:
            return
        if os.path.isabs(uri) and os.path.exists(uri):
            target = uri
        else:
            filename = os.path.basename(uri)
            target = os.path.join(self._uploads_dir, filename)

        if os.path.exists(target):
            try:
                os.remove(target)
                logger.info(f"LocalStorageService: Permanently deleted local file: {target}")
            except Exception as e:
                logger.warning(f"LocalStorageService: Failed to delete local file {target}: {e}")

    def verify_connection(self) -> None:
        logger.info("LocalStorageService: Verifying uploads directory exists and is writeable...")
        if not os.path.exists(self._uploads_dir):
            raise FileNotFoundError(f"Uploads directory does not exist: {self._uploads_dir}")
        if not os.access(self._uploads_dir, os.W_OK):
            raise PermissionError(f"Uploads directory is not writeable: {self._uploads_dir}")


class S3StorageService(BaseStorageService):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        prefix: str | None = None,
    ):
        self._bucket = bucket_name
        self._access_key = aws_access_key_id
        self._secret_key = aws_secret_access_key
        self._endpoint_url = endpoint_url
        self._region_name = region_name or "us-east-1"
        self._prefix = prefix.strip("/") if prefix else ""

    def _get_client(self):
        import boto3
        from botocore.client import Config

        return boto3.client(
            "s3",
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
            config=Config(signature_version="s3v4"),
        )

    def _extract_key(self, uri: str) -> str:
        if uri.startswith("http://") or uri.startswith("https://"):
            from urllib.parse import urlparse

            path = urlparse(uri).path.lstrip("/")
            if path.startswith(f"{self._bucket}/"):
                path = path[len(self._bucket) + 1 :]
            return path
        return uri

    def upload(self, filename: str, content: bytes) -> str:
        logger.info(f"S3StorageService: Uploading '{filename}' to S3 bucket '{self._bucket}'...")

        s3 = self._get_client()
        safe_filename = _build_safe_storage_name(filename)
        s3_key = f"{self._prefix}/{safe_filename}" if self._prefix else safe_filename

        s3.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=content,
            ContentType="application/pdf",
        )

        logger.info(f"S3StorageService: Upload completed. S3 Key: {s3_key}")
        return s3_key

    def get_local_path(self, uri: str) -> tuple[str, bool]:
        import tempfile

        s3_key = self._extract_key(uri)
        logger.info(f"S3StorageService: Downloading remote CV file for key: '{s3_key}'...")

        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)

        try:
            if uri.startswith("http://") or uri.startswith("https://"):
                with httpx.Client(timeout=60.0) as dl_client:
                    dl_resp = dl_client.get(uri)
                    dl_resp.raise_for_status()
                    temp_file.write(dl_resp.content)
            else:
                s3 = self._get_client()
                s3.download_fileobj(self._bucket, s3_key, temp_file)
        finally:
            temp_file.close()

        logger.info(f"S3StorageService: Downloaded remote file to temp path: {temp_file.name}")
        return temp_file.name, True

    def clean_up(self, local_path: str) -> None:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(
                    f"S3StorageService: Cleaned up and deleted temporary file: {local_path}"
                )
            except Exception as e:
                logger.warning(
                    f"S3StorageService: Failed to delete temporary file {local_path}: {e}"
                )

    def delete(self, uri: str) -> None:
        if not uri:
            return

        s3_key = self._extract_key(uri)
        logger.info(f"S3StorageService: Deleting key '{s3_key}' from S3 bucket '{self._bucket}'...")
        try:
            s3 = self._get_client()
            s3.delete_object(Bucket=self._bucket, Key=s3_key)
            logger.info(
                f"S3StorageService: Key '{s3_key}' deleted successfully from bucket"
                f" '{self._bucket}'."
            )
        except Exception as e:
            logger.warning(f"S3StorageService: Failed to delete S3 object '{s3_key}': {e}")

    def verify_connection(self) -> None:
        logger.info(f"S3StorageService: Verifying connection to S3 bucket '{self._bucket}'...")
        s3 = self._get_client()
        s3.list_objects_v2(Bucket=self._bucket, MaxKeys=1)
        logger.info("S3StorageService: Connection verified successfully!")


def get_storage_service_from_env() -> BaseStorageService:
    provider = os.environ.get("STORAGE_PROVIDER", "local").lower()
    prefix = os.environ.get("STORAGE_PREFIX") or os.environ.get("STORAGE_PATH_PREFIX")
    if provider == "s3":
        bucket_name = os.environ.get("S3_BUCKET_NAME") or os.environ.get("AWS_S3_BUCKET_NAME")
        if not bucket_name:
            raise RuntimeError("S3_BUCKET_NAME env variable is required when STORAGE_PROVIDER=s3")
        aws_access_key_id = os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get(
            "AWS_ACCESS_KEY_ID", ""
        )
        aws_secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get(
            "AWS_SECRET_ACCESS_KEY", ""
        )
        endpoint_url = os.environ.get("S3_ENDPOINT_URL") or os.environ.get("AWS_S3_ENDPOINT_URL")
        region_name = os.environ.get("S3_REGION") or os.environ.get(
            "AWS_DEFAULT_REGION", "us-east-1"
        )

        return S3StorageService(
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
            prefix=prefix,
        )
    else:
        uploads_dir = os.environ.get("UPLOADS_DIR", "uploads")
        return LocalStorageService(uploads_dir=uploads_dir, prefix=prefix)
