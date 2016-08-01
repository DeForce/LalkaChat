import threading
import wx
import thread
import os
import signal
import ConfigParser
from wx import html2

translations = {}
ids = {}
main_class = None


def get_id_from_name(name):
    for item in ids:
        if ids[item] == name:
            return item


def fix_sizes(size1, size2):
    if size1[0] > size2[0]:
        label_x_size = size1[0]
    else:
        label_x_size = size2[0]

    if size1[1] > size2:
        label_y_size = size1[1]
    else:
        label_y_size = size2[1]
    return label_x_size, label_y_size


def load_translations(settings, language):
    conf_file = 'translations.cfg'
    config = ConfigParser.ConfigParser(allow_no_value=True)
    config.read(os.path.join(settings['conf'], conf_file))

    try:
        config.items(language)
    except ConfigParser.NoSectionError:
        language = 'English'

    for param, value in config.items(language):
        print param, value
        translations[param] = value


def translate_language(item):
    print "Translating: ", item
    return translations.get(item, item)


class MainMenuToolBar(wx.ToolBar):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TB_NOICONS | wx.TB_TEXT
        wx.ToolBar.__init__(self, *args, **kwds)
        self.SetToolBitmapSize((0, 0))

        l_id = wx.Window_NewControlId()
        ids[l_id] = 'menu.settings'
        label_text = translate_language(ids[l_id])
        self.AddLabelTool(l_id, label_text, wx.NullBitmap, wx.NullBitmap,
                          wx.ITEM_NORMAL, label_text, label_text)
        main_class.Bind(wx.EVT_TOOL, main_class.on_settings, id=l_id)

        l_id = wx.Window_NewControlId()
        ids[l_id] = 'menu.reload'
        label_text = translate_language(ids[l_id])
        self.AddLabelTool(l_id, label_text, wx.NullBitmap, wx.NullBitmap,
                          wx.ITEM_NORMAL, label_text, label_text)
        main_class.Bind(wx.EVT_TOOL, main_class.on_about, id=l_id)

        self.Realize()


class SettingsWindow(wx.Frame):
    def __init__(self, parent, configs, on_top=False, title=translate_language("menu.settings")):
        wx.Frame.__init__(self, parent, title=title, size=(500, 400))
        self.SetBackgroundColour('cream')
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.configs = configs
        self.border_left = 20
        self.border_right = 20

        self.labelMinSize = wx.Size(100, -1)
        self.label_x_offset = 20
        self.label_y_offset = 0

        self.SettingGrid = wx.FlexGridSizer(0, 2, 0, 15)
        self.grid = wx.BoxSizer

        if on_top:
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)

        self.load_main_config()

        self.SetSizer(self.SettingGrid)
        self.SettingGrid.Fit(self)
        # self.Layout()
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

    def check_box_placed(self, event):
        print 'Checkbox ', event.IsChecked()
        print ids[event.GetId()]
        # print event.GetEventObject()

    def load_main_config(self):
        config = ConfigParser.ConfigParser(allow_no_value=True)
        config.read(self.configs['main'])

        # print config._sections
        for item in config._sections:
            # Spacer for configuration section
            self.SettingGrid.SetRows(self.SettingGrid.GetRows() + 1)
            self.SettingGrid.Add((-1, 10))
            self.SettingGrid.Add((-1, -1))
            self.SettingGrid.SetRows(self.SettingGrid.GetRows() + 1)

            # Header of configuration section
            header_text = wx.StaticText(self, label=translate_language(item), style=wx.ALIGN_CENTRE_HORIZONTAL)
            header_elements = [(header_text, 0, wx.EXPAND | wx.LEFT, self.border_left),
                               wx.StaticText(self)]
            header_elements[1].Hide()
            self.SettingGrid.AddMany(header_elements)

            # Spacer for configuration section
            self.SettingGrid.SetRows(self.SettingGrid.GetRows() + 1)
            self.SettingGrid.Add((-1, 7))
            self.SettingGrid.Add((-1, -1))

            # Setting section items
            for param, value in config.items(item):
                self.SettingGrid.SetRows(self.SettingGrid.GetRows() + 1)

                # Creating item settings
                module_name = '{0}.{1}'.format(item, param)
                module_id = wx.Window_NewControlId()
                ids[module_id] = module_name

                # Creating item labels
                text_text = '{0}:'.format(translate_language(module_name))
                text = wx.StaticText(self, wx.ID_ANY, text_text, style=wx.ALIGN_RIGHT)
                text.SetMinSize(fix_sizes(text.GetSize(), self.labelMinSize))

                # Creating item objects
                if value is not None:
                    # If item has true or false - it's a checkbox
                    if value == 'true' or value == 'false':
                        box = wx.CheckBox(self, id=module_id)
                        main_class.Bind(wx.EVT_CHECKBOX, self.check_box_placed, id=module_id)
                        if value == 'true':
                            box.SetValue(True)
                        else:
                            box.SetValue(False)
                    # If not - it's text control
                    else:
                        box = wx.TextCtrl(self, id=module_id)
                        box.Create(self)
                # If item doesn't have any values it's a button
                else:
                    box = wx.Button(self, id=module_id)

                self.SettingGrid.Add(text, 0, wx.EXPAND | wx.ALIGN_RIGHT | wx.LEFT, self.border_left)
                self.SettingGrid.Add(box, 1, wx.EXPAND | wx.RIGHT, self.border_right)
            self.SettingGrid.SetRows(self.SettingGrid.GetRows() + 1)
            self.SettingGrid.Add(wx.Size(75, 20))


