from nslookup import Nslookup

class caloDevice:
    def __init__(self, device_id, data):
        self.device_id = device_id
        self.uri = str(data['default_inline_tool'])
        self.device_name = str((data['device_name'].split("/"))[0].replace(" ",""))
        self.model_number = str(data['model_number'])
        self.hostname = str(data['hostname'])
        self.serial_number = str(data['serial_number'])
        self.state = str(data['automation_status'][1]['text'])
        if 'main_console' in data.keys():
            self.console_access = str(data['main_console'])
        else :
            self.console_access = 'Not Found'
        self.ipAddress = None
        self.vlan = None
        self.testbed = None
        self.setIPandVLAN()

    def __str__(self):
        string = f"CALO ID : {self.device_id}\n"
        string = string + f"Device Name : {self.device_name}\n"
        string = string + f"Model : {self.model_number}\n"
        string = string + f"State : {self.state}\n"
        string = string + f"Console Access : {self.console_access}\n"
        string = string + f"IP address : {self.ipAddress}\n"
        return string

    def setIPandVLAN(self):
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


    def setTestBed(self, string):
        #Expected string : 'BSNS-1010-2 Has Been Booked to Apr24dwagemanBRUTestbed2945 For Seventeen days.'
        testbed = string.split("to")
        testbed = testbed[1]
        testbed = testbed.split("For")
        testbed = testbed[0]
        testbed = testbed.replace(' ','')
        self.testbed = testbed



