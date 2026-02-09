"""
Upload strategies for handling images during Notion import.
Supports: AWS S3, Google Cloud Storage, Notion Native Upload.

Each strategy handles image upload differently to solve the 404 problem.
"""
import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import requests

from .constants import S3_PRESIGNED_URL_EXPIRY
from .models import StrategyConfig, UploadMode


class UploadStrategy(ABC):
    """Base class for image upload strategies"""
    
    @abstractmethod
    def prepare(self, source_dir: Path) -> str:
        """
        Prepare upload strategy (start tunnel, init CDN client, etc.)
        
        Returns:
            Base URL for images (or empty string if not applicable)
        """
        pass
    
    @abstractmethod
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """
        Upload a single image and return accessible URL.
        
        Args:
            local_path: Path to local image file
            context: Import context (source_dir, page_id, etc.)
        
        Returns:
            URL that Notion can fetch the image from
        """
        pass
    
    @abstractmethod
    def cleanup(self, failed_count: int = 0):
        """
        Cleanup resources after import.
        
        Args:
            failed_count: Number of pages with failed images (may affect keepalive)
        """
        pass
    
    @abstractmethod
    def needs_keepalive(self) -> bool:
        """Does this strategy need keepalive waiting?"""
        pass
    
    def get_name(self) -> str:
        """Strategy name for logging"""
        return self.__class__.__name__
    
    def _get_content_type(self, path: Path) -> str:
        """Get MIME type from file extension"""
        types = {
            # Images
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
            
            # Videos
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            
            # Documents
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            
            # Text files
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.md': 'text/markdown',
            
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
            
            # Draw.io
            '.drawio': 'application/xml',
            
            # Other
            '.rtf': 'application/rtf',
            '.epub': 'application/epub+zip',
        }
        mime_type = types.get(path.suffix.lower(), 'application/octet-stream')
        
        # Log file types that are being uploaded
        if path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']:
            print(f"  [dim]Uploading {path.suffix} file with MIME type: {mime_type}[/dim]")
            
        return mime_type


