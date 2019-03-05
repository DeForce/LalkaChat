import wx
import wx.grid
import wx.adv

from modules.helper.system import translate_key, MODULE_KEY, VERSION, SOURCE_REPO_URL


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
        label_text = wx.StaticText(label_panel, label=value, style=wx.ALIGN_CENTER)
        self.text = label_text
        label_sizer.Add(label_text, 1, wx.ALIGN_CENTER)
        label_sizer2.Add(label_sizer, 1, wx.ALIGN_CENTER)
        label_panel.SetSizer(label_sizer2)
        label_panel.SetBackgroundColour(str(value))
        self.panel = label_panel

        button = wx.Button(panel, label=translate_key(MODULE_KEY.join(key + ['button'])))
        button.Bind(wx.EVT_BUTTON, self.on_button_press)
        border_size = wx.SystemSettings.GetMetric(wx.SYS_BORDER_Y)
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


class AboutWindow(wx.Dialog):
    def __init__(self, parent, title):
        self.parent = parent

        super().__init__(parent, style=wx.OK, title=title, size=wx.Size(300, 170))
        self.button_sizer = self.CreateStdDialogButtonSizer(wx.OK)

        title = 'LalkaChat'
        title_ctrl = wx.StaticText(self, label=title)

        branch = parent.loaded_modules['main'].config['system']['release_channel']
        version = parent.loaded_modules['main'].config['system']['current_version']

        version_text = f'Version: {VERSION}-{branch}-{version}'
        version_ctrl = wx.StaticText(self, label=version_text)

        owner_text = f'Created by Open Source'
        owner_ctrl = wx.StaticText(self, label=owner_text)

        hyper_sizer = wx.BoxSizer(wx.HORIZONTAL)
        repo_text = f'Link to GitHub:'
        repo_ctrl = wx.StaticText(self, label=repo_text)
        hyper_sizer.Add(repo_ctrl, 0, wx.ALIGN_CENTER | wx.ALIGN_RIGHT)

        hyperlink = SOURCE_REPO_URL
        hyperlink_ctrl = wx.adv.HyperlinkCtrl(self, label='Repo Link', url=hyperlink, style=wx.adv.HL_ALIGN_LEFT)
        hyper_sizer.Add(hyperlink_ctrl, 0, wx.ALIGN_LEFT)

        empty_ctrl = wx.StaticText(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title_ctrl, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        sizer.Add(version_ctrl, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        sizer.Add(owner_ctrl, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        sizer.Add(hyper_sizer, 0, wx.TOP | wx.ALIGN_CENTER, 5)

        sizer.Add(empty_ctrl, 1, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER, 10)
        sizer.Add(self.button_sizer, 0, wx.ALIGN_BOTTOM | wx.ALIGN_CENTER | wx.BOTTOM, 5)
        self.SetSizer(sizer)
        self.Layout()


class MainMenuToolBar(wx.ToolBar):
    def __init__(self, *args, **kwargs):
        self.main_class = kwargs['main_class']
        kwargs.pop('main_class')

        kwargs["style"] = wx.TB_NOICONS | wx.TB_TEXT

        wx.ToolBar.__init__(self, *args, **kwargs)
        self.SetToolBitmapSize((0, 0))

        self.create_tool('menu.settings', self.main_class.on_settings)
        self.create_tool('menu.reload', self.main_class.on_reload)
        self.create_tool('menu.about', self.main_class.on_about)

        self.Realize()

    def create_tool(self, name, binding=None, style=wx.ITEM_NORMAL, s_help="", l_help=""):
        label_text = translate_key(name)
        button = self.AddTool(toolId=wx.ID_ANY, label=label_text, bitmap=wx.NullBitmap, bmpDisabled=wx.NullBitmap,
                              kind=style, shortHelp=s_help, longHelp=l_help)
        if binding:
            self.main_class.Bind(wx.EVT_TOOL, binding, id=button.Id)
        return button

