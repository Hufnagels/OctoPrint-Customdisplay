# coding=utf-8
from __future__ import absolute_import

# Octoprint specific
import octoprint.plugin
from octoprint.events import Events, eventManager
from octoprint.printer import PrinterCallback
import flask

# global modules
import requests
from time import sleep
import time
import json
import sys
# from types import SimpleNamespace
import smbus
import errno

# Plugin specific
from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, ws0010
from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO
# import board
# import adafruit_dht
# import Adafruit_DHT
# from pigpio_dht import DHT11, DHT22
# import dht11
import Python_DHT
from w1thermsensor import W1ThermSensor, Sensor
import paho.mqtt.client as mqtt


"""
class ProgressTempMonitor(PrinterCallback):
    def __init__(self, *args, **kwargs):
        super(ProgressTempMonitor, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.completion = None
        self.time_elapsed_s = None
        self.time_left_s = None
        self.tool0_a = None
        self.tool0_t = None
        self.bed_a = None
        self.bed_t = None

    def on_printer_send_current_data(self, data):
        self.completion = data["progress"]["completion"]
        self.time_elapsed_s = data["progress"]["printTime"]
        self.time_left_s = data["progress"]["printTimeLeft"]

    def on_printer_add_temperature(self, data):
        self.tool0_a = data["tool0"]["actual"]
        self.tool0_t = data["tool0"]["target"]
        self.bed_a = data["bed"]["actual"]
        self.bed_t = data["bed"]["target"]
"""


# getDevice class begin

"""
class getDevice():
    validAddress = ''
    validType = ''
    i2cList = []
    addressList = []

    def getGivenDisplays(self, displays2):
        for device in displays2:
            try:
                self.addressList.append(device['address'])
            except Exception as e:
                print(e)
        # print( "getGivenDisplays" )
        # print( len(self.addressList) )
        # print( self.addressList )
        if (len(self.addressList) > 0):
            return self.addressList
        return False

    def i2cScan(self):
        bus_number = 1  # 1 indicates /dev/i2c-1
        bus = smbus.SMBus(bus_number)
        device_count = 0
        for device in range(3, 128):
            try:
                bus.write_byte(device, 0)
                print("Found {0}".format(hex(device)))
                self.i2cList.append(hex(device))
                device_count = device_count + 1
            except IOError as e:
                if e.errno != errno.EREMOTEIO:
                    print("Error: {0} on address {1}".format(e, hex(device)))
            except Exception as e:  # exception if read_byte fails
                print("Error unknown: {0} ".format(e))

        bus.close()
        bus = None
        print("Found {0} I2C device(s)".format(device_count))
        # print( "i2cScan" )
        # print( len(self.i2cList) )
        # print( self.i2cList )
        if (len(self.i2cList) > 0):
            return self.i2cList
        return False

    def intersection(self, lst1, lst2):
        lst3 = [value for value in lst1 if value in lst2]
        if (len(lst3) > 0):
            return lst3
        return False

    def getConnectedDisplayData(self, address, displays2):
        for device in displays2:
            # print("getConnectedDisplayData")
            # print(address, device)
            if (device['address'] == address[0]):
                print(address, device)
                return device
        return False

    def initDisplay(self, address, displays2):
        display = self.getConnectedDisplayData(address, displays2)
        # print("initDisplay")
        # print(display)
        # print(type(display))
        if (display and display['type'] == 'OLED'):
            # if OLED
            serial = i2c(port=1, address=display['address'])
            # substitute ssd1331(...) or sh1106(...) below if using that device
            # device = ssd1306(serial)
            device = sh1106(serial)
            device.clear()
            return device
        if (display and display['type'] == 'LCD'):
            # if LCD
            device = CharLCD(i2c_expander='PCF8574',
                             address=int(display['address'], 0), port=1,
                             cols=display['width'], rows=display['height'], dotsize=8,
                             charmap='A02',
                             auto_linebreaks=True,
                             backlight_enabled=True)
            # substitute ssd1331(...) or sh1106(...) below if using that device
            # device = ssd1306(serial)
            device.clear()
            return device
        return False

    def checkStatus(self):
        if (self.i2cScan() and self.getGivenDisplays()):
            # print("checking for display")
            address = self.intersection(self.i2cList, self.addressList)
            # print(address)
            if (address):
                device = self.initDisplay(address)
                if (device):
                    return device
                else:
                    return False
            else:
                print("No matching device found")
                return False
        else:
            print("No device found")
            return False

    def __init__(self):
        self.i2cList = []
        self.addressList = []
"""

