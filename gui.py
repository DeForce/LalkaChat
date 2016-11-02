import threading
from collections import OrderedDict

import webbrowser
import wx
import wx.grid
import os
import logging
from ConfigParser import ConfigParser
from cefpython3.wx import chromectrl
from modules.helper.system import MODULE_KEY, translate_key
from modules.helper.parser import return_type
# ToDO: Support customization of borders/spacings
# ToDO: Exit by cancel button

IDS = {}
log = logging.getLogger('chat_gui')
INFORMATION_TAG = 'gui_information'
SECTION_GUI_TAG = '__gui'
SKIP_TAGS = [INFORMATION_TAG]
SKIP_TXT_CONTROLS = ['list_input', 'list_input2']
SKIP_BUTTONS = ['list_add', 'list_remove', 'apply_button', 'cancel_button', 'ok_button']
ITEM_SPACING_VERT = 6
ITEM_SPACING_HORZ = 30


def get_id_from_name(name, error=False):
    for item, item_id in IDS.iteritems():
        if item_id == name:
            return item
    if error:
        raise ReferenceError
    return None


def id_renew(name, update=False):
    module_id = get_id_from_name(name)
    if module_id:
        del IDS[module_id]
    new_id = wx.Window.NewControlId(1)
    if update:
        IDS[new_id] = name
    return new_id


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


def check_duplicate(item, window):
    items = window.GetItems()
    if item in items:
        return True
    return False


def create_categories(loaded_modules):
    cat_dict = OrderedDict()
    for module_name, module_config in loaded_modules.items():
        if 'config' not in module_config:
            continue

        config = module_config.get('config')
        if INFORMATION_TAG in config:
            tag = config[INFORMATION_TAG].get('category', 'undefined')
            if tag not in cat_dict:
                cat_dict[tag] = OrderedDict()
            cat_dict[tag][module_name] = module_config
    return cat_dict


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


class SettingsWindow(wx.Frame):
    main_grid = None
    page_list = []
    selected_cell = None

    def __init__(self, *args, **kwargs):
        self.spacer_size = (0, 10)
        self.main_class = kwargs.pop('main_class')  # type: ChatGui
        self.categories = kwargs.pop('categories')  # type: dict

        wx.Frame.__init__(self, *args, **kwargs)

        self.settings_saved = True
        self.tree_ctrl = None
        self.content_page = None
        self.sizer_list = []
        self.changes = {}
        self.buttons = {}

        # Setting up the window
        self.SetBackgroundColour('cream')
        self.show_hidden = self.main_class.gui_settings.get('show_hidden')

        # Setting up events
        self.Bind(wx.EVT_CLOSE, self.on_close)

        styles = wx.DEFAULT_FRAME_STYLE
        if wx.STAY_ON_TOP & self.main_class.GetWindowStyle() == wx.STAY_ON_TOP:
            styles = styles | wx.STAY_ON_TOP
        self.SetWindowStyle(styles)

        self.create_layout()
        self.Show(True)

    def on_exit(self, event):
        log.debug(event)
        self.Destroy()

    def on_close(self, event):
        self.on_exit(event)

    def on_listbox_change(self, event):
        item_object = event.EventObject
        selection = item_object.get_key_from_index(item_object.GetSelection())
        description = translate_key(MODULE_KEY.join([selection, 'description']))

        item_key = IDS[event.GetId()].split(MODULE_KEY)
        show_description = self.main_class.loaded_modules[item_key[0]]['gui'][item_key[1]].get('description', False)

        if isinstance(item_object, KeyListBox):
            self.on_change(IDS[event.GetId()], selection, section=True)

        if show_description:
            item_id_key = MODULE_KEY.join(item_key[:-1])
            descr_static_text = wx.FindWindowById(get_id_from_name(MODULE_KEY.join([item_id_key, 'descr_explain'])))
            descr_static_text.SetLabel(description)
            descr_static_text.Wrap(descr_static_text.GetSize()[0])

    def on_checklist_box_change(self, event):
        window = event.EventObject
        item_ids = window.GetChecked()
        items_values = [window.get_key_from_index(item_id) for item_id in item_ids]
        self.on_change(IDS[event.GetId()], items_values, section=True)

    def on_change(self, key, value, section=False, listbox=False):
        def apply_changes():
            self.changes[key] = value
            self.buttons[MODULE_KEY.join(['settings', 'apply_button'])].Enable()

        def clear_changes():
            if key in self.changes:
                self.changes.pop(key)
            if not self.changes:
                self.buttons[MODULE_KEY.join(['settings', 'apply_button'])].Disable()
        split_keys = key.split(MODULE_KEY)
        config = self.main_class.loaded_modules[split_keys[0]]['config']
        if section:
            if isinstance(value, list):
                if set(config[split_keys[1]].keys()) != set(value):
                    apply_changes()
                else:
                    clear_changes()
            else:
                if config[split_keys[1]].decode('utf-8') != return_type(value):
                    apply_changes()
                else:
                    clear_changes()
        elif listbox:
            apply_changes()
        else:
            if isinstance(value, bool):
                if config[split_keys[1]][split_keys[2]] != value:
                    apply_changes()
                else:
                    clear_changes()
            else:
                if config[split_keys[1]][split_keys[2]].decode('utf-8') != return_type(value):
                    apply_changes()
                else:
                    clear_changes()

    def on_tree_ctrl_changed(self, event):
        self.settings_saved = False
        tree_ctrl = event.EventObject  # type: wx.TreeCtrl
        selection = tree_ctrl.GetFocusedItem()
        selection_text = tree_ctrl.GetItemData(selection).GetData()
        key_list = selection_text.split(MODULE_KEY)

        # Drawing page
        self.fill_page_with_content(self.content_page, key_list[1], key_list[-1],
                                    self.main_class.loaded_modules[key_list[-1]])

        event.Skip()

    def on_textctrl(self, event):
        text_ctrl = event.EventObject
        self.on_change(IDS[event.GetId()], text_ctrl.GetValue())
        event.Skip()

    def on_spinctrl(self, event):
        spin_ctrl = event.EventObject
        self.on_change(IDS[event.GetId()], spin_ctrl.GetValue())
        event.Skip()

    def on_check_change(self, event):
        check_ctrl = event.EventObject
        self.on_change(IDS[event.GetId()], check_ctrl.IsChecked())
        event.Skip()

    def create_layout(self):
        self.main_grid = wx.BoxSizer(wx.HORIZONTAL)
        style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_TWIST_BUTTONS | wx.TR_NO_LINES
        # style = wx.TR_HAS_BUTTONS | wx.TR_SINGLE | wx.TR_HIDE_ROOT

        tree_ctrl_id = id_renew('settings.tree', update=True)
        tree_ctrl = wx.TreeCtrl(self, id=tree_ctrl_id, style=style)
        tree_ctrl.SetQuickBestSize(False)
        root_key = MODULE_KEY.join(['settings', 'tree', 'root'])
        root_node = tree_ctrl.AddRoot(translate_key(root_key))
        for item, value in self.categories.iteritems():
            item_key = MODULE_KEY.join(['settings', item])
            item_data = wx.TreeItemData()
            item_data.SetData(item_key)

            item_node = tree_ctrl.AppendItem(root_node, translate_key(item_key), data=item_data)
            for f_item, f_value in value.iteritems():
                if not f_item == item:
                    f_item_key = MODULE_KEY.join([item_key, f_item])
                    f_item_data = wx.TreeItemData()
                    f_item_data.SetData(f_item_key)
                    tree_ctrl.AppendItem(item_node, translate_key(f_item), data=f_item_data)
        tree_ctrl.ExpandAll()
        tree_ctrl.SetMinSize(wx.Size(tree_ctrl.GetSize()[0] + 70, -1))

        self.tree_ctrl = tree_ctrl
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_ctrl_changed, id=tree_ctrl_id)
        self.main_grid.Add(self.tree_ctrl, 0, wx.EXPAND | wx.ALL, 7)

        content_page_id = id_renew(MODULE_KEY.join(['settings', 'content']))
        self.content_page = wx.Panel(self, id=content_page_id)
        self.main_grid.Add(self.content_page, 1, wx.EXPAND)

        self.main_grid.Layout()
        self.SetSizer(self.main_grid)
        tree_ctrl.SelectItem(tree_ctrl.GetFirstChild(root_node)[0])

    def fill_page_with_content(self, panel, setting_category, category_item, category_config):
        def create_button(button_key, function, enabled=True):
            button_id = id_renew(button_key, update=True)
            c_button = wx.Button(panel, id=button_id, label=translate_key(button_key))
            if not enabled:
                c_button.Disable()
            self.buttons[button_key] = c_button
            self.Bind(wx.EVT_BUTTON, function, id=button_id)
            return c_button

        page_sizer = panel.GetSizer()  # type: wx.Sizer
        if not page_sizer:
            page_sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(page_sizer)
            # Buttons
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            button_sizer.Add(create_button(MODULE_KEY.join(['settings', 'ok_button']),
                                           self.button_clicked), 0, wx.ALIGN_RIGHT)
            button_sizer.Add(create_button(MODULE_KEY.join(['settings', 'apply_button']),
                                           self.button_clicked, enabled=False), 0, wx.ALIGN_RIGHT)
            button_sizer.Add(create_button(MODULE_KEY.join(['settings', 'cancel_button']),
                                           self.button_clicked), 0, wx.ALIGN_RIGHT)
            page_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
        else:
            children = page_sizer.GetChildren()
            children_len = len(children)
            for index, child in enumerate(children):
                window = child.GetWindow() if child.GetWindow() else child.GetSizer()
                if index < children_len - 1:
                    page_sizer.Hide(window)

        if category_item in self.sizer_list:
            # +1 because we have button sizer
            sizer_index = self.sizer_list.index(category_item)
            page_sizer.Show(sizer_index)
        else:
            # Creating sizer for page
            sizer = wx.BoxSizer(wx.VERTICAL)
            # Window for settings
            sizer.Add(self.fill_sc_with_config(panel, category_config, category_item), 1, wx.EXPAND)
            page_sizer.Prepend(sizer, 1, wx.EXPAND)
            self.sizer_list.insert(0, category_item)
        page_sizer.Layout()
        panel.Layout()

    def fill_sc_with_config(self, panel, category_config, category_item):
        page_sc_window = wx.ScrolledWindow(panel, id=id_renew(category_item), style=wx.VSCROLL)
        page_sc_window.SetScrollbars(5, 5, 10, 10)
        border_all = 5
        sizer = wx.BoxSizer(wx.VERTICAL)
        for section_key, section_items in category_config['config'].items():
            if section_key in SKIP_TAGS:
                continue

            static_key = MODULE_KEY.join([category_item, section_key])
            static_box = wx.StaticBox(page_sc_window, label=translate_key(static_key))
            static_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)

            log.debug("Working on {0}".format(static_key))

            static_sizer.Add(self.create_items(static_box, static_key,
                                               section_items, category_config.get('gui', {}).get(section_key, {})),
                             0, wx.EXPAND | wx.ALL, border_all)

            sizer.Add(static_sizer, 0, wx.EXPAND)
        page_sc_window.SetSizer(sizer)
        return page_sc_window

    def create_items(self, parent, key, section, section_gui):
        sizer = wx.BoxSizer(wx.VERTICAL)
        view = section_gui.get('view', 'normal')
        if 'list' in view:
            sizer.Add(self.create_list(parent, view, key, section, section_gui))
        elif 'choose' in view:
            sizer.Add(self.create_choose(parent, view, key, section, section_gui))
        else:
            sizer.Add(self.create_item(parent, view, key, section, section_gui))
        return sizer

    def create_list(self, parent, view, key, section, section_gui):
        is_dual = True if 'dual' in view else False
        style = wx.ALIGN_CENTER_VERTICAL
        item_sizer = wx.BoxSizer(wx.VERTICAL)
        addable_sizer = None
        if section_gui.get('addable', False):
            addable_sizer = wx.BoxSizer(wx.HORIZONTAL)
            item_input_key = MODULE_KEY.join([key, 'list_input'])
            addable_sizer.Add(wx.TextCtrl(parent, id=id_renew(item_input_key, update=True)), 0, style)
            if is_dual:
                item_input2_key = MODULE_KEY.join([key, 'list_input2'])
                addable_sizer.Add(wx.TextCtrl(parent, id=id_renew(item_input2_key, update=True)), 0, style)

            item_apply_key = MODULE_KEY.join([key, 'list_add'])
            item_apply_id = id_renew(item_apply_key, update=True)
            addable_sizer.Add(wx.Button(parent, id=item_apply_id, label=translate_key(item_apply_key)), 0, style)
            self.Bind(wx.EVT_BUTTON, self.button_clicked, id=item_apply_id)

            item_remove_key = MODULE_KEY.join([key, 'list_remove'])
            item_remove_id = id_renew(item_remove_key, update=True)
            addable_sizer.Add(wx.Button(parent, id=item_remove_id, label=translate_key(item_remove_key)), 0, style)
            self.Bind(wx.EVT_BUTTON, self.button_clicked, id=item_remove_id)

            item_sizer.Add(addable_sizer, 0, wx.EXPAND)
        list_box = wx.grid.Grid(parent, id=id_renew(MODULE_KEY.join([key, 'list_box']), update=True))
        list_box.CreateGrid(0, 2 if is_dual else 1)
        list_box.DisableDragColSize()
        list_box.DisableDragRowSize()
        list_box.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.select_cell)
        list_box.SetMinSize(wx.Size(-1, 100))

        for index, (item, value) in enumerate(section.items()):
            list_box.AppendRows(1)
            if is_dual:
                list_box.SetCellValue(index, 0, item.decode('utf-8'))
                list_box.SetCellValue(index, 1, value.decode('utf-8'))
            else:
                list_box.SetCellValue(index, 0, item.decode('utf-8'))
        list_box.SetColLabelSize(1)
        list_box.SetRowLabelSize(1)
        if addable_sizer:
            col_size = addable_sizer.GetMinSize()[0] - 2
            if is_dual:
                first_col_size = list_box.GetColSize(0)
                second_col_size = col_size - first_col_size if first_col_size < col_size else -1
                list_box.SetColSize(1, second_col_size)
            else:
                list_box.SetDefaultColSize(col_size, resizeExistingCols=True)
        else:
            list_box.AutoSize()

        # Adding size of scrollbars
        size = list_box.GetEffectiveMinSize()
        size[0] += 18
        size[1] += 18
        list_box.SetMinSize(size)
        item_sizer.Add(list_box, 1, wx.EXPAND)
        return item_sizer

    def create_choose(self, parent, view, key, section, section_gui):
        is_single = True if 'single' in view else False
        description = section_gui.get('description', False)
        style = wx.LB_SINGLE if is_single else wx.LB_EXTENDED
        item_sizer = wx.BoxSizer(wx.VERTICAL)
        list_items = []
        translated_items = []

        if section_gui['check_type'] in ['dir', 'folder', 'files']:
            check_type = section_gui['check_type']
            keep_extension = section_gui['file_extension'] if 'file_extension' in section_gui else False
            for item_in_list in os.listdir(os.path.join(self.main_class.main_config['root_folder'],
                                                        section_gui['check'])):
                item_path = os.path.join(self.main_class.main_config['root_folder'],
                                         section_gui['check'], item_in_list)
                if check_type in ['dir', 'folder'] and os.path.isdir(item_path):
                    list_items.append(item_in_list)
                elif check_type == 'files' and os.path.isfile(item_path):
                    if not keep_extension:
                        item_in_list = ''.join(os.path.basename(item_path).split('.')[:-1])
                    if '__init__' not in item_in_list:
                        if item_in_list not in list_items:
                            list_items.append(item_in_list)
                            translated_items.append(translate_key(item_in_list))
        elif section_gui['check_type'] == 'sections':
            parser = ConfigParser(allow_no_value=True)
            parser.read(section_gui.get('check', ''))
            for item in parser.sections():
                list_items.append(translate_key(item))

        item_key = MODULE_KEY.join([key, 'list_box'])
        label_text = translate_key(item_key)
        if label_text:
            item_sizer.Add(wx.StaticText(parent, label=label_text, style=wx.ALIGN_RIGHT))
        if is_single:
            item_list_box = KeyListBox(parent, id=id_renew(item_key, update=True), keys=list_items,
                                       choices=translated_items if translated_items else list_items, style=style)
            item_list_box.Bind(wx.EVT_LISTBOX, self.on_listbox_change)
        else:
            item_list_box = KeyCheckListBox(parent, id=id_renew(item_key, update=True), keys=list_items,
                                            choices=translated_items if translated_items else list_items)
            item_list_box.Bind(wx.EVT_LISTBOX, self.on_listbox_change)
            item_list_box.Bind(wx.EVT_CHECKLISTBOX, self.on_checklist_box_change)

        section_for = section if not is_single else {section: None}
        if is_single:
            [item_list_box.SetSelection(list_items.index(item)) for item, value in section_for.items()]
        else:
            check_items = [list_items.index(item) for item, value in section_for.items()]
            item_list_box.SetChecked(check_items)
        if description:
            adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
            adv_sizer.Add(item_list_box, 0, wx.EXPAND)

            descr_key = MODULE_KEY.join([key, 'descr_explain'])
            descr_text = wx.StaticText(parent, id=id_renew(descr_key, update=True),
                                       label=translate_key(descr_key), style=wx.ST_NO_AUTORESIZE)
            adv_sizer.Add(descr_text, 0, wx.EXPAND | wx.LEFT, 10)

            sizes = descr_text.GetSize()
            sizes[0] -= 20
            descr_text.SetMinSize(sizes)
            descr_text.Fit()
            # descr_text.Wrap(descr_text.GetSize()[0])
            item_sizer.Add(adv_sizer)
        else:
            item_sizer.Add(item_list_box)
        return item_sizer

    def create_dropdown(self, parent, view, key, section, section_gui, section_item=False, short_key=None):
        item_text = wx.StaticText(parent, label=translate_key(key),
                                  style=wx.ALIGN_RIGHT)
        choices = section_gui.get('choices')
        key = key if section_item else MODULE_KEY.join([key, 'dropdown'])
        item_box = KeyChoice(parent, id=id_renew(key, update=True),
                             keys=choices, choices=choices)
        item_value = section[short_key] if section_item else section
        item_box.SetSelection(choices.index(item_value))
        return item_text, item_box

    def create_spin(self, parent, view, key, section, section_gui, section_item=False, short_key=None):
        item_text = wx.StaticText(parent, label=translate_key(key),
                                  style=wx.ALIGN_RIGHT)
        key = key if section_item else MODULE_KEY.join([key, 'spin'])
        value = short_key if section_item else section
        item_box = wx.SpinCtrl(parent, id=id_renew(key, update=True), min=section_gui['min'], max=section_gui['max'],
                               initial=int(value))
        item_box.Bind(wx.EVT_SPINCTRL, self.on_spinctrl)
        item_box.Bind(wx.EVT_TEXT, self.on_spinctrl)
        return item_text, item_box

    def create_item(self, parent, view, key, section, section_gui):
        flex_grid = wx.FlexGridSizer(0, 2, ITEM_SPACING_VERT, ITEM_SPACING_HORZ)
        if not section:
            return wx.Sizer()
        for item, value in section.items():
            if not self.show_hidden and item in section_gui.get('hidden', []):
                continue
            item_name = MODULE_KEY.join([key, item])
            if item in section_gui:
                if 'list' in section_gui[item].get('view'):
                    flex_grid.Add(self.create_list(parent, view, item_name, section, section_gui[item]))
                    flex_grid.AddSpacer(wx.Size(0, 0))
                elif 'choose' in section_gui[item].get('view'):
                    flex_grid.Add(self.create_choose(parent, view, item_name, section, section_gui[item]))
                    flex_grid.AddSpacer(wx.Size(0, 0))
                elif 'dropdown' in section_gui[item].get('view'):
                    text, control = self.create_dropdown(parent, view, item_name, section, section_gui[item],
                                                         section_item=True, short_key=item)
                    flex_grid.Add(text)
                    flex_grid.Add(control)
                elif 'spin' in section_gui[item].get('view'):
                    text, control = self.create_spin(parent, view, item_name, section, section_gui[item],
                                                     section_item=True, short_key=section[item])
                    flex_grid.Add(text)
                    flex_grid.Add(control)
            else:
                # Checking type of an item
                style = wx.ALIGN_CENTER_VERTICAL
                if value is None:  # Button
                    button_id = id_renew(item_name, update=True)
                    item_button = wx.Button(parent, id=button_id, label=translate_key(item_name))
                    flex_grid.Add(item_button, 0, wx.ALIGN_LEFT)
                    flex_grid.AddSpacer(wx.Size(0, 0))
                    self.main_class.Bind(wx.EVT_BUTTON, self.button_clicked, id=button_id)
                elif isinstance(value, bool):  # Checkbox
                    item_box = wx.CheckBox(parent, id=id_renew(item_name, update=True),
                                           label=translate_key(item_name), style=style)
                    item_box.SetValue(value)
                    item_box.Bind(wx.EVT_CHECKBOX, self.on_check_change)
                    flex_grid.Add(item_box, 0, wx.ALIGN_LEFT)
                    flex_grid.AddSpacer(wx.Size(0, 0))
                else:  # TextCtrl
                    item_box = wx.TextCtrl(parent, id=id_renew(item_name, update=True),
                                           value=str(value).decode('utf-8'))
                    item_box.Bind(wx.EVT_TEXT, self.on_textctrl)
                    item_text = wx.StaticText(parent, label=translate_key(item_name),
                                              style=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_HORIZONTAL)
                    flex_grid.Add(item_text)
                    flex_grid.Add(item_box)
        flex_grid.Fit(parent)
        return flex_grid

    def button_clicked(self, event):
        log.debug("[Settings] Button clicked: {0}".format(IDS[event.GetId()]))
        button_id = event.GetId()
        keys = IDS[button_id].split(MODULE_KEY)
        if keys[-1] in ['list_add', 'list_remove']:
            self.list_operation(MODULE_KEY.join(keys[:-1]), action=keys[-1])
            self.on_change(IDS[button_id], 'listbox_changed', listbox=True)
        elif keys[-1] in ['ok_button', 'apply_button']:
            if self.save_settings():
                log.debug('Got non-dynamic changes')
                dialog = wx.MessageDialog(self,
                                          message=translate_key(MODULE_KEY.join(['main', 'save', 'non_dynamic'])),
                                          caption="Caption",
                                          style=wx.OK_DEFAULT,
                                          pos=wx.DefaultPosition)
                dialog.ShowModal()
                if keys[-1] == 'ok_button':
                    self.on_exit(event)
            self.settings_saved = True
        elif keys[-1] == 'cancel_button':
            self.on_close(event)

        event.Skip()

    def save_settings(self):
        dynamic_check = False
        for module in self.main_class.loaded_modules.keys():
            if not self.save_module(module):
                dynamic_check = True
        return dynamic_check

    def save_module(self, module):
        module_settings = self.main_class.loaded_modules.get(module, {})
        non_dynamic = module_settings.get('gui', {}).get('non_dynamic', [])
        module_config = module_settings.get('config')
        non_dynamic_check = False
        if module_settings:
            parser = module_settings['parser']  # type: ConfigParser
            items = get_list_of_ids_from_module_name(module, return_tuple=True)
            for item, name in items:
                module_name, section, item_name = name.split(MODULE_KEY)

                if not parser.has_section(section):
                    continue
                # Check for non-dynamic items
                for d_item in non_dynamic:
                    if section in d_item:
                        if MODULE_KEY.join([section, '*']) in d_item:
                            non_dynamic_check = True
                            break
                        elif MODULE_KEY.join([section, item_name]) in d_item:
                            non_dynamic_check = True
                            break
                # Saving
                wx_window = wx.FindWindowById(item)
                if isinstance(wx_window, wx.CheckBox):
                    if name == MODULE_KEY.join(['main', 'gui', 'show_hidden']):
                        self.show_hidden = wx_window.IsChecked()
                    parser.set(section, item_name, wx_window.IsChecked())
                    module_config[section][item_name] = wx_window.IsChecked()
                elif isinstance(wx_window, wx.TextCtrl):
                    if item_name not in SKIP_TXT_CONTROLS:
                        parser.set(section, item_name, wx_window.GetValue().encode('utf-8').strip())
                        module_config[section][item_name] = wx_window.GetValue().encode('utf-8').strip()
                elif isinstance(wx_window, wx.grid.Grid):
                    col_count = wx_window.GetNumberCols()
                    row_count = wx_window.GetNumberRows()
                    parser_options = parser.options(section)
                    grid_elements = [[wx_window.GetCellValue(row, col).encode('utf-8').strip()
                                      for col in range(col_count)]
                                     for row in range(row_count)]
                    if not grid_elements:
                        for option in parser_options:
                            parser.remove_option(section, option)
                            module_config[section].pop(option)
                    else:
                        item_list = [item[0] for item in grid_elements]
                        for option in parser_options:
                            if option not in item_list:
                                module_config[section].pop(option)
                                parser.remove_option(section, option)
                        for elements in grid_elements:
                            parser.set(section, *elements)
                            if len(elements) == 1:
                                module_config[section][elements[0]] = None
                            elif len(elements) == 2:
                                module_config[section][elements[0]] = elements[1]
                elif isinstance(wx_window, wx.Button):
                    if item_name not in SKIP_BUTTONS:
                        parser.set(section, item_name)
                        module_config[section][item_name] = None
                elif isinstance(wx_window, KeyListBox):
                    item_id = wx_window.GetSelection()
                    parser_options = parser.options(section)
                    item_value = wx_window.get_key_from_index(item_id)
                    if not item_value:
                        for option in parser_options:
                            parser.remove_option(section, option)
                            module_config[section] = None
                    else:
                        for option in parser_options:
                            parser.remove_option(section, option)
                        parser.set(section, item_value)
                        module_config[section] = item_value
                elif isinstance(wx_window, KeyCheckListBox):
                    item_ids = wx_window.GetChecked()
                    parser_options = parser.options(section)
                    items_values = [wx_window.get_key_from_index(item_id) for item_id in item_ids]
                    if not items_values:
                        for option in parser_options:
                            parser.remove_option(section, option)
                            module_config[section].pop(option)
                    else:
                        for option in parser_options:
                            if option not in items_values:
                                parser.remove_option(section, option)
                                module_config[section].pop(option)
                        for value in items_values:
                            parser.set(section, value)
                            module_config[section][value] = None
                elif isinstance(wx_window, KeyChoice):
                    item_id = wx_window.GetSelection()
                    item_value = wx_window.get_key_from_index(item_id)
                    parser.set(section, item_name, item_value)
                    module_config[section][item_name] = item_value
                elif isinstance(wx_window, wx.SpinCtrl):
                    item_value = wx_window.GetValue()
                    parser.set(section, item_name, item_value)
                    module_config[section][item_name] = item_value
            with open(module_settings['file'], 'w') as config_file:
                parser.write(config_file)
            if 'class' in module_settings:
                module_settings['class'].apply_settings()
        return non_dynamic_check

    def select_cell(self, event):
        self.selected_cell = (event.GetRow(), event.GetCol())
        event.Skip()

    def list_operation(self, key, action):
        if action == 'list_add':
            list_input_value = wx.FindWindowById(get_id_from_name(MODULE_KEY.join([key, 'list_input']))).GetValue()

            try:
                list_input2 = wx.FindWindowById(get_id_from_name(MODULE_KEY.join([key, 'list_input2']), error=True))
                list_input2_value = list_input2.GetValue() if list_input2 else None
            except ReferenceError:
                list_input2_value = None

            list_box = wx.FindWindowById(get_id_from_name(MODULE_KEY.join([key, 'list_box'])))
            list_box.AppendRows(1)
            row_count = list_box.GetNumberRows() - 1
            list_box.SetCellValue(row_count, 0, list_input_value.strip())
            if list_input2_value:
                list_box.SetCellValue(row_count, 1, list_input2_value.strip())

        elif action == 'list_remove':
            list_box = wx.FindWindowById(get_id_from_name(MODULE_KEY.join([key, 'list_box'])))
            top = list_box.GetSelectionBlockTopLeft()
            bot = list_box.GetSelectionBlockBottomRight()
            if top and bot:
                top = top[0][0]
                bot = bot[0][0] + 1
                del_rows = range(top, bot) if top < bot else range(bot, top)
            else:
                del_rows = [self.selected_cell[0]]

            if list_box.GetNumberRows():
                ids_deleted = 0
                for select in del_rows:
                    list_box.DeleteRows(select - ids_deleted)
                    ids_deleted += 1


class ChatGui(wx.Frame):
    def __init__(self, parent, title, url, **kwargs):
        # Setting the settings
        self.main_config = kwargs.get('main_config')
        self.gui_settings = kwargs.get('gui_settings')
        self.loaded_modules = kwargs.get('loaded_modules')
        self.queue = kwargs.get('queue')
        self.settings_window = None

        wx.Frame.__init__(self, parent, title=title, size=self.gui_settings.get('size'))
        # Set window style
        styles = wx.DEFAULT_FRAME_STYLE
        if self.gui_settings.get('on_top', False):
            log.info("Application is on top")
            styles = styles | wx.STAY_ON_TOP
        self.SetFocus()
        self.SetWindowStyle(styles)

        # Creating categories for gui
        log.debug("Sorting modules to categories")
        self.sorted_categories = create_categories(self.loaded_modules)

        # Creating main gui window
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = MainMenuToolBar(self, main_class=self)
        self.browser_window = chromectrl.ChromeCtrl(self, useTimer=False, url=str(url), hasNavBar=False)

        vbox.Add(self.toolbar, 0, wx.EXPAND)
        vbox.Add(self.browser_window, 1, wx.EXPAND)

        # Set events
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Show window after creation
        self.SetSizer(vbox)
        self.Show(True)

        # Show update dialog if new version found
        if self.main_config['update']:
            dialog = wx.MessageDialog(self, message="There is new version, do you want to update?",
                                      caption="New Update Available",
                                      style=wx.YES_NO | wx.YES_DEFAULT,
                                      pos=wx.DefaultPosition)
            response = dialog.ShowModal()
            if response == wx.ID_YES:
                webbrowser.open(self.main_config['update_url'])

    def on_close(self, event):
        log.info("Exiting...")
        # Saving last window size
        parser = self.loaded_modules['main']['parser']  # type: ConfigParser
        size = self.Size
        parser.set('gui_information', 'width', size[0])
        parser.set('gui_information', 'height', size[1])
        parser.write(open(self.loaded_modules['main']['file'], 'w'))
        self.Destroy()

    def on_right_down(self, event):
        log.info(event)
        event.Skip()

    def on_settings(self, event):
        log.debug("Got event from {0}".format(IDS[event.GetId()]))
        module_groups = IDS[event.GetId()].split(MODULE_KEY)
        settings_category = MODULE_KEY.join(module_groups[1:-1])
        settings_menu_id = id_renew(settings_category, update=True)
        if self.settings_window:
            self.settings_window.SetFocus()
        else:
            self.settings_window = SettingsWindow(self,
                                                  id=settings_menu_id,
                                                  title=translate_key('settings'),
                                                  size=(700, 400),
                                                  main_class=self,
                                                  categories=self.sorted_categories)

    def button_clicked(self, event):
        button_id = event.GetId()
        keys = IDS[event.GetId()].split(MODULE_KEY)
        log.debug("[ChatGui] Button clicked: {0}, {1}".format(keys, button_id))
        event.Skip()

    def on_toolbar_button(self, event):
        button_id = event.GetId()
        list_keys = IDS[event.GetId()].split(MODULE_KEY)
        log.debug("[ChatGui] Toolbar clicked: {0}, {1}".format(list_keys, button_id))
        if list_keys[0] in self.loaded_modules:
            self.loaded_modules[list_keys[0]]['class'].gui_button_press(self, event, list_keys)
        else:
            for module, settings in self.loaded_modules.items():
                if 'class' in settings:
                    settings['class'].gui_button_press(self, event, list_keys)
        event.Skip()


class GuiThread(threading.Thread):
    title = 'LalkaChat'
    url = 'http://localhost'
    port = '8080'

    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.gui = None
        self.kwargs = kwargs
        if 'webchat' in self.kwargs.get('loaded_modules'):
            self.port = self.kwargs['loaded_modules']['webchat']['port']

    def run(self):
        chromectrl.Initialize()
        url = ':'.join([self.url, str(self.port)])
        app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
        self.gui = ChatGui(None, "LalkaChat", url, **self.kwargs)  # A Frame is a top-level window.
        app.MainLoop()
        self.quit()

    def quit(self):
        try:
            self.gui.on_close('event')
        except wx.PyDeadObjectError:
            pass
        os._exit(0)
