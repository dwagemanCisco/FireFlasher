from nslookup import Nslookup
import logging

class caloDevice:
    def __init__(self, device_id, uri, device_name, model_number, serial_number, state, console_access):
        self.logger = logging.getLogger('MyLogger')
        self.device_id = device_id
        self.uri = uri
        self.device_name = device_name
        self.model_number = model_number
        self.username = 'admin'
        self.password = 'Cxlabs!12'
        self.serial_number = serial_number
        self.state = state
        self.console_access = console_access
        self.ipAddress = None
        self.vlan = None
        self.testbed = None
        self.netmask = None
        self.gateway = None
        self.setIpVlanNetmaskGateway()


    def __str__(self):
        string = f"Device Name : {self.device_name}\n"
        string = string + f"Model : {self.model_number}\n"
        string = string + f"Console Access : {self.console_access}\n"
        string = string + f"Username : {self.username}\n"
        string = string + f"Password : {self.password}\n"
        string = string + f"IP address : {self.ipAddress}\n"
        string = string + f"Netmask : {self.netmask}\n"
        string = string + f"Gateway : {self.gateway}\n"
        string = string + f"Testbed : {self.testbed}\n"
        return string

    def setIpVlanNetmaskGateway(self):
        # NSLOOKUP
        dns_query = Nslookup()
        dns_query = Nslookup(verbose=False, tcp=False)
        ips_record = dns_query.dns_lookup(f"{self.device_name}.cisco.com")
        soa_record = dns_query.soa_lookup(f"{self.device_name}.cisco.com")


        # Assign Ip address and vlan
        if len(ips_record.answer) >= 1 :
            self.ipAddress = str(ips_record.answer[0])
            splittedIP = self.ipAddress.split('.')
            self.vlan = splittedIP[2]

            # vlan 67 doesn't exist, it's vlan 66 and /23
            if self.vlan == "67" :
                self.vlan = "66"

            #need to improve the below
            if self.vlan == '66':
                self.netmask = "255.255.254.0"
            else :
                self.netmask = "255.255.255.0"

            self.gateway = f'{splittedIP[0]}.{splittedIP[1]}.{self.vlan}.1'

    def setTestBed(self, string):

        #Expected string : 'BSNS-1010-2 Has Been Booked to Apr24dwagemanBRUTestbed2945 For Seventeen days.'
        testbed = string.split("to")
        testbed = testbed[1]
        testbed = testbed.split("For")
        testbed = testbed[0]
        testbed = testbed.replace(' ','')
        self.testbed = testbed