class S3TempStrategy(UploadStrategy):
    """
    S3 with auto-delete lifecycle rules (RECOMMENDED).
    
    Uploads to S3 with:
    - Temporary storage prefix (notion-temp/)
    - Lifecycle rule: auto-delete after 1 day
    - Pre-signed URLs (expire in 1 hour)
    
    Pros:
    - Auto-deletes via S3 lifecycle rules (reliable!)
    - You control the infrastructure
    - Very reliable (99.99% uptime)
    - Fast CDN delivery
    - Cheap (~$0.001 for temp storage)
    
    Cons:
    - Requires AWS account setup (15 min)
    - Tiny cost (~$0.001 vs free)
    
    Best for: Production imports (100-1000+ pages)
    """
    
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str, 
                 lifecycle_days: int = 1, use_presigned: bool = True):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.lifecycle_days = lifecycle_days
        self.use_presigned = use_presigned
        self.client = None
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        from src.models.errors import UploadError, ErrorCode
        
        # Explicitly use signature v4 and set appropriate timeouts
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        
        self.client = boto3.client('s3',
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=config
        )
        
        # Verify bucket exists and check region
        try:
            response = self.client.get_bucket_location(Bucket=self.bucket)
            bucket_region = response.get('LocationConstraint')
            # AWS returns None for us-east-1
            if bucket_region is None:
                bucket_region = 'us-east-1'
            if bucket_region != self.region:
                raise UploadError(
                    ErrorCode.CONFIG_S3_REGION_MISMATCH,
                    f"Bucket '{self.bucket}' is in region '{bucket_region}' but config specifies '{self.region}'",
                    "Update your S3 region in settings to match the bucket location"
                )
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                raise UploadError(
                    ErrorCode.CONFIG_MISSING_S3,
                    f"S3 bucket '{self.bucket}' not found",
                    "Check bucket name and ensure you have access"
                )
            raise
        
        # Test if public access works for notion-temp prefix
        import requests
        test_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/notion-temp/test.txt"
        try:
            # Just check if we get 403 vs 404 (403 = no public access, 404 = public access ok)
            resp = requests.head(test_url, timeout=2)
            if resp.status_code == 403:
                print(f"[yellow]⚠️  Warning: S3 bucket may not have public read access for notion-temp/*[/yellow]")
                print(f"[yellow]   Notion might show 'Invalid image url' errors[/yellow]")
                print(f"[yellow]   To fix: Add bucket policy allowing public read for notion-temp/* prefix[/yellow]")
        except:
            # Network error or timeout, skip the check
            pass
        
        print(f"[green]Using S3 Auto-Delete: {self.bucket} ({self.region})[/green]")
        print(f"[green]  Files will auto-delete after {self.lifecycle_days} day(s)[/green]")
        print(f"[dim]  Using signature version: s3v4[/dim]")
        return ""
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """Upload to S3 temp prefix and return URL (auto-deletes via lifecycle)"""
        
        # Generate unique key with timestamp and hash
        content_hash = hashlib.md5(local_path.read_bytes()).hexdigest()[:12]
        timestamp = int(time.time())
        # Use notion-temp/ prefix for lifecycle rule targeting
        key = f'notion-temp/{timestamp}/{content_hash}/{local_path.name}'
        
        # Upload
        with open(local_path, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=f.read(),
                ContentType=self._get_content_type(local_path)
            )
        
        self.uploaded_count += 1
        
        # Generate URL
        # For notion-temp prefix, always use public URL (bucket policy allows public read)
        # This avoids issues with Notion's HEAD request validation
        if key.startswith('notion-temp/'):
            url = f'https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}'
        elif self.use_presigned:
            # Presigned URL for other prefixes
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=S3_PRESIGNED_URL_EXPIRY
            )
        else:
            # Public URL (requires bucket to be public-read)
            url = f'https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}'
        
        print(f"  [dim]→ S3 temp ({self.uploaded_count}): {local_path.name}[/dim]")
        return url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} images to S3 (temp storage)[/green]")
        print(f"[green]  S3 lifecycle will auto-delete after {self.lifecycle_days} day(s)[/green]")
        print(f"[cyan]  Set lifecycle rule in S3 console if not already configured[/cyan]")
    
    def needs_keepalive(self) -> bool:
        return False  # URLs valid for 1 hour, lifecycle deletes after 1 day


class S3PermanentStrategy(UploadStrategy):
    """
    AWS S3 upload strategy (PERMANENT storage).
    
    Pros: Permanent, reliable, fast
    Cons: Requires AWS account, storage costs, manual cleanup
    
    Use S3TempStrategy instead for auto-delete!
    """
    
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.client = None
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        import boto3
        
        self.client = boto3.client('s3',
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
        
        print(f"[green]Using AWS S3: {self.bucket} ({self.region})[/green]")
        return ""
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """Upload to S3 and return permanent URL"""
        
        # Generate unique key with hash (avoid collisions)
        content_hash = hashlib.md5(local_path.read_bytes()).hexdigest()[:12]
        timestamp = int(time.time())
        key = f'notion-imports/{timestamp}/{content_hash}/{local_path.name}'
        
        # Upload
        with open(local_path, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=f.read(),
                ContentType=self._get_content_type(local_path),
                ACL='public-read'  # Make publicly accessible
            )
        
        self.uploaded_count += 1
        cdn_url = f'https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}'
        
        print(f"  [dim]→ S3 ({self.uploaded_count}): {local_path.name}[/dim]")
        return cdn_url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} images to S3[/green]")
        print(f"[yellow]⚠ Images stored permanently - remember to delete old imports![/yellow]")
    
    def needs_keepalive(self) -> bool:
        return False


