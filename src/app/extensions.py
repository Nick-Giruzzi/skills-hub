#!/usr/bin/env python3

import logging
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

# configure logging obj (default log level of INFO)
logging.basicConfig(format=f'SKILLS-HUB | %(threadName)s | %(levelname)s | {globals.support_code} | {globals.challenge_code} | Variant {globals.variant_index} | %(message)s', level=logging.INFO)
logger = logging.getLogger("SkillsHub")