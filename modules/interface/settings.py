import collections
import logging

import wx

from modules.helper.functions import find_by_type
from modules.helper.module import BaseModule
from modules.helper.parser import return_type
from modules.helper.system import WINDOWS, MODULE_KEY, get_key, translate_key
from modules.interface import TRANSPARENCY_MULTIPLIER
from modules.interface.types import LCObject, LCPanel, deep_get

log = logging.getLogger('settings')

INFORMATION_TAG = 'gui_information'
SKIP_TAGS = [INFORMATION_TAG]


def hide_sizer_items(page_sizer):
    for index, child in enumerate(page_sizer.GetChildren()):
        page_sizer.Hide(index)


class SettingsKeyError(Exception):
    pass


class CategoryKeyError(Exception):
    pass


class ModuleKeyError(Exception):
    pass


class SettingsWindow(wx.Frame):
    main_grid = None
    page_list = []
    selected_cell = None

    def __init__(self, *args, **kwargs):
        self.spacer_size = (0, 10)
        self.main_class = kwargs.pop('main_class')
        self.categories = kwargs.pop('categories')  # type: dict

        wx.Frame.__init__(self, *args, **kwargs)

        self.settings_saved = True
        self.tree_ctrl = None
        self.tree_ctrl_image_dict = {}
        self.tree_ctrl_ids = {}
        self.content_page = None
        self.content_sizer = None
        self.buttons_sizer = None

        self.special_settings = {
            get_key('main', 'gui', 'show_hidden'): self.process_hidden,
            get_key('main', 'gui', 'show_counters'): self.process_counters,
            get_key('main', 'gui', 'on_top'): self.process_on_top,
            get_key('main', 'gui', 'transparency'): self.process_transparency,
            get_key('messaging', 'messaging'): self.process_text_module_change
        }
        self.special_settings.update({
            get_key(module, 'system', 'enabled'): self.toggle_module for module in self.categories['messaging']
        })

        self.sizer_dict = {}
        self.changes = {}
        self.buttons = {}
        self.list_map = {}
        self.redraw_map = {}

        self.show_icons = self.main_class.main_module.get_config('gui', 'show_icons')

        # Setting up the window
        if WINDOWS:
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

    def on_change(self, key, value, item_type=None, section=False):
        def enable_button():
            self.buttons['apply'].Enable()

        def compare_2d_lists(list1, list2):
            return not set(map(tuple, list1)) ^ set(map(tuple, list2))

        def apply_changes():
            self.changes[key] = {'value': value, 'type': item_type}
            self.buttons['apply'].Enable()

        def clear_changes(remote_change=None):
            if key in self.changes:
                self.changes.pop(key)
            if remote_change:
                for change in self.changes.keys():
                    if remote_change in change:
                        self.changes.pop(change)
            if not self.changes:
                self.buttons['apply'].Disable()

        split_keys = key.split(MODULE_KEY)
        module_name = split_keys[0]
        panel_key_list = split_keys[1:-1]
        config_section_name = split_keys[-1]

        redraw_item = self.redraw_map.get(get_key(module_name, *panel_key_list), {})
        for section_name, section_config in redraw_item.items():
            if config_section_name in section_config['redraw_trigger']:
                redraw_key = MODULE_KEY.join(section_config['key'])
                self.redraw_item(section_config, value)
                clear_changes(redraw_key)
                enable_button()
        config_item = self.main_class.loaded_modules[module_name].get_config(*split_keys[1:])

        if section:
            check = config_item.value if isinstance(config_item, LCObject) else config_item
            if isinstance(value, list):
                apply_changes() if set(check) != set(value) else clear_changes()
            else:
                if check != return_type(value):
                    apply_changes()
                else:
                    clear_changes()
        elif item_type == 'gridbox':
            if compare_2d_lists(value, config_item.simple()):
                clear_changes()
            else:
                apply_changes()
        else:
            test_value = value if isinstance(value, bool) else return_type(value)
            if config_item.simple() != test_value:
                apply_changes()
            else:
                clear_changes()

    def on_tree_ctrl_changed(self, event):
        self.settings_saved = False
        tree_ctrl = event.EventObject  # type: wx.TreeCtrl
        selection = tree_ctrl.GetFocusedItem()
        selection_text = tree_ctrl.GetItemData(selection)
        key_list = selection_text.split(MODULE_KEY)

        # Drawing page
        self.fill_page_with_content(self.content_page, key_list)

        event.Skip()

    def get_tree_item(self, key, node, image=-1, name_key=None, enabled=True):
        tree_item_id = self.tree_ctrl.AppendItem(
            node, translate_key(name_key if name_key else key),
            data=key, image=image)
        item_color = self.tree_ctrl.GetItemTextColour(tree_item_id)
        if not enabled:
            self.tree_ctrl.SetItemTextColour(tree_item_id, wx.Colour('gray'))
        self.tree_ctrl_ids[name_key] = {'id': tree_item_id, 'color': item_color}
        return tree_item_id

    def create_layout(self):
        self.main_grid = wx.BoxSizer(wx.HORIZONTAL)
        style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_TWIST_BUTTONS | wx.TR_NO_LINES
        # style = wx.TR_HAS_BUTTONS | wx.TR_SINGLE | wx.TR_HIDE_ROOT

        image_list = wx.ImageList(16, 16)

        self.tree_ctrl = wx.TreeCtrl(self, style=style, size=wx.Size(230, -2))
        root_key = get_key('settings', 'tree', 'root')
        root_node = self.tree_ctrl.AddRoot(translate_key(root_key))
        for cat_name, category in self.categories.items():
            item_node = self.get_tree_item(get_key('settings', cat_name), root_node, name_key=cat_name)
            for module_name, module in category.items():
                if module_name == cat_name:
                    continue
                if '.' in module_name:
                    continue

                config = module.get_config()
                if config.icon:
                    icon = wx.Bitmap(config.icon)
                    self.tree_ctrl_image_dict[module_name] = image_list.GetImageCount()
                    image_list.Add(icon)
                else:
                    self.tree_ctrl_image_dict[module_name] = -1

                module_node = self.get_tree_item(
                    get_key('settings', cat_name, module_name),
                    item_node, name_key=module_name,
                    image=self.tree_ctrl_image_dict[module_name], enabled=module.enabled
                )

                tree_nodes = self._get_panels(config)
                if not tree_nodes:
                    continue
                self.create_nested_tree_item(tree_nodes, node=module_node,
                                             key=get_key('settings', cat_name, module_name))

        if self.show_icons:
            self.tree_ctrl.AssignImageList(image_list)
        self.tree_ctrl.ExpandAll()

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_ctrl_changed, id=self.tree_ctrl.Id)

        self.main_grid.Add(self.tree_ctrl, 0, wx.EXPAND | wx.ALL, 7)

        self.content_page = wx.Panel(self)
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)

        config_grid = wx.BoxSizer(wx.VERTICAL)
        self.buttons_sizer = self.create_page_buttons(self.content_page)
        config_grid.Add(self.content_sizer, 1, wx.EXPAND)
        config_grid.Add(self.buttons_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
        self.content_page.SetSizer(config_grid)

        self.main_grid.Add(self.content_page, 15, wx.EXPAND)
        self.main_grid.Layout()
        self.SetSizer(self.main_grid)
        self.tree_ctrl.SelectItem(self.tree_ctrl.GetFirstChild(root_node)[0])

    def fill_page_with_content(self, panel, keys):

        if keys[0] != 'settings':
            raise SettingsKeyError("Key is not for settings GUI")

        if keys[1] not in self.categories:
            raise CategoryKeyError("Key not found in categories")

        category = keys[1]
        module_id = keys[1] if not keys[2:] else MODULE_KEY.join(keys[2:])

        if module_id not in self.categories[category]:
            raise ModuleKeyError("Key not found in modules")

        module_item = self.categories[category][module_id]
        if isinstance(module_item, BaseModule):
            custom_renderer = module_item.custom_render
            module_config = module_item.get_config()
            module_gui_config = module_item.conf_params.get('gui', {})
        else:
            custom_renderer = False
            module_config = module_item.get('config', {})
            module_gui_config = module_item.get('gui', {})
            module_item = self.categories[category][keys[1]]

        if module_id not in self.sizer_dict:
            module_sizer = wx.BoxSizer(wx.VERTICAL)
            if custom_renderer:
                module_item.render(sizer=module_sizer, panel=panel)
            else:
                self.create_page(sizer=module_sizer, panel=panel, config=module_config, module=module_item,
                                 gui=module_gui_config, key=module_id.split(MODULE_KEY))
            hide_sizer_items(module_sizer)
            self.sizer_dict[module_id] = module_sizer

        # page_sizer.Add(self.buttons_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        page_sizer = self.content_sizer  # type: wx.Sizer
        hide_sizer_items(page_sizer)
        found = False
        for index, child in enumerate(page_sizer.GetChildren()):
            if self.sizer_dict[module_id] == child.GetSizer():
                page_sizer.Show(index)
                found = True
                break
        if not found:
            page_sizer.Add(self.sizer_dict[module_id], 1, wx.EXPAND)
            page_sizer.Show(page_sizer.GetItemCount() - 1)

        page_sizer.Layout()
        panel.Layout()

    def create_page(self, sizer, panel, config, module, gui, key):
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        page_subitem_sizer = wx.BoxSizer(wx.VERTICAL)
        self.create_page_items(page_subitem_sizer, panel, config, module, gui, key)
        page_sizer.Add(page_subitem_sizer, 1, wx.EXPAND)
        sizer.Add(page_sizer, 1, wx.EXPAND)

    def create_page_items(self, page_sizer, panel, config, module, gui, key):
        page_sc_window = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        page_sc_window.SetScrollbars(5, 5, 10, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)
        joined_keys = MODULE_KEY.join(key)
        if gui and 'redraw' in gui:
            for redraw_target, redraw_settings in gui['redraw'].items():
                if joined_keys not in self.redraw_map:
                    self.redraw_map[joined_keys] = {}
                self.redraw_map[joined_keys][redraw_target] = {
                    'key': None,
                    'item': None,
                    'redraw_type': None,
                    'redraw_trigger': redraw_settings['redraw_trigger'],
                    'redraw_target': redraw_target,
                    'get_config': redraw_settings['get_config'],
                    'get_gui': redraw_settings['get_gui'],
                    'sizer_parent': sizer,
                    'panel_parent': page_sc_window,
                    'all_settings': redraw_settings,
                    'module': module
                }

        for section_key, section_item in config.items():
            if section_key in SKIP_TAGS:
                continue

            if not self.show_hidden:
                if section_item.hidden:
                    continue

            gui_settings = gui.get(section_key, {}).copy() if gui else {}
            item_keys = key + [section_key]
            sizer_item = section_item.create_ui(
                parent=self, panel=page_sc_window, gui=gui_settings,
                key=item_keys, show_hidden=self.show_hidden, module=module
            )
            if isinstance(sizer_item, dict):
                sizer_item = sizer_item['item']

            if joined_keys in self.redraw_map.keys():
                if section_key in self.redraw_map[joined_keys]:
                    self.redraw_map[joined_keys][section_key].update({
                        'bind_item': section_item,
                        'item': sizer_item,
                        'redraw_type': type(section_item),
                        'key': item_keys,
                    })

            sizer.Add(sizer_item, 0, wx.EXPAND)

        page_sc_window.SetSizer(sizer)
        page_sizer.Add(page_sc_window, 1, wx.EXPAND)

    def create_page_buttons(self, panel):
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, label=translate_key(MODULE_KEY.join(['settings', 'ok_button'])))
        ok_button.Bind(wx.EVT_BUTTON, self.button_ok)
        self.buttons['ok'] = ok_button

        apply_button = wx.Button(panel, label=translate_key(MODULE_KEY.join(['settings', 'apply_button'])))
        apply_button.Bind(wx.EVT_BUTTON, self.button_apply)
        apply_button.Disable()
        self.buttons['apply'] = apply_button

        cancel_button = wx.Button(panel, label=translate_key(MODULE_KEY.join(['settings', 'cancel_button'])))
        cancel_button.Bind(wx.EVT_BUTTON, self.button_cancel)
        self.buttons['cancel'] = cancel_button

        button_sizer.Add(ok_button, 0, wx.ALIGN_RIGHT)
        button_sizer.Add(apply_button, 0, wx.ALIGN_RIGHT)
        button_sizer.Add(cancel_button, 0, wx.ALIGN_RIGHT)
        return button_sizer

    def redraw_item(self, redraw_keys, redraw_value):
        sizer = redraw_keys['item']
        sizer_parent = redraw_keys['sizer_parent']
        key = redraw_keys['key']

        kwargs = {
            'value': redraw_keys['get_config'](redraw_value, keys=redraw_keys),
            'gui': redraw_keys['get_gui'](redraw_value),
            'panel': redraw_keys['panel_parent'],
            'bind': redraw_keys['bind_item'].bind,
            'module': redraw_keys['module']
        }

        static_box = None

        if isinstance(sizer, wx.StaticBoxSizer):
            static_box = sizer.GetStaticBox()

        item_index = 0
        self.detach_all_children(sizer)
        for index, item_sizer in enumerate(sizer_parent.GetChildren()):
            if item_sizer.GetSizer() == sizer:
                item_index = index
                sizer_parent.Detach(index)
        if static_box:
            static_box.Destroy()
        sizer.Destroy()

        fnc = redraw_keys['bind_item'].create_ui
        new_sizer = fnc(parent=self, item=redraw_keys['redraw_target'], key=key, **kwargs)
        sizer_parent.Insert(index=item_index, sizer=new_sizer['item'], flag=wx.EXPAND)

        self.redraw_map[get_key(*key[:-1])][key[-1]]['item'] = new_sizer['item']

        self.main_grid.Layout()

    def detach_all_children(self, sizer):
        if not sizer:
            return
        for index, child in reversed(list(enumerate(sizer.GetChildren()))):
            child_item = child.GetSizer()
            if not child_item:
                continue
            elif child_item.GetChildren():
                self.detach_all_children(child_item)
            sizer.Remove(index)

    def apply_settings(self):
        if self.save_settings():
            log.debug('Got non-dynamic changes')
            dialog = wx.MessageDialog(self,
                                      message=translate_key(MODULE_KEY.join(['main', 'save', 'non_dynamic'])),
                                      caption='Restart Warning',
                                      style=wx.OK_DEFAULT | wx.ICON_WARNING,
                                      pos=wx.DefaultPosition)
            dialog.ShowModal()

    def button_ok(self, event):
        self.apply_settings()
        self.on_exit(event)

    def button_apply(self, event):
        self.apply_settings()
        event.Skip()

    def button_cancel(self, event):
        self.on_close(event)

    def save_settings(self):
        dynamic_check = False
        for module_name in self.main_class.loaded_modules.keys():
            change_list = {}
            for item, change in self.changes.items():
                if module_name == item.split(MODULE_KEY)[0]:
                    change_list[item] = change
            for key in change_list.keys():
                self.changes.pop(key)

            if self.save_module(module_name, change_list):
                dynamic_check = True
        self.buttons['apply'].Disable()
        return dynamic_check

    def save_module(self, module_name, changed_items):
        non_dynamic_check = False
        if changed_items:
            module_item = self.main_class.loaded_modules.get(module_name, {})
            non_dynamic = module_item.conf_params.get('gui', {}).get('non_dynamic', [])
            module_config = module_item.get_config()

            for item, change in changed_items.items():
                item_split = item.split(MODULE_KEY)
                if item_split[-1] in ['list_box']:
                    del item_split[-1]

                section = item_split[-2]
                item_name = item_split[-1]

                deep_config = deep_get(module_config, *item_split[1:-1])
                for d_item in non_dynamic:
                    if section in d_item:
                        if MODULE_KEY.join([section, '*']) in d_item:
                            non_dynamic_check = True
                            break
                        elif MODULE_KEY.join([section, item_name]) in d_item:
                            non_dynamic_check = True
                            break

                old_value = deep_config[item_name].value
                deep_config[item_name].value = change['value']
                self.apply_custom_gui_settings(item, new=change['value'], old=old_value)
            module_item.apply_settings(changes=changed_items)
        return non_dynamic_check

    @staticmethod
    def _get_panels(module_settings):
        return find_by_type(module_settings, LCPanel)

    def create_nested_tree_item(self, tree_item, node=None, key=None):
        for name, data in tree_item.items():
            category, module_name = key.split(MODULE_KEY)[1:3]
            key_left = key.split(MODULE_KEY)[3:]
            full_key_list = key_left + [name]
            key_string = get_key(module_name, *full_key_list)

            node_l = self.get_tree_item(get_key(key, name), node,
                                        name_key=get_key(key, name))
            if isinstance(data, collections.Mapping):
                self.create_nested_tree_item(data, node_l, get_key(key, name))

            if key_string in self.categories[category]:
                continue

            panel_data = deep_get(self.categories[category][module_name].get_config(), *full_key_list)
            gui_data = deep_get(self.categories[category][module_name].conf_params['gui'], *full_key_list)
            self.categories[category][key_string] = {}
            self.categories[category][key_string]['config'] = panel_data
            self.categories[category][key_string]['gui'] = gui_data

    def apply_custom_gui_settings(self, key, new, old):
        if key in self.special_settings:
            self.special_settings[key](new=new, old=old, key=key)
        self.main_class.status_frame.refresh_labels()

    def process_hidden(self, new, **kwargs):
        self.show_hidden = new

    def process_counters(self, new, **kwargs):
        if self.main_class.status_frame.chat_count:
            self.main_class.status_frame.is_shown(new)
        else:
            self.main_class.status_frame.is_shown(False)

    def process_on_top(self, new, **kwargs):
        if new:
            style = self.main_class.styles | wx.STAY_ON_TOP
        else:
            style = self.main_class.styles ^ wx.STAY_ON_TOP
        self.main_class.styles = style
        self.main_class.SetWindowStyle(style)

    def process_transparency(self, new, **kwargs):
        self.main_class.SetTransparent((100 - new) * TRANSPARENCY_MULTIPLIER)

    def process_text_module_change(self, new, old, **kwargs):
        delta = set(old).symmetric_difference(set(new))

        for item in delta:
            if item in new:
                self.toggle_module(True, item)
            else:
                self.toggle_module(False, item)
            [self.sizer_dict.pop(module) for module in self.sizer_dict.keys() if module.startswith(item)]

    def toggle_module(self, new, key, **kwargs):
        module = key.split(MODULE_KEY)[0]
        module_class = self.main_class.loaded_modules[module]
        messaging_list = self.main_class.loaded_modules['messaging'].config['messaging'].value

        if new:
            titem = self.tree_ctrl_ids[module]
            self.tree_ctrl.SetItemTextColour(titem['id'], titem['color'])
            module_class.enable()
            if module not in messaging_list:
                messaging_list.append(module)
        else:
            self.tree_ctrl.SetItemTextColour(self.tree_ctrl_ids[module]['id'], wx.Colour('gray'))
            module_class.disable()
            if module in messaging_list:
                messaging_list.remove(module)
        self.main_class.loaded_modules['messaging'].config['messaging'].value = messaging_list
        if 'messaging' in self.sizer_dict:
            self.sizer_dict.pop('messaging')