class GCSStrategy(UploadStrategy):
    """
    Google Cloud Storage upload strategy.
    
    Supports two authentication modes:
    1. Local signing: Uses service account JSON file (credentials never leave your machine)
    2. Impersonation: Uses ADC + service account impersonation (no local JSON needed)
    
    Supports auto-delete via lifecycle rules.
    
    Pros:
    - Reliable (99.9% uptime)
    - Supports lifecycle auto-delete
    - Good for Google Cloud users
    - Impersonation mode works without local credential files
    
    Cons:
    - Requires GCP account and service account setup
    - Impersonation requires iam.serviceAccountTokenCreator role
    """
    
    def __init__(self, bucket: str, project_id: str, credentials_path: str = "",
                 lifecycle_days: int = 1, use_impersonation: bool = False,
                 impersonate_service_account: str = ""):
        self.bucket_name = bucket
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.lifecycle_days = lifecycle_days
        self.use_impersonation = use_impersonation
        self.impersonate_service_account = impersonate_service_account
        self.client = None
        self.bucket = None
        self.uploaded_count = 0
        self._signing_credentials = None  # For signed URL generation
    
    def _run_gcloud_adc_login(self) -> bool:
        """
        Run gcloud auth application-default login to trigger browser authentication.
        Returns True if successful, False otherwise.
        """
        import subprocess
        import shutil
        
        gcloud_path = shutil.which('gcloud')
        if not gcloud_path:
            print("[yellow]gcloud CLI not found. Please install Google Cloud SDK.[/yellow]")
            print("[yellow]  https://cloud.google.com/sdk/docs/install[/yellow]")
            return False
        
        print("[cyan]Opening browser for Google Cloud authentication...[/cyan]")
        print("[dim]  Please complete the login in your browser.[/dim]")
        
        try:
            # Run gcloud auth application-default login
            # This will open browser and wait for user to complete auth
            result = subprocess.run(
                [gcloud_path, 'auth', 'application-default', 'login'],
                capture_output=False,  # Let it show output to user
                text=True
            )
            
            if result.returncode == 0:
                print("[green]✓ Google Cloud authentication successful![/green]")
                return True
            else:
                print("[red]✗ Google Cloud authentication failed or was cancelled.[/red]")
                return False
                
        except Exception as e:
            print(f"[red]✗ Failed to run gcloud auth: {str(e)}[/red]")
            return False
    
    def _get_adc_credentials(self):
        """
        Get ADC credentials, triggering browser auth if needed.
        Returns (credentials, project) tuple or raises UploadError.
        """
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError
        from src.models.errors import UploadError, ErrorCode
        
        try:
            return google.auth.default()
        except DefaultCredentialsError:
            # ADC not configured - trigger browser authentication
            print("[yellow]Google Cloud ADC not configured.[/yellow]")
            print("[yellow]Starting browser authentication...[/yellow]")
            
            if self._run_gcloud_adc_login():
                # Retry after successful auth
                try:
                    return google.auth.default()
                except DefaultCredentialsError:
                    raise UploadError(
                        ErrorCode.CONFIG_GCS_ADC_AUTH_FAILED,
                        "ADC still not available after authentication",
                        "Try running manually: gcloud auth application-default login"
                    )
            else:
                raise UploadError(
                    ErrorCode.CONFIG_GCS_ADC_NOT_CONFIGURED,
                    "Google Cloud ADC authentication required",
                    "Run: gcloud auth application-default login"
                )
    
    def prepare(self, source_dir: Path) -> str:
        from src.models.errors import UploadError, ErrorCode
        
        try:
            from google.cloud import storage
        except ModuleNotFoundError:
            raise UploadError(
                ErrorCode.CONFIG_MISSING_GCS_LIBRARY,
                "Google Cloud libraries not installed",
                "Run: pip install google-cloud-storage google-auth"
            )
        
        try:
            if self.use_impersonation:
                # Impersonation mode: use ADC + impersonate service account
                from google.auth import impersonated_credentials
                from google.auth.exceptions import RefreshError
                
                # Get source credentials from ADC (triggers browser auth if needed)
                source_credentials, _ = self._get_adc_credentials()
                
                # Create impersonated credentials
                target_credentials = impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=self.impersonate_service_account,
                    target_scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                self.client = storage.Client(
                    project=self.project_id,
                    credentials=target_credentials
                )
                self._signing_credentials = target_credentials
                auth_mode = f"impersonating {self.impersonate_service_account}"
                
                # Test impersonation by trying to access the bucket
                # This will fail early if impersonation permissions are missing or credentials expired
                try:
                    self.bucket = self.client.bucket(self.bucket_name)
                    # Force a refresh to test impersonation
                    _ = self.bucket.exists()
                except RefreshError as e:
                    error_str = str(e)
                    
                    # Check if reauthentication is needed (expired credentials)
                    if "Reauthentication is needed" in error_str or "reauth" in error_str.lower():
                        print(f"[yellow][{ErrorCode.CONFIG_GCS_ADC_EXPIRED.value}] Google Cloud credentials expired.[/yellow]")
                        print("[yellow]Starting browser authentication...[/yellow]")
                        
                        if self._run_gcloud_adc_login():
                            # Retry after successful reauthentication
                            print(f"[green][{ErrorCode.CONFIG_GCS_ADC_REAUTH_SUCCESS.value}] Reauthentication successful![/green]")
                            print("[cyan]Retrying GCS connection...[/cyan]")
                            # Recreate credentials and client after reauth
                            source_credentials, _ = self._get_adc_credentials()
                            target_credentials = impersonated_credentials.Credentials(
                                source_credentials=source_credentials,
                                target_principal=self.impersonate_service_account,
                                target_scopes=['https://www.googleapis.com/auth/cloud-platform']
                            )
                            self.client = storage.Client(
                                project=self.project_id,
                                credentials=target_credentials
                            )
                            self._signing_credentials = target_credentials
                            self.bucket = self.client.bucket(self.bucket_name)
                            # Test again
                            _ = self.bucket.exists()
                        else:
                            raise UploadError(
                                ErrorCode.CONFIG_GCS_ADC_AUTH_FAILED,
                                "Browser reauthentication failed or was cancelled",
                                "Run manually: gcloud auth application-default login"
                            )
                    elif "Gaia id not found" in error_str or "Unable to acquire impersonated credentials" in error_str:
                        # Service account not found or user identity not recognized
                        raise UploadError(
                            ErrorCode.CONFIG_GCS_SA_NOT_FOUND,
                            f"Cannot find service account or your identity",
                            f"1. Verify SA email is correct: {self.impersonate_service_account}\n"
                            f"   2. Ensure SA exists in the project\n"
                            f"   3. Grant roles/iam.serviceAccountTokenCreator with: gcloud iam service-accounts add-iam-policy-binding {self.impersonate_service_account} --member='user:YOUR_EMAIL' --role='roles/iam.serviceAccountTokenCreator'"
                        )
                    elif "iam.serviceAccounts.getAccessToken" in error_str or "permission" in error_str.lower():
                        raise UploadError(
                            ErrorCode.CONFIG_GCS_IMPERSONATION_FAILED,
                            f"Cannot impersonate {self.impersonate_service_account}",
                            "Grant roles/iam.serviceAccountTokenCreator to your account on the target SA"
                        )
                    else:
                        raise
                    
            else:
                # Local signing mode: use service account JSON file
                from google.oauth2 import service_account
                
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                self.client = storage.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                self._signing_credentials = credentials
                auth_mode = "service account for local signing"
                self.bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise UploadError(
                    ErrorCode.CONFIG_MISSING_GCS,
                    f"GCS bucket '{self.bucket_name}' not found",
                    "Check bucket name and service account permissions"
                )
            
            print(f"[green]Using GCS: {self.bucket_name} (project: {self.project_id})[/green]")
            print(f"[green]  Files will auto-delete after {self.lifecycle_days} day(s)[/green]")
            print(f"[dim]  Using {auth_mode}[/dim]")
            return ""
            
        except UploadError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            error_str = str(e)
            error_module = str(type(e).__module__)
            
            # Check for reauthentication needed
            if "Reauthentication is needed" in error_str or "reauth" in error_str.lower():
                print(f"[yellow][{ErrorCode.CONFIG_GCS_ADC_EXPIRED.value}] Google Cloud credentials expired.[/yellow]")
                print("[yellow]Starting browser authentication...[/yellow]")
                
                if self._run_gcloud_adc_login():
                    raise UploadError(
                        ErrorCode.CONFIG_GCS_ADC_REAUTH_SUCCESS,
                        "Reauthentication completed successfully",
                        "Credentials have been refreshed - please retry the import"
                    )
                else:
                    raise UploadError(
                        ErrorCode.CONFIG_GCS_ADC_AUTH_FAILED,
                        "Browser reauthentication failed or was cancelled",
                        "Run manually: gcloud auth application-default login"
                    )
            
            # Check for specific Google auth errors
            if "Gaia id not found" in error_str or "Unable to acquire impersonated credentials" in error_str:
                raise UploadError(
                    ErrorCode.CONFIG_GCS_SA_NOT_FOUND,
                    f"Cannot find service account or your identity",
                    f"1. Verify SA email is correct: {self.impersonate_service_account}\n"
                    f"   2. Ensure SA exists in the project\n"
                    f"   3. Grant permission: gcloud iam service-accounts add-iam-policy-binding {self.impersonate_service_account} --member='user:YOUR_EMAIL' --role='roles/iam.serviceAccountTokenCreator'"
                )
            
            if "iam.serviceAccounts.getAccessToken" in error_str:
                raise UploadError(
                    ErrorCode.CONFIG_GCS_IMPERSONATION_FAILED,
                    f"Cannot impersonate {self.impersonate_service_account}",
                    "Grant roles/iam.serviceAccountTokenCreator to your account on the target SA"
                )
            
            if "google" in error_module:
                hint = "Check credentials and permissions"
                if self.use_impersonation:
                    hint = "Check ADC setup and iam.serviceAccountTokenCreator role"
                raise UploadError(
                    ErrorCode.CONFIG_INVALID_GCS,
                    f"GCS initialization failed: {error_str}",
                    hint
                )
            raise
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """Upload to GCS and return public URL.
        
        Note: Bucket must have public access enabled:
          gcloud storage buckets update gs://BUCKET --no-public-access-prevention
          gcloud storage buckets add-iam-policy-binding gs://BUCKET --member=allUsers --role=roles/storage.objectViewer
        """
        # Generate unique key with timestamp and hash (unguessable)
        content_hash = hashlib.md5(local_path.read_bytes()).hexdigest()[:12]
        timestamp = int(time.time())
        # Use notion-temp/ prefix for lifecycle rule targeting
        key = f'notion-temp/{timestamp}/{content_hash}/{local_path.name}'
        
        blob = self.bucket.blob(key)
        
        # Upload file
        blob.upload_from_filename(
            str(local_path),
            content_type=self._get_content_type(local_path)
        )
        
        self.uploaded_count += 1
        
        # Use public URL (same approach as S3 - Notion rejects signed URLs)
        # Bucket must be configured for public read access
        public_url = f"https://storage.googleapis.com/{self.bucket_name}/{key}"
        
        # Debug: print first URL to verify format
        if self.uploaded_count == 1:
            print(f"  [cyan]First public URL: {public_url}[/cyan]")
        
        print(f"  [dim]→ GCS ({self.uploaded_count}): {local_path.name}[/dim]")
        return public_url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} files to GCS[/green]")
        print(f"[green]  GCS lifecycle will auto-delete after {self.lifecycle_days} day(s)[/green]")
        print(f"[cyan]  Set lifecycle rule in GCS console if not already configured[/cyan]")
    
    def needs_keepalive(self) -> bool:
        return False


