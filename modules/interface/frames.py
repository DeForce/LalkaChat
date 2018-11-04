import logging
import threading

import time
import wx

from modules.helper.module import ConfigModule, CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING
from modules.helper.system import WINDOWS

try:
    from cefpython3.wx import chromectrl as browser
    HAS_CHROME = True
except ImportError:
    from wx import html2 as browser

log = logging.getLogger('chat_gui')

CHANNEL_STATUS_COLORS = {
    CHANNEL_ONLINE: wx.Colour(0, 128, 0),
    CHANNEL_OFFLINE: wx.Colour(255, 0, 0),
    CHANNEL_PENDING: wx.Colour(200, 200, 0)
}


class OAuthBrowser(wx.Frame):
    def __init__(self, parent, url):
        wx.Frame.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        if HAS_CHROME:
            self.browser = browser.ChromeWindow(self, url)
        else:
            self.browser = browser.WebView.New(parent=self, url=url, name='LalkaWebViewGui')

        self.sizer.Add(self.browser, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.Show()
        self.SetFocus()


class StatusFrame(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=wx.Size(-1, 24))
        self.parent = parent
        self.chats = {}
        self.border_sizer = self._create_sizer()
        self.chat_modules = None
        self._update_thread = None

        if WINDOWS:
            self.SetBackgroundColour('cream')

    def load(self):
        self.chat_modules = self.parent.sorted_categories['chat']
        for chat_name, chat_settings in self.chat_modules.items():
            if chat_name == 'chat':
                continue

            class_item = chat_settings['class']
            channels = class_item.channels

            for channel_name, channel_class in channels.items():
                wx.CallAfter(self.add_channel, chat_name, channel_name)

        self._update_thread = threading.Thread(target=self._frame_update, name='StatusFrameUpdateThread')
        self._update_thread.daemon = True
        self._update_thread.start()

        self.Fit()
        self.Layout()
        self.Show(False)

    @property
    def chat_count(self):
        return sum([len(item.values()) for item in self.chats.values()])

    def _frame_update(self):
        while True:
            for chat_name, chat_settings in self.chat_modules.items():
                if isinstance(chat_settings['class'], ConfigModule):
                    continue

                class_item = chat_settings['class']

                for channel_name, channel in class_item.channels.items():
                    if channel not in self.chats.get(chat_name, {}):
                        wx.CallAfter(self.add_channel, chat_name, channel_name)

                    self.set_channel_status(chat_name, channel_name, channel.status)
                    self.set_viewers(chat_name, channel_name, channel.viewers)

                difference = [item for item in self.chats.get(chat_name, {})
                              if item.lower() not in [channel.lower() for channel in class_item.channels]]
                if difference:
                    for channel in difference:
                        wx.CallAfter(self.remove_channel, chat_name, channel)

            wx.CallAfter(self.Layout)
            wx.CallAfter(self.Refresh)
            time.sleep(1)

    def _create_sizer(self):
        border_sizer = wx.BoxSizer(wx.HORIZONTAL)
        border_sizer.AddSpacer(2)
        item_sizer = wx.FlexGridSizer(0, 0, 10, 10)
        border_sizer.Add(item_sizer, 0, wx.EXPAND)
        border_sizer.AddSpacer(2)
        self.SetSizer(border_sizer)
        return item_sizer

    def _create_item(self, channel, icon, multiple):
        item_sizer = wx.BoxSizer(wx.VERTICAL)
        module_sizer = wx.FlexGridSizer(0, 0, 5, 3)

        bitmap = wx.StaticBitmap(self, wx.ID_ANY,
                                 wx.Bitmap(icon),
                                 size=wx.Size(16, 16))
        module_sizer.Add(bitmap, 0, wx.EXPAND)

        channel_name = '{}: '.format(channel) if multiple else ''
        channel_text = wx.StaticText(self, id=wx.ID_ANY, label=channel_name)
        module_sizer.Add(channel_text, 0, wx.EXPAND)

        label = wx.StaticText(self, id=wx.ID_ANY, label='N/A')
        module_sizer.Add(label, 1, wx.EXPAND)
        module_sizer.AddSpacer(2)

        item_sizer.Add(module_sizer, 0, wx.EXPAND)

        status_sizer = wx.BoxSizer(wx.HORIZONTAL)
        status_item = wx.Panel(self, size=wx.Size(-1, 5))
        status_item.SetBackgroundColour('gray')

        status_sizer.Add(status_item, 1, wx.EXPAND)

        item_sizer.AddSpacer(3)
        item_sizer.Add(status_sizer, 1, wx.EXPAND)
        item_sizer.AddSpacer(2)

        self.border_sizer.Add(item_sizer, 0, wx.EXPAND)
        return {'item': item_sizer, 'label': label,
                'status': status_item, 'name': channel_text, 'channel': channel}

    def add_channel(self, module_name, channel):
        if module_name not in self.chats:
            self.chats[module_name] = {}
        if channel.lower() not in self.chats[module_name]:
            config = self.chat_modules.get(module_name)['class'].conf_params()['config']
            icon = config.icon
            multiple = config['config']['show_channel_names']
            self.chats[module_name][channel.lower()] = self._create_item(channel, icon, multiple)
        if self.chats and self.parent.main_config['config']['gui']['show_counters']:
            self.Show(True)
            self.parent.Layout()

        if self.Shown:
            self.Layout()
            self.Refresh()

    def remove_channel(self, module_name, channel):
        channel = channel.lower()
        if module_name not in self.chats:
            return
        if channel not in self.chats[module_name]:
            return

        chat = self.chats[module_name][channel]
        self.border_sizer.Detach(chat['item'])
        chat['item'].Clear(True)
        del self.chats[module_name][channel]
        if not self.chat_count:
            self.Show(False)
            self.parent.Layout()
        if self.Shown:
            self.Layout()
            self.Refresh()

    def _set_channel_color(self, element, color):
        if element.GetBackgroundColour() != color:
            log.debug('Changing element background color')
            element.SetBackgroundColour(color)

    def _update_label(self, element, label):
        if element.GetLabel() != label:
            log.debug('Changing element label')
            element.SetLabel(label)

    def set_channel_status(self, module_name, channel, status):
        if module_name in self.chats:
            if channel.lower() in self.chats[module_name]:
                f_color = CHANNEL_STATUS_COLORS[status]
                wx.CallAfter(self._set_channel_color,
                             self.chats[module_name][channel.lower()]['status'],
                             f_color)

    def refresh_labels(self):
        for chat_name, chat in self.chats.items():
            show_names = self.chat_modules[chat_name]['config']['config']['show_channel_names']
            for name, settings in self.chats[chat_name].items():
                channel = '{}: '.format(settings['channel']) if show_names else ''
                wx.CallAfter(self._update_label,
                             self.chats[chat_name][name]['name'], channel)

    def set_viewers(self, module_name, channel, viewers):
        if not viewers:
            return
        if isinstance(viewers, int):
            viewers = str(viewers)
        if len(viewers) >= 5:
            viewers = '{0}k'.format(viewers[:-3])
        if module_name in self.chats:
            if channel.lower() in self.chats[module_name]:
                wx.CallAfter(self._update_label,
                             self.chats[module_name][channel.lower()]['label'],
                             str(viewers))

    def is_shown(self, value):
        self.Show(value)
        self.parent.Layout()


class UpdateDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='Update', size=wx.Size(250, 90))
        self.progress = 0

        self.gauge = wx.Gauge(self, range=100)
        self.update_text = wx.StaticText(self, label='Downloading new version...')
        self.button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.button_sizer.AffirmativeButton.Disable()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.update_text, 0, wx.EXPAND)
        sizer.Add(self.gauge, 0, wx.EXPAND)
        sizer.Add(self.button_sizer, 1, wx.EXPAND | wx.BOTTOM)
        self.SetSizer(sizer)

        self.Layout()

    def update_progress(self, amount):
        old = self.gauge.GetValue()
        self.gauge.SetValue(old + amount)
