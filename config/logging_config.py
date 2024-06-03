import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime
import platform


# Configure logger
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)  # Set to your desired level, such as DEBUG or INFO

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s.%(funcName)s] -  %(message)s')

if 'Linux' in platform.system():
    # Create a stream handler to output to the console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Create a TimedRotatingFileHandler for daily rotation
log_directory = "./logs/"  # Make sure this directory exists
if not os.path.exists(log_directory):
    print()
    os.makedirs(log_directory)

current_date = datetime.now().strftime("%Y-%m-%d")
log_filename = os.path.join(log_directory, f"{current_date}.log")
file_handler = TimedRotatingFileHandler(log_filename, when='midnight', interval=1, backupCount=7)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