class NotionNativeStrategy(UploadStrategy):
    """
    Notion native file upload strategy.
    
    Uploads files directly to Notion's storage using their file upload API.
    Images become permanently hosted by Notion (no external dependencies).
    
    API Flow:
    1. Create file upload: POST /v1/file_uploads
    2. Send file contents: POST /v1/file_uploads/{id}/send
    3. Return special URL scheme for block creation to use file_upload type
    
    Pros:
    - Images are permanently hosted by Notion
    - No external storage costs
    - No URL expiration issues
    
    Cons:
    - Requires Notion API token
    - 20MB max per file (single-part upload)
    - Files must be attached within 1 hour of upload
    """
    
    # Special URL scheme to indicate Notion native upload
    # Block creation code checks for this and uses file_upload type
    NATIVE_URL_SCHEME = "notion-file-upload://"
    
    def __init__(self, notion_token: str):
        self.notion_token = notion_token
        self.uploaded_count = 0
        self.api_base = "https://api.notion.com/v1"
        # Use latest API version for file_upload support
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2025-09-03"
        }
    
    # Notion's file size limit (20MB)
    MAX_FILE_SIZE_MB = 20
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    def prepare(self, source_dir: Path) -> str:
        """Validate Notion token and scan for oversized files"""
        print("[cyan]Using Notion Native Upload (files hosted by Notion)[/cyan]")
        
        # Test the token by making a simple API call
        try:
            response = requests.get(
                f"{self.api_base}/users/me",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 401:
                from .models import UploadError, ErrorCode
                raise UploadError(
                    ErrorCode.UPLOAD_STRATEGY_FAILED,
                    "Notion token is invalid or expired",
                    "Check your Notion integration token"
                )
            elif response.status_code != 200:
                from .models import UploadError, ErrorCode
                raise UploadError(
                    ErrorCode.UPLOAD_STRATEGY_FAILED,
                    f"Notion API error: {response.status_code}",
                    response.text[:200]
                )
            print("[green]✓ Notion token validated[/green]")
        except requests.RequestException as e:
            from .models import UploadError, ErrorCode
            raise UploadError(
                ErrorCode.UPLOAD_STRATEGY_FAILED,
                "Failed to connect to Notion API",
                str(e)
            )
        
        # Scan for files exceeding Notion's 20MB limit
        self._scan_oversized_files(source_dir)
        
        return ""
    
    def _scan_oversized_files(self, source_dir: Path) -> None:
        """Scan attachments folder for files exceeding Notion's 20MB limit"""
        attachments_dir = source_dir / "attachments"
        if not attachments_dir.exists():
            return
        
        oversized_files = []
        
        # Common media file extensions
        media_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', 
                          '.mp4', '.mov', '.avi', '.webm', '.mp3', '.wav',
                          '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                          '.zip', '.tar', '.gz', '.rar'}
        
        for file_path in attachments_dir.rglob('*'):
            if file_path.is_file():
                # Check if it's a media/attachment file
                if file_path.suffix.lower() in media_extensions or file_path.parent.name != "attachments":
                    try:
                        size = file_path.stat().st_size
                        if size > self.MAX_FILE_SIZE_BYTES:
                            size_mb = size / (1024 * 1024)
                            oversized_files.append((file_path.name, size_mb))
                    except OSError:
                        pass
        
        if oversized_files:
            print(f"\n[yellow]⚠ Warning: {len(oversized_files)} file(s) exceed Notion's {self.MAX_FILE_SIZE_MB}MB limit:[/yellow]")
            # Sort by size descending
            oversized_files.sort(key=lambda x: x[1], reverse=True)
            for name, size_mb in oversized_files[:10]:  # Show first 10
                print(f"  [yellow]• {name} ({size_mb:.1f} MB)[/yellow]")
            if len(oversized_files) > 10:
                print(f"  [yellow]... and {len(oversized_files) - 10} more[/yellow]")
            print(f"[yellow]  These files will be skipped during upload.[/yellow]\n")
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """
        Upload file to Notion and return special URL with file_upload ID.
        
        Returns:
            URL in format: notion-file-upload://{file_upload_id}
            This signals block creation to use file_upload type instead of external.
        """
        from .models import UploadError, ErrorCode
        
        # Check file size before uploading
        try:
            file_size = local_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                raise UploadError(
                    ErrorCode.NOTION_FILE_SIZE_EXCEEDED,
                    f"File exceeds Notion's {self.MAX_FILE_SIZE_MB}MB limit",
                    f"{local_path.name} is {size_mb:.1f} MB"
                )
        except OSError as e:
            raise UploadError(
                ErrorCode.UPLOAD_INVALID_PATH,
                f"Cannot read file: {local_path.name}",
                str(e)
            )
        
        # Step 1: Create file upload object
        try:
            create_response = requests.post(
                f"{self.api_base}/file_uploads",
                headers={**self.headers, "Content-Type": "application/json"},
                json={},
                timeout=30
            )
            
            if create_response.status_code != 200:
                raise UploadError(
                    ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                    f"Failed to create file upload: {create_response.status_code}",
                    create_response.text[:200]
                )
            
            upload_data = create_response.json()
            file_upload_id = upload_data.get("id")
            upload_url = upload_data.get("upload_url")
            
            if not file_upload_id or not upload_url:
                raise UploadError(
                    ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                    "Invalid response from Notion file upload API",
                    str(upload_data)[:200]
                )
        except requests.RequestException as e:
            raise UploadError(
                ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                "Network error creating file upload",
                str(e)
            )
        
        # Step 2: Send file contents
        try:
            content_type = self._get_content_type(local_path)
            
            with open(local_path, 'rb') as f:
                files = {
                    'file': (local_path.name, f, content_type)
                }
                
                # Use upload_url directly (includes the file_upload_id)
                send_response = requests.post(
                    upload_url,
                    headers={
                        "Authorization": self.headers["Authorization"],
                        "Notion-Version": self.headers["Notion-Version"]
                    },
                    files=files,
                    timeout=120  # Longer timeout for file upload
                )
            
            if send_response.status_code != 200:
                raise UploadError(
                    ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                    f"Failed to upload file: {send_response.status_code}",
                    send_response.text[:200]
                )
            
            result = send_response.json()
            if result.get("status") == "expired":
                raise UploadError(
                    ErrorCode.NOTION_FILE_UPLOAD_EXPIRED,
                    "File upload expired before attachment",
                    "Files must be attached within 1 hour of upload"
                )
            elif result.get("status") != "uploaded":
                raise UploadError(
                    ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                    f"File upload status: {result.get('status')}",
                    str(result)[:200]
                )
                
        except requests.RequestException as e:
            raise UploadError(
                ErrorCode.NOTION_FILE_UPLOAD_FAILED,
                "Network error uploading file",
                str(e)
            )
        
        self.uploaded_count += 1
        
        # Return special URL scheme that signals native upload
        native_url = f"{self.NATIVE_URL_SCHEME}{file_upload_id}"
        
        if self.uploaded_count == 1:
            print(f"  [cyan]First file upload ID: {file_upload_id}[/cyan]")
        
        print(f"  [dim]→ Notion Native ({self.uploaded_count}): {local_path.name}[/dim]")
        return native_url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} files to Notion[/green]")
        print(f"[green]  Files are permanently hosted by Notion[/green]")
    
    def needs_keepalive(self) -> bool:
        return False