# getDevice class end


class CustomdisplayPlugin(octoprint.plugin.StartupPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.ProgressPlugin,
                          octoprint.plugin.EventHandlerPlugin,
                          octoprint.printer.PrinterCallback,
                          octoprint.plugin.RestartNeedingPlugin):
    output_time_left = True
    progress_from_time = False
    tempsensors = {
        "DS18B20": [
            {"name": "Bot", "id": "0300a279ea58", "pin": 4},
            {"name": "SKR", "id": "00000c178efd", "pin": 4}
        ],
        "DHT11": [
            {"name": "Top", "id": "", "pin": 27}
        ]
    }
    sensordata = []
    ifttt_event = 'printer_event'
    ifttt_api_key = 'g76cMC4NcQBikT4P_wMdJ'
    validAddress = ''
    validType = ''
    i2cList = []
    addressList = []
    mqtt_broker = '192.168.1.215'
    mqtt_events_base_topic = 'Octopi/events/'
    mqtt_gpio_base_topic = 'Octopi/gpio_state/'
    mqtt_temp_base_topic = 'Octopi/temp/'
    mqtt_port = 1883
    mqtt_MSG = ''
    MQTT_TOPICS = []
    mqtt_flag_connected = 0
    
    def __init__(self):
    	self.mqtt_publish = lambda *args, **kwargs: None
		self.mqtt_subscribe = lambda *args, **kwargs: None
		self.mqtt_unsubscribe = lambda *args, **kwargs: None

    def get_settings_defaults(self):
        return dict(
            ifttt_event='printer_event',
            ifttt_api_key='g76cMC4NcQBikT4P_wMdJ',
            tempsensors={
                "DS18B20": [{"name": "Bot", "id": "0300a279ea58", "pin": 4},
                            {"name": "SKR", "id": "00000c178efd", "pin": 4}],
                "DHT11": [{"name": "Top", "id": "", "pin": 27}]
            },
            displays2=[
                {
                    "type": "OLED",
                    "bus": "SH1106",
                    "width": 128,
                    "height": 64,
                    "address": "0x3c",
                    "enabled": 1
                },
                {
                    "type": "LCD",
                    "bus": "i2clcd",
                    "width": 16,
                    "height": 2,
                    "address": "0x3f",
                    "enabled": 0
                }
            ],
            mqtt_broker = '192.168.1.215',
            mqtt_events_base_topic = 'octoPrint/events/',
            mqtt_gpio_base_topic = 'octoPrint/gpio_state/',
            mqtt_temp_base_topic = 'octoPrint/chamber/',
            mqtt_port = 1883,
            mqtt_MSG = '',
            MQTT_TOPICS = [],
            mqtt_flag_connected = 0

        )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        settings = self._settings

    # self.output_time_left = settings.get_boolean(["output_time_left"])
    # self.progress_from_time = settings.get_boolean(["progress_from_time"])

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/CustomDisplay.js"],
            css=["css/CustomDisplay.css"],
            less=["less/CustomDisplay.less"]
        )

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    def on_after_startup(self):
        self._logger.info("-----------------------------")
        self._logger.info("plugin: Customdisplay started")
        self._logger.info("Customdisplay! (more: %s)" % self._settings.get(["ifttt_api_key"]))
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        # self._printerCommData = ProgressTempMonitor()
        # self._printer.register_callback(self._printerCommData)
        self._printer.register_callback(self)
        if(self.mqtt_flag_connected == 0):
            self.mqtt_connect()

    # ~~ Printer communication Section

    def on_event(self, event, payload):
        """
        INFO - --------event---------------------
        octoprint.plugins.CustomDisplay - INFO - ClientOpened
        octoprint.server.util.flask - INFO - Passively logging in user pisti from 2001:4c4e:1b8e:7000:71e4:36ef:3ad2:6291
        octoprint.access.users - INFO - Logged in user: pisti
        octoprint.plugins.CustomDisplay - INFO - --------event---------------------
        octoprint.plugins.CustomDisplay - INFO - UserLoggedIn
        octoprint.server.util.sockjs - INFO - User pisti logged in on the socket from client 2001:4c4e:1b8e:7000:71e4:36ef:3ad2:6291
        octoprint.plugins.CustomDisplay - INFO - --------event---------------------
        octoprint.plugins.CustomDisplay - INFO - ClientAuthed
        INFO - --------event---------------------
        INFO - PrinterStateChanged
        INFO - --------event---------------------
        INFO - Connected
        INFO - --------event---------------------
        INFO - FileSelected
        
        """
        self._logger.info("--------event---------------------")
        self._logger.info(event)
        self._logger.info("plugin: event: %s", event)
        
        #if (event == "Startup"):
        if(self.mqtt_flag_connected == 0):
            self.mqtt_connect()
        
        rules = [
                event == Events.PRINT_STARTED,
                event == Events.PRINT_PAUSED,
                event == Events.PRINT_RESUMED,
                event == Events.PRINT_DONE,
                event == "PrintCancelling",
                event == Events.PRINT_CANCELLED,
                event == Events.PRINT_FAILED,
                ]
        if all(rules):
            self._logger.info("plugin: payload %s", payload['name'])
            mqtt_MSG=json.dumps({"filename": payload['name'],"eventName":  event});
            MQTT_TOPIC = self._settings.get(["mqtt_events_base_topic"])+self._settings.get(["ifttt_event"])
            #self.send_IFTTT_notification(payload['name'], event)
        else:
            mqtt_MSG=json.dumps({"eventName":  event});
            MQTT_TOPIC = self._settings.get(["mqtt_events_base_topic"])+"other_events"

        self.mqttPublish(MQTT_TOPIC, mqtt_MSG)
 
    def on_printer_send_current_data(self, data):
        if not self._printer.is_printing():
            return
        self.completion = data["progress"]["completion"]
        self.time_elapsed_s = data["progress"]["printTime"]
        self.time_left_s = data["progress"]["printTimeLeft"]
        self._logger.info("--on_printer_send_current_data--------")
        self._logger.info(data["progress"])

    def on_printer_add_temperature(self, data):
        #timeing to avoid mqtt publish in every sec
        
        if (data["tool0"]["actual"] < 30 and data["bed"]["actual"] < 30):
            self._logger.info("--on_printer_add_temperature- if-------")
            self.getSensorData()
            return
        self.tool0_a = data["tool0"]["actual"]
        self.tool0_t = data["tool0"]["target"]
        self.bed_a = data["bed"]["actual"]
        self.bed_t = data["bed"]["target"]
        self._logger.info("--on_printer_add_temperature--------")
        # self._logger.info(type(data["tool0"]["actual"]))
        self._logger.info(self.tool0_a)

    # ~~ Printing progress Section
    """
    # Printing progress
    def on_print_progress(self, storage, path, progress):
        if not self._printer.is_printing():
            return

        progress = 0.0
        time_left = None

        self._logger.info("--on_printer_add_temperature--------")
        self._logger.info(self._printerCommData)

        if self.output_time_left and self._printerCommData.time_left_s is not None:
            # M73 expects time left value in minutes, not seconds
            time_left = self._printerCommData.time_left_s / 60

        if (
            self.progress_from_time and
            self._printerCommData.time_left_s is not None and
            self._printerCommData.time_elapsed_s is not None
        ):
            time_left_s = self._printerCommData.time_left_s
            time_elapsed_s = self._printerCommData.time_elapsed_s
            progress = time_elapsed_s / (time_left_s + time_elapsed_s)
            progress = progress * 100.0
        else:
            progress = self._printerCommData.completion or 0.0

        self._set_progress(progress=progress, time_left=time_left)

    def _set_progress(self, progress, time_left=None):
        if time_left is None:
            gcode = "M73 P{:.0f}".format(progress)
        else:
            gcode = "M73 P{:.0f} R{:.0f}".format(progress, time_left)

        self._logger.info("--_set_progress-------- %s", gcode)
        # self._logger.info(gcode)
        # self._printer.commands(gcode)

    # Temperature data from comm
    def on_printer_add_temperature(self, data):
        for key, value in data.items():
            self._logger.info("--on_printer_add_temperature-------- %s -- %s", key, value)

    def sanitize_temperatures(comm, parsed_temps):
        return dict((k, v) for k, v in parsed_temps.items() if isinstance(v, tuple) and len(v) == 2 and is_sane(v[0]))
    """

    # ~~ TEMP Sensor Section
    def getSensorData(self):
        
        # read DHT11 data using pin
        resp = {}
        humidity = 0
        temperature_c = 0
        """
        try:
            import Python_DHT
            for tempsensors in self.tempsensors['DHT11']:
                dht11sensor = Python_DHT.DHT11
                dht11pin = int(tempsensors['pin'])
                self._logger.info("--dht_device--------")
                self._logger.info(dht11sensor)
                self._logger.info(dht11pin)

                try:
                    humidity, temperature_c = Python_DHT.read_retry(dht11sensor, dht11pin)
                    print(tempsensors['name'] + " T:" + str(temperature_c) + "C H:" + str(humidity) + "%")
                    temperature_f = temperature_c * (9 / 5) + 32
                    self.sensordata.append({'name': tempsensors['name'],'temp': 'T:' + str(temperature_c),'hum': ' H:' + str(humidity) + '%'})
                    #time.sleep(.5)
                    MQTT_TOPIC = self._settings.get(["mqtt_temp_base_topic"])+tempsensors['name']
                    mqtt_MSG=json.dumps({'name': tempsensors['name'],'temp ':  str(temperature_c),'hum': str(humidity) + '%'});
                    self.mqttPublish(MQTT_TOPIC, mqtt_MSG)
                except Exception as err:
                    # print("Oops! " + tempsensors['name'] + " not found. Check connection! ")
                    self._logger.info("--getSensorData--------")
                    self._logger.info(err)
                    self.sensordata.append({'name': tempsensors['name'], 'temp': 'T: n/a', 'hum': ' H: n/a'})
        except ModuleNotFoundError:
            print("module 'Python_DHT' is notinstalled")
            self.sensordata.append({'name': tempsensors['name'], 'temp': 'T: n/a', 'hum': ' H: n/a'})
        # read DS18B20 data using W1ThermSensor
        """
        try:
            import w1thermsensor
            for tempsensors in self.tempsensors['DS18B20']:
                humidity = 0
                try:
                    temperature_c = W1ThermSensor(Sensor.DS18B20, tempsensors['id']).get_temperature()
                    print(tempsensors['name'] + ": %-3.1f C" % temperature_c)
                    # print("Temperature: %-3.1f C" % data)
                    self.sensordata.append({'name': tempsensors['name'], 'temp': 'T:' + str(round(temperature_c, 1)),'hum': ' H:' + str(humidity) + '%'})
                    MQTT_TOPIC = self._settings.get(["mqtt_temp_base_topic"])+tempsensors['name']
                    mqtt_MSG=json.dumps({'name': tempsensors['name'], 'temp': str(round(temperature_c, 1)),'hum': str(humidity) + '%'});
                    self.mqttPublish(MQTT_TOPIC, mqtt_MSG)
                except Exception:
                    # print("Oops! " + tempsensors['name'] + "(" +tempsensors['id'] + ") not found. Check connection! ")
                    self.sensordata.append({'name': tempsensors['name'], 'temp': 'T: n/a', 'hum': ' H:' + str(humidity) + '%'})
        except ModuleNotFoundError:
            print("module 'w1thermsensor' is not installed")
            self.sensordata.append({'name': tempsensors['name'], 'temp': 'T: n/a', 'hum': ' H: n/a'})
        return self.sensordata

    # ~~ OLED/LCD Section
    def getGivenDisplays(self,):
        for device in self._settings.displays2:
            try:
                self.addressList.append(device['address'])
            except Exception as e:
                print(e)
        # print( "getGivenDisplays" )
        # print( len(self.addressList) )
        # print( self.addressList )
        if (len(self.addressList) > 0):
            return self.addressList
        return False

    def i2cScan(self):
        bus_number = 1  # 1 indicates /dev/i2c-1
        bus = smbus.SMBus(bus_number)
        device_count = 0
        for device in range(3, 128):
            try:
                bus.write_byte(device, 0)
                print("Found {0}".format(hex(device)))
                self.i2cList.append(hex(device))
                device_count = device_count + 1
            except IOError as e:
                if e.errno != errno.EREMOTEIO:
                    print("Error: {0} on address {1}".format(e, hex(device)))
            except Exception as e:  # exception if read_byte fails
                print("Error unknown: {0} ".format(e))

        bus.close()
        bus = None
        print("Found {0} I2C device(s)".format(device_count))
        # print( "i2cScan" )
        # print( len(self.i2cList) )
        # print( self.i2cList )
        if (len(self.i2cList) > 0):
            return self.i2cList
        return False

    def intersection(self, lst1, lst2):
        lst3 = [value for value in lst1 if value in lst2]
        if (len(lst3) > 0):
            return lst3
        return False

    def getConnectedDisplayData(self, address):
        for device in self._settings.displays2:
            # print("getConnectedDisplayData")
            # print(address, device)
            if (device['address'] == address[0]):
                print(address, device)
                return device
        return False

    def initDisplay(self, address):
        display = self.getConnectedDisplayData(address, self._settings.displays2)
        # print("initDisplay")
        # print(display)
        # print(type(display))
        if (display and display['type'] == 'OLED'):
            # if OLED
            serial = i2c(port=1, address=display['address'])
            # substitute ssd1331(...) or sh1106(...) below if using that device
            # device = ssd1306(serial)
            device = sh1106(serial)
            device.clear()
            return device
        if (display and display['type'] == 'LCD'):
            # if LCD
            device = CharLCD(i2c_expander='PCF8574',
                             address=int(display['address'], 0), port=1,
                             cols=display['width'], rows=display['height'], dotsize=8,
                             charmap='A02',
                             auto_linebreaks=True,
                             backlight_enabled=True)
            # substitute ssd1331(...) or sh1106(...) below if using that device
            # device = ssd1306(serial)
            device.clear()
            return device
        return False

    def checkStatus(self):
        if (self.i2cScan() and self.getGivenDisplays()):
            # print("checking for display")
            address = self.intersection(self.i2cList, self.addressList)
            # print(address)
            if (address):
                device = self.initDisplay(address)
                if (device):
                    return device
                else:
                    return False
            else:
                print("No matching device found")
                return False
        else:
            print("No device found")
            return False
    # ~~ Print message Section
    # ~~ Printer communication Section

    # ~~ IFTTT Section
    def send_IFTTT_notification(self, fileName, event):
        self._logger.info("plugin: Customdisplay")
        self._logger.info("send_notification to IFTTT")
        # self._logger.info("Sending notification to: %s with msg: %s with key: %s", provider, message, api_key)
        try:
            res = self.build_IFTTT_request( self._settings.get(["ifttt_event"]),
                                            self._settings.get(["ifttt_api_key"]),
                                            fileName,
                                            event)
            if (res.status_code != requests.codes['ok']):
                try:
                    j = res.json()
                except ValueError:
                    self._logger.info("plugin: Customdisplay")
                    self._logger.info('Error: Could not parse server response. Event not sent')
        except Exception as e:
            self._logger.info("plugin: Customdisplay")
            self._logger.info("try to communicate with IFTTT server. error occurred:")
            self._logger.info(e)
            pass
            """
            except requests.exceptions.ConnectionError:
                self._logger.info("plugin: Customdisplay")
                self._logger.info("Error: Could not connect to IFTTT")
            except requests.exceptions.HTTPError:
                self._logger.info("plugin: Customdisplay")
                self._logger.info("Error: Received invalid response")
            except requests.exceptions.Timeout:
                self._logger.info("plugin: Customdisplay")
                self._logger.info("Error: Request timed out")
            except requests.exceptions.TooManyRedirects:
                self._logger.info("plugin: Customdisplay")
                self._logger.info("Error: Too many redirects")
            except requests.exceptions.RequestException as reqe:
                self._logger.info("plugin: Customdisplay")
                self._logger.info("Error: {e}".format(e=reqe))
            """

        # for err in j['errors']:
        #    self._logger.info('Error: {}'.format(err['message']))
        """
        except Exception as ex:
            self._logger.info("plugin: Customdisplay")
            self._logger.info("IFTTT communication error")
            self._logger.info(ex)
        """

    def build_IFTTT_request(self, ifttt_event, ifttt_api_key, fname, event):
        fname = "masina"
        url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}?value1={f}&value2={en}".format(e=ifttt_event,
                                                                                               k=ifttt_api_key, f=fname,
                                                                                               en=event)
        # url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}".format(e=ifttt_event, k=api_key)
        payload = {'value1': fname, 'value2': event}
        return requests.post(url, data=payload)

    # ~~ MQTT Section
    def mqtt_connect(self):
        self.client = mqtt.Client()
        # Register connect callback
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message
        self.client.connect(self._settings.get(["mqtt_broker"]), self._settings.get(["mqtt_port"]), 60)
        try:
            self.client.loop_forever()
            self.mqtt_flag_connected = 1
            self._logger.info("--------mqtt connected---------------------")
            sleep(60)
        except KeyboardInterrupt:
            MQTT_TOPIC = self._settings.get(["mqtt_events_base_topic"])+self._settings.get(["ifttt_event"])
            self.mqttUnSubscribe(MQTT_TOPIC)

    def on_connect(self,client, userdata, flags, rc):
        self._logger.info("--------mqtt---------------------")
        print("Connection returned result: "+str(rc))
        MQTT_TOPIC = self._settings.get(["mqtt_events_base_topic"])+self._settings.get(["ifttt_event"])
        self.mqttSubscribe(MQTT_TOPIC)

    def on_publish(self, client, userdata, mid):
        print("Message Published...", mid)

    def on_message(self,client, userdata, message):
        print("Received message: " + str(message.payload.decode('utf-8')) + " on topic "+ message.topic + " with QoS " + str(message.qos))
        print(str(message.payload.decode('utf-8')))
    
    def mqttSubscribe(self, topic):
        self.client.subscribe(topic)
    
    def mqttUnSubscribe(self, topic):
        self.client.unsubscribe(topic)
    
    def mqttPublish(self, topic, message):
        self.client.publish(topic, message)

    # ~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            CustomDisplay=dict(
                displayName="Customdisplay Plugin",
                displayVersion=self._plugin_version,
                # version check: github repository
                type="github_release",
                user="Hufnagels",
                repo="OctoPrint-Customdisplay",
                current=self._plugin_version,
                # update method: pip
                pip="https://github.com/Hufnagels/OctoPrint-Customdisplay/archive/{target_version}.zip"
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Customdisplay Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
# __plugin_pythoncompat__ = ">=2.7,<3" # only python 2
# __plugin_pythoncompat__ = ">=3,<4" # only python 3
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CustomdisplayPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
