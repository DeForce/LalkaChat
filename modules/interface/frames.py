import logging
import threading

import time
import wx

from modules.helper.module import ConfigModule, CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING
from modules.helper.system import WINDOWS, NO_VIEWERS

try:
    from cefpython3.wx import chromectrl as browser
    HAS_CHROME = True
except ImportError:
    from wx import html2 as browser, StdDialogButtonSizer
    HAS_CHROME = False

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


class ChannelStatus(object):
    def __init__(self, name, status, sizer, viewers, channel_text, status_panel):
        self.name = name
        self.status = status
        self.viewers = NO_VIEWERS

        self.sizer = sizer
        self.viewers_wx = viewers
        self.channel_text = channel_text
        self.status_panel = status_panel


class StatusFrame(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=wx.Size(-1, 24))
        self.parent = parent
        self.chats = {}
        self.border_sizer = self._create_sizer()
        self.chat_modules = None
        self.changes = {}

        self._update_thread = None
        self._running = True

        if WINDOWS:
            self.SetBackgroundColour('cream')

    def load(self):
        self.chat_modules = self.parent.sorted_categories['chat']
        for chat_name, chat_settings in self.chat_modules.items():
            if chat_name == 'chat':
                continue

            channels = chat_settings.channels
            for channel_name, channel_class in channels.items():
                wx.CallAfter(self.add_channel, chat_name, channel_class)

        self._update_thread = threading.Thread(target=self._frame_update, name='StatusFrameUpdateThread')
        self._update_thread.daemon = True
        self._update_thread.start()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.Fit()
        self.Layout()
        self.Show(False)

    def on_close(self, event):
        self._running = False
        event.Skip()

    @property
    def chat_count(self):
        return sum([len(item.values()) for item in self.chats.values()])

    def _frame_update(self):
        while True:
            if not self._running:
                break
            changes = []
            for chat_name, chat_class in self.chat_modules.items():
                if isinstance(chat_class, ConfigModule):
                    continue

                channels = self.chats.get(chat_name, {})

                for channel_name, channel_settings in chat_class.channels.items():
                    if channel_name.lower() not in channels:
                        wx.CallAfter(self.add_channel, chat_name, channel_settings)
                        continue

                    changes.append(self.set_channel_status(chat_name, channel_name, channel_settings.status))
                    changes.append(self.set_viewers(chat_name, channel_name, channel_settings.viewers))

                difference = [item for item in self.chats.get(chat_name, {})
                              if item.lower() not in [channel_settings.lower()
                                                      for channel_settings in chat_class.channels]]
                if difference:
                    for channel_settings in difference:
                        wx.CallAfter(self.remove_channel, chat_name, channel_settings)
            if any(changes):
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
        sizer = wx.BoxSizer(wx.VERTICAL)
        module_sizer = wx.FlexGridSizer(0, 0, 5, 3)

        bitmap = wx.StaticBitmap(self, wx.ID_ANY,
                                 wx.Bitmap(icon),
                                 size=wx.Size(16, 16))
        module_sizer.Add(bitmap, 0, wx.EXPAND)

        channel_name = f'{channel}: ' if multiple else ''
        channel_text = wx.StaticText(self, id=wx.ID_ANY, label=channel_name)
        module_sizer.Add(channel_text, 0, wx.EXPAND)

        viewers = wx.StaticText(self, id=wx.ID_ANY, label='N/A')
        module_sizer.Add(viewers, 1, wx.EXPAND)
        module_sizer.AddSpacer(2)

        sizer.Add(module_sizer, 0, wx.EXPAND)

        status_sizer = wx.BoxSizer(wx.HORIZONTAL)
        status_item = wx.Panel(self, size=wx.Size(-1, 5))
        status_item.SetBackgroundColour('gray')

        status_sizer.Add(status_item, 1, wx.EXPAND)

        sizer.AddSpacer(3)
        sizer.Add(status_sizer, 1, wx.EXPAND)
        sizer.AddSpacer(2)

        self.border_sizer.Add(sizer, 0, wx.EXPAND)
        return ChannelStatus(channel, status=CHANNEL_OFFLINE, sizer=sizer,
                             viewers=viewers, channel_text=channel_text, status_panel=status_item)

    def add_channel(self, chat_name, channel_class):
        if chat_name not in self.chats:
            self.chats[chat_name] = {}

        channel = channel_class.channel.lower()
        if channel not in self.chats[chat_name]:
            config = channel_class.chat_module.config
            icon = config.icon
            multiple = config['config']['show_channel_names']
            self.chats[chat_name][channel.lower()] = self._create_item(channel_class.channel, icon, multiple)

        if self.chats and self.parent.main_module.get_config('gui', 'show_counters'):
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
        self.border_sizer.Detach(chat.sizer)
        chat.sizer.Clear(True)
        del self.chats[module_name][channel]

        if not self.chat_count:
            self.Show(False)
            self.parent.Layout()

        if self.Shown:
            self.Layout()
            self.Refresh()

    @staticmethod
    def _set_channel_color(element, status):
        log.debug('Changing element background color')
        color = CHANNEL_STATUS_COLORS[status]
        element.status = status
        panel = element.status_panel
        panel.SetBackgroundColour(color)

    @staticmethod
    def _update_channel_name(element, text):
        label = element.channel_text
        log.debug('Changing element label')
        label.SetLabel(text)

    @staticmethod
    def _update_viewers(element, text):
        element.viewers = text
        label = element.viewers_wx
        log.debug('Changing element label')
        label.SetLabel(text)

    def set_channel_status(self, module_name, channel, status):
        if module_name not in self.chats:
            return

        if channel.lower() not in self.chats[module_name]:
            return

        status_object = self.chats[module_name][channel.lower()]
        old_status = status_object.status
        if status == old_status:
            return

        wx.CallAfter(self._set_channel_color, status_object, status)
        return True

    def refresh_labels(self):
        for chat_name, chat in self.chats.items():
            show_names = self.chat_modules[chat_name].get_config('config', 'show_channel_names')
            for name, ch_status in self.chats[chat_name].items():
                channel = f'{ch_status.name}: ' if show_names else ''
                wx.CallAfter(self._update_channel_name,
                             self.chats[chat_name][name], channel)
        wx.CallAfter(self.Layout)
        wx.CallAfter(self.Refresh)

    def set_viewers(self, module_name, channel, viewers):
        if not viewers:
            return
        if module_name not in self.chats:
            return
        if channel.lower() not in self.chats[module_name]:
            return

        if isinstance(viewers, int):
            viewers = str(viewers)
        if len(viewers) >= 5:
            viewers = f'{viewers[:-3]}k'

        status = self.chats[module_name][channel.lower()]
        if status.viewers == viewers:
            return

        wx.CallAfter(self._update_viewers, status, viewers)
        return True

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
        ok_button_id = self.GetAffirmativeId()
        ok_button = self.FindWindowById(ok_button_id, self)
        ok_button.Disable()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.update_text, 0, wx.EXPAND)
        sizer.Add(self.gauge, 0, wx.EXPAND)
        sizer.Add(self.button_sizer, 1, wx.EXPAND | wx.BOTTOM)
        self.SetSizer(sizer)

        self.Layout()

    def update_progress(self, amount):
        old = self.gauge.GetValue()
        self.gauge.SetValue(old + amount)
