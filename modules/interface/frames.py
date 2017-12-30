import logging

import wx

from modules.helper.system import WINDOWS

try:
    from cefpython3.wx import chromectrl as browser
    HAS_CHROME = True
except ImportError:
    from wx import html2 as browser

log = logging.getLogger('chat_gui')


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

        if WINDOWS:
            self.SetBackgroundColour('cream')

    def load(self):
        self.chat_modules = self.parent.sorted_categories['chat']
        for chat_name, chat_settings in self.chat_modules.items():
            if chat_name == 'chat':
                continue
            if chat_settings['class'].get_queue('status_frame'):
                for item in chat_settings['class'].get_queue('status_frame'):
                    if item['action'] == 'add':
                        self.add_channel(chat_name, item['channel'])
                        del item

                for item in chat_settings['class'].get_queue('status_frame'):
                    if item['action'] == 'set_online':
                        self.set_channel_online(chat_name, item['channel'])
                    elif item['action'] == 'set_pending':
                        self.set_channel_pending(chat_name, item['channel'])
                    elif item['action'] == 'set_offline':
                        self.set_channel_offline(chat_name, item['channel'])
                    del item

        self.Fit()
        self.Layout()
        self.Show(False)

    @property
    def chat_count(self):
        return sum([len(item.values()) for item in self.chats.values()])

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

    def set_channel_online(self, module_name, channel):
        if module_name in self.chats:
            if channel.lower() in self.chats[module_name]:
                f_color = wx.Colour(0, 128, 0)
                wx.CallAfter(self._set_channel_color,
                             self.chats[module_name][channel.lower()]['status'],
                             f_color)
        self.Layout()
        self.Refresh()

    def set_channel_pending(self, module_name, channel):
        if module_name in self.chats:
            if channel.lower() in self.chats[module_name]:
                f_color = wx.Colour(200, 200, 0)
                wx.CallAfter(self._set_channel_color,
                             self.chats[module_name][channel.lower()]['status'],
                             f_color)
        self.Layout()
        self.Refresh()

    def set_channel_offline(self, module_name, channel):
        if module_name in self.chats:
            if channel in self.chats[module_name]:
                f_color = wx.Colour(255, 0, 0)
                wx.CallAfter(self._set_channel_color,
                             self.chats[module_name][channel.lower()]['status'],
                             f_color)
        self.Refresh()

    def refresh_labels(self, module_name):
        if module_name not in self.chats:
            return
        show_names = self.chat_modules[module_name]['config']['config']['show_channel_names']
        for name, settings in self.chats[module_name].items():
            channel = '{}: '.format(settings['channel']) if show_names else ''
            wx.CallAfter(self._update_label,
                         self.chats[module_name][name]['name'], channel)
        self.Layout()
        self.Refresh()

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
