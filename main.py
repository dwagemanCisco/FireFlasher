from webex_bot.webex_bot import WebexBot
import botFunction
import threading
import yaml
from _datetime import datetime
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import platform


# Configure logger
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)  # Set to your desired level, such as DEBUG or INFO

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s.%(funcName)s] -  %(message)s')

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


lock = threading.Lock()
webextoken = ''
username = ''
password = ''

with open("config/sensitive", 'r') as file:
    settings = yaml.full_load(file)
    webextoken = settings['teams_bot_token']
    username = settings['username']
    password = settings['password']


# (Optional) Proxy configuration
# Supports https or wss proxy, wss prioritized.
proxies = {
    'https': 'http://proxy.esl.cisco.com:80',
    'wss': 'socks5://proxy.esl.cisco.com:1080'
}

# Create a Bot Object
bot = WebexBot(teams_bot_token=webextoken,
               bot_name="FireFlasher",
               approved_domains=["cisco.com"],
               include_demo_commands=False,
               proxies=proxies
               )


# Add new commands for the bot to listen out for.
bot.add_command(botFunction.listDevices(username,password))
bot.add_command(botFunction.reimageDevice(bot, lock, username, password))

logger.info("!!!!!Welcome!!!!")

#Run
bot.run()



