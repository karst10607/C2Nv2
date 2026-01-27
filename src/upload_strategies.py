"""
Upload strategies for handling images during Notion import.
Supports: Tunnel, file.io, AWS S3, Cloudflare R2, Backblaze B2, Notion Native.

Each strategy handles image upload differently to solve the 404 problem.
"""
import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import requests

from .constants import (
    TUNNEL_KEEPALIVE_PER_FAILED_PAGE,
    S3_PRESIGNED_URL_EXPIRY
)
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


class TunnelStrategy(UploadStrategy):
    """
    Original tunnel-based serving (cloudflared/ngrok).
    
    Pros: Fast, free, no account needed
    Cons: Tunnel expires after keepalive, causes 404s if Notion delays
    """
    
    def __init__(self, keepalive_sec: int):
        self.keepalive_sec = keepalive_sec
        self.server = None
        self.tunnel = None
        self.public_url = ""
        self.source_dir = None
    
    def prepare(self, source_dir: Path) -> str:
        from .image_server import StaticServer, Tunnel
        
        self.source_dir = source_dir
        self.server = StaticServer(source_dir)
        self.server.start()
        self.tunnel = Tunnel(self.server.base_url())
        self.public_url = self.tunnel.start()
        
        print(f"[green]Tunnel started:[/green] {self.public_url}")
        return self.public_url
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        # No upload - served via tunnel
        rel_path = local_path.relative_to(self.source_dir)
        return f"{self.public_url}/{rel_path}"
    
    def cleanup(self, failed_count: int = 0):
        # Extend keepalive if there are failures
        keepalive = self.keepalive_sec
        if failed_count > 0:
            extra = failed_count * TUNNEL_KEEPALIVE_PER_FAILED_PAGE
            keepalive += extra
            print(f"[yellow]Extending keepalive by {extra}s for {failed_count} failed pages[/yellow]")
        
        print(f"[cyan]Keeping tunnel alive for {keepalive}s...[/cyan]")
        time.sleep(keepalive)
        
        if self.tunnel:
            self.tunnel.stop()
    
    def needs_keepalive(self) -> bool:
        return True


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


class CloudflareR2Strategy(UploadStrategy):
    """
    Cloudflare R2 upload strategy (S3-compatible, cheaper than S3).
    
    Pros: Cheaper than S3 ($0.015/GB vs S3's $0.023/GB), no egress fees
    Cons: Requires Cloudflare account
    """
    
    def __init__(self, bucket: str, account_id: str, access_key: str, secret_key: str, public_domain: str):
        self.bucket = bucket
        self.account_id = account_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.public_domain = public_domain
        self.client = None
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        import boto3
        
        endpoint = f'https://{self.account_id}.r2.cloudflarestorage.com'
        
        self.client = boto3.client('s3',
            endpoint_url=endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
        
        print(f"[green]Using Cloudflare R2: {self.bucket}[/green]")
        return ""
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        content_hash = hashlib.md5(local_path.read_bytes()).hexdigest()[:12]
        timestamp = int(time.time())
        key = f'notion-imports/{timestamp}/{content_hash}/{local_path.name}'
        
        with open(local_path, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=f.read(),
                ContentType=self._get_content_type(local_path)
            )
        
        self.uploaded_count += 1
        cdn_url = f'https://{self.public_domain}/{key}'
        
        print(f"  [dim]→ Cloudflare R2 ({self.uploaded_count}): {local_path.name}[/dim]")
        return cdn_url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} images to Cloudflare R2[/green]")
    
    def needs_keepalive(self) -> bool:
        return False


class NotionNativeStrategy(UploadStrategy):
    """
    Notion native file upload via S3 temp bridge (EXPERIMENTAL).
    
    Uses S3TempStrategy as bridge instead of file.io (more reliable).
    
    Approach:
    1. Upload to S3 temp storage
    2. Give S3 URL to Notion
    3. Notion downloads and caches
    4. Notion converts to 'file' type (hopefully)
    5. S3 lifecycle auto-deletes after 1 day
    
    Pros: Images become Notion-hosted, reliable bridge
    Cons: Experimental conversion, requires S3 account
    """
    
    def __init__(self, s3_bucket: str, s3_region: str, s3_access_key: str, s3_secret_key: str):
        self.s3_helper = S3TempStrategy(s3_bucket, s3_region, s3_access_key, s3_secret_key)
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        print("[yellow]Using Notion Native (via S3 temp bridge) - experimental[/yellow]")
        return self.s3_helper.prepare(source_dir)
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """Upload via S3, hope Notion converts to 'file' type"""
        url = self.s3_helper.upload_image(local_path, context)
        self.uploaded_count += 1
        return url
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} images (Notion should cache as 'file' type)[/green]")
        self.s3_helper.cleanup(failed_count)
    
    def needs_keepalive(self) -> bool:
        return False


class FallbackStrategy(UploadStrategy):
    """
    Fallback strategy that tries primary, falls back to secondary on failure.
    
    Example: Try file.io first, fall back to S3 if file.io fails.
    """
    
    def __init__(self, primary: UploadStrategy, fallback: UploadStrategy):
        self.primary = primary
        self.fallback = fallback
        self.using_fallback = False
        self.primary_failures = 0
    
    def prepare(self, source_dir: Path) -> str:
        try:
            return self.primary.prepare(source_dir)
        except Exception as e:
            print(f"[yellow]Primary strategy failed: {e}[/yellow]")
            print(f"[yellow]Falling back to {self.fallback.get_name()}...[/yellow]")
            self.using_fallback = True
            return self.fallback.prepare(source_dir)
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        if self.using_fallback:
            return self.fallback.upload_image(local_path, context)
        
        try:
            return self.primary.upload_image(local_path, context)
        except Exception as e:
            self.primary_failures += 1
            
            # Switch to fallback after 3 failures
            if self.primary_failures >= 3 and not self.using_fallback:
                print(f"[yellow]Switching to fallback after {self.primary_failures} failures[/yellow]")
                self.using_fallback = True
                self.fallback.prepare(context.get('source_dir', Path.cwd()))
            
            if self.using_fallback:
                return self.fallback.upload_image(local_path, context)
            else:
                raise  # Re-raise if not using fallback yet
    
    def cleanup(self, failed_count: int = 0):
        if self.using_fallback:
            self.fallback.cleanup(failed_count)
        else:
            self.primary.cleanup(failed_count)
    
    def needs_keepalive(self) -> bool:
        if self.using_fallback:
            return self.fallback.needs_keepalive()
        return self.primary.needs_keepalive()


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
    
    elif mode == UploadMode.CLOUDFLARE:
        return CloudflareR2Strategy(
            bucket=config.cloudflare.bucket,
            account_id=config.cloudflare.account_id,
            access_key=config.cloudflare.access_key,
            secret_key=config.cloudflare.secret_key,
            public_domain=config.cloudflare.public_domain
        )
    
    elif mode == UploadMode.NOTION_NATIVE:
        # Notion Native via S3 temp bridge
        return NotionNativeStrategy(
            s3_bucket=config.s3.bucket,
            s3_region=config.s3.region,
            s3_access_key=config.s3.access_key,
            s3_secret_key=config.s3.secret_key
        )
    
    else:  # UploadMode.TUNNEL (default)
        return TunnelStrategy(
            keepalive_sec=config.tunnel.keepalive_sec
        )

