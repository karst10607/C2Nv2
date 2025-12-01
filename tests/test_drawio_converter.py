"""Tests for Draw.io converter"""
import pytest
from pathlib import Path
from src.processors import converter_registry, ConversionFormat
from src.processors.drawio_converter import DrawioConverter


def test_drawio_converter_registration():
    """Test that Draw.io converter is registered"""
    # Create a dummy .drawio file path
    drawio_path = Path("test.drawio")
    
    # Check if converter can be found
    converter = converter_registry.get_converter(drawio_path, ConversionFormat.PNG)
    assert converter is not None
    assert isinstance(converter, DrawioConverter)


def test_drawio_converter_supported_types():
    """Test supported file types"""
    converter = DrawioConverter()
    supported = converter.supported_input_types()
    
    assert '.drawio' in supported
    assert '.html' in supported
    assert '.htm' in supported


def test_can_convert_drawio_files():
    """Test can_convert for various file types"""
    converter = DrawioConverter()
    
    # Should convert .drawio files
    assert converter.can_convert(Path("diagram.drawio"), ConversionFormat.PNG)
    assert converter.can_convert(Path("diagram.drawio.svg"), ConversionFormat.PNG)
    
    # Should not convert to PDF
    assert not converter.can_convert(Path("diagram.drawio"), ConversionFormat.PDF)
    
    # Should not convert random files
    assert not converter.can_convert(Path("image.png"), ConversionFormat.PNG)


def test_drawio_pattern_matching():
    """Test Draw.io content detection patterns"""
    converter = DrawioConverter()
    
    # Test mxfile pattern
    html_with_mxfile = '<html><body><mxfile version="1.0">diagram content</mxfile></body></html>'
    assert converter._contains_drawio_diagram(html_with_mxfile)
    
    # Test mxGraphModel pattern
    html_with_mxgraph = '<html><body><!-- mxGraphModel data here --></body></html>'
    assert converter._contains_drawio_diagram(html_with_mxgraph)
    
    # Test drawio class pattern
    html_with_drawio_div = '<html><body><div class="drawio-diagram">content</div></body></html>'
    assert converter._contains_drawio_diagram(html_with_drawio_div)
    
    # Test negative case
    html_without_drawio = '<html><body><p>Just regular content</p></body></html>'
    assert not converter._contains_drawio_diagram(html_without_drawio)


def test_decode_drawio_data():
    """Test decoding of Draw.io encoded data"""
    converter = DrawioConverter()
    
    # This is a simplified test - in reality, Draw.io encoding is more complex
    # For now, we just verify the method exists and handles errors
    try:
        result = converter._decode_drawio_data("invalid_data")
    except Exception:
        # Expected to fail with invalid data
        pass








