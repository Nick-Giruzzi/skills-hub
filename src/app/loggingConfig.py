#!/usr/bin/env python3

import logging
from logging.handlers import RotatingFileHandler
from app.extensions import globals

class LevelFilter(logging.Filter):
    """Filter to only accept specific log levels"""
    def __init__(self, level):
        self.level = level
    
    def filter(self, record):
        return record.levelno == self.level

def setup_logging(app):
    # Clear default log formatting
    app.logger.handlers.clear()
    # Create default log formatting
    formatter = logging.Formatter(
        f'%(asctime)s: SKILLS-HUB | %(levelname)s | {globals.support_code} | {globals.lab_code} | %(message)s'
    )
    # Create new log handler w/ custom formatting and assign.
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    # 
    app.logger.addHandler(handler)
    # Set base logging level
    app.logger.setLevel(logging.INFO)

    app.logger.info("Logging Configured.")
    if globals.local_logging:
        # INFO file handler
        info_handler = RotatingFileHandler(
            f'{globals.logs_dir}/info.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        info_handler.addFilter(LevelFilter(logging.INFO))
        app.logger.addHandler(info_handler)
        
        # WARNING file handler
        debug_handler = RotatingFileHandler(
            f'{globals.logs_dir}/debug.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        debug_handler.addFilter(LevelFilter(logging.DEBUG))
        app.logger.addHandler(debug_handler)
        
        warning_handler = RotatingFileHandler(
            f'{globals.logs_dir}/warning.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.setFormatter(formatter)
        warning_handler.addFilter(LevelFilter(logging.WARNING))
        app.logger.addHandler(warning_handler)

        # ERROR file handler
        error_handler = RotatingFileHandler(
            f'{globals.logs_dir}/error.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(LevelFilter(logging.ERROR))
        app.logger.addHandler(error_handler)
        
        # Optional: Add a general log file that captures everything
        general_handler = RotatingFileHandler(
            f'{globals.logs_dir}/all.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )

        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        app.logger.addHandler(general_handler)
        
        # Optional: Console handler for systemd
        #console_handler = logging.StreamHandler()
        #console_handler.setFormatter(formatter)
        #app.logger.addHandler(console_handler)
        
        app.logger.info("Local Logging Enabled!")

        globals.app = app