from pprint import pprint
import threading
import wx
import os
import ConfigParser
import re
from modules.helpers.parser import FlagConfigParser
from wx import html2
# import signal
# import thread
# ToDO: Support customization of borders/spacings

translations = {}
ids = {}


def get_id_from_name(name):
    for item in ids:
        if ids[item] == name:
            return item


def get_list_of_ids_from_module_name(name, id_group=1):
    split_key = '.'

    id_array = []
    for item in ids:
        item_name = split_key.join(ids[item].split(split_key)[:id_group])
        if item_name == name:
            id_array.append(item)
    return id_array


def fix_sizes(size1, size2):
    if size1[0] > size2[0]:
        label_x_size = size1[0]
    else:
        label_x_size = size2[0]

    if size1[1] > size2[1]:
        label_y_size = size1[1]
    else:
        label_y_size = size2[1]
    return [label_x_size, label_y_size]


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


def find_translation(item, length=0, wildcard=1):
    translation = translations.get(item, item)
    if item == translation:
        if wildcard < length:
            translation = find_translation('.'.join(['*'] + item.split('.')[-wildcard:]),
                                           length=length, wildcard=wildcard+1)
        else:
            return translation
    return translation


def translate_language(item):
    item_no_flags = item.split('/')[0]
    old_item = item_no_flags

    translation = find_translation(item_no_flags, length=len(item_no_flags.split('.')))

    if re.match('\*', translation):
        return old_item
    return translation


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

    max_size = (500, 400)

    labelMinSize = wx.Size(100, -1)
    label_x_offset = 20
    label_y_offset = 0

    flex_horizontal_gap = 7
    flex_vertical_gap = 7

    show_hidden = False
    module_key = '.'
    keyword = '/'
    flag_keyword = ','

    def __init__(self, parent, configs, on_top=False, title=translate_language("menu.settings"), **kwds):
        wx.Frame.__init__(self, parent, title=title, size=self.max_size)
        self.main_class = kwds['main_class']

        self.SetBackgroundColour('cream')
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.configs = configs

        # pprint(self.main_class.modules_configs)

        self.main_grid = wx.BoxSizer(wx.VERTICAL)

        if on_top:
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)

        self.main_grid.Add(self.create_and_load_config(self), 1, wx.EXPAND)

        self.SetSizer(self.main_grid)
        self.Layout()
        # self.main_grid.Fit(self)
        # print config_size_max
        # self.SetSize(config_size_max)
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

    def add_list_item(self, module_group):
        module = module_group[:-1]
        module_list = get_list_of_ids_from_module_name(self.module_key.join(module), id_group=len(module))

        item_input = None
        box = None

        for item in module_list:
            item_split = ids[item].split(self.module_key)
            if 'list_input' in item_split:
                item_input = wx.FindWindowById(item)
            elif 'list_box' in item_split:
                box = wx.FindWindowById(item)

        if item_input and box:
            item_text = item_input.GetValue()
            items_in_box = box.GetCount()
            if items_in_box == 1:
                if box.GetString(0) == '':
                    box.Delete(0)
                    items_in_box -= 1
            box.Insert(item_text, items_in_box)
        pass

    def button_clicked(self, event):
        print ids[event.GetId()]
        module_groups = ids[event.GetId()].split('.')
        if module_groups[1] == 'apply_button':
            # print "Got Apply Event"
            self.write_config(module_groups)
            self.on_close(event)
        elif module_groups[1] == 'cancel_button':
            # print "Got Cancel Event"
            event.Skip()
        elif 'list_add' in module_groups:
            self.add_list_item(module_groups)
            event.Skip()
        elif 'list_remove' in module_groups:
            event.Skip()

    def write_config(self, module_groups):
        module_hit = None
        parser = None
        conf_file = None

        print module_groups
        for module in self.main_class.modules_configs:
            if module_groups[0] in module:
                module_hit = module_groups[0]
                parser = module[module_groups[0]]['parser']
                conf_file = module[module_groups[0]]['file']
                break
        if module_hit:
            id_list = get_list_of_ids_from_module_name(module_groups[0])
            for id_item in id_list:
                if len(ids[id_item].split('.')) > 2:
                    section, param = ids[id_item].split('.')[1:]
                    param_split = param.split(self.keyword)
                    try:
                        param_split[1]
                    except IndexError:
                        param = param_split[0]
                    window = self.FindWindowById(id_item)
                    # get type of item and do shit
                    if isinstance(window, wx.CheckBox):
                        parser.set(section, param, str(window.IsChecked()).lower())
                    elif isinstance(window, wx.TextCtrl):
                        # print "Got TextCtrl, YAY", str(window.GetValue())
                        parser.set(section, param, window.GetValue().encode('utf-8'))

            with open(conf_file, 'w') as config_file:
                parser.write(config_file)

    def create_and_load_config(self, main_panel):
        notebook_id = wx.Window_NewControlId()
        notebook_text = translate_language('config')
        notebook = wx.Notebook(main_panel, id=notebook_id, style=wx.NB_TOP, name=notebook_text)

        # self.main_class.modules_configs = [self.main_class.modules_configs[0]]

        for config in self.main_class.modules_configs:
            panel_id = wx.Window_NewControlId()
            config_name = config.keys()[0]
            panel_name = translate_language(config_name)
            panel = wx.Panel(notebook, id=panel_id)
            # panel.SetScrollbars(5, 5, 10, 10)

            # print config[config_name]
            panel_sizer = self.load_config(config_params=config[config_name], panel=panel)
            panel.SetSizer(panel_sizer)
            # panel.Fit()

            notebook.AddPage(panel, panel_name)

        return notebook

    def load_config(self, config_params=None, panel=None, **kwargs):
        conf_params = config_params
        # print conf_params
        sizer = wx.BoxSizer(wx.VERTICAL)

        config = FlagConfigParser(allow_no_value=True)
        config.read(conf_params['file'])

        conf_panel_id = wx.Window_NewControlId()
        conf_panel = wx.ScrolledWindow(panel, id=conf_panel_id, style=wx.VSCROLL)
        conf_panel.SetScrollbars(5, 5, 10, 10)
        conf_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        module_prefix = conf_params['filename']

        gui_settings = {}
        sections = config._sections
        # print sections
        for item in sections:
            # Check if it is GUI settings
            item_split = item.split('_')
            if len(item_split) > 1 and item_split[-1] == 'gui':
                print "found GUI settings ", '.'.join([module_prefix, '_'.join(item_split[:-1])])
                for gui_item in config.get(item, 'for').split(','):
                    gui_item = gui_item.strip()
                    print gui_item
                    gui_settings[gui_item] = {}
                    for param, value in config.get_items(item):
                        if param != 'for':
                            gui_settings[gui_item][param] = value

            else:
                view = None
                if item in gui_settings:
                    print "Found Settings for this section", item
                    print gui_settings[item]
                    view = gui_settings[item].get('view', None)

                # Create header for section
                f_panel = conf_panel
                header_text = translate_language('.'.join([module_prefix, item]))
                section_header = wx.StaticBox(f_panel, -1, header_text)
                section_sizer = wx.StaticBoxSizer(section_header, wx.VERTICAL)

                if view == 'list':
                    item_sizer = wx.BoxSizer(wx.HORIZONTAL)

                    text_box_id = wx.Window_NewControlId()
                    ids[text_box_id] = '.'.join([module_prefix, item, 'list_input'])
                    text_box = wx.TextCtrl(f_panel, id=text_box_id)
                    item_sizer.Add(text_box, 0, wx.ALIGN_CENTER_VERTICAL)

                    list_button_id = wx.Window_NewControlId()
                    ids[list_button_id] = '.'.join([module_prefix, item, 'list_add'])
                    list_button_text = translate_language(ids[list_button_id])
                    list_button = wx.Button(f_panel, id=list_button_id, label=list_button_text)
                    self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=list_button_id)
                    item_sizer.Add(list_button, 0, wx.ALIGN_CENTER_VERTICAL)

                    list_button_id = wx.Window_NewControlId()
                    ids[list_button_id] = '.'.join([module_prefix, item, 'list_remove'])
                    list_button_text = translate_language(ids[list_button_id])
                    list_button = wx.Button(f_panel, id=list_button_id, label=list_button_text)
                    self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=list_button_id)
                    item_sizer.Add(list_button, 0, wx.ALIGN_CENTER_VERTICAL)

                    section_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, self.border_all)

                    list_box_id = wx.Window_NewControlId()
                    ids[list_box_id] = '.'.join([module_prefix, item, 'list_box'])
                    list_box_text = translate_language(ids[list_box_id])
                    list_box = wx.ListBox(f_panel, id=list_box_id)

                    values = []
                    for param, value in config.get_items(item):
                        values.append(param)

                    if not values:
                        values = ['']
                    list_box.InsertItems(values, 0)
                    list_box.SetMinSize(wx.Size(item_sizer.GetMinSize()[0], 100))

                    section_sizer.Add(list_box, 0, wx.ALL, self.border_all)

                else:
                    # Setting section items
                    for param, value, flags in config.items_with_flags(item):
                        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
                        rotate = False
                        # print param, flags
                        # Creating item settings
                        if flags:
                            module_name = self.keyword.join(['.'.join([module_prefix, item, param]),
                                                             self.flag_keyword.join(flags)])
                        else:
                            module_name = '.'.join([module_prefix, item, param])
                        # print module_name

                        if 'hidden' in flags:
                            if self.show_hidden:
                                pass
                            else:
                                continue

                        module_id = wx.Window_NewControlId()
                        ids[module_id] = module_name

                        # Creating item labels
                        text_text = translate_language(module_name)
                        text = wx.StaticText(f_panel, wx.ID_ANY, text_text,
                                             style=wx.ALIGN_RIGHT)
                        # text.SetBackgroundColour('red')
                        # text.SetMinSize(fix_sizes(text.GetSize(), self.labelMinSize))

                        # Creating item objects
                        if value is not None:
                            # If item has true or false - it's a checkbox
                            if value == 'true' or value == 'false':
                                rotate = True
                                if module_name == 'config.gui.show_hidden' and value == 'true':
                                    self.show_hidden = True
                                box = wx.CheckBox(f_panel, id=module_id)
                                # self.main_class.Bind(wx.EVT_CHECKBOX, self.check_box_clicked, id=module_id)
                                if value == 'true':
                                    box.SetValue(True)
                                else:
                                    box.SetValue(False)
                            # If not - it's text control
                            else:
                                box = wx.TextCtrl(f_panel, id=module_id, value=value.decode('utf-8'))
                                # box.AppendText(value)

                        # If item doesn't have any values it's a button
                        else:
                            box_text = translate_language('.'.join([module_name,'button']))
                            box = wx.Button(f_panel, id=module_id, label=box_text)
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
                conf_panel_sizer.Add(section_sizer, 0, wx.EXPAND)
                conf_panel.SetSizer(conf_panel_sizer)

        # Add buttons for saving/cancelling configuration updates
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)

        button_id = wx.Window_NewControlId()
        button_name = '.'.join([module_prefix, 'apply_button'])
        ids[button_id] = button_name
        apply_button = wx.Button(panel, id=button_id,
                                 label=translate_language(button_name))
        self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=button_id)
        buttons_sizer.Add(apply_button, 0, wx.ALIGN_RIGHT)

        # buttons_sizer.AddSpacer(self.flex_horizontal_gap*2)

        button_id = wx.Window_NewControlId()
        button_name = '.'.join([module_prefix, 'cancel_button'])
        ids[button_id] = button_name
        apply_button = wx.Button(panel, id=button_id,
                                 label=translate_language(button_name))
        self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=button_id)
        buttons_sizer.Add(apply_button, 0, wx.ALIGN_RIGHT)

        sizer.Add(conf_panel, 1, wx.EXPAND | wx.ALL, self.border_all)
        sizer.Add(buttons_sizer, 0, wx.ALIGN_RIGHT | wx.TOP, self.border_all)
        return sizer


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
        # self.main_window
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
