import os
import time
import logging
import httpx
from core.domain.interfaces.services import BaseStorageService

logger = logging.getLogger(__name__)


class LocalStorageService(BaseStorageService):
    def __init__(self, uploads_dir: str):
        self._uploads_dir = os.path.abspath(uploads_dir)
        os.makedirs(self._uploads_dir, exist_ok=True)

    def upload(self, filename: str, content: bytes) -> str:
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{filename}"
        saved_file_path = os.path.join(self._uploads_dir, safe_filename)
        
        with open(saved_file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"LocalStorageService: Uploaded file saved to local path: {saved_file_path}")
        return saved_file_path

    def get_local_path(self, uri: str) -> tuple[str, bool]:
        logger.info(f"LocalStorageService: Retrieving local file path for URI: {uri}")
        return uri, False

    def clean_up(self, local_path: str) -> None:
        # Local files are kept in the uploads folder permanently
        pass

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
    ):
        self._bucket = bucket_name
        self._access_key = aws_access_key_id
        self._secret_key = aws_secret_access_key
        self._endpoint_url = endpoint_url
        self._region_name = region_name or "us-east-1"

    def upload(self, filename: str, content: bytes) -> str:
        import boto3
        from botocore.client import Config

        logger.info(f"S3StorageService: Uploading '{filename}' to S3 bucket '{self._bucket}'...")
        
        s3 = boto3.client(
            "s3",
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
            config=Config(signature_version="s3v4"),
        )
        
        timestamp = int(time.time())
        s3_key = f"{timestamp}_{filename}"
        
        s3.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=content,
            ContentType="application/pdf",
        )
        
        # Generate S3 Presigned URL for GET request valid for 1 hour (3600 seconds)
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": s3_key},
            ExpiresIn=3600,
        )
            
        logger.info("S3StorageService: Upload completed. Presigned URL generated successfully.")
        return url

    def get_local_path(self, uri: str) -> tuple[str, bool]:
        import tempfile
        logger.info(f"S3StorageService: Downloading remote CV file from URL: {uri}...")
        
        with httpx.Client(timeout=60.0) as dl_client:
            dl_resp = dl_client.get(uri)
            dl_resp.raise_for_status()
            cv_bytes = dl_resp.content
            
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        temp_file.write(cv_bytes)
        temp_file.close()
        
        logger.info(f"S3StorageService: Successfully downloaded remote file to temporary local path: {temp_file.name}")
        return temp_file.name, True

    def clean_up(self, local_path: str) -> None:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"S3StorageService: Cleaned up and deleted temporary file: {local_path}")
            except Exception as e:
                logger.warning(f"S3StorageService: Failed to delete temporary file {local_path}: {e}")

    def verify_connection(self) -> None:
        import boto3
        logger.info(f"S3StorageService: Verifying connection to S3 bucket '{self._bucket}'...")
        
        s3 = boto3.client(
            "s3",
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
        )
        
        # Test credentials and connection by listing up to 1 key
        s3.list_objects_v2(Bucket=self._bucket, MaxKeys=1)
        logger.info("S3StorageService: Connection verified successfully!")


def get_storage_service_from_env() -> BaseStorageService:
    provider = os.environ.get("STORAGE_PROVIDER", "local").lower()
    if provider == "s3":
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        if not bucket_name:
            raise RuntimeError("S3_BUCKET_NAME env variable is required when STORAGE_PROVIDER=s3")
        aws_access_key_id = os.environ.get("S3_ACCESS_KEY_ID", "")
        aws_secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY", "")
        endpoint_url = os.environ.get("S3_ENDPOINT_URL")
        region_name = os.environ.get("S3_REGION")
        
        return S3StorageService(
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )
    else:
        uploads_dir = os.environ.get("UPLOADS_DIR", "uploads")
        return LocalStorageService(uploads_dir=uploads_dir)