class ChatGui(wx.Frame):
    def __init__(self, parent, title, url, main_config, gui_settings={}):
        wx.Frame.__init__(self, parent, title=title, size=(450, 500))

        global main_class
        main_class = self
        self.main_config = main_config
        self.settingWindow = None

        styles = wx.DEFAULT_FRAME_STYLE

        if gui_settings.get('on_top', False):
            print "Application is on top"
            styles = styles | wx.STAY_ON_TOP

        # print styles
        self.SetWindowStyle(styles)

        vbox = wx.BoxSizer(wx.VERTICAL)

        toolbar = MainMenuToolBar(self)
        self.main_window = html2.WebView.New(parent=self, url=url, name='LalkaWebViewGui')
        # self.main_window = html2.WebView.New(parent=self, url=url, name='LalkaWebViewGui', size=(300, 600))

        vbox.Add(toolbar, 0, wx.EXPAND)
        vbox.Add(self.main_window, 1, wx.EXPAND)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_right_down, self.main_window)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        # self.Bind(wx.EVT_TOOL, self.on_settings, id=get_id_from_name('settings'))
        # self.Bind(wx.EVT_TOOL, self.on_about, id=ids['about'])

        # vbox.Fit(self)
        self.SetSizer(vbox)
        self.Show(True)

    def on_about(self, event):
        self.main_window.Reload(wx.html2.WEBVIEW_RELOAD_NO_CACHE)

    def on_exit(self, event):
        print "Exiting... "
        self.Destroy()

    def on_right_down(self, event):
        print "RClick"

    def on_settings(self, event):
        # print event
        # print wx.STAY_ON_TOP, self.GetWindowStyle()
        if not self.settingWindow:
            if wx.STAY_ON_TOP & self.GetWindowStyle() == wx.STAY_ON_TOP:
                self.settingWindow = SettingsWindow(self, self.main_config, on_top=True,
                                                    title=translate_language("menu.settings"))
            else:
                self.settingWindow = SettingsWindow(self, self.main_config, title=translate_language("menu.settings"))
        else:
            self.settingWindow.SetFocus()
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
        load_translations(self.main_config, self.gui_settings.get('language', 'default'))
        app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
        frame = ChatGui(None, "LalkaChat", self.url, self.main_config, self.gui_settings)  # A Frame is a top-level window.
        app.MainLoop()
