import requests
from utils.device import caloDevice
import logging
import traceback
import urllib3
import json

class CaloTool:
    def __init__(self, username, password):
        self.logger = logging.getLogger('MyLogger')
        self.session = requests.Session()
        self.root_uri = 'https://calo-new.cisco.com'
        self.client_connection_id = ""
        self.username = username
        self.password = password
        self.authenticate(username,password)
        self.uuid = ''


    # perform the authentication on the calo tool and retrieve the client_connection_id
    def authenticate(self, uname, pwd):
        data = {
            "requested_uri": "/",
            "attempt_login": 1,
            "username": uname,
            "password": pwd
        }

        urllib3.disable_warnings()
        response = self.session.post(self.root_uri, data=data, verify=False)
        if response.status_code >= 200 & response.status_code <= 299:
            if self.session.cookies.get("omnitool_ticket_prod") is None:
                return False

            data = {
                "set_utc_offset": -120,
                "set_timezone_name": "Europe/Brussels"
            }

            uri = "%s/ui/get_instance_info" % (self.root_uri)

            response = self.session.post(uri, data=data, verify=False)
            if response.status_code >= 200 & response.status_code <= 200:
                resp = response.json()
                self.client_connection_id = resp['client_connection_id']
                return self.client_connection_id

            return False

        return False

    # wrapper to handle post requests and the calo tool and retrieve the client_connection_id
    def post(self, extra_uri, data):
        uri = f"{self.root_uri}/{extra_uri}"
        response = self.session.post(uri, data=data, verify=False)
        if response.status_code >= 200 & response.status_code <= 200:
            response.raise_for_status()
            resp = response.json()
            return resp

        return None

    # Internal call to Calo
    def _send_json_data(self, extra_uri,data):
        uri = f"{self.root_uri}/tools/{extra_uri}/send_json_data"

        response = self.session.post(uri, headers={'Accept': 'application/json'},
                                     data=data, verify=False)
        if response.status_code >= 200 & response.status_code <= 200:
            response.raise_for_status()
            resp = response.json()
            return resp

        return False

    # # restrict the data to be searched for
    # # the Brussels lab
    def search_for_available_firepower_brussels(self):
        data = {
            "menu_37_1": "No", #available
            "via_quick_search": 1,
            "client_connection_id": self.client_connection_id,
            "quick_keyword": "FPR", #look for PID contains FPR
            "menu_35_1": "3_1", #location = Brussels
            "menu_36_1": "equipment_chassis"

        }
        try :
            data = self._send_json_data("search_devices" , data)
        except Exception as e :
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error when searching device : " + str(e)

        if data != None:
            if "records" in data.keys():
                devices = dict()

                for device_id in data['records'].keys():
                    device_data = data['records'][device_id]

                    if 'SSPT' not in str(device_data['device_name']) :
                        console_access = str(device_data['automation_status'][1]['text'])
                        if 'main_console' in device_data.keys():
                            console_access = str(device_data['main_console'])
                        else:
                            for item in device_data['name_plus_access']:
                                if "onsole" in item['text']:
                                    console_access = item['uri'].replace('telnet://','')

                        try :
                            device_temp = caloDevice(device_id, str(device_data['default_inline_tool']), str((device_data['device_name'].split("/"))[0].replace(" ","")),
                                                     str(device_data['model_number']), str(device_data['serial_number']), str(device_data['automation_status'][1]['text']), console_access)

                            if device_temp.ipAddress is None :
                                self.logger.error(
                                    self.uuid + " -- Unable resolve device hostname : " + str (device_temp))

                        except Exception as e :
                            self.logger.error(self.uuid + " -- error during device instanciation : " + traceback.format_exc())

                        devices[device_temp.device_name] = device_temp
                return devices
            else :
                return "Error during search request on Calo"

    def search_for_available_firepower_brussels_by_model(self, model):
        filteredDevices = dict()
        devices = self.search_for_available_firepower_brussels()
        for item in devices.keys():
            if model in item:
                filteredDevices[item] = devices[item]
        return filteredDevices

    def book_device(self, device_id, caseNumber, requester):
        data = {
                "has_some_cases": "1",
                "book_devices_form_mode": "create_case",
                "form_submitted": "1",
                "for_case": "",
                "service_request": "Customer+Recreate",
                "equipment_loan_borrower": requester,
                "csone_or_qddts_id": caseNumber,
                "case_title": requester,
                "request_description": "",
                "time_needed": "1468800",
                "express_booking": "",
                "uri_base": "",
                "client_connection_id":  self.client_connection_id
        }
        try:
            self.logger.info(self.uuid + " -- Sending book request for device_id : " + device_id)
            self.logger.info(self.uuid + " -- Booking data : " + str(data))

            data = self._send_json_data(f"search_devices/book_device/{device_id}", data)
            self.logger.info(self.uuid + " -- Response : " + json.dumps(data))
        except Exception as e :
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error during booking request on Calo : " + str(e)

        if 'title' in data.keys():
            return data['title']
        else:
            return "Error during booking request on Calo"

    def clear_console(self, device_id):
        data = {
            "client_connection_id": self.client_connection_id
        }
        try:
            self.logger.info(self.uuid + " -- Sending clear Console")
            data = self._send_json_data(f"search_devices/clear_consoles/{device_id}", data=data)
            self.logger.info(self.uuid + " -- Response : " + json.dumps(data))

        except Exception as e :
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error when clearing console :" + str(e)
        if 'title' in data.keys():
            return data['title']
        else:
            return "Error when clearing console"

    def reboot_device(self, device):
        data = {
            "client_connection_id": self.client_connection_id
        }
        try:
            if "On" in device.state:
                self.logger.info(self.uuid + " -- Sending 'Power cycle'")
                data = self._send_json_data(f"search_devices/power_cycle/{device.device_id}", data=data)
            else:
                self.logger.error(self.uuid + " -- Sending 'Toggle Power'")
                data = (self._send_json_data(f"search_devices/toggle_power/{device.device_id}", data=data))
            self.logger.info(self.uuid + " -- Response : " + json.dumps(data))
        except Exception as e:
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error when rebooting device" + str(e)

        if 'title' in data.keys():
            return data['title']
        else:
            return "Error when rebooting device"

    def release_device(self, device_id):
        data = {
            "client_connection_id": self.client_connection_id,
            "form_submitted": "1",
            "release_justification": "not needed",
            "email_release": "No"
        }
        try:
            self.logger.info(self.uuid + " -- Releasing device, data :" + str(data))
            data = self._send_json_data(f"search_devices/release_device/{device_id}", data=data)
            self.logger.info(self.uuid + " -- Response : " + json.dumps(data))
        except Exception as e :
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error when clearing console :" + str(e)
        print()
        if 'title' in data.keys():
            return data['title']
        else:
            return "Error when releasing device"

    def switch_matrix_enable(self, device_id, testbed, vlan):
        data = {
            "client_connection_id": self.client_connection_id
        }
        try:
            data = self._send_json_data(f"search_devices/the_switch_matrix/{testbed}", data=data)
            self.logger.info(self.uuid + " -- Response : " + str(data))
        except Exception as e:
            self.logger.error(self.uuid + " -- " + traceback.format_exc())
            return "Error during switch matrix commit" + str(e)
        if 'title' in data.keys():
            #Below is the parse inital string : ['31_1:107741_2', '35_1:63732_2', '34_1:56503_2', '51_1:4136864_2', '63_1:18643_2', '63_1:18644_2', '63_1:18645_2', '63_1:18646_2']
            # and get the following after parsing : ['18646_2_', '18645_2_', '18644_2_', '18643_2_']
            device = data['metainfo'][device_id]

            temp = device['children'].split(',')
            size = len(temp)

            temp1 = list()
            switchMatrixElement = list()
            temp1.append(temp[size - 1])
            temp1.append(temp[size - 2])
            temp1.append(temp[size - 3])
            temp1.append(temp[size - 4])

            for item in temp1 :
                temp2 = item.replace('63_1','')
                temp2 = temp2.replace(':', '')
                temp2 = temp2 + "_"
                switchMatrixElement.append(temp2)

            data = {
                "form_submitted": "1",
                "save_topology": [
                    "No",
                    "No",
                    "No",
                    "No"
                ],
                "dont_post_case_update": [
                    "1",
                    "1",
                    "1",
                    "1"
                ],
                "params_key": [
                    switchMatrixElement[2],
                    switchMatrixElement[1],
                    switchMatrixElement[0],
                    switchMatrixElement[3]
                ],
                f"{switchMatrixElement[2]}status": "up",
                f"{switchMatrixElement[2]}current_vlans": vlan,
                f"{switchMatrixElement[2]}speed": "auto",
                f"{switchMatrixElement[2]}duplex": "auto",
                f"{switchMatrixElement[2]}trunk_type": "default",

                f"{switchMatrixElement[1]}status": "up",
                f"{switchMatrixElement[1]}current_vlans": vlan,
                f"{switchMatrixElement[1]}speed": "auto",
                f"{switchMatrixElement[1]}duplex": "auto",
                f"{switchMatrixElement[1]}trunk_type": "default",

                f"{switchMatrixElement[0]}status": "up",
                f"{switchMatrixElement[0]}current_vlans": vlan,
                f"{switchMatrixElement[0]}speed": "auto",
                f"{switchMatrixElement[0]}duplex": "auto",
                f"{switchMatrixElement[0]}trunk_type": "default",

                f"{switchMatrixElement[3]}status": "up",
                f"{switchMatrixElement[3]}current_vlans": vlan,
                f"{switchMatrixElement[3]}speed": "auto",
                f"{switchMatrixElement[3]}duplex": "auto",
                f"{switchMatrixElement[3]}trunk_type": "default",
                "uri_base": "",
                "client_connection_id": self.client_connection_id
            }

            try:
                self.logger.info(self.uuid + " -- Enabling switchmatrix port, data : " + str(data))
                data = self._send_json_data(f"search_devices/the_switch_matrix/{testbed}", data=data)
                if 'Topology is being committed' in data['control_area']['topology_commit_message'] :
                    return 'SwitchMatrix Topology is being committed, all ports configured on vlan ' + vlan

            except Exception as e :
                self.logger.error(self.uuid + " -- " + traceback.format_exc())
                return "Error during switch matrix commit :" + str(e)

            return "Error during switch matrix commit"




