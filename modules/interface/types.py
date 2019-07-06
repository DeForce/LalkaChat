import collections
from builtins import object

from functools import reduce

import wx
import wx.grid
from collections import OrderedDict

import logging

from modules.helper.system import translate_key, MODULE_KEY
from modules.interface.controls import KeyChoice, CustomColourPickerCtrl, KeyListBox, KeyCheckListBox

log = logging.getLogger('interface/types')
LEFT_BORDER = 5
TEXT_BORDER = 20


def dict_instance(d):
    return isinstance(d, (collections.Mapping, LCDict))


def deep_get(dictionary, *keys):
    return reduce(lambda d, key: d.get(key, None) if dict_instance(d) else None, keys, dictionary)


class DualGridDict(OrderedDict):
    pass


class LCObject(object):
    def __init__(self, value=None, always_on=False, hidden=False, *args, **kwargs):
        self._value = value

        self.key = None
        self.parent = None
        self.module = None

        self._enabled = True
        self._hidden = hidden
        self._always_on = always_on

        self.wx_controls = {}

        self.properties = ['always_on']

    def __bool__(self):
        return bool(self._value)

    def __len__(self):
        return self._value.__len__()

    def __contains__(self, item):
        return item in self._value

    def __repr__(self):
        return self._value.__repr__()

    def __str__(self):
        return self._value.__str__()

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, value: bool):
        self._hidden = value

    @property
    def enabled(self):
        return self._enabled

    @property
    def always_on(self):
        return self._always_on

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def _create_ui(self, panel=None, key=None, **kwargs):
        raise NotImplementedError(f'create_ui is not implemented in {type(self)}')

    def create_ui(self, **kwargs):
        self.module = kwargs.get('module')
        self._enabled = self.module.enabled
        self.key = MODULE_KEY.join(kwargs.get('key'))
        self.parent = kwargs.get('parent')
        data = self._create_ui(**kwargs)
        self.wx_controls = data
        self.enable() if self.enabled else self.disable()
        return data

    def enable(self):
        if self.wx_controls:
            self._enable()
        self._enabled = True

    def _enable(self):
        pass

    def disable(self):
        if not self._always_on:
            if self.wx_controls:
                self._disable()
            self._enabled = False
        else:
            self.enable()

    def _disable(self):
        pass

    def simple(self):
        return self.value


