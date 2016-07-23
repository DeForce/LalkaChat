import threading
import wx
import thread
import os
import signal
import ConfigParser
from wx import html2


class MainMenuToolBar(wx.ToolBar):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TB_NOICONS | wx.TB_TEXT
        wx.ToolBar.__init__(self, *args, **kwds)
        self.SetToolBitmapSize((0, 0))

        self.AddLabelTool(wx.ID_TOP, "Settings", wx.NullBitmap, wx.NullBitmap, wx.ITEM_NORMAL, "Settings", "Settings")

        self.Realize()


class SettingsWindow(wx.Frame):
    def __init__(self, parent, configs,on_top=False, title='Settings'):
        wx.Frame.__init__(self, parent, title=title, size=(500, 400))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.configs = configs

        self.grid = wx.GridSizer(0, 2)

        if on_top:
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)

        self.load_main_config()

        self.SetSizer(self.grid)
        self.grid.Fit(self)
        self.Layout()
        self.Show(True)

    def on_exit(self, event):
        self.Destroy()

    def on_close(self, event):
        dialog = wx.MessageDialog(self, message="Are you sure you want to quit?",
                                  caption="Caption",
                                  style=wx.YES_NO,
                                  pos=wx.DefaultPosition)
        response = dialog.ShowModal()

        if response == wx.ID_YES:
            self.on_exit(event)
        else:
            event.StopPropagation()

    def load_main_config(self):
        config = ConfigParser.ConfigParser(allow_no_value=True)
        config.read(self.configs['main'])

        # print config._sections
        for item in config._sections:
            self.grid.SetRows(self.grid.GetRows() + 1)
            self.grid.AddMany([wx.StaticText(self, label=item), wx.StaticText(self)])

            for param, value in config.items(item):
                self.grid.SetRows(self.grid.GetRows() + 1)
                text = wx.StaticText(self, wx.ID_ANY, param,
                                     style=wx.ALIGN_RIGHT)
                print text.GetMaxWidth(), text.GetMinWidth(), text.GetSize(), text.GetEffectiveMinSize()
                print text.GetMaxSize()
                # print help(text)
                # text = wx.StaticText(self, label=param)
                text.SetBackgroundColour('black')
                text.SetForegroundColour('white')
                # print type(text)
                # self.grid.Add(text)

                if value is not None:
                    if value == 'true' or value == 'false':
                        box = wx.CheckBox(self)

                # print self.grid.GetRows(), self.grid.GetCols()
                # print param, value
                self.grid.Add(text, wx.EXPAND)
                self.grid.Add(box, wx.EXPAND)
            self.grid.SetRows(self.grid.GetRows() + 1)
            self.grid.Add(wx.Size(75, 20))


class ChatGui(wx.Frame):
    def __init__(self, parent, title, url, main_config, gui_settings={}):
        wx.Frame.__init__(self, parent, title=title, size=(300, 500))

        self.main_config = main_config

        styles = wx.DEFAULT_FRAME_STYLE

        if gui_settings.get('on_top', False):
            print "Application is on top"
            styles = styles | wx.STAY_ON_TOP

        print styles
        self.SetWindowStyle(styles)

        vbox = wx.BoxSizer(wx.VERTICAL)

        toolbar = MainMenuToolBar(self)
        self.main_window = html2.WebView.New(parent=self, url=url, name='LalkaWebViewGui', size=(300, 500))

        vbox.Add(toolbar, 0, wx.EXPAND)
        vbox.Add(self.main_window, 0, wx.EXPAND)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_right_down, self.main_window)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_TOOL, self.on_settings, id=wx.ID_TOP)

        self.SetSizer(vbox)
        self.Show(True)

    def on_about(self, event):
        print "HelloWorld "

    def on_exit(self, event):
        print "Exiting... "
        self.Destroy()

    def on_right_down(self, event):
        print "RClick"

    def on_settings(self, event):
        print wx.STAY_ON_TOP, self.GetWindowStyle()
        if wx.STAY_ON_TOP & self.GetWindowStyle() == wx.STAY_ON_TOP:
            settingsWindow = SettingsWindow(self, self.main_config, on_top=True)
        else:
            settingsWindow = SettingsWindow(self, self.main_config)
        event.Skip()


class GuiThread(threading.Thread):
    def __init__(self, gui_settings, main_config):
        threading.Thread.__init__(self)
        self.daemon = True
        self.gui_settings = gui_settings
        self.main_config = main_config

    title = 'LalkaChat'
    url = 'http://localhost:8080'

    def run(self):
        app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
        frame = ChatGui(None, "LalkaChat", self.url, self.main_config, self.gui_settings)  # A Frame is a top-level window.
        app.MainLoop()
