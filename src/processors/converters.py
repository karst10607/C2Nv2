"""Media conversion infrastructure for handling format transformations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Type
from enum import Enum

from ..models.errors import NotionImporterError, ErrorCode


class ConversionFormat(Enum):
    """Supported conversion output formats."""
    PNG = "png"
    JPG = "jpg"
    PDF = "pdf"


@dataclass
class ConversionResult:
    """Result of a media conversion operation."""
    success: bool
    output_path: Optional[Path] = None
    format: Optional[ConversionFormat] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConversionError(NotionImporterError):
    """Raised when media conversion fails."""
    def __init__(self, message: str, source_path: Path = None):
        super().__init__(ErrorCode.CONVERSION_ERROR, message)
        self.source_path = source_path


class MediaConverter(ABC):
    """Abstract base class for media converters."""
    
    @abstractmethod
    def supported_input_types(self) -> list[str]:
        """Return list of supported input file extensions."""
        pass
    
    @abstractmethod
    def can_convert(self, source_path: Path, target_format: ConversionFormat) -> bool:
        """Check if this converter can handle the given conversion."""
        pass
    
    @abstractmethod
    def convert(self, source_path: Path, target_format: ConversionFormat, 
                output_dir: Optional[Path] = None) -> ConversionResult:
        """
        Convert media file to target format.
        
        Args:
            source_path: Path to source file
            target_format: Desired output format
            output_dir: Optional output directory (defaults to source directory)
            
        Returns:
            ConversionResult with success status and output path
        """
        pass


class ConverterRegistry:
    """Registry for managing media converters."""
    
    def __init__(self):
        self._converters: Dict[str, Type[MediaConverter]] = {}
        self._instances: Dict[str, MediaConverter] = {}
    
    def register(self, name: str, converter_class: Type[MediaConverter]):
        """Register a converter class."""
        self._converters[name] = converter_class
    
    def get_converter(self, source_path: Path, target_format: ConversionFormat) -> Optional[MediaConverter]:
        """Get appropriate converter for the given conversion."""
        for name, converter_class in self._converters.items():
            if name not in self._instances:
                self._instances[name] = converter_class()
            
            converter = self._instances[name]
            if converter.can_convert(source_path, target_format):
                return converter
        
        return None
    
    def can_convert(self, source_path: Path, target_format: ConversionFormat) -> bool:
        """Check if any converter can handle this conversion."""
        return self.get_converter(source_path, target_format) is not None


# Global converter registry
converter_registry = ConverterRegistry()










