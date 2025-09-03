#!/usr/bin/env python3

import logging
from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
# local imports
from app.globals import Globals

#######
## This file contains all of the persistent objects to be used throughout the sites execution
#######

# Create database object
db = SQLAlchemy()
record_solves_lock = Lock()

# Instantiate globals object
globals = Globals()