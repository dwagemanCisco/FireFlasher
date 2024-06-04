from webex_bot.models.command import Command
from utils.caloInterraction import CaloTool
from utils.reimage import deviceReimage
import logging
import uuid
import yaml
import traceback
import time
import re
from ping3 import ping


class listDevices (Command):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        super().__init__(
            command_keyword='list',
            help_message='List available Firepower in Brussels - USAGE : @calo list [1010|1120|1140|1150|2120|...]',
        )

    def execute(self, message, attachment_actions, activity):
        calo = CaloTool(username=self.username, password=self.password)

        if calo == False :
            return "Authentication error with Calo, please wait and try again later"
        else:
            # need to differentiate 1-1 messages or global
            if "list" in message :
                message = message.replace("Calo list", '')
                message = message.replace(" ", '')
            else :
                message = message[1:]


            string = "**Available Firepower in Brussels**\n\n```\n"
            messageSplitted = message.split(" ")

            if len(messageSplitted) == 1 : #argument has been set for specific model
                devices = calo.search_for_available_firepower_brussels_by_model(model=messageSplitted[0])
            else :
                devices = calo.search_for_available_firepower_brussels()

            if len(devices) == 0 :
                return "No device found --- Command usage : @calo list [1010|1120|1140|1150|2120|...]"
            else:
                for item in devices.keys():
                    string = string + str(item) + "\n"
                string = string + "```"
                return string





