"""
Test module for logging functionality.
"""
import os
import sys
import pytest
import logging
from unittest.mock import Mock, patch, call
from pathlib import Path
import json
from datetime import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils.logger import setup_logger, LogFormatter, get_logger

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir

@pytest.fixture
def mock_time():
    """Mock datetime for consistent timestamps in tests."""
    with patch('src.utils.logger.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
        yield mock_dt

def test_log_directory_creation(temp_log_dir):
    """Test that log directory is created if it doesn't exist."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    assert logger.handlers
    assert log_path.parent.exists()

def test_log_file_creation(temp_log_dir):
    """Test that log file is created when logging."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    logger.info("Test message")
    assert log_path.exists()

def test_log_format(temp_log_dir, mock_time):
    """Test that log messages are properly formatted."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    
    # Test different log levels
    logger.info("Info message")
    logger.error("Error message")
    logger.warning("Warning message")
    
    log_content = log_path.read_text()
    log_lines = log_content.strip().split('\n')
    
    # Check format: [TIMESTAMP] LEVEL - MESSAGE
    assert "[2024-01-01 12:00:00] INFO - Info message" in log_lines[0]
    assert "[2024-01-01 12:00:00] ERROR - Error message" in log_lines[1]
    assert "[2024-01-01 12:00:00] WARNING - Warning message" in log_lines[2]

def test_json_logging(temp_log_dir, mock_time):
    """Test logging of JSON structured data."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    
    data = {"key": "value", "nested": {"inner": "data"}}
    logger.info("Data received", extra={"data": data})
    
    log_content = log_path.read_text()
    assert "Data received" in log_content
    assert json.dumps(data, indent=2) in log_content

def test_exception_logging(temp_log_dir):
    """Test logging of exceptions with traceback."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception("An error occurred")
    
    log_content = log_path.read_text()
    assert "An error occurred" in log_content
    assert "ValueError: Test error" in log_content
    assert "Traceback" in log_content

def test_log_rotation(temp_log_dir):
    """Test that log files are rotated when they reach max size."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path, max_bytes=100, backup_count=3)
    
    # Write enough data to trigger rotation
    for i in range(10):
        logger.info("X" * 20)  # Each log entry will be > 20 bytes with timestamp
    
    # Check that backup files were created
    assert log_path.exists()
    assert (log_path.parent / "test.log.1").exists()
    assert (log_path.parent / "test.log.2").exists()

def test_get_logger_singleton():
    """Test that get_logger returns the same logger instance."""
    logger1 = get_logger("test")
    logger2 = get_logger("test")
    assert logger1 is logger2

def test_sensitive_data_masking(temp_log_dir):
    """Test that sensitive data is properly masked in logs."""
    log_path = temp_log_dir / "test.log"
    logger = setup_logger("test_logger", log_path)
    
    sensitive_data = {
        "api_key": "secret_key_12345",
        "password": "very_secret",
        "token": "bearer_token_xyz"
    }
    
    logger.info("API request", extra={"data": sensitive_data})
    
    log_content = log_path.read_text()
    assert "secret_key_12345" not in log_content
    assert "very_secret" not in log_content
    assert "bearer_token_xyz" not in log_content
    assert "***MASKED***" in log_content
