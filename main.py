from webex_bot.webex_bot import WebexBot
import botFunction
import config.logging_config
import threading
import yaml



# webexToken = os.environ['WEBEX_TOKEN']
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



#Run
bot.run()



