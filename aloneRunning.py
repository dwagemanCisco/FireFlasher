import time
from utils.reimage import deviceReimage
from utils.device import caloDevice
import traceback
import config.logging_config
import uuid



def main():
    # # Object used to interect with Calo
    # calo = CaloTool("dwageman", "GHBpnl891992!")
    #
    # #
    #
    # devices = calo.search_for_available_firepower_brussels_by_model('1010')
    # print()
    # if len(devices) == 0:
    #     pass
    #     print ("Cannot find devices with mentioned criteria")
    # else:
    #     # Select first device in the list
    #     name = list(devices.keys())[0]
    #     device = devices[name]
    #
    #     # print devices details
    #     print(str(device))
    #
    #     # book the device
    #     booking = calo.book_device(device.device_id)
    #     device.setTestBed(booking)
    #
    #     print(booking)
    #
    #     # Clear console
    #     clear = calo.clear_console(device.device_id)
    #     print(clear)
    #
    #     # Reboot device
    #     reboot = calo.reboot_device(device)
    #     print(reboot)
    #
    #     device_id = device.device_id
    #     testbed = device.testbed
    #     vlan = device.vlan
    #
    #     # device_id = '406603_2'
    #     # testbed = 'Apr24dwagemanBRUTestbed2945'
    #     # vlan = '66'
    #     switchMatrix = calo.switch_matrix_enable(device_id, testbed, vlan)
    #     print (switchMatrix)

    device_id = "not needed"
    uri = "not needed"
    device_name = 'BSNS-1010-7'
    model_number = "FPR1010"
    serial_number = "not needed"
    console_access = 'BRU-COM-0-087:2126'
    state = "not needed"




    softwareVersion = '7.3.1'
    softwareType = 'FTD'


    device = caloDevice(device_id, uri, device_name, model_number, serial_number, state, console_access)



    deviceConsole = deviceReimage(device,softwareVersion,softwareType)
    deviceConsole.uuid = "ab2d0fc0-7224-11ec-8ef2-b658b885fb3"
    # deviceConsole.rommon_mode()
    # deviceConsole.factory_reset()
    try:
        deviceConsole.establish_telnet_connection()
    except Exception as e:
        print(traceback.format_exc())

    deviceConsole.rommon_mode()
    print(deviceConsole.defineNetworkAndBootImage())
    deviceConsole.startReimage()
    deviceConsole.finalInstall()


    while (1):
        output = deviceConsole.send_command_and_read_output('')
        time.sleep(3)
        print(output)







if __name__ == main():
    main()