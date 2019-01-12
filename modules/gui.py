# Copyright (C) 2016   CzT/Vladislav Ivanov
import shutil
import sys

import threading

import requests

from modules.helper.updater import UPDATE_FOLDER, do_update, UPDATE_FILE, prepare_update
from modules.interface.controls import MainMenuToolBar

from modules.interface.events import EVT_STATUS_CHANGE
from modules.interface.frames import OAuthBrowser, StatusFrame, UpdateDialog
from modules.interface.settings import SettingsWindow
from modules.interface.types import *
from collections import OrderedDict
import os
import logging
import wx
from modules.helper.system import translate_key, WINDOWS, LOG_FOLDER
from modules.helper.module import UIModule
from interface import TRANSPARENCY_MULTIPLIER

if WINDOWS:
    from interface import chromium as browser

    HAS_CHROME = True
else:
    from wx import html2 as browser
    HAS_CHROME = False

# ToDO: Support customization of borders/spacings

log = logging.getLogger('chat_gui')
SECTION_GUI_TAG = '__gui'
SKIP_TXT_CONTROLS = ['list_input', 'list_input2']
SKIP_BUTTONS = ['list_add', 'list_remove', 'apply_button', 'cancel_button', 'ok_button']
ITEM_SPACING_VERT = 6
ITEM_SPACING_HORZ = 30
CHUNK_SIZE = 1024 ** 2


def create_categories(loaded_modules):
    cat_dict = OrderedDict()
    for module_name, module in loaded_modules.items():
        if not module.config:
            continue

        tag = module.category
        if tag == 'hidden':
            continue

        if tag not in cat_dict:
            cat_dict[tag] = OrderedDict()
        cat_dict[tag][module_name] = module
    return cat_dict


