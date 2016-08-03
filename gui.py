
import threading
import wx
import os
import ConfigParser
from wx import html2
# import signal
# import thread
# ToDO:
# Support customization of borders/spacings

translations = {}
ids = {}


def get_id_from_name(name):
    for item in ids:
        if ids[item] == name:
            return item


def get_list_of_ids_from_module_name(name):
    id_array = []
    for item in ids:
        if ids[item].split('.')[0] == name:
            id_array.append(item)
    return id_array


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
    # print config

    try:
        config.items(language)
    except ConfigParser.NoSectionError:
        print "Warning, have not found language ", language
        language = 'English'

    for param, value in config.items(language):
        # print param, value
        translations[param] = value


def translate_language(item):
    # print "Translating: ", item
    return translations.get(item, item).decode('utf-8')


class MainMenuToolBar(wx.ToolBar):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TB_NOICONS | wx.TB_TEXT
        self.main_class = kwds['main_class']
        kwds.pop('main_class')
        wx.ToolBar.__init__(self, *args, **kwds)
        self.SetToolBitmapSize((0, 0))

        l_id = wx.Window_NewControlId()
        ids[l_id] = 'menu.settings'
        label_text = translate_language(ids[l_id])
        self.AddLabelTool(l_id, label_text, wx.NullBitmap, wx.NullBitmap,
                          wx.ITEM_NORMAL, label_text, label_text)
        self.main_class.Bind(wx.EVT_TOOL, self.main_class.on_settings, id=l_id)

        l_id = wx.Window_NewControlId()
        ids[l_id] = 'menu.reload'
        label_text = translate_language(ids[l_id])
        self.AddLabelTool(l_id, label_text, wx.NullBitmap, wx.NullBitmap,
                          wx.ITEM_NORMAL, label_text, label_text)
        self.main_class.Bind(wx.EVT_TOOL, self.main_class.on_about, id=l_id)

        self.Realize()


