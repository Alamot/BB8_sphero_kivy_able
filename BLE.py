# Author: Alamot
from able import BluetoothDispatcher, GATT_SUCCESS
from kivy.properties import BooleanProperty, NumericProperty
from kivy.logger import Logger


def unpack_nibbles(byte):
    return str(byte >> 4) + "." + str(byte & 0x0F)


class BTInterface(BluetoothDispatcher):
    ready = BooleanProperty(False)
    battery_voltage = NumericProperty(0)
    rssi = NumericProperty(0)
    
    def __init__(self, target_name="BB", **args):
        super(BTInterface, self).__init__(**args)
        self.target_name = target_name
        self.uids = {"antidos": "22bb746f-2bbd-7554-2d6f-726568705327",
                     "wakecpu": "22bb746f-2bbf-7554-2d6f-726568705327",
                     "txpower": "22bb746f-2bb2-7554-2d6f-726568705327",
                     "notify": "22bb746f-2ba6-7554-2d6f-726568705327",
                     "roll": "22bb746f-2ba1-7554-2d6f-726568705327"}
        self.services = {"antidos": None,
                         "wakecpu": None,
                         "txpower": None,
                         "roll": None,
                         "notify": None}
        self.power_states = {0:"-", 1:"charging", 2:"OK", 3:"low", 4:"critical"}
        self.clear_stats()

    def clear_stats(self):
        self.ready = False
        self.device = None
        self.sphero_app_version = "-"        
        self.power_state = "-"
        self.num_recharges = 0
        self.secs_since_recharge = 0
        self.rssi = 0
        self.battery_voltage = 0
        
    def connect(self, *args, **kwargs):
        if self.ready:
            return
        self.stop_scan() # stop previous scan
        Logger.info("Starting new scan...")
        self.start_scan() # start a scan for devices

    def disconnect(self):  
        if not self.ready:
            return
        self.clear_stats()        
        self.close_gatt()

    def on_device(self, device, rssi, advertisement):
        name = device.getName()
        if name:
            Logger.info("Device found: " + name)
            Logger.info("Device RSSI: " + str(rssi))
            if name.startswith(self.target_name):
                self.device = device
                self.rssi = int(rssi)
                Logger.info("Device matched target! Stopping scan...")                
                self.stop_scan()

    def on_rssi_updated(self, rssi, status):
        if status == GATT_SUCCESS:
            self.rssi = int(rssi)

    def on_scan_completed(self):
        if self.device:
            Logger.info("Connecting to device...")
            self.connect_gatt(self.device)

    def on_connection_state_change(self, status, state):
        if status == GATT_SUCCESS and state:
            Logger.info("Connection established. Discovering services...")
            self.discover_services() 
        else:  
            Logger.error("Connection error.")
            self.close_gatt()  

    def on_services(self, status, services):
        self.services["antidos"] = services.search(self.uids["antidos"])
        self.services["wakecpu"] = services.search(self.uids["wakecpu"])
        self.services["txpower"] = services.search(self.uids["txpower"])
        self.services["notify"] = services.search(self.uids["notify"])
        self.services["roll"] = services.search(self.uids["roll"])
        Logger.info("Initiating startup sequence...")
        self.write_characteristic(self.services["antidos"], '011i3')
        self.write_characteristic(self.services["txpower"], '\x0007')
        self.write_characteristic(self.services["wakecpu"], '\x01')
        self.ready = True      
        self.enable_notifications(self.services["notify"], True)

    def on_characteristic_write(self, characteristic, status):
        if not self.ready:
            return
        if status == GATT_SUCCESS:
            pass
            # Logger.info("Characteristic write to " + str(characteristic) + " succeededd")
        else:
            Logger.error("Write status: %d", status)

    def on_characteristic_changed(self, characteristic):
        if not self.ready:
            return
        uuid = characteristic.getUuid().toString()
        if self.uids["notify"] in uuid:
            v = bytes(characteristic.getValue())
            h = v.hex()
            Logger.info(h)
            if h[:6] == "ffff00":
                try:
                    if self.response_type == "version":
                        self.response_type = None
                        self.sphero_app_version = str(v[8]) + "." + str(v[9])
                        Logger.info("[VERSION]" + " SOP1 " + hex(v[0])[2:] + " SOP2 " + hex(v[1])[2:] + " MRSP " + hex(v[2])[2:] +  " SEQ " + str(v[3]) + 
                                    " DLEN " + str(v[4]) + " RECV " + str(v[5]) + " MDL " + unpack_nibbles(v[6]) + " HW " + str(v[7]) + 
                                    " MSA " + self.sphero_app_version + " BL " + unpack_nibbles(v[10]) + " BAS " + unpack_nibbles(v[11]) + 
                                    " OVERLAY_MANAGER " + unpack_nibbles(v[12]))
                    elif self.response_type == "powerstate":
                        self.response_type = None
                        self.battery_voltage = int.from_bytes(v[7:9], "big")/100
                        self.power_state = self.power_states[v[6]]
                        self.num_recharges = int.from_bytes(v[9:11], "big")
                        self.secs_since_recharge = int.from_bytes(v[11:13], "big")
                        Logger.info("[POWER]" + " SOP1 " + hex(v[0])[2:] + " SOP2 " + hex(v[1])[2:] + " MRSP " + hex(v[2])[2:] +  " SEQ " + str(v[3]) + 
                                    " DLEN " + str(v[4]) + " RECV " + str(v[5]) + " Powerstate " + self.power_state +
                                    " BattVoltage " + str(self.battery_voltage) + " NumCharges " + str(self.num_recharges) + 
                                    " TimeSinceChg " + str(self.secs_since_recharge))
                except IndexError:
                    pass
           
    def send(self, data):
        if not self.ready:
            return
        self.write_characteristic(self.services["roll"], data)

    def set_response_type(self, response_type):
        self.response_type = response_type
        
