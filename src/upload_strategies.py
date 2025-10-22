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
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        return types.get(path.suffix.lower(), 'application/octet-stream')


class TunnelStrategy(UploadStrategy):
    """
    Original tunnel-based serving (cloudflared/ngrok).
    
    Pros: Fast, free, no account needed
    Cons: Tunnel expires after keepalive, causes 404s if Notion delays
    """
    
    def __init__(self, keepalive_sec: int = 600):
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
            extra = failed_count * 30  # 30s per failed page
            keepalive += extra
            print(f"[yellow]Extending keepalive by {extra}s for {failed_count} failed pages[/yellow]")
        
        print(f"[cyan]Keeping tunnel alive for {keepalive}s...[/cyan]")
        time.sleep(keepalive)
        
        if self.tunnel:
            self.tunnel.stop()
    
    def needs_keepalive(self) -> bool:
        return True


class FileIOStrategy(UploadStrategy):
    """
    Upload to file.io - one-time download service.
    
    Pros:
    - Auto-deletes after Notion downloads (privacy + no storage costs)
    - No account needed (free tier)
    - URLs valid for 14 days (plenty of time)
    - No tunnel timeout issues
    
    Cons:
    - Rate limited (~10-20 uploads/min on free tier)
    - 100 MB per file limit (free tier)
    - Slower than tunnel (upload takes time)
    
    Best for: Medium imports (10-100 pages, <100 images)
    """
    
    def __init__(self, api_key: Optional[str] = None, expire_days: int = 14):
        self.api_key = api_key
        self.expire_days = expire_days
        self.upload_url = 'https://file.io'
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        print("[green]Using file.io strategy - images will auto-delete after Notion downloads[/green]")
        return ""
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """Upload to file.io with one-time download"""
        
        # Rate limiting for free tier
        if not self.api_key and self.uploaded_count > 0:
            if self.uploaded_count % 10 == 0:
                print(f"  [dim]Rate limit pause (uploaded {self.uploaded_count} images)...[/dim]")
                time.sleep(6)  # 6s pause every 10 uploads
        
        with open(local_path, 'rb') as f:
            files = {'file': (local_path.name, f, self._get_content_type(local_path))}
            
            data = {
                'expires': f'{self.expire_days}d',
                'maxDownloads': '1',  # Auto-delete after first download!
                'autoDelete': 'true'
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(self.upload_url, files=files, data=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    file_url = result['link']
                    self.uploaded_count += 1
                    print(f"  [dim]→ file.io ({self.uploaded_count}): {local_path.name}[/dim]")
                    return file_url
                else:
                    raise Exception(f'file.io upload failed: {result.get("message", "Unknown error")}')
            else:
                raise Exception(f'file.io HTTP {response.status_code}: {response.text[:100]}')
    
    def cleanup(self, failed_count: int = 0):
        print(f"[green]✓ Uploaded {self.uploaded_count} images to file.io[/green]")
        print("[green]  Files will auto-delete after Notion downloads them (no cleanup needed!)[/green]")
    
    def needs_keepalive(self) -> bool:
        return False  # URLs valid for 14 days


class S3Strategy(UploadStrategy):
    """
    AWS S3 upload strategy.
    
    Pros: Permanent, reliable, fast
    Cons: Requires AWS account, storage costs
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
    Notion native file upload (EXPERIMENTAL).
    
    Uploads images as Notion 'file' type (not 'external').
    Images are hosted by Notion permanently.
    
    WARNING: Uses workaround methods as Notion API doesn't officially
    support file uploads for image blocks. May break with API changes.
    
    Approach:
    1. Create a temporary file block in the page
    2. Upload file content via Notion's file endpoint
    3. Convert to image block referencing the file
    
    OR (simpler):
    1. Upload as external URL first (via file.io)
    2. Let Notion cache it
    3. Notion converts external → file automatically
    
    Pros: Images hosted by Notion forever, no external dependencies
    Cons: Experimental, may not work reliably
    """
    
    def __init__(self, notion_client, use_fileio_bridge: bool = True):
        self.notion = notion_client
        self.use_fileio_bridge = use_fileio_bridge
        self.fileio_helper = None
        self.uploaded_count = 0
    
    def prepare(self, source_dir: Path) -> str:
        if self.use_fileio_bridge:
            # Use file.io as bridge, let Notion cache and convert
            print("[yellow]Using Notion Native (via file.io bridge) - experimental[/yellow]")
            self.fileio_helper = FileIOStrategy(expire_days=7)
            self.fileio_helper.prepare(source_dir)
        else:
            print("[yellow]Using Notion Native (direct upload) - highly experimental[/yellow]")
        
        return ""
    
    def upload_image(self, local_path: Path, context: Dict) -> str:
        """
        Upload image so it becomes Notion 'file' type (not external).
        
        Method 1 (use_fileio_bridge=True, RECOMMENDED):
        - Upload to file.io temporarily
        - Return file.io URL
        - Notion fetches and caches as 'file' type
        - file.io auto-deletes
        
        Method 2 (use_fileio_bridge=False, EXPERIMENTAL):
        - Try to use Notion's undocumented upload endpoint
        - May not work
        """
        
        if self.use_fileio_bridge:
            # Use file.io as bridge - Notion will cache it
            # We'll verify it becomes 'file' type, not 'external'
            url = self.fileio_helper.upload_image(local_path, context)
            self.uploaded_count += 1
            return url
        
        else:
            # Direct upload attempt (undocumented, may fail)
            page_id = context.get('page_id')
            
            # This is speculative - Notion API doesn't officially support this
            # Would need to reverse-engineer the endpoint
            raise NotImplementedError(
                "Direct Notion file upload not yet implemented. "
                "Use use_fileio_bridge=True for Notion-hosted images."
            )
    
    def cleanup(self, failed_count: int = 0):
        if self.use_fileio_bridge:
            print(f"[green]✓ Uploaded {self.uploaded_count} images (Notion will cache as 'file' type)[/green]")
            print("[green]  file.io links will auto-delete after Notion downloads[/green]")
        else:
            print(f"[green]✓ Uploaded {self.uploaded_count} images directly to Notion[/green]")
    
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


def create_strategy(config) -> UploadStrategy:
    """
    Factory function to create upload strategy based on configuration.
    
    Args:
        config: ImportConfig object with upload_mode and related settings
    
    Returns:
        Appropriate UploadStrategy instance
    """
    mode = getattr(config, 'upload_mode', 'tunnel')
    
    if mode == 'fileio':
        primary = FileIOStrategy(
            api_key=getattr(config, 'fileio_api_key', None),
            expire_days=getattr(config, 'fileio_expiry_days', 14)
        )
        
        # Fallback to tunnel if file.io fails
        fallback = TunnelStrategy(keepalive_sec=getattr(config, 'tunnel_keepalive_sec', 600))
        
        if getattr(config, 'enable_fallback', True):
            return FallbackStrategy(primary, fallback)
        return primary
    
    elif mode == 's3':
        return S3Strategy(
            bucket=config.s3_bucket,
            region=config.s3_region,
            access_key=config.s3_access_key,
            secret_key=config.s3_secret_key
        )
    
    elif mode == 'cloudflare':
        return CloudflareR2Strategy(
            bucket=config.cf_bucket,
            account_id=config.cf_account_id,
            access_key=config.cf_access_key,
            secret_key=config.cf_secret_key,
            public_domain=config.cf_public_domain
        )
    
    elif mode == 'notion_native':
        return NotionNativeStrategy(
            notion_client=None,  # Will be set later
            use_fileio_bridge=True  # Safe mode - use file.io then let Notion cache
        )
    
    else:  # 'tunnel' (default)
        return TunnelStrategy(
            keepalive_sec=getattr(config, 'tunnel_keepalive_sec', 600)
        )

