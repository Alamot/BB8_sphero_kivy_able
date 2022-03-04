# Author: Alamot
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.logger import Logger
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.slider import MDSlider
from kivy.garden.joystick import Joystick
from kivy.uix.colorpicker import ColorPicker
import sphero_driver


class BB8App(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.bb8 = None
        self.root = MDBoxLayout(orientation="vertical", padding=10, spacing=50)
        self.color_picker = ColorPicker(size_hint=(1, .3))
        self.slider_box = MDBoxLayout(orientation="horizontal", size_hint=(1, .1), padding=10, spacing=10)
        self.backled_label = MDLabel(text="Back LED", size_hint=(0.3, 1))
        self.backled_slider = MDSlider(min=0, max=255, value=0)
        self.joystick_label = MDLabel(text="Heading: 0  |  Magnitude: 0", size_hint=(1, .05), padding=(20,20))
        self.joystick = Joystick(size_hint=(1, 0.4))
        self.status_label = MDLabel(text="Sphero App version: -\nBattery: - \nNumber of recharges: -\nRSSI: -", size_hint=(1, .1), padding=(20,20))
        self.buttons_box = MDBoxLayout(orientation="horizontal", size_hint=(1, 0.05), padding=10, spacing=10)    
        self.connect_button = MDRaisedButton(text='Connect to BB8', md_bg_color=(0, 0.75, 0, 1), on_press=self.connect)
        self.disconnect_button = MDRaisedButton(text='Disconnect', md_bg_color=(0.5, 0.5, 0.5, 1), on_press=self.disconnect)
        self.sleep_button = MDRaisedButton(text='Sleep', md_bg_color=(0.5, 0.5, 0.5, 1), on_press=self.sleep)
        self.root.add_widget(self.color_picker)
        self.root.add_widget(self.slider_box)
        self.slider_box.add_widget(self.backled_label)
        self.slider_box.add_widget(self.backled_slider)
        self.root.add_widget(self.joystick_label)
        self.root.add_widget(self.joystick)
        self.root.add_widget(self.status_label)
        self.root.add_widget(self.buttons_box)
        self.buttons_box.add_widget(self.connect_button)
        self.buttons_box.add_widget(self.disconnect_button)
        self.buttons_box.add_widget(self.sleep_button)
        self.color_picker.bind(color=self.on_color_changed)    
        self.backled_slider.bind(value=self.on_backled_changed)    
        self.joystick.bind(pad=self.on_joystick_changed)
        Clock.schedule_interval(self.update_status, 5)

    def is_ready(self):   
        if not self.bb8:
            return False
        if not self.bb8.ble:
            return False    
        if not self.bb8.ble.ready:
            return False
        return True

    def connect(self, *args, **kwargs):
        if not self.bb8:
            self.bb8 = sphero_driver.Sphero(target_name="BB")
        self.bb8.connect()
        self.bb8.ble.bind(ready=self.on_state_changed)
        self.bb8.ble.bind(rssi=self.on_stats_changed)
        self.bb8.ble.bind(battery_voltage=self.on_stats_changed)

    def disconnect(self, *args, **kwargs):
        if not self.is_ready():
            return   
        self.bb8.disconnect()

    def sleep(self, *args, **kwargs):
        if not self.is_ready():
            return   
        self.bb8.go_to_sleep(0, 0, False)

    def update_status(self, dt):
        if not self.is_ready():
            return   
        self.bb8.ble.update_rssi()
        self.bb8.set_response_type("powerstate")
        self.bb8.get_power_state(True)        

    def on_stats_changed(self, *args, **kwargs):
        if not self.bb8 or not self.bb8.ble:
            return 
        text = "Sphero App version: {}\nBattery: {} ({}V)\nNumber of recharges: {} (last recharge: {}s)\nRSSI: {} dBm"
        self.status_label.text = text.format(self.bb8.ble.sphero_app_version, self.bb8.ble.power_state, str(self.bb8.ble.battery_voltage), str(self.bb8.ble.num_recharges), str(self.bb8.ble.secs_since_recharge), str(self.bb8.ble.rssi))
        
    def on_state_changed(self, *args, **kwargs):
        if self.is_ready():
            self.bb8.set_response_type("version")
            self.bb8.get_version(True)               
            self.bb8.get_version(True)   
            self.connect_button.md_bg_color = (0.5, 0.5, 0.5, 1)
            self.disconnect_button.md_bg_color = (1, 0, 0, 1)
            self.sleep_button.md_bg_color = (0.5, 0, 0, 1)
        else:
            self.connect_button.md_bg_color = (0, 0.75, 0, 1)
            self.disconnect_button.md_bg_color = (0.5, 0.5, 0.5, 1)
            self.sleep_button.md_bg_color = (0.5, 0.5, 0.5, 1)

    def on_color_changed(self, instance, value):
        if not self.is_ready():
            return
        colors = str(instance.hex_color)[1:]
        red, green, blue, alpha = [int(colors[i:i+2], 16) for i in range(0, len(colors), 2)]
        self.bb8.set_rgb_led(red, green, blue, 0, False)

    def on_backled_changed(self, obj, value):
        if not self.is_ready():
            return 
        self.bb8.set_back_led((int(value)), False)

    def on_joystick_changed(self, joystick, pad):
        heading = int(joystick.angle)
        magnitude = int(255*joystick.magnitude)
        if heading:
            heading = (90 - heading) % 360
        text = "Heading: {}  |  Magnitude: {}"
        self.joystick_label.text = text.format(str(heading), str(magnitude))
        if not self.is_ready():
            return

        if magnitude:
            self.bb8.roll(magnitude, heading, 1, False)
        else:
            self.bb8.roll(0, heading, 0, False)            
    
 
if __name__ == '__main__':
    BB8App().run()