class LCDict(LCObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = OrderedDict()

    def __bool__(self):
        return bool(self.__len__())

    def __setitem__(self, key, value):
        self._value[key] = value

    def __getitem__(self, item):
        return self._value[item]

    def enable_all(self):
        for item in self._value.values():
            if isinstance(item, LCDict):
                item.enable_all()
            else:
                item.enable()
        self.enable()

    def disable_all(self):
        for item in self._value.values():
            if isinstance(item, LCDict):
                item.disable_all()
            else:
                if not isinstance(item, LCObject):
                    pass
                item.disable()
        self.disable()

    def get(self, key, default=None):
        return self._value.get(key, default)

    def items(self):
        return self._value.items()

    def _create_ui(self, panel=None, key=None, **kwargs):
        pass


class LCPanel(LCDict):
    def __init__(self, icon=None, *args, **kwargs):
        super(LCPanel, self).__init__(*args, **kwargs)
        self.properties += 'icon'
        self.icon = icon

    def _create_ui(self, panel=None, key=None, **kwargs):
        return wx.BoxSizer(wx.VERTICAL)


class LCStaticBox(LCDict):
    def __init__(self, label=True, *args, **kwargs):
        self.label = label
        super().__init__(*args, **kwargs)
        self.properties.append('label')

    def _enable(self):
        if 'box' in self.wx_controls:
            self.wx_controls['box'].Enable()

    def _disable(self):
        fixed_items = [item for item in self.value.values() if item.always_on]
        if 'box' in self.wx_controls and not fixed_items:
            self.wx_controls['box'].Disable()
        else:
            self._enable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        box_kwargs = {}
        if self.label and isinstance(self.label, bool):
            box_kwargs['label'] = translate_key(MODULE_KEY.join(key))
        elif self.label:
            box_kwargs['label'] = translate_key(MODULE_KEY.join(self.label))

        static_box = wx.StaticBox(panel, **box_kwargs)
        static_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        instatic_sizer = wx.BoxSizer(wx.VERTICAL)
        spacer_size = 7

        max_text_size = 0
        text_ctrls = []
        log.debug("Working on %s", MODULE_KEY.join(key))
        spacer = False
        hidden_items = kwargs['gui'].get('hidden', [])

        # Create elements that are child of static-box
        for item, value in self._value.items():
            if not kwargs.get('show_hidden'):
                if value.hidden:
                    continue
                elif item in hidden_items:
                    continue

            item_dict = value.create_ui(panel=static_box, key=key+[item], from_sb=True,
                                        **kwargs)

            if 'text_size' in item_dict:
                if max_text_size < item_dict.get('text_size'):
                    max_text_size = item_dict['text_size']

                text_ctrls.append(item_dict['text_ctrl'])
            spacer = True if not spacer else instatic_sizer.AddSpacer(spacer_size)
            instatic_sizer.Add(item_dict['item'], 0, wx.EXPAND, 5)

        if max_text_size:
            for ctrl in text_ctrls:
                ctrl.SetMinSize((max_text_size, ctrl.GetSize()[1]))

        item_count = instatic_sizer.GetItemCount()
        if not item_count:
            static_sizer.Destroy()
            return {'item': wx.BoxSizer(wx.VERTICAL)}

        static_sizer.Add(instatic_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return {'item': static_sizer, 'box': static_box}


class LCLabel(LCObject):
    def __init__(self, value='', *args, **kwargs):
        super().__init__(str(value), *args, **kwargs)
        self.color = None
        self.def_color = None

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        item_text = wx.StaticText(panel, label=translate_key(self.value))
        self.def_color = item_text.GetForegroundColour()
        if self.color:
            item_text.SetForegroundColour(wx.Colour(self.color))
        item_text.Wrap(250)
        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        return {'item': item_sizer, 'control': item_text}

    def update(self):
        if not self.wx_controls:
            return

        if self.color:
            self.wx_controls['control'].SetForegroundColour(wx.Colour(self.color))
        else:
            self.wx_controls['control'].SetForegroundColour(self.def_color)

    def hide(self, enabled):
        if not self.wx_controls:
            return

        self.wx_controls['control'].Show(not enabled)


class LCText(LCObject):
    def __init__(self, value=None):
        if isinstance(value, int):
            value = str(value)
        elif not isinstance(value, str) and not isinstance(value, LCText):
            raise TypeError(f'LCText should be text, not {type(value)}')

        LCObject.__init__(self, value)

    def simple(self):
        return self._value

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def format(self, *args):
        return self._value.format(*args)

    def bind(self, event):
        log.debug(event)
        text_ctrl = self.wx_controls['control']
        self.parent.on_change(self.key, text_ctrl.GetValue())

    def _enable(self):
        self.wx_controls['control'].Enable()
        self.wx_controls['text_ctrl'].Enable()

    def _disable(self):
        self.wx_controls['control'].Disable()
        self.wx_controls['text_ctrl'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        item_name = MODULE_KEY.join(key)
        item_box = wx.TextCtrl(panel, value=self._value)
        item_box.Bind(wx.EVT_TEXT, self.bind)
        item_text = wx.StaticText(panel, label=translate_key(item_name))
        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        item_sizer.Add(item_box, 1, wx.RIGHT, border=LEFT_BORDER)
        return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text,
                'control': item_box}


class LCColour(LCObject):
    def __init__(self, *args, **kwargs):
        super(LCColour, self).__init__(*args, **kwargs)

    def __repr__(self):
        return str(self._value)

    def __getitem__(self, item):
        return str(self._value)[item]

    def simple(self):
        return self._value

    def startswith(self, value):
        return str(self._value).startswith(value)

    def bind(self, event):
        self.parent.on_change(self.key, event['hex'])

    def _enable(self):
        self.wx_controls['text_ctrl'].Enable()

    def _disable(self):
        self.wx_controls['text_ctrl'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)

        item_name = MODULE_KEY.join(key)
        colour_picker = CustomColourPickerCtrl()
        item_box = colour_picker.create(panel, value=self._value, event=self.bind, key=key)

        item_text = wx.StaticText(panel, label=translate_key(item_name))
        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        item_sizer.Add(item_box, 1, wx.EXPAND)
        return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


class LCBool(LCObject):
    _value = bool

    def __init__(self, value, *args, **kwargs):
        super(LCBool, self).__init__(value, *args, **kwargs)

    def __repr__(self):
        return str(self._value)

    def simple(self):
        return bool(self)

    def bind(self, event):
        log.debug(event)
        control = self.wx_controls['control']
        self.parent.on_change(self.key, control.IsChecked())

    def _enable(self):
        self.wx_controls['control'].Enable()

    def _disable(self):
        self.wx_controls['control'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        style = wx.ALIGN_CENTER_VERTICAL
        item_key = MODULE_KEY.join(key)
        checkbox = wx.CheckBox(panel, label=translate_key(item_key), style=style)
        checkbox.SetValue(bool(self._value))
        checkbox.Bind(wx.EVT_CHECKBOX, self.bind)
        item_sizer.Add(checkbox, 0, wx.ALIGN_LEFT)
        return {'item': item_sizer, 'control': checkbox}


class LCList(LCObject):
    def __init__(self, value=(), addable=True, *args, **kwargs):
        super(LCList, self).__init__(value, *args, **kwargs)

        self.selected = None
        self.addable = addable
        self.bind_map = {}
        self.properties.append('addable')

    def __iter__(self):
        return self.value.__iter__()

    def _enable(self):
        if self.addable:
            self.wx_controls['add'].Enable()
            self.wx_controls['remove'].Enable()
            self.wx_controls['input'].Enable()
        self.wx_controls['control'].Enable()

    def _disable(self):
        if self.addable:
            self.wx_controls['add'].Disable()
            self.wx_controls['remove'].Disable()
            self.wx_controls['input'].Disable()
        self.wx_controls['control'].Disable()

    def simple(self):
        return list(self._value)

    def update_ui(self, rows, list_box, elements):
        max_rows = 7
        if rows <= max_rows:
            list_box.SetMinSize((-1, -1))
            self.parent.content_page.GetSizer().Layout()
        else:
            scroll_size = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
            max_size = self.parent.list_map.get(self.key)
            if max_size:
                list_box.SetMinSize((max_size[0] + scroll_size, max_size[1]))
                list_box.SetSize((max_size[0] + scroll_size, max_size[1]))
            else:
                max_size = (list_box.GetBestSize()[0], list_box.GetDefaultRowSize()*max_rows)
                list_box.SetMinSize((max_size[0], max_size[1]))
                list_box.SetSize((max_size[0], max_size[1]))
            self.parent.content_page.GetSizer().Layout()
        if rows == max_rows:
            self.parent.list_map[self.key] = list_box.GetBestSize()
        self.parent.on_change(self.key, elements, item_type='gridbox')

    def bind_add(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']
        list_input = self.wx_controls['input']
        list_input_value = list_input.GetValue().strip()

        row_count = list_box.GetNumberRows()
        row_values = [list_box.GetCellValue(f_row, 0).lower() for f_row in range(0, row_count)]
        if list_input_value.lower() not in row_values:
            list_box.AppendRows(1)
            list_box.SetCellValue(row_count, 0, list_input_value)

        list_input.SetValue('')

        rows = list_box.GetNumberRows()
        grid_elements = OrderedDict.fromkeys([list_box.GetCellValue(row, 0) for row in range(rows)]).keys()
        self.update_ui(rows, list_box, grid_elements)

    def bind_remove(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']
        top = list_box.GetSelectionBlockTopLeft()
        bot = list_box.GetSelectionBlockBottomRight()
        if top and bot:
            top = top[0][0]
            bot = bot[0][0] + 1
            del_rows = range(top, bot) if top < bot else range(bot, top)
        else:
            del_rows = [self.selected[0]]

        if list_box.GetNumberRows():
            ids_deleted = 0
            for select in del_rows:
                list_box.DeleteRows(select - ids_deleted)
                ids_deleted += 1

        rows = list_box.GetNumberRows()
        grid_elements = OrderedDict.fromkeys([list_box.GetCellValue(row, 0) for row in range(rows)]).keys()
        self.update_ui(rows, list_box, grid_elements)

    def bind_select(self, event):
        self.selected = (event.GetRow(), event.GetCol())

    def bind_edit(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']
        rows = list_box.GetNumberRows()
        grid_elements = OrderedDict.fromkeys([list_box.GetCellValue(row, 0) for row in range(rows)]).keys()
        self.update_ui(rows, list_box, grid_elements)

    def _create_ui(self, panel=None, key=None, **kwargs):
        style = wx.ALIGN_CENTER_VERTICAL
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        item_sizer = wx.BoxSizer(wx.VERTICAL)

        static_label = MODULE_KEY.join(key)
        static_text = wx.StaticText(panel, label=f'{translate_key(static_label)}:', style=wx.ALIGN_RIGHT)
        item_sizer.Add(static_text)

        input_ctrl = None
        inputs = {}
        addable_sizer = wx.BoxSizer(wx.HORIZONTAL) if self.addable else None
        if addable_sizer:
            input_ctrl = wx.TextCtrl(panel)
            addable_sizer.Add(input_ctrl, 0, style)

            item_apply_key = MODULE_KEY.join(key + ['list_add'])
            item_apply = wx.Button(panel, label=translate_key(item_apply_key))
            inputs['add'] = item_apply
            addable_sizer.Add(item_apply, 0, style)
            item_apply.Bind(wx.EVT_BUTTON, self.bind_add, id=item_apply.Id)

            item_remove_key = MODULE_KEY.join(key + ['list_remove'])
            item_remove = wx.Button(panel, label=translate_key(item_remove_key))
            inputs['remove'] = item_remove
            addable_sizer.Add(item_remove, 0, style)
            item_remove.Bind(wx.EVT_BUTTON, self.bind_remove, id=item_remove.Id)

            item_sizer.Add(addable_sizer, 0, wx.EXPAND)

        list_box = wx.grid.Grid(panel)
        list_box.CreateGrid(0, 1)
        list_box.DisableDragColSize()
        list_box.DisableDragRowSize()
        list_box.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.bind_select)
        list_box.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.bind_edit)

        for index, item in enumerate(self._value):
            list_box.AppendRows(1)
            list_box.SetCellValue(index, 0, item)

        list_box.SetColLabelSize(1)
        list_box.SetRowLabelSize(1)

        max_rows = 7
        if addable_sizer:
            col_size = addable_sizer.GetMinSize()[0] - 2
            list_box.SetDefaultColSize(col_size, resizeExistingCols=True)
            if list_box.GetNumberRows() > max_rows:
                scroll_size = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                max_size = wx.Size(list_box.GetBestSize()[0], list_box.GetDefaultRowSize() * max_rows)
                list_box.SetMinSize((max_size[0] + scroll_size, max_size[1]))
                list_box.SetSize((max_size[0] + scroll_size, max_size[1]))
        else:
            list_box.AutoSize()

        item_sizer.Add(list_box)

        border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return_dict = {'item': border_sizer, 'control': list_box, 'input': input_ctrl}
        return_dict.update(inputs)
        return return_dict


class LCButton(LCObject):
    def __init__(self, fnc=None, *args, **kwargs):
        self.function = fnc if fnc else self.pass_function
        super(LCButton, self).__init__(value=str(fnc), *args, **kwargs)

    def __repr__(self):
        return str(self._value)

    def bind(self, event):
        pass

    def pass_function(self):
        pass

    def _create_ui(self, panel=None, key=None, parent=None, enabled=True, **kwargs):
        item_sizer = wx.BoxSizer(wx.VERTICAL)
        item_name = MODULE_KEY.join(key)
        c_button = wx.Button(panel, label=translate_key(item_name))
        if not enabled:
            c_button.Disable()

        if item_name in parent.buttons:
            parent.buttons[item_name].append(c_button)
        else:
            parent.buttons[item_name] = [c_button]

        # TODO: Implement button function pressing
        c_button.Bind(wx.EVT_BUTTON, self.function, id=c_button.Id)

        item_sizer.Add(c_button)
        return {'item': item_sizer}


class LCSpin(LCObject):
    def __init__(self, value, min_v=0, max_v=100, *args, **kwargs):
        super(LCSpin, self).__init__(value, *args, **kwargs)
        self.min = min_v
        self.max = max_v

    def __repr__(self):
        return str(self._value)

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def simple(self):
        return int(self.value)

    def bind(self, event):
        log.debug(event)

        spin_ctrl = self.wx_controls['control']
        self.parent.on_change(self.key, spin_ctrl.GetValue())

    def _enable(self):
        self.wx_controls['text_ctrl'].Enable()
        self.wx_controls['control'].Enable()

    def _disable(self):
        self.wx_controls['text_ctrl'].Disable()
        self.wx_controls['control'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        item_name = MODULE_KEY.join(key)
        style = wx.ALIGN_LEFT
        item_box = wx.SpinCtrl(panel, min=self.min, max=self.max,
                               initial=self._value, style=style)
        item_box.Bind(wx.EVT_SPINCTRL, self.bind)
        item_box.Bind(wx.EVT_TEXT, self.bind)
        item_text = wx.StaticText(panel, label=translate_key(item_name))
        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        item_sizer.Add(item_box)
        return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text,
                'control': item_box}


class LCSlider(LCObject):
    def __init__(self, value, min_v=0, max_v=100, *args, **kwargs):
        super(LCSlider, self).__init__(value, *args, **kwargs)
        self.min = min_v
        self.max = max_v

    def __repr__(self):
        return str(self._value)

    def __int__(self):
        return self._value

    def __mul__(self, other):
        return self._value * other

    def simple(self):
        return int(self._value)

    def bind(self, event):
        spin_ctrl = event.EventObject
        self.parent.on_change(self.key, spin_ctrl.GetValue())

    def _enable(self):
        self.wx_controls['control'].Enable()

    def _disable(self):
        self.wx_controls['control'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        item_name = MODULE_KEY.join(key)
        style = wx.SL_VALUE_LABEL | wx.SL_AUTOTICKS
        item_box = wx.Slider(panel, minValue=self.min, maxValue=self.max,
                             value=self._value, style=style)
        freq = (self.max - self.min) / 5
        item_box.SetTickFreq(freq)
        item_box.SetLineSize(4)
        item_box.Bind(wx.EVT_SCROLL, self.bind)
        item_text = wx.StaticText(panel, label=translate_key(item_name))
        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        item_sizer.Add(item_box, 1, wx.EXPAND | wx.RIGHT, border=LEFT_BORDER)
        return {'item': item_sizer, 'control': item_box}


class LCDropdown(LCObject):
    def __init__(self, value, available_list=(), *args, **kwargs):
        super(LCDropdown, self).__init__(value, *args, **kwargs)
        self.list = available_list

    def __repr__(self):
        return self._value

    def simple(self):
        return str(self._value)

    def bind(self, event):
        log.debug(event)

        control = self.wx_controls['control']
        self.parent.on_change(
            self.key,
            control.get_key_from_index(control.GetCurrentSelection()))

    def _enable(self):
        self.wx_controls['control'].Enable()

    def _disable(self):
        self.wx_controls['control'].Disable()

    def _create_ui(self, panel=None, key=None, **kwargs):
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        choices = list(self.list)
        translated_choices = [translate_key(item) for item in choices]
        item_name = MODULE_KEY.join(key)
        item_text = wx.StaticText(panel, label=translate_key(item_name))
        item_box = KeyChoice(panel, keys=choices, choices=translated_choices)
        item_box.Bind(wx.EVT_CHOICE, self.bind)
        if str(self._value) in choices:
            item_box.SetSelection(choices.index(str(self._value)))
        else:
            item_box.SetSelection(0)

        item_sizer.Add(item_text, 0, wx.ALIGN_CENTER | wx.RIGHT, TEXT_BORDER)
        item_sizer.Add(item_box)
        return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text,
                'control': item_box}


class LCGridDual(LCObject):
    def __init__(self, value=None, addable=True, *args, **kwargs):
        if value is None:
            value = OrderedDict()
        super(LCGridDual, self).__init__(value, *args, **kwargs)
        self.addable = addable
        self.selected = None

    def simple(self):
        return self._value

    def update_ui(self, rows, list_box, elements):
        max_rows = 7
        if rows <= max_rows:
            list_box.SetMinSize((-1, -1))
            self.parent.content_page.GetSizer().Layout()
        else:
            scroll_size = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
            max_size = self.parent.list_map.get(self.key)
            if max_size:
                list_box.SetMinSize((max_size[0] + scroll_size, max_size[1]))
                list_box.SetSize((max_size[0] + scroll_size, max_size[1]))
            else:
                max_size = (list_box.GetBestSize()[0], list_box.GetDefaultRowSize()*max_rows)
                list_box.SetMinSize((max_size[0], max_size[1]))
                list_box.SetSize((max_size[0], max_size[1]))
            self.parent.content_page.GetSizer().Layout()
        if rows == max_rows:
            self.parent.list_map[self.key] = list_box.GetBestSize()
        self.parent.on_change(self.key, elements, item_type='gridbox')

    def _enable(self):
        if self.addable:
            self.wx_controls['input1'].Enable()
            if 'input2' in self.wx_controls:
                self.wx_controls['input2'].Enable()
            self.wx_controls['add'].Enable()
            self.wx_controls['remove'].Enable()
        self.wx_controls['control'].Enable()

    def _disable(self):
        if self.addable:
            self.wx_controls['input1'].Disable()
            if 'input2' in self.wx_controls:
                self.wx_controls['input2'].Disable()
            self.wx_controls['add'].Disable()
            self.wx_controls['remove'].Disable()
        self.wx_controls['control'].Disable()

    def bind_add(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']
        list_input = self.wx_controls['input1']
        list_input_value = list_input.GetValue().strip()

        row_count = list_box.GetNumberRows()
        row_values = [list_box.GetCellValue(f_row, 0).lower() for f_row in range(0, row_count)]
        if list_input_value.lower() not in row_values:
            list_box.AppendRows(1)
            list_box.SetCellValue(row_count, 0, list_input_value)

        list_input2 = self.wx_controls['input2']
        list_input2_value = list_input2.GetValue().strip()
        row_values = [list_box.GetCellValue(f_row, 1).lower() for f_row in range(0, row_count)]
        if list_input2_value.lower() not in row_values:
            list_box.SetCellValue(row_count, 1, list_input2_value)

        list_input.SetValue('')
        list_input2.SetValue('')

        rows = list_box.GetNumberRows()
        cols = list_box.GetNumberCols()
        list_box_item = [[list_box.GetCellValue(row, col).strip()
                          for col in range(cols)]
                         for row in range(rows)]
        grid_elements = OrderedDict()
        for (item, value) in list_box_item:
            grid_elements[item] = value

        self.update_ui(rows, list_box, grid_elements)

    def bind_remove(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']
        top = list_box.GetSelectionBlockTopLeft()
        bot = list_box.GetSelectionBlockBottomRight()
        if top and bot:
            top = top[0][0]
            bot = bot[0][0] + 1
            del_rows = range(top, bot) if top < bot else range(bot, top)
        else:
            del_rows = [self.selected[0]]

        if list_box.GetNumberRows():
            ids_deleted = 0
            for select in del_rows:
                list_box.DeleteRows(select - ids_deleted)
                ids_deleted += 1

        rows = list_box.GetNumberRows()
        cols = list_box.GetNumberCols()
        list_box_item = [
            [list_box.GetCellValue(row, col).strip() for col in range(cols)]
            for row in range(rows)]
        grid_elements = OrderedDict()
        for (item, value) in list_box_item:
            grid_elements[item] = value

        self.update_ui(rows, list_box, grid_elements)

    def bind_edit(self, event):
        log.debug(event)

        list_box = self.wx_controls['control']

        rows = list_box.GetNumberRows()
        cols = list_box.GetNumberCols()
        list_box_item = [
            [list_box.GetCellValue(row, col).strip() for col in range(cols)]
            for row in range(rows)]
        grid_elements = OrderedDict()
        for (item, value) in list_box_item:
            grid_elements[item] = value

        self.update_ui(rows, list_box, grid_elements)

    def bind_select(self, event):
        self.selected = (event.GetRow(), event.GetCol())

    def _create_ui(self, panel=None, key=None, **kwargs):
        style = wx.ALIGN_CENTER_VERTICAL
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        item_sizer = wx.BoxSizer(wx.VERTICAL)

        static_label = MODULE_KEY.join(key)
        static_text = wx.StaticText(panel, label=f'{translate_key(static_label)}:', style=wx.ALIGN_RIGHT)
        item_sizer.Add(static_text)

        inputs = {}
        addable_sizer = wx.BoxSizer(wx.HORIZONTAL) if self.addable else None
        if addable_sizer:
            item_input = wx.TextCtrl(panel)
            inputs['input1'] = item_input
            addable_sizer.Add(item_input, 0, style)

            item_input2 = wx.TextCtrl(panel)
            inputs['input2'] = item_input2
            addable_sizer.Add(item_input2, 0, style)

            item_apply_key = MODULE_KEY.join(key + ['list_add'])
            item_apply = wx.Button(panel, label=translate_key(item_apply_key))
            inputs['add'] = item_apply
            addable_sizer.Add(item_apply, 0, style)
            item_apply.Bind(wx.EVT_BUTTON, self.bind_add, id=item_apply.Id)

            item_remove_key = MODULE_KEY.join(key + ['list_remove'])
            item_remove = wx.Button(panel, label=translate_key(item_remove_key))
            inputs['remove'] = item_remove
            addable_sizer.Add(item_remove, 0, style)
            item_remove.Bind(wx.EVT_BUTTON, self.bind_remove, id=item_remove.Id)

            item_sizer.Add(addable_sizer, 0, wx.EXPAND)

        list_box = wx.grid.Grid(panel)
        list_box.CreateGrid(0, 2)
        list_box.DisableDragColSize()
        list_box.DisableDragRowSize()
        list_box.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.bind_select)
        list_box.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.bind_edit)

        for index, (item, item_value) in enumerate(self._value.items()):
            list_box.AppendRows(1)
            list_box.SetCellValue(index, 0, item)
            list_box.SetCellValue(index, 1, item_value)

        list_box.SetColLabelSize(1)
        list_box.SetRowLabelSize(1)

        max_rows = 7
        if addable_sizer:
            col_size = addable_sizer.GetMinSize()[0] - 2
            first_col_size = list_box.GetColSize(0)
            second_col_size = col_size - first_col_size if first_col_size < col_size else -1
            list_box.SetColSize(1, second_col_size)
            if list_box.GetNumberRows() > max_rows:
                scroll_size = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                max_size = wx.Size(list_box.GetBestSize()[0], list_box.GetDefaultRowSize() * max_rows)
                list_box.SetMinSize((max_size[0] + scroll_size, max_size[1]))
                list_box.SetSize((max_size[0] + scroll_size, max_size[1]))
        else:
            list_box.AutoSize()

        item_sizer.Add(list_box)

        border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return_item = {'item': border_sizer, 'control': list_box}
        return_item.update(inputs)
        return return_item


class LCGridSingle(LCList):
    def __init__(self, value=(), *args, **kwargs):
        super(LCGridSingle, self).__init__(value, *args, **kwargs)


class LCChooseSingle(LCObject):
    def __init__(self, value=(), empty_label=False, available_list=(), hidden=(), *args, **kwargs):
        super(LCChooseSingle, self).__init__(value, *args, **kwargs)
        self.list = available_list
        self.multiple = False
        self.keep_extension = kwargs.get('keep_extension', False)
        self.description = kwargs.get('description')
        self.empty_label = empty_label
        self._skip = {item: item == value for item in hidden}
        self.bind_map = {}

    @property
    def skip(self):
        return self._skip

    @skip.setter
    def skip(self, value):
        return

    def simple(self):
        return self.value

    def _enable(self):
        self.wx_controls['control'].Enable()

    def _disable(self):
        self.wx_controls['control'].Disable()

    def __repr__(self):
        return str(self.value)

    def bind_check(self, event):
        log.debug(event)

        item_object = self.wx_controls['control']
        selection = item_object.get_key_from_index(item_object.GetSelection())
        description = translate_key(MODULE_KEY.join([selection, 'description']))

        show_description = self.description

        if isinstance(item_object, KeyListBox):
            self.parent.on_change(self.key, selection, item_type='listbox', section=True)

        if show_description:
            descr_static_text = self.wx_controls['description']
            descr_static_text.SetLabel(description)
            descr_static_text.Wrap(descr_static_text.GetSize()[0])

    def bind_check_change(self, event):
        log.debug(event)

        item = self.wx_controls['control']
        item_ids = item.GetCheckedItems()
        items_values = [item.get_key_from_index(item_id) for item_id in item_ids] + \
                       [item for item, skip in self._skip.items() if skip]
        self.parent.on_change(self.key, items_values, item_type='listbox_check', section=True)

    def _create_ui(self, panel=None, key=None, **kwargs):
        active_item = self._value
        available_items = [item for item in self.list if item not in self.skip]
        translated_items = [translate_key(item) for item in available_items]

        style = wx.LB_SINGLE
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        item_sizer = wx.BoxSizer(wx.VERTICAL)

        static_label = MODULE_KEY.join(key)
        if not self.empty_label:
            static_text = wx.StaticText(panel, label=f'{translate_key(static_label)}:', style=wx.ALIGN_RIGHT)
            item_sizer.Add(static_text)

        item_key = MODULE_KEY.join(key + ['list_box'])
        label_text = translate_key(item_key)
        if label_text:
            item_sizer.Add(wx.StaticText(panel, label=label_text, style=wx.ALIGN_RIGHT))

        item_list_box = KeyListBox(panel, keys=available_items,
                                   choices=translated_items if translated_items else available_items, style=style)
        item_list_box.Bind(wx.EVT_LISTBOX, self.bind_check)

        if active_item not in item_list_box.GetItems():
            if item_list_box.GetItems():
                item_list_box.SetSelection(0)
        else:
            item_list_box.SetSelection(available_items.index(active_item))

        descr_text = None
        if self.description:
            adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
            adv_sizer.Add(item_list_box, 0, wx.EXPAND)

            descr_key = MODULE_KEY.join(key + ['descr_explain'])
            descr_text = wx.StaticText(panel, label=translate_key(descr_key), style=wx.ST_NO_AUTORESIZE)
            adv_sizer.Add(descr_text, 0, wx.EXPAND | wx.LEFT, 10)

            sizes = descr_text.GetSize()
            sizes[0] -= 20
            descr_text.SetMinSize(sizes)
            descr_text.Fit()
            item_sizer.Add(adv_sizer)
        else:
            item_sizer.Add(item_list_box)
        border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return {'item': border_sizer, 'control': item_list_box,
                'description': descr_text}


class LCChooseMultiple(LCChooseSingle):
    def __init__(self, value=(), hidden=None, *args, **kwargs):
        if hidden is None:
            hidden = {}

        super(LCChooseMultiple, self).__init__(value, *args, **kwargs)
        self.multiple = True
        self._skip = {item: item in value for item in hidden}

    @property
    def value(self):
        return self._value + [item for item, value in self._skip.items() if value and item not in self._value]

    @value.setter
    def value(self, value):
        self._value = value

    def simple(self):
        return list(self.value)

    def _enable(self):
        pass

    def _disable(self):
        pass

    def _create_ui(self, panel=None, key=None, **kwargs):
        active_items = self._value
        available_items = [item for item in self.list if item not in self.skip]
        translated_items = [translate_key(item) for item in available_items]

        border_sizer = wx.BoxSizer(wx.VERTICAL)
        item_sizer = wx.BoxSizer(wx.VERTICAL)

        static_label = MODULE_KEY.join(key)
        if not self.empty_label:
            static_text = wx.StaticText(panel, label=f'{translate_key(static_label)}:', style=wx.ALIGN_RIGHT)
            item_sizer.Add(static_text)

        item_key = MODULE_KEY.join(key + ['list_box'])
        label_text = translate_key(item_key)
        if label_text:
            item_sizer.Add(wx.StaticText(panel, label=label_text, style=wx.ALIGN_RIGHT))

        item_list_box = KeyCheckListBox(panel, keys=available_items,
                                        choices=translated_items if translated_items else available_items)
        item_list_box.Bind(wx.EVT_CHECKLISTBOX, self.bind_check_change)
        item_list_box.Bind(wx.EVT_LISTBOX, self.bind_check)

        section_for = active_items
        check_items = [available_items.index(item) for item in section_for if item in available_items]
        item_list_box.SetCheckedItems(check_items)

        descr_text = None
        if self.description:
            adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
            adv_sizer.Add(item_list_box, 0, wx.EXPAND)

            descr_key = MODULE_KEY.join(key + ['descr_explain'])
            descr_text = wx.StaticText(panel, label=translate_key(descr_key), style=wx.ST_NO_AUTORESIZE)
            adv_sizer.Add(descr_text, 0, wx.EXPAND | wx.LEFT, 10)

            sizes = descr_text.GetSize()
            sizes[0] -= 20
            descr_text.SetMinSize(sizes)
            descr_text.Fit()
            item_sizer.Add(adv_sizer)
        else:
            item_sizer.Add(item_list_box)
        border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return {'item': border_sizer, 'control': item_list_box,
                'description': descr_text}


TYPE_TO_LC = {
    OrderedDict: LCStaticBox,
    bool: LCBool,
    str: LCText,
    int: LCText,
    'spin': LCSpin,
    'dropdown': LCDropdown,
    'slider': LCSlider,
    'colour_picker': LCColour,
    'list': LCList,
    'button': LCButton,
    'choose_mult': LCChooseMultiple
}


def alter_data_to_lc_style(data, gui):
    new_data = LCStaticBox()
    for item, value in data.items():
        item_type = gui.get(item, {}).get('view', type(value))
        if item_type not in TYPE_TO_LC:
            new_data[item] = value
        else:
            try:
                new_data[item] = TYPE_TO_LC[item_type](value, **gui.get(item, {}))
            except Exception as exc:
                log.info(exc)
                new_data[item] = value
    return new_data