class SettingsWindow(wx.Frame):
    border_left = 20
    border_right = 20
    border_top = 15
    border_all = 5

    labelMinSize = wx.Size(100, -1)
    label_x_offset = 20
    label_y_offset = 0

    flex_horizontal_gap = 7
    flex_vertical_gap = 7

    def __init__(self, parent, configs, on_top=False, title=translate_language("menu.settings"), **kwds):
        wx.Frame.__init__(self, parent, title=title, size=(500, 400))
        self.main_class = kwds['main_class']

        self.SetBackgroundColour('cream')
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.configs = configs

        self.main_grid = wx.BoxSizer(wx.VERTICAL)

        if on_top:
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)

        self.load_config(config=configs)

        self.SetSizer(self.main_grid)
        self.Layout()
        self.main_grid.Fit(self)
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

    def check_box_clicked(self, event):
        print 'Checkbox ', event.IsChecked()
        print ids[event.GetId()]
        # print event.GetEventObject()

    def button_clicked(self, event):
        print 'Checkbox ', event.IsChecked()
        print ids[event.GetId()]
        module_groups = ids[event.GetId()].split('.')
        if module_groups[1] == 'apply_button':
            print "Got Apply Event"
            self.write_config(module_groups)

        elif ids[event.GetId()].split('.')[1] == 'cancel_button':
            print "Got Cancel Event"
            event.Skip()

    def write_config(self, module_groups):
        module_hit = None
        for module in self.main_class.modules_configs:
            # print module
            if module == module_groups[0]:
                module_hit = module
        if module_hit:
            id_list = get_list_of_ids_from_module_name(module_hit)
            parser = self.main_class.modules_configs[module_hit]['parser']

            for id_item in id_list:
                if len(ids[id_item].split('.')) > 2:
                    section, param = ids[id_item].split('.')[1:]
                    print section, param
                    window = self.FindWindowById(id_item)
                    # get type of item and do shit
                    if isinstance(window, wx.CheckBox):
                        print "Got Checkbox, YAY"
                        parser.set(section, param, str(window.IsChecked()).lower())
                    elif isinstance(window, wx.TextCtrl):
                        # print "Got TextCtrl, YAY", str(window.GetValue())
                        parser.set(section, param, window.GetValue().encode('utf-8'))

            with open(self.main_class.modules_configs[module_hit]['file'], 'w') as config_file:
                parser.write(config_file)

    def load_config(self, config={}, **kwargs):
        conf_params = config

        config = ConfigParser.ConfigParser(allow_no_value=True)
        config.read(conf_params['file_loc'])
        config_sizer = wx.BoxSizer(wx.VERTICAL)

        module_prefix = conf_params['filename']
        for item in config._sections:
            # Create header for section
            header_text = translate_language('.'.join([module_prefix, item]))
            section_header = wx.StaticBox(self, -1, header_text)
            section_sizer = wx.StaticBoxSizer(section_header, wx.VERTICAL)

            # Setting section items
            for param, value in config.items(item):
                item_sizer = wx.BoxSizer(wx.HORIZONTAL)
                # print param, value
                rotate = False

                # Creating item settings
                module_name = '.'.join([module_prefix, item, param])
                module_id = wx.Window_NewControlId()
                ids[module_id] = module_name

                # Creating item labels
                text_text = translate_language(module_name)
                text = wx.StaticText(self, wx.ID_ANY, text_text,
                                     style=wx.ALIGN_RIGHT)
                # text.SetBackgroundColour('red')
                # text.SetMinSize(fix_sizes(text.GetSize(), self.labelMinSize))

                # Creating item objects
                if value is not None:
                    # If item has true or false - it's a checkbox
                    if value == 'true' or value == 'false':
                        rotate = True
                        box = wx.CheckBox(self, id=module_id)
                        self.main_class.Bind(wx.EVT_CHECKBOX, self.check_box_clicked, id=module_id)
                        if value == 'true':
                            box.SetValue(True)
                        else:
                            box.SetValue(False)
                    # If not - it's text control
                    else:
                        box = wx.TextCtrl(self, id=module_id, value=value.decode('utf-8'))
                        # box.AppendText(value)

                # If item doesn't have any values it's a button
                else:
                    box = wx.Button(self, id=module_id, label=translate_language('.'.join([module_name, 'button'])))

                if rotate:
                    item_sizer.AddSpacer(self.flex_vertical_gap*2)
                    item_sizer.Add(box, 0, wx.ALIGN_LEFT)
                    item_sizer.AddSpacer(self.flex_vertical_gap)
                    item_sizer.Add(text, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
                else:
                    item_sizer.AddSpacer(self.flex_vertical_gap*2)
                    item_sizer.Add(text, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
                    item_sizer.AddSpacer(self.flex_vertical_gap)
                    item_sizer.Add(box, 0, wx.ALIGN_LEFT)
                item_sizer.AddSpacer(self.flex_horizontal_gap)
                section_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, self.border_all)
            config_sizer.Add(section_sizer, 0, wx.EXPAND)

        # Add buttons for saving/cancelling configuration updates
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)

        button_id = wx.Window_NewControlId()
        button_name = '.'.join([module_prefix, 'apply_button'])
        ids[button_id] = button_name
        apply_button = wx.Button(self, id=button_id,
                                 label=translate_language(button_name))
        self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=button_id)
        buttons_sizer.Add(apply_button, 0, wx.ALIGN_RIGHT)

        # buttons_sizer.AddSpacer(self.flex_horizontal_gap*2)

        button_id = wx.Window_NewControlId()
        button_name = '.'.join([module_prefix, 'cancel_button'])
        ids[button_id] = button_name
        apply_button = wx.Button(self, id=button_id,
                                 label=translate_language(button_name))
        self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=button_id)
        buttons_sizer.Add(apply_button, 0, wx.ALIGN_RIGHT)

        config_sizer.Add(buttons_sizer, 0, wx.ALIGN_RIGHT | wx.TOP, self.border_all)

        self.main_grid.Add(config_sizer, 0, wx.ALL, self.border_all)


class ChatGui(wx.Frame):
    def __init__(self, parent, title, url, **kwds):
        wx.Frame.__init__(self, parent, title=title, size=(450, 500))

        self.main_config = kwds['main_config']
        self.gui_settings = kwds['gui_settings']
        self.modules_configs = kwds['modules_configs']
        self.settingWindow = None

        styles = wx.DEFAULT_FRAME_STYLE

        if self.gui_settings.get('on_top', False):
            print "Application is on top"
            styles = styles | wx.STAY_ON_TOP

        # print styles
        self.SetWindowStyle(styles)

        vbox = wx.BoxSizer(wx.VERTICAL)

        toolbar = MainMenuToolBar(self, main_class=self)
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
                                                    title=translate_language("menu.settings"), main_class=self)
            else:
                self.settingWindow = SettingsWindow(self, self.main_config, title=translate_language("menu.settings"),
                                                    main_class=self)
        else:
            self.settingWindow.SetFocus()
        event.Skip()


class GuiThread(threading.Thread):
    def __init__(self, **kwds):
        threading.Thread.__init__(self)
        self.daemon = True
        self.gui_settings = kwds.get('gui_settings', {})
        self.modules_configs = kwds.get('modules_configs', {})
        self.main_config = kwds.get('main_config', {})

    title = 'LalkaChat'
    url = 'http://localhost:8080'

    def run(self):
        load_translations(self.main_config, self.gui_settings.get('language', 'default'))
        app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
        frame = ChatGui(None, "LalkaChat", self.url, main_config=self.main_config, gui_settings=self.gui_settings,
                        modules_configs=self.modules_configs)  # A Frame is a top-level window.
        app.MainLoop()
