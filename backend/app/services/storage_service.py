import os
import boto3
from botocore.exceptions import ClientError
from backend.app.core.config import settings


class StorageService:
    """S3/MinIO storage wrapper with transparent local file fallback."""

    @staticmethod
    def _get_s3_client():
        """Build and return an S3/MinIO client, or None if not configured."""
        if not settings.S3_ENDPOINT_URL or not settings.S3_ACCESS_KEY:
            return None
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )

    @classmethod
    def ensure_bucket_exists(cls) -> bool:
        """Create the configured S3/MinIO bucket if it does not exist."""
        client = cls._get_s3_client()
        if not client or not settings.S3_BUCKET:
            return False
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
        except ClientError:
            try:
                client.create_bucket(Bucket=settings.S3_BUCKET)
                return True
            except ClientError as create_err:
                print(f"StorageService: Could not create bucket '{settings.S3_BUCKET}': {create_err}")
                return False
        return True

    @classmethod
    def upload_file(cls, local_path: str, s3_key: str) -> str:
        """
        Upload a local file to S3/MinIO.
        Returns the storage URL on success, or the local path as fallback.
        """
        client = cls._get_s3_client()
        if not client or not settings.S3_BUCKET:
            return local_path  # transparent local fallback

        cls.ensure_bucket_exists()
        try:
            client.upload_file(local_path, settings.S3_BUCKET, s3_key)
            return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET}/{s3_key}"
        except ClientError as e:
            print(f"StorageService: S3 upload failed for '{s3_key}': {e}. Falling back to local path.")
            return local_path

    @classmethod
    def get_url(cls, s3_key: str) -> str:
        """
        Generate a pre-signed URL for an existing S3/MinIO object.
        Falls back to a local media URL if S3 is not configured.
        """
        client = cls._get_s3_client()
        if not client or not settings.S3_BUCKET:
            return f"/media/{s3_key}"

        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
                ExpiresIn=3600,
            )
            return url
        except ClientError as e:
            print(f"StorageService: Presigned URL generation failed for '{s3_key}': {e}")
            return f"/media/{s3_key}"

    @classmethod
    def delete_file(cls, s3_key: str) -> bool:
        """Delete an object from S3/MinIO. Returns True on success."""
        client = cls._get_s3_client()
        if not client or not settings.S3_BUCKET:
            # Try to delete locally
            local_path = os.path.join(settings.MEDIA_DIR, s3_key)
            if os.path.exists(local_path):
                os.remove(local_path)
                return True
            return False
        try:
            client.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
            return True
        except ClientError as e:
            print(f"StorageService: Delete failed for '{s3_key}': {e}")
            return False