def create_strategy(config: StrategyConfig) -> UploadStrategy:
    """
    Factory function to create upload strategy based on configuration.
    
    Args:
        config: StrategyConfig with upload_mode and related settings
    
    Returns:
        Appropriate UploadStrategy instance
    """
    mode = config.upload_mode
    
    if mode == UploadMode.S3_TEMP:
        # S3 with auto-delete (RECOMMENDED)
        return S3TempStrategy(
            bucket=config.s3.bucket,
            region=config.s3.region,
            access_key=config.s3.access_key,
            secret_key=config.s3.secret_key,
            lifecycle_days=config.s3.lifecycle_days,
            use_presigned=config.s3.use_presigned
        )
    
    elif mode == UploadMode.S3_PERMANENT:
        # S3 permanent (manual cleanup needed)
        return S3PermanentStrategy(
            bucket=config.s3.bucket,
            region=config.s3.region,
            access_key=config.s3.access_key,
            secret_key=config.s3.secret_key
        )
    
    elif mode == UploadMode.GCS:
        # Google Cloud Storage
        return GCSStrategy(
            bucket=config.gcs.bucket,
            project_id=config.gcs.project_id,
            credentials_path=config.gcs.credentials_path,
            lifecycle_days=config.gcs.lifecycle_days,
            use_impersonation=config.gcs.use_impersonation,
            impersonate_service_account=config.gcs.impersonate_service_account
        )
    
    elif mode == UploadMode.NOTION_NATIVE:
        # Notion native file upload (files hosted by Notion)
        return NotionNativeStrategy(
            notion_token=config.notion_token
        )
    
    else:
        # Default to S3 temp (RECOMMENDED)
        return S3TempStrategy(
            bucket=config.s3.bucket,
            region=config.s3.region,
            access_key=config.s3.access_key,
            secret_key=config.s3.secret_key,
            lifecycle_days=config.s3.lifecycle_days,
            use_presigned=config.s3.use_presigned
        )

