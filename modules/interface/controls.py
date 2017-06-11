import wx
import wx.grid

from modules.helper.system import translate_key, MODULE_KEY

IDS = {}


def get_list_of_ids_from_module_name(name, id_group=1, return_tuple=False):
    split_key = MODULE_KEY

    id_array = []
    for item_key, item in IDS.items():
        item_name = split_key.join(item.split(split_key)[:id_group])
        if item_name == name:
            if return_tuple:
                id_array.append((item_key, item))
            else:
                id_array.append(item_key)
    return id_array


def get_id_from_name(name):
    for item, item_id in IDS.iteritems():
        if item_id == name:
            return item
    return None


def id_renew(name, update=False, multiple=False):
    module_id = get_id_from_name(name)
    if not multiple and module_id:
        del IDS[module_id]
    new_id = wx.Window.NewControlId(1)
    if update:
        IDS[new_id] = name
    return new_id


class GuiCreationError(Exception):
    pass


class CustomColourPickerCtrl(object):
    def __init__(self):
        self.panel = None
        self.button = None
        self.text = None
        self.event = None
        self.key = None

    def create(self, panel, value="#FFFFFF", orientation=wx.HORIZONTAL, event=None, key=None,
               *args, **kwargs):
        item_sizer = wx.BoxSizer(orientation)

        self.event = event
        self.key = key
        label_panel = wx.Panel(panel, style=wx.BORDER_SIMPLE)
        label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_sizer2 = wx.BoxSizer(wx.VERTICAL)
        label_text = wx.StaticText(label_panel, label=unicode(value), style=wx.ALIGN_CENTER)
        self.text = label_text
        label_sizer.Add(label_text, 1, wx.ALIGN_CENTER)
        label_sizer2.Add(label_sizer, 1, wx.ALIGN_CENTER)
        label_panel.SetSizer(label_sizer2)
        label_panel.SetBackgroundColour(str(value))
        self.panel = label_panel

        button = wx.Button(panel, label=translate_key(MODULE_KEY.join(key + ['button'])))
        button.Bind(wx.EVT_BUTTON, self.on_button_press)
        border_size = wx.SystemSettings_GetMetric(wx.SYS_BORDER_Y)
        button_size = button.GetSize()
        if button_size[0] > 150:
            button_size[0] = 150
        button_size[1] -= border_size*2
        self.button = button

        label_panel.SetMinSize(button_size)
        label_panel.SetSize(button_size)

        item_sizer.Add(label_panel, 0, wx.ALIGN_CENTER)
        item_sizer.AddSpacer(2)
        item_sizer.Add(button, 0, wx.EXPAND)
        return item_sizer

    def on_button_press(self, event):
        dialog = wx.ColourDialog(self.panel)
        if dialog.ShowModal() == wx.ID_OK:
            colour = dialog.GetColourData()
            hex_colour = colour.Colour.GetAsString(flags=wx.C2S_HTML_SYNTAX)
            self.panel.SetBackgroundColour(colour.Colour)
            self.panel.Refresh()
            self.text.SetLabel(hex_colour)
            self.panel.Layout()
            col = colour.Colour
            if (col.red * 0.299 + col.green * 0.587 + col.blue * 0.114) > 186:
                self.text.SetForegroundColour('black')
            else:
                self.text.SetForegroundColour('white')

            self.event({'colour': colour.Colour, 'hex': hex_colour, 'key': self.key})


class KeyListBox(wx.ListBox):
    def __init__(self, *args, **kwargs):
        self.keys = kwargs.pop('keys', [])
        wx.ListBox.__init__(self, *args, **kwargs)

    def get_key_from_index(self, index):
        return self.keys[index]


class KeyCheckListBox(wx.CheckListBox):
    def __init__(self, *args, **kwargs):
        self.keys = kwargs.pop('keys', [])
        wx.CheckListBox.__init__(self, *args, **kwargs)

    def get_key_from_index(self, index):
        return self.keys[index]


class KeyChoice(wx.Choice):
    def __init__(self, *args, **kwargs):
        self.keys = kwargs.pop('keys', [])
        wx.Choice.__init__(self, *args, **kwargs)

    def get_key_from_index(self, index):
        return self.keys[index]


class MainMenuToolBar(wx.ToolBar):
    def __init__(self, *args, **kwargs):
        self.main_class = kwargs['main_class']  # type: ChatGui
        kwargs.pop('main_class')

        kwargs["style"] = wx.TB_NOICONS | wx.TB_TEXT

        wx.ToolBar.__init__(self, *args, **kwargs)
        self.SetToolBitmapSize((0, 0))

        self.create_tool('menu.settings', self.main_class.on_settings)
        self.create_tool('menu.reload', self.main_class.on_toolbar_button)

        self.Realize()

    def create_tool(self, name, binding=None, style=wx.ITEM_NORMAL, s_help="", l_help=""):
        l_id = id_renew(name)
        IDS[l_id] = name
        label_text = translate_key(IDS[l_id])
        button = self.AddLabelTool(l_id, label_text, wx.NullBitmap, wx.NullBitmap,
                                   style, s_help, l_help)
        if binding:
            self.main_class.Bind(wx.EVT_TOOL, binding, id=l_id)
        return button