class reimageDevice (Command):
    def __init__(self, bot, lock, username, password):
        self.bot = bot
        self.logger = logging.getLogger('MyLogger')
        self.args = ''
        self.lock = lock
        self.username = username
        self.password = password
        super().__init__(
            command_keyword='reimage',
            help_message='Book Firepower in Brussels',
            delete_previous_message=True
        )

    def execute(self, message, attachment_actions, activity):
        try :

            #Object used to interact with Calo
            calo = CaloTool(username=self.username, password=self.password)
            calo.uuid = uuid.uuid4().__str__()

            #Logging
            self.logger.info(f'{calo.uuid} -- MESSAGE FROM  : ' + activity['actor']['id'])
            self.logger.info(f'{calo.uuid} -- MESSAGE RECEIVED : ' + message)




            # need to differentiate 1-1 messages or global
            if "reimage" in message :
                message = message.replace("Calo reimage ", '')
            else :
                message = message[1:]
            #removing bot name
            message = message.replace("Calo reimage ", '')


            #Split and validate arguments
            self.args = message.split(" ")
            validation = self.validateArguments()

            if validation is not None :
                return self.handle_error(validation)

            # Arguments validated
            startMessage = (f"On it boss ! 👍\n"
                            f"Task id : {calo.uuid}")

            resp = self.bot.send_message_to_room_or_person("None", attachment_actions.roomId,
                                                           reply_one_to_one=False,
                                                           is_one_on_one_space=True,
                                                           reply=startMessage,
                                                           conv_target_id=activity['id'])

            #need to use lock for concurrent access to device search
            self.logger.info(calo.uuid + " -- Trying to get thread lock")
            with self.lock :
                self.logger.info(calo.uuid + " -- Lock Acquired")
                #Device search
                devices = calo.search_for_available_firepower_brussels_by_model(model=self.args[0])

                if len(devices) == 0 :
                    return self.handle_error('MODELNOTFOUND')


                name = list(devices.keys())[0]
                device = devices[name]

                #book the device
                booking = calo.book_device(device.device_id, self.args[3], activity['actor']['id'].replace("@cisco.com",''))
                if 'Error' in booking :
                    return self.handle_error('BOOKING')


                device.setTestBed(booking)


            self.logger.info(calo.uuid + " -- Lock released")

            #show the booked device to user
            deviceString = "**Device details**\n```\n"
            deviceString = deviceString + str(device)
            deviceString = deviceString + f"Task UUID : {calo.uuid}"
            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True, reply=deviceString,
                                                    conv_target_id=activity['id'])

            self.logger.info(calo.uuid + " -- Device booked : " + str(device) + "State :" + device.state)


            #SwitchMatrix
            #If device name contains "EMEA", those are part of new devices where Management port is always enabled right vlan
            # if "EMEA" not in toBook.device_name :
            switchMatrix = calo.switch_matrix_enable(device.device_id, device.testbed, device.vlan)

            #Clear console
            clear = calo.clear_console(device.device_id)

            #reboot / toggle power (intent is to switch to rommon)
            reboot = calo.reboot_device(device)
            device.state = "Powered On"


            string = (f"Switchmatrix ports enabled on vlan {device.vlan}. "
                      f"\nConsole cleared and device rebooted/powered on. "
                      f"\n Starting reimage process\n")


            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True, reply=string,
                                                    conv_target_id=activity['id'])



            #initiate object to interract with device via Telnet
            deviceConsole = deviceReimage(device, self.args[2], self.args[1])
            deviceConsole.uuid = calo.uuid

            #reimage
            deviceConsole.establish_telnet_connection()
            deviceConsole.rommon_mode()
            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True, reply="Factory-reset in progress",
                                                    conv_target_id=activity['id'])
            bootable = deviceConsole.factory_reset()
            if bootable == True :
                calo.reboot_device(device)
                deviceConsole.rommon_mode()
                self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True, reply="Trying to boot from rommon via TFTP",
                                                    conv_target_id=activity['id'])
            deviceConsole.defineNetworkAndBootImage()

            #loop until link is confirmed
            network_validation = deviceConsole.startReimage()
            while network_validation == False :
                self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                        is_one_on_one_space=True,
                                                        reply="Link DOWN, retriggering switchmatrix",
                                                        conv_target_id=activity['id'])
                calo.switch_matrix_enable(device.device_id, device.testbed, device.vlan)
                time.sleep(60)
                network_validation = deviceConsole.startReimage()

            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True,
                                                    reply="Link UP, booting from TFTP",
                                                    conv_target_id=activity['id'])

            #FXOS failed state
            deviceConsole.fxos_failed()

            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True,
                                                    reply="Image successfully downloaded from FXOS, final installation, this will take some time...",
                                                    conv_target_id=activity['id'])

            #Image downloaded from FXOS, pending application to come up
            deviceConsole.waiting_for_application()
            self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                    is_one_on_one_space=True,
                                                    reply="Application initialized, network setup in progress",
                                                    conv_target_id=activity['id'])

            #ip setup is different based on software type (asa or ftd)
            if 'ftd' in self.args[1]:
                deviceConsole.FTDsetup()

                resp = ping(device.ipAddress)
                while (resp ==  False) or (resp == None) :
                    time.sleep(60)
                    resp = ping(device.ipAddress)
                    self.bot.send_message_to_room_or_person("None", attachment_actions.roomId,
                                                            reply_one_to_one=False,
                                                            is_one_on_one_space=True,
                                                            reply="Ping failed, retrying",
                                                            conv_target_id=activity['id'])

                self.logger.info(calo.uuid + " -- Ping successful, device ready")
                self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                        is_one_on_one_space=True,
                                                        reply="Device is now ready and reachable !",
                                                        conv_target_id=activity['id'])

            #for testing purpose, releasing the device after all operation
            if "debug" in message :
                release = calo.release_device(device.device_id)
                self.bot.send_message_to_room_or_person("None", attachment_actions.roomId, reply_one_to_one=False,
                                                        is_one_on_one_space=True,
                                                        reply="Debug mode, device released!",
                                                        conv_target_id=activity['id'])



        except Exception as e :
            self.logger.error(calo.uuid + " -- " + traceback.format_exc())

    def validateArguments(self):
        #arguments[0] = device model, 1 = ASA or FTD, 2 = version, 3 = (optionnal) case number
        if len(self.args) < 4 :
            return "ARGS_SIZE"

        #arg 0 (device model)
        if all(code not in self.args[0] for code in ('1010', '1120', '1140', '1150')):
            if all(code not in self.args[0] for code in ('2110', '2120', '2130', '2140')):
                if all(code not in self.args[0] for code in ('3105','3110', '3120', '3130', '3140')):
                    return "DEVICE_MODEL"

        #arg 1 (should be ASA or FTD)
        self.args[1] = self.args[1].lower()
        if ('asa' not in self.args[1]) and ('ftd' not in self.args[1]):
            return "DEVICE_TYPE"

        # arg 3 (case number)
        if len(self.args) == 4 :
            if not re.search(r"^\d{9}$", self.args[3]):
                return "CASE_NUMBER"

        # arg 2 (version)
        with open("config/supported.yaml", 'r') as file:
            supported = yaml.full_load(file)
            if 'asa' in self.args[1]:
                return "ASA_UNSUPPORTED"
            else:
                if any(code in self.args[0] for code in ('1010', '1120', '1140', '1150')):
                    versions = supported['1000']['ftd']

                if any(code in self.args[0] for code in ('2110', '2120', '2130', '2140')):
                    versions = supported['2000']['ftd']

                if '3105' in self.args[0]:
                    versions = supported['3105']['ftd']

                if any(code in self.args[0] for code in ('3110', '3120', '3130', '3140')):
                    versions = supported['3000']['ftd']

                for v in versions:
                    if self.args[2] in v:
                        return None

                return "VERSION"





    def handle_error(self, error):
        if 'MODELNOTFOUND' in error:
            return "We coulnd't find a device matching your criteria, you can use the command 'list' to show all devices available, reach out to dwageman@cisco.com with task id"

        if "ARGS_SIZE" in error :
            return "Invalid argument number. Usage : reimage [1XXX|21XX|31XX] [asa|ftd] [version] [case number]', reach out to dwageman@cisco.com with task id"

        if "DEVICE_TYPE" in error :
            return "Invalid device type, it should be ASA or FTD, reach out to dwageman@cisco.com with task id"

        if "DEVICE_MODEL" in error :
            return ("Invalid device model!! \n\n"
                    "**Supported devices**\n"
                    "1010,1120,1140,1150\n"
                    "2110,2120,2130,2140\n"
                    "3105,3110,3120,3130,3140\n"
                    "Reach out to dwageman@cisco.com")

        if 'VERSION' in error :
            return "Invalid software version. Need to check supported versions (redirect to 'supported.yaml), reach out to dwageman@cisco.com with task id"

        if "ASA_UNSUPPORTED" in error :
            return "Reimage to ASA is currently unsupported, reach out to dwageman@cisco.com with task id"

        if "CASE_NUMBER" in error :
            return "Invalid case number, case number is mandatory to add you as interested parties on Calo Testbed, reach out to dwageman@cisco.com with task id"

        if "BOOKING" in error :
            return "Internal error during booking request, please try again or reach out to dwageman@cisco.com with task id"
