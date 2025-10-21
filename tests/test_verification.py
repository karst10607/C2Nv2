"""
Unit tests for verification module.
Tests image verification logic with mocked Notion API.
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.verification import ImageVerifier


class TestImageVerifier:
    """Test ImageVerifier class"""
    
    def test_is_cached_url_notion_domain(self):
        """Notion.so URLs should be recognized as cached"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        url = 'https://www.notion.so/image/abc123.png'
        assert verifier.is_cached_url(url) is True
    
    def test_is_cached_url_s3(self):
        """S3 URLs should be recognized as cached"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        url = 'https://prod-files-secure.s3.us-west-2.amazonaws.com/abc/image.png'
        assert verifier.is_cached_url(url) is True
    
    def test_is_not_cached_tunnel_url(self):
        """Tunnel URLs should NOT be recognized as cached"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        url = 'https://some-random-name.trycloudflare.com/image.png'
        assert verifier.is_cached_url(url) is False
    
    def test_get_image_url_file_type(self):
        """Should extract URL from 'file' type image"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        block = {
            'type': 'image',
            'image': {
                'type': 'file',
                'file': {'url': 'https://notion.so/image.png'}
            }
        }
        
        result = verifier.get_image_url(block)
        assert result == 'https://notion.so/image.png'
    
    def test_get_image_url_external_type(self):
        """Should extract URL from 'external' type image"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        block = {
            'type': 'image',
            'image': {
                'type': 'external',
                'external': {'url': 'https://example.com/image.png'}
            }
        }
        
        result = verifier.get_image_url(block)
        assert result == 'https://example.com/image.png'
    
    def test_count_verified_images_simple(self):
        """Should count verified images in simple blocks"""
        notion = Mock()
        notion.get_blocks = Mock(return_value=[])
        verifier = ImageVerifier(notion)
        
        blocks = [
            {
                'type': 'paragraph',
                'paragraph': {}
            },
            {
                'type': 'image',
                'image': {
                    'type': 'file',
                    'file': {'url': 'https://notion.so/img1.png'}
                }
            },
            {
                'type': 'image',
                'image': {
                    'type': 'external',
                    'external': {'url': 'https://tunnel.com/img2.png'}
                }
            },
            {
                'type': 'image',
                'image': {
                    'type': 'external',
                    'external': {'url': 'https://s3.us-west-2.amazonaws.com/img3.png'}
                }
            }
        ]
        
        # Should count 2 (notion.so and s3, not tunnel.com)
        result = verifier.count_verified_images_in_blocks(blocks)
        assert result == 2
    
    def test_verify_page_images_success(self):
        """Should return success when all images verified"""
        notion = Mock()
        notion.get_blocks = Mock(return_value=[
            {
                'type': 'image',
                'image': {
                    'type': 'file',
                    'file': {'url': 'https://notion.so/img1.png'}
                }
            },
            {
                'type': 'image',
                'image': {
                    'type': 'external',
                    'external': {'url': 'https://s3.us-west-2.amazonaws.com/img2.png'}
                }
            }
        ])
        
        verifier = ImageVerifier(notion)
        
        # Should succeed immediately (2 cached images, expecting 2)
        success, count = verifier.verify_page_images('page123', expected_count=2, timeout=10)
        
        assert success is True
        assert count == 2
    
    def test_verify_page_images_zero_expected(self):
        """Should return success immediately if no images expected"""
        notion = Mock()
        verifier = ImageVerifier(notion)
        
        success, count = verifier.verify_page_images('page123', expected_count=0, timeout=10)
        
        assert success is True
        assert count == 0

