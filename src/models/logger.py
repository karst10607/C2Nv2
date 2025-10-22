"""
Centralized logging for Notion Importer
Provides consistent output formatting and error display
"""
from typing import Optional
from rich import print as rich_print
from .errors import NotionImporterError, ErrorCode


class Logger:
    """Centralized logger for consistent output"""
    
    @staticmethod
    def error(message: str, code: Optional[ErrorCode] = None) -> None:
        """Print error message in red"""
        if code:
            rich_print(f"[red][{code.value}] {message}[/red]")
        else:
            rich_print(f"[red]{message}[/red]")
    
    @staticmethod
    def warning(message: str) -> None:
        """Print warning message in yellow"""
        rich_print(f"[yellow]{message}[/yellow]")
    
    @staticmethod
    def info(message: str) -> None:
        """Print info message in cyan"""
        rich_print(f"[cyan]{message}[/cyan]")
    
    @staticmethod
    def success(message: str) -> None:
        """Print success message in green"""
        rich_print(f"[green]{message}[/green]")
    
    @staticmethod
    def dim(message: str) -> None:
        """Print dimmed message"""
        rich_print(f"[dim]{message}[/dim]")
    
    @staticmethod
    def error_from_exception(e: Exception) -> None:
        """Print error from exception"""
        if isinstance(e, NotionImporterError):
            Logger.error(str(e))
        else:
            Logger.error(str(e))
    
    @staticmethod
    def header(title: str, width: int = 40) -> None:
        """Print a header with separators"""
        separator = "═" * width
        rich_print(f"[green]{separator}[/green]")
        rich_print(f"[green]{title}[/green]")
        rich_print(f"[green]{separator}[/green]")
    
    @staticmethod
    def subheader(title: str, width: int = 22) -> None:
        """Print a subheader"""
        separator = "═" * width
        rich_print(f"\n[green]{'═' * 3} {title} {'═' * 3}[/green]")


# Convenience functions for backward compatibility
def log_error(message: str, code: Optional[ErrorCode] = None) -> None:
    Logger.error(message, code)

def log_warning(message: str) -> None:
    Logger.warning(message)

def log_info(message: str) -> None:
    Logger.info(message)

def log_success(message: str) -> None:
    Logger.success(message)

def log_dim(message: str) -> None:
    Logger.dim(message)
