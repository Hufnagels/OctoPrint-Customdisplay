# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.events import Events
import flask


import requests
from time import sleep
import time
import json
#from types import SimpleNamespace
import smbus
import errno

from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, ws0010
from RPLCD.i2c import CharLCD
import Python_DHT
from w1thermsensor import W1ThermSensor, Sensor

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

class CustomdisplayPlugin(octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.SettingsPlugin):

    def on_after_startup(self):
        self._logger.info("-----------------------------")
        self._logger.info("plugin: Customdisplay start")

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(url="https://en.wikipedia.org/wiki/Hello_world")

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/CustomDisplay.js"],
			css=["css/CustomDisplay.css"],
			less=["less/CustomDisplay.less"]
		)

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]


    ##~~ IFTTT Section
    def send_notification(self, message):
        provider = 'ifttt'
        api_key = 'g76cMC4NcQBikT4P_wMdJ'
        event = 'printer_event'
        try:
            self._logger.info("send_notification to IFTTT while M600 gcode sent", provider)
            if provider == 'ifttt':
                self._logger.debug("Sending notification to: %s with msg: %s with key: %s", provider, message, api_key)
                try:
                    res = self.build_ifttt_request(message, event, api_key)
                except requests.exceptions.ConnectionError:
                    self._logger.info("Error: Could not connect to IFTTT")
                except requests.exceptions.HTTPError:
                    self._logger.info("Error: Received invalid response")
                except requests.exceptions.Timeout:
                    self._logger.info("Error: Request timed out")
                except requests.exceptions.TooManyRedirects:
                    self._logger.info("Error: Too many redirects")
                except requests.exceptions.RequestException as reqe:
                    self._logger.info("Error: {e}".format(e=reqe))
                if res.status_code != requests.codes['ok']:
                    try:
                        j = res.json()
                    except ValueError:
                        self._logger.info('Error: Could not parse server response. Event not sent')
                    for err in j['errors']:
                        self._logger.info('Error: {}'.format(err['message']))
        except Exception as ex:
            self.log_error(ex)
            pass

    def build_ifttt_request(self, message, event, api_key):
        url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}/".format(e=event, k=api_key)
        payload = {'value1': message,}
        return requests.post(url, data=payload)








	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
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
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = CustomdisplayPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
