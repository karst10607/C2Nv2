"""
Plugin system for extensible transformations.
Allows users to customize import behavior without modifying core code.
"""
from .base import TransformerPlugin, ImagePlugin
from .manager import PluginManager

__all__ = ['TransformerPlugin', 'ImagePlugin', 'PluginManager']

