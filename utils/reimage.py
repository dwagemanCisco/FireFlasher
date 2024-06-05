import time
import telnetlib
import yaml
import re
import logging


class deviceReimage:
    def __init__(self, device, softwareVersion, softwareType, uuid):
        self.logger = logging.getLogger('MyLogger')
        self.device = device
        self.softwareVersion = softwareVersion #7.2.5 or 9.18
        self.softwareType = softwareType #ASA or FTD
        self.softwareImage = ''
        self.packageVersion = None
        self.tftpServer = ''
        self.setImage()
        self.settftpserver()
        self.uuid = uuid
        self.logger.info("\n"
                         "**Full details** -- self.uuid\n" +
                         str(self.device) +
                         str(self))

    def __str__(self):
        string = f"softwareVersion : {self.softwareVersion}\n"
        string = string + f"softwareType : {self.softwareType}\n"
        string = string + f"softwareImage : {self.softwareImage}\n"
        string = string + f"packageVersion : {self.packageVersion}\n"
        string = string + f"tftpServer : {self.tftpServer}\n"
        return string

    def settftpserver(self):
        with open("config/settings.yaml", 'r') as file:
            settings = yaml.full_load(file)
            self.tftpServer = settings['ftp server']



    #This function should fill variable softwareImage, first, it should check hardware based on hostname
    #then it should check it a config file and found a mapping for example : FTD - 1010 - 7.2.5  ----> cisco-ftd-fp1k.7.2.5-208.SPA and 7.2.5-208
    def setImage(self):


        with open("config/supported.yaml", 'r') as file:
            supported = yaml.full_load(file)
            if self.softwareImage == "ASA":
                pass
            else:
                if any(code in self.device.model_number for code in ('1010', '1120', '1140', '1150')):
                    self.logger.info(f'{self.uuid} -- Model number : {self.device.model_number} -- Matching 1K')
                    versions = supported['1000']['ftd']

                if any(code in self.device.model_number for code in ('2110', '2120', '2130', '2140')):
                    self.logger.info(f'{self.uuid} -- Model number : {self.device.model_number} -- Matching 1K')
                    versions = supported['2000']['ftd']

                if '3105' in self.device.model_number:
                    self.logger.info(f'{self.uuid} -- Model number : {self.device.model_number} -- Matching 1K')
                    versions = supported['3105']['ftd']

                if any(code in self.device.model_number for code in ('3110', '3120', '3130', '3140')):
                    self.logger.info(f'{self.uuid} -- Model number : {self.device.model_number} -- Matching 1K')
                    versions = supported['3000']['ftd']

                for v in versions:
                    if self.softwareVersion in v:
                        self.softwareImage = v
                        pattern = re.compile(r'\.(\d+\.\d+\.\d+-\d+)\.SPA') #cisco-ftd-fp3k.7.2.5-208.SPA -> 7.2.5-208
                        match = pattern.search(v)
                        if match :
                            self.packageVersion = match.group(1)
                        else:
                            pattern = re.compile(r'\d+\.\d+\.\d+-\d+\b') #Cisco_FTD_SSP_FP3K_Upgrade-7.4.1-172.sh.REL.tar -> 7.4.1-172
                            match = pattern.search(v)
                            if match :
                                self.packageVersion = match.group(0)

    # Function to establish serial connection
    def establish_telnet_connection(self):
        self.telnet = telnetlib.Telnet(f"{self.device.console_access.split(':')[0]}.cisco.com", int(self.device.console_access.split(':')[1]))
        self.logger.info(self.uuid + " -- TELNET connection established")

    # Function to send commands to the device
    def send_command_and_read_output(self, command):
        self.telnet.write(command.encode('cp437'))
        output = self.telnet.read_very_eager().decode('cp437')
        # self.logger.info(self.uuid + " -- Function : send_command_and_read_output : " + output )
        return output

    def rommon_mode(self):
        output = ''
        self.logger.info(self.uuid + " -- Waiting to read 'Cisco System ROMMON'")
        while "Cisco System ROMMON" not in output:
            time.sleep(1)
            output = self.telnet.read_very_eager().decode('cp437')
            if len(output) > 0:
                self.logger.info(self.uuid + " --  " + output)

        self.logger.info(self.uuid + " -- Starting to send ESC")
        self.telnet.write(chr(27).encode('cp437'))
        while "rommon 1 >" not in output :
            time.sleep(1)
            if len(output) > 0 :
                self.logger.info(self.uuid + " --  " + output)
            self.telnet.write(chr(27).encode('cp437'))
            output = self.telnet.read_very_eager().decode('cp437')


        self.logger.info(self.uuid + " -- Rommon mode confirmed !  \n" + output)


    def factory_reset(self):
        self.logger.info(self.uuid + " -- Starting factory-reset from rommon")

        self.telnet.write("confreg0x1\n".encode('cp437'))
        self.telnet.write("factory-reset\n".encode('cp437'))
        self.telnet.write("yes\n".encode('cp437'))
        self.telnet.write("ERASE\n".encode('cp437'))
        self.telnet.write("yes\n".encode('cp437'))
        self.telnet.write("boot\n".encode('cp437'))
        time.sleep(30)
        output = self.telnet.read_very_eager().decode('cp437')
        if 'boot: cannot determine first file name on device "disk0:/installables/switch"' in output:
            self.logger.info(self.uuid + " --  Error found during factory reset : " + 'boot: cannot determine first file name on device "disk0:/installables/switch"')
            return False
        else:
            output = ''
            while "login:" not in output:
                time.sleep(1)
                output = self.telnet.read_very_eager().decode('cp437')
                if len(output) > 0:
                    self.logger.info(self.uuid + " --  " + output)
            time.sleep(60)
            self.logger.info(self.uuid + " -- Factory-reset completed, need to go in rommon again, rebooting")
            return True

    def defineNetworkAndBootImage(self):
        self.telnet.write(f"address {self.device.ipAddress} \n".encode('cp437'))
        self.telnet.write(f"netmask {self.device.netmask} \n".encode('cp437'))
        self.telnet.write(f"server {self.tftpServer} \n".encode('cp437'))
        self.telnet.write(f"gateway {self.device.gateway} \n".encode('cp437'))
        self.telnet.write(f"file NGFW_BOT/{self.softwareImage} \n".encode('cp437'))
        self.telnet.write(f"sync\n".encode('cp437'))
        self.send_command_and_read_output("\nset\n")

        output = self.telnet.read_very_eager().decode('cp437')
        self.logger.info(self.uuid + " -- " + output)
        return output


    def startReimage(self):
        self.logger.info(self.uuid + " -- " + "tftpdnld started, waiting for Network confirmation")
        self.telnet.write(f"tftpdnld -b\n".encode('cp437'))
        time.sleep(60)
        output = self.send_command_and_read_output('\n')
        self.logger.info(self.uuid + " -- " + output)
        if "!!!!" not in output : #on FPR 1K and 2K, !!! are shownd during download
            if "==" not in output :   #on FPR 3K, == are shownd during download
                self.logger.info(self.uuid + " -- " + "Network issue, need to retrigger switchmatrix")
                return False
        else:
            self.logger.info(self.uuid + " -- " + "Network settings validated, download in progress")
            return True



    def fxos_failed(self):
        output = self.telnet.read_very_eager().decode('cp437')
        self.logger.info(self.uuid + " -- " + output)

        output = ''
        self.logger.info(self.uuid + " -- Waiting for FXOS failed state")

        while "login:" not in output:
            self.telnet.write(f"\n".encode('cp437'))
            output = output = self.telnet.read_very_eager().decode('cp437')
            if len(output) > 0 :
                self.logger.info(self.uuid + " --  " + output)
            time.sleep(1)


        self.logger.info(self.uuid + " -- FXOS failed state discovered, need to download image from here")


        self.telnet.write(f"admin\n".encode('cp437'))
        self.telnet.write(f"Admin123\n".encode('cp437'))
        self.telnet.write(f"Cxlabs!12\n".encode('cp437'))
        self.telnet.write(f"Cxlabs!12\n".encode('cp437'))
        self.telnet.write(f"scope fabric-interconnect\n".encode('cp437'))
        self.telnet.write(f"set out-of-band static ip {self.device.ipAddress} netmask {self.device.netmask} gw {self.device.gateway}\n".encode('cp437'))
        self.telnet.write(f"commit-buffer\n".encode('cp437'))
        self.telnet.write(f"scope firmware\n".encode('cp437'))
        self.telnet.write(f"download image tftp://{self.tftpServer}:/NGFW_BOT/{self.softwareImage}\n".encode('cp437'))

        self.logger.info(self.uuid + " -- Download image command sent, waiting for system to come up and start download ")

        output = self.telnet.read_very_eager().decode('cp437')
        self.logger.info(self.uuid + " --  " + output)

        output = ''
        while "download progress" not in output:
            time.sleep(1)
            output = output = self.telnet.read_very_eager().decode('cp437')
            if len(output) > 0:
                self.logger.info(self.uuid + " --  " + output)


        self.logger.info(
            self.uuid + " -- Download image command accepted, download started")



        output = ''
        while self.packageVersion not in output:
            time.sleep(20)
            self.telnet.write(f"show package\n".encode('cp437'))
            output = self.telnet.read_very_eager().decode('cp437')
            if len(output) > 0 :
                self.logger.info(self.uuid + " --  " + output)

        self.logger.info(self.uuid + " -- Download success, package found, installing package")


        self.telnet.write(f"scope auto-install\n".encode('cp437'))
        self.telnet.write(f"install security-pack version {self.packageVersion}\n".encode('cp437'))
        self.telnet.write("yes\n".encode('cp437'))
        self.telnet.write("yes\n".encode('cp437'))

        self.logger.info(self.uuid + " --  " + self.telnet.read_very_eager().decode('cp437'))

        self.logger.info(self.uuid + " --  Final installation triggered")

    def waiting_for_application(self):
        if 'ftd' in self.softwareType:
            output = ''
            while 'FTD initialization finished successfully' not in output:
                time.sleep(5)
                output = self.telnet.read_very_eager().decode('cp437')
                if len(output) > 0:
                    self.logger.info(self.uuid + " --  " + output)

            self.logger.info(self.uuid + " -- FTD initialized successfully")

    def FTDsetup(self):
        output = ''
        while 'login:' not in output:
            time.sleep(5)
            output = self.telnet.read_very_eager().decode('cp437')
            if len(output) > 0 :
                self.logger.info(self.uuid + " --  " + output)

        self.telnet.write("admin\n".encode('cp437'))
        self.telnet.write("Admin123\n".encode('cp437'))
        self.telnet.write("Cxlabs!12\n".encode('cp437'))
        self.telnet.write("Cxlabs!12\n".encode('cp437'))
        time.sleep(60)

        self.telnet.write("connect ftd\n".encode('cp437'))
        self.telnet.write("n\n".encode('cp437')) #display EULA
        self.telnet.write("YES\n".encode('cp437')) #approve EULA
        self.telnet.write("y\n".encode('cp437')) #IPV4 IP
        self.telnet.write("n\n".encode('cp437')) #IPV6 IP
        self.telnet.write("\n".encode('cp437')) #manual IP
        self.telnet.write(f"{self.device.ipAddress}\n".encode('cp437')) #IP
        self.telnet.write(f"{self.device.netmask}\n".encode('cp437'))  # Netmask
        self.telnet.write(f"{self.device.gateway}\n".encode('cp437'))  # GW
        self.telnet.write(f"{self.device.device_name}\n".encode('cp437'))  # Hostname
        self.telnet.write("\n".encode('cp437'))  # DNS
        self.telnet.write("\n".encode('cp437'))  # Search domain
        self.telnet.write("No\n".encode('cp437'))  # Manage the device locally ?
        self.telnet.write("\n".encode('cp437')) #routed mode (default)

        output = self.telnet.read_very_eager().decode('cp437')
        self.logger.info(self.uuid + " --  Final setup done : " + output)