class ChatGui(wx.Frame):
    def __init__(self, parent, title, url, **kwargs):
        # Setting the settings
        self.main_module = kwargs.get('main_module')
        self.gui_settings = kwargs.get('gui_settings')
        self.loaded_modules = kwargs.get('loaded_modules')
        self.queue = kwargs.get('queue')
        self.settings_window = None
        self.status_frame = None
        self.browser = None
        self.first_readjust = False

        wx.Frame.__init__(self, parent, title=title,
                          size=self.gui_settings.get('size'),
                          pos=self.gui_settings.get('position'))
        # Set window style
        if self.gui_settings.get('transparency') > 0:
            transp = self.gui_settings.get('transparency')
            if transp > 90:
                transp = 90
            log.info("Application is transparent")
            self.SetTransparent((100 - transp) * TRANSPARENCY_MULTIPLIER)
        if self.gui_settings.get('borderless', False):
            log.info("Application is in borderless mode")
            styles = wx.CLIP_CHILDREN | wx.BORDER_NONE | wx.FRAME_SHAPED
        else:
            styles = wx.DEFAULT_FRAME_STYLE
        if self.gui_settings.get('on_top', False):
            log.info("Application is on top")
            styles = styles | wx.STAY_ON_TOP
        self.styles = styles
        self.SetFocus()
        self.SetWindowStyle(styles)

        # Creating categories for gui
        log.debug("Sorting modules to categories")
        self.sorted_categories = create_categories(self.loaded_modules)

        # Creating main gui window
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = MainMenuToolBar(self, main_class=self)
        vbox.Add(self.toolbar, 0, wx.EXPAND)

        self.status_frame = StatusFrame(self)
        self.status_frame.load()

        vbox.Add(self.status_frame, 0, wx.EXPAND)
        if self.main_module.get_config('gui', 'show_counters'):
            if self.status_frame.chats:
                self.status_frame.Show(True)
                self.status_frame.Fit()
                self.status_frame.Layout()
        if self.gui_settings['show_browser']:
            if HAS_CHROME:
                self.browser = browser.ChromeCtrl(self, use_timer=False, url=str(url), browser_settings={})
                if self.main_module.get_config('system', 'testing_mode'):
                    self.browser2 = browser.ChromeCtrl(self, use_timer=False, url=str(url).replace('/gui', ''),
                                                       browser_settings={})
                    vbox.Add(self.browser2, 1, wx.EXPAND)
            else:
                self.browser = browser.WebView.New(parent=self, url=url, name='LalkaWebViewGui')
                if self.main_module.get_config('system', 'testing_mode'):
                    self.browser2 = browser.WebView.New(
                        parent=self,
                        url=str(url).replace('/gui', ''), name='LalkaWebViewGui2')
                    vbox.Add(self.browser2, 1, wx.EXPAND)
            vbox.Add(self.browser, 1, wx.EXPAND)

        # Set events
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(EVT_STATUS_CHANGE, self.process_status_change)
        self.Bind(wx.EVT_ACTIVATE, self.activate)

        # Show window after creation
        self.SetSizer(vbox)

        if not self.gui_settings['show_browser']:
            self.Layout()
            self.Fit()
            current_size = self.GetSize()
            max_height = self.status_frame.GetSize()[1] + self.toolbar.GetBestSize()[1]
            if current_size[1] != max_height:
                self.SetSize(wx.Size(current_size[0], max_height))

        self.Show(True)
        # Show update dialog if new version found
        if self.main_module.update:
            self.check_update()

    def check_update(self):
        # Do updates only on Windows, and if it's frozen. Duh.
        if WINDOWS and hasattr(sys, 'frozen'):
            with wx.MessageDialog(
                    self, message="There is new version, do you want to update?",
                    caption="New Update Available",
                    style=wx.YES_NO | wx.YES_DEFAULT,
                    pos=wx.DefaultPosition) as dialog:
                response = dialog.ShowModal()
                if response == wx.ID_YES:
                    self.do_update(self.main_module.get_update_url())
                    self.on_close('exiting')

    def download_update(self, url, filename, dialog):
        # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        size = r.headers.get('content-length')

        wx.CallAfter(dialog.gauge.SetRange, int(size))
        with open(os.path.join(UPDATE_FOLDER, filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    wx.CallAfter(dialog.update_progress, CHUNK_SIZE)

        wx.CallAfter(dialog.update_text.SetLabel, "Unpacking update...")
        prepare_update()
        wx.CallAfter(dialog.update_text.SetLabel, "Update is ready, do you want to proceed?")
        ok_button_id = dialog.GetAffirmativeId()
        ok_button = dialog.FindWindowById(ok_button_id, dialog)
        wx.CallAfter(ok_button.Enable)

    def do_update(self, url):
        if os.path.exists(os.path.join(UPDATE_FOLDER)):
            shutil.rmtree(os.path.join(UPDATE_FOLDER))
        os.mkdir(UPDATE_FOLDER)

        with UpdateDialog(self) as dlg:
            download_thread = threading.Thread(target=self.download_update, args=[url, UPDATE_FILE, dlg])
            download_thread.start()
            response = dlg.ShowModal()
            if response == wx.ID_OK:
                do_update()
                self.main_module.config['system']['current_version'] = self.main_module.get_version()
                self.main_module.apply_settings()
        return True

    def activate(self, event):
        if not self.first_readjust and not self.gui_settings['show_browser']:
            self.first_readjust = True
            if self.GetBestSize()[1] > self.GetSize()[1]:
                self.SetSize(self.GetBestSize())
            self.Layout()
            self.Fit()
        event.Skip()

    def on_close(self, event):
        log.info("Exiting...")
        log.debug(event)

        # Saving last window size
        config = self.loaded_modules['main'].get_config('gui_information')

        if self.gui_settings['show_browser']:
            size = self.Size
            config['width'] = size[0]
            config['height'] = size[1]
        config['pos_x'] = self.Position.x
        config['pos_y'] = self.Position.y

        for module_name, module_dict in self.loaded_modules.iteritems():
            log.info('stopping %s', module_name)
            module_dict.apply_settings(system_exit=True)
        self.status_frame.Close()
        log.info('all done, exiting...')
        if isinstance(event, wx.Event):
            event.Skip()
        else:
            self.Destroy()

    @staticmethod
    def on_right_down(event):
        log.info(event)
        event.Skip()

    def on_settings(self, event):
        log.debug("Got event from {0}".format(event.GetId()))
        if self.settings_window:
            self.settings_window.Maximize(False)
            self.settings_window.Raise()
            self.settings_window.Restore()
            self.settings_window.SetFocus()
        else:
            self.settings_window = SettingsWindow(
                self,
                title=translate_key('settings'),
                size=(700, 400),
                main_class=self,
                categories=self.sorted_categories)

    def on_reload(self, event):
        webchat = self.loaded_modules.get('webchat')
        if webchat:
            webchat.reload_chat()

    def create_browser(self, url):
        browser_window = OAuthBrowser(self, url)
        pass

    def process_status_change(self, event):
        log.debug('PROCESSING STATUS CHANGE %s', event.data)
        data = event.data
        if data['type'] in ['viewers', 'channel_label']:
            data['item'].SetLabel(data['value'])
        elif data['type'] == 'channel_state':
            data['item'].SetBackgroundColour(data['value'])
        self.Layout()


class GuiThread(UIModule):
    title = 'LalkaChat'
    url = 'http://localhost'
    port = '8080'

    def __init__(self, **kwargs):
        UIModule.__init__(self, **kwargs)
        self._category = 'hidden'
        self.daemon = True
        self.gui = None
        self.kwargs = kwargs
        self.port = self.kwargs['loaded_modules']['webchat'].port

    def run(self):
        if HAS_CHROME:
            browser.initialize()
        url = ':'.join([self.url, str(self.port)])
        url += '/gui'
        console = self.kwargs['loaded_modules']['main'].get_config('gui', 'show_console')
        if console:
            app = wx.App(False)
        else:
            app = wx.App(True, filename=os.path.join(LOG_FOLDER, 'main.log'))
        self.gui = ChatGui(None, "LalkaChat", url, **self.kwargs)  # A Frame is a top-level window.
        app.MainLoop()
        log.info('quit main loop')
        del app
        self.quit()

    def apply_settings(self, **kwargs):
        pass

    def quit(self):
        if HAS_CHROME:
            browser.shutdown()
        os._exit(0)
