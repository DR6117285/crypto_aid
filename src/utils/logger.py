"""
Logging configuration module.
"""
import logging
import logging.handlers
from datetime import datetime
import os
import json
from typing import Any, Dict, Optional
from pathlib import Path

class LogFormatter(logging.Formatter):
    """Custom formatter that handles structured data and masks sensitive information."""
    
    SENSITIVE_KEYS = {'api_key', 'private_key', 'secret', 'password', 'token'}
    
    def formatTime(self, record: logging.LogRecord) -> str:
        """Format the timestamp in the expected format."""
        # Use datetime.now() instead of fromtimestamp for consistent mocking
        dt = datetime.now()
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with optional structured data."""
        # Format the basic message
        formatted = f"[{self.formatTime(record)}] {record.levelname} - {record.getMessage()}"
        
        # Add structured data if present
        if hasattr(record, 'data'):
            data = self._mask_sensitive_data(record.data)
            formatted += f"\nData:\n{json.dumps(data, indent=2)}"
            
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """Recursively mask sensitive information in the data structure."""
        if isinstance(data, dict):
            return {
                k: "***MASKED***" if k.lower() in self.SENSITIVE_KEYS 
                else self._mask_sensitive_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data

_loggers: Dict[str, logging.Logger] = {}

def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.
    Ensures only one logger exists per name (singleton pattern).
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]

def setup_logger(
    name: str,
    log_file: Optional[str | Path] = None,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name (str): Logger name
        log_file (str | Path, optional): Path to log file
        max_bytes (int): Maximum size of each log file in bytes
        backup_count (int): Number of backup files to keep
        level (int): Logging level
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = get_logger(name)
    logger.setLevel(level)
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = LogFormatter()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
