"""
Centralized logging configuration for HPPS system.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import Config


def setup_logger(name: str = "hpps", log_level: str = None) -> logging.Logger:
    """
    Set up and configure logger with file and console handlers.
    
    Args:
        name: Logger name
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    log_level = log_level or Config.LOG_LEVEL
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = Config.LOG_DIR / Config.LOG_FILE
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Create default logger
logger = setup_logger()
