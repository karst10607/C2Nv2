"""
Unit tests for image_utils module.
Tests image filtering logic in isolation.
"""
import pytest
from bs4 import BeautifulSoup
from src.image_utils import should_skip_image, extract_image_src, is_content_image, normalize_image_url


class TestImageFiltering:
    """Test image filtering logic"""
    
    def test_skip_jira_icon_by_class(self):
        """JIRA icons with class='icon' should be skipped"""
        html = '<img class="icon" src="https://atlassian.net/rest/api/2/universal_avatar/..." />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is True
    
    def test_skip_avatar_by_url(self):
        """Avatar URLs should be skipped"""
        html = '<img src="https://example.com/universal_avatar/view/type/user/123" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is True
    
    def test_skip_emoticon(self):
        """Emoticons should be skipped"""
        html = '<img class="emoticon" src="images/emoticons/smile.png" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is True
    
    def test_skip_gif(self):
        """GIF files should be skipped (usually UI elements)"""
        html = '<img src="images/icons/bullet_blue.gif" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is True
    
    def test_skip_thumbnails(self):
        """Confluence thumbnails should be skipped"""
        html = '<img src="attachments/thumbnails/123/456" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is True
    
    def test_keep_content_image(self):
        """Real content images should NOT be skipped"""
        html = '<img src="attachments/123/456.png" data-image-src="attachments/123/456.png" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is False
    
    def test_keep_screenshot(self):
        """Screenshots should NOT be skipped"""
        html = '<img src="attachments/2876541231/4116874546.png" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        src = img.get('src')
        
        assert should_skip_image(img, src) is False


class TestImageSrcExtraction:
    """Test image source extraction"""
    
    def test_prefer_data_image_src(self):
        """Should prefer data-image-src over src"""
        html = '<img src="attachments/thumbnails/123/456" data-image-src="attachments/123/456.png" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        
        result = extract_image_src(img)
        assert result == "attachments/123/456.png"
    
    def test_fallback_to_src(self):
        """Should use src if data-image-src not present"""
        html = '<img src="attachments/123/456.png" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        
        result = extract_image_src(img)
        assert result == "attachments/123/456.png"
    
    def test_remove_query_params(self):
        """Should remove query parameters"""
        html = '<img src="attachments/123/456.png?width=760" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        
        result = extract_image_src(img)
        assert result == "attachments/123/456.png"
    
    def test_no_src(self):
        """Should return None if no src"""
        html = '<img alt="broken" />'
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img')
        
        result = extract_image_src(img)
        assert result is None


class TestUrlNormalization:
    """Test URL normalization"""
    
    def test_relative_path(self):
        """Should convert relative path to absolute"""
        result = normalize_image_url('attachments/123/image.png', 'http://localhost:8000')
        assert result == 'http://localhost:8000/attachments/123/image.png'
    
    def test_absolute_url_unchanged(self):
        """Should leave absolute URLs unchanged"""
        url = 'https://example.com/image.png'
        result = normalize_image_url(url, 'http://localhost:8000')
        assert result == url
    
    def test_strip_slashes(self):
        """Should handle trailing/leading slashes"""
        result = normalize_image_url('/attachments/image.png', 'http://localhost:8000/')
        assert result == 'http://localhost:8000/attachments/image.png'

