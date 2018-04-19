import wx
import wx.grid

from modules.helper.system import MODULE_KEY, translate_key, log
from modules.interface.controls import GuiCreationError, CustomColourPickerCtrl, KeyListBox, KeyCheckListBox, KeyChoice, \
    id_renew
from modules.interface.types import LCPanel


def create_textctrl(panel=None, value=None, key=None, bind=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)
    item_name = MODULE_KEY.join(key)
    item_box = wx.TextCtrl(panel, id=id_renew(item_name, update=True),
                           value=unicode(value.simple()))
    item_box.Bind(wx.EVT_TEXT, bind)
    item_text = wx.StaticText(panel, label=translate_key(item_name))
    item_sizer.Add(item_text, 0, wx.ALIGN_CENTER)
    item_sizer.Add(item_box)
    return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


def create_button(source_class=None, panel=None, key=None, value=None,
                  bind=None, enabled=True, multiple=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.VERTICAL)
    item_name = MODULE_KEY.join(key)
    button_id = id_renew(item_name, update=True, multiple=multiple)
    c_button = wx.Button(panel, id=button_id, label=translate_key(item_name))
    if not enabled:
        c_button.Disable()

    if item_name in source_class.buttons:
        source_class.buttons[item_name].append(c_button)
    else:
        source_class.buttons[item_name] = [c_button]

    if value:
        # TODO: Implement button function pressing
        if callable(value.value):
            c_button.Bind(wx.EVT_BUTTON, value.value, id=button_id)
        c_button.Bind(wx.EVT_BUTTON, bind, id=button_id)
    else:
        c_button.Bind(wx.EVT_BUTTON, bind, id=button_id)

    item_sizer.Add(c_button)
    return {'item': item_sizer}


def create_static_box(source_class, panel=None, value=None,
                      gui=None, key=None, show_hidden=None, **kwargs):
    if isinstance(value, LCPanel):
        return wx.BoxSizer(wx.VERTICAL)
    item_value = value

    static_box = wx.StaticBox(panel, label=translate_key(MODULE_KEY.join(key)))
    static_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
    instatic_sizer = wx.BoxSizer(wx.VERTICAL)
    spacer_size = 7

    max_text_size = 0
    text_ctrls = []
    log.debug("Working on {0}".format(MODULE_KEY.join(key)))
    spacer = False
    hidden_items = gui.get('hidden', [])

    for item, value in item_value.items():
        if item in hidden_items and not show_hidden:
            continue

        view = type(value)
        if view in source_class.controls.keys():
            bind_fn = source_class.controls[view]
        elif callable(value):
            bind_fn = source_class.controls['button']
        else:
            # bind_fn = {'function': create_empty}
            raise GuiCreationError('Unable to create item, bad value map')
        item_dict = bind_fn['function'](source_class=source_class, panel=static_box, item=item,
                                        value=value, key=key + [item],
                                        bind=bind_fn.get('bind'), gui=gui.get(item, {}),
                                        from_sb=True)
        if 'text_size' in item_dict:
            if max_text_size < item_dict.get('text_size'):
                max_text_size = item_dict['text_size']

            text_ctrls.append(item_dict['text_ctrl'])
        spacer = True if not spacer else instatic_sizer.AddSpacer(spacer_size)
        instatic_sizer.Add(item_dict['item'], 0, wx.EXPAND, 5)

    if max_text_size:
        for ctrl in text_ctrls:
            ctrl.SetMinSize((max_text_size + 50, ctrl.GetSize()[1]))

    item_count = instatic_sizer.GetItemCount()
    if not item_count:
        static_sizer.Destroy()
        return wx.BoxSizer(wx.VERTICAL)

    static_sizer.Add(instatic_sizer, 0, wx.EXPAND | wx.ALL, 5)
    return static_sizer


def create_spin(panel=None, value=None, key=None, bind=None, **kwargs):
    item_class = value
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)
    item_name = MODULE_KEY.join(key)
    style = wx.ALIGN_LEFT
    item_box = wx.SpinCtrl(panel, id=id_renew(item_name, update=True),
                           min=item_class.min, max=item_class.max,
                           initial=value.simple(), style=style)
    item_text = wx.StaticText(panel, label=translate_key(item_name))
    item_box.Bind(wx.EVT_SPINCTRL, bind)
    item_box.Bind(wx.EVT_TEXT, bind)
    item_sizer.Add(item_text, 0, wx.ALIGN_CENTER)
    item_sizer.Add(item_box)
    return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


def create_list(panel=None, value=None, key=None, bind=None, gui=None, from_sb=None, **kwargs):
    view = gui.get('view')
    is_dual = True if 'dual' in view else False
    style = wx.ALIGN_CENTER_VERTICAL
    border_sizer = wx.BoxSizer(wx.VERTICAL)
    item_sizer = wx.BoxSizer(wx.VERTICAL)

    static_label = MODULE_KEY.join(key)
    static_text = wx.StaticText(panel, label=u'{}:'.format(translate_key(static_label)), style=wx.ALIGN_RIGHT)
    item_sizer.Add(static_text)

    addable_sizer = wx.BoxSizer(wx.HORIZONTAL) if gui.get('addable') else None
    if addable_sizer:
        item_input_key = MODULE_KEY.join(key + ['list_input'])
        addable_sizer.Add(wx.TextCtrl(panel, id=id_renew(item_input_key, update=True)), 0, style)
        if is_dual:
            item_input2_key = MODULE_KEY.join(key + ['list_input2'])
            addable_sizer.Add(wx.TextCtrl(panel, id=id_renew(item_input2_key, update=True)), 0, style)

        item_apply_key = MODULE_KEY.join(key + ['list_add'])
        item_apply_id = id_renew(item_apply_key, update=True)
        item_apply = wx.Button(panel, id=item_apply_id, label=translate_key(item_apply_key))
        addable_sizer.Add(item_apply, 0, style)
        item_apply.Bind(wx.EVT_BUTTON, bind['add'], id=item_apply_id)

        item_remove_key = MODULE_KEY.join(key + ['list_remove'])
        item_remove_id = id_renew(item_remove_key, update=True)
        item_remove = wx.Button(panel, id=item_remove_id, label=translate_key(item_remove_key))
        addable_sizer.Add(item_remove, 0, style)
        item_remove.Bind(wx.EVT_BUTTON, bind['remove'], id=item_remove_id)

        item_sizer.Add(addable_sizer, 0, wx.EXPAND)

    list_box = wx.grid.Grid(panel, id=id_renew(MODULE_KEY.join(key + ['list_box']), update=True))
    list_box.CreateGrid(0, 2 if is_dual else 1)
    list_box.DisableDragColSize()
    list_box.DisableDragRowSize()
    list_box.Bind(wx.grid.EVT_GRID_SELECT_CELL, bind['select'])
    list_box.Bind(wx.grid.EVT_GRID_CELL_CHANGED, bind['edit'])

    if is_dual:
        for index, (item, item_value) in enumerate(value.items()):
            list_box.AppendRows(1)
            list_box.SetCellValue(index, 0, item)
            list_box.SetCellValue(index, 1, item_value)
    else:
        for index, item in enumerate(value):
            list_box.AppendRows(1)
            list_box.SetCellValue(index, 0, item)

    list_box.SetColLabelSize(1)
    list_box.SetRowLabelSize(1)

    max_rows = 7
    if addable_sizer:
        col_size = addable_sizer.GetMinSize()[0] - 2
        if is_dual:
            first_col_size = list_box.GetColSize(0)
            second_col_size = col_size - first_col_size if first_col_size < col_size else -1
            list_box.SetColSize(1, second_col_size)
        else:
            list_box.SetDefaultColSize(col_size, resizeExistingCols=True)
        if list_box.GetNumberRows() > max_rows:
            scroll_size = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
            max_size = wx.Size(list_box.GetBestSize()[0], list_box.GetDefaultRowSize()*max_rows)
            list_box.SetMinSize((max_size[0] + scroll_size, max_size[1]))
            list_box.SetSize((max_size[0] + scroll_size, max_size[1]))
    else:
        list_box.AutoSize()

    item_sizer.Add(list_box)

    border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
    if from_sb:
        return {'item': border_sizer}
    else:
        return border_sizer


def create_colour_picker(panel=None, value=None, key=None, bind=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)

    item_name = MODULE_KEY.join(key)
    colour_picker = CustomColourPickerCtrl()
    item_box = colour_picker.create(panel, value=value, event=bind, key=key)

    item_text = wx.StaticText(panel, label=translate_key(item_name))
    item_sizer.Add(item_text, 0, wx.ALIGN_CENTER)
    item_sizer.Add(item_box, 1, wx.EXPAND)
    return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


def create_choose(panel=None, value=None, key=None, bind=None, **kwargs):
    item_class = value

    active_items = item_class.value
    available_items = [item for item in item_class.list if item not in item_class.skip]
    translated_items = [translate_key(item) for item in available_items]

    is_single = False if item_class.multiple else True
    style = wx.LB_SINGLE if is_single else wx.LB_EXTENDED
    border_sizer = wx.BoxSizer(wx.VERTICAL)
    item_sizer = wx.BoxSizer(wx.VERTICAL)

    static_label = MODULE_KEY.join(key)
    if not item_class.empty_label:
        static_text = wx.StaticText(panel, label=u'{}:'.format(translate_key(static_label)), style=wx.ALIGN_RIGHT)
        item_sizer.Add(static_text)

    item_key = MODULE_KEY.join(key + ['list_box'])
    label_text = translate_key(item_key)
    if label_text:
        item_sizer.Add(wx.StaticText(panel, label=label_text, style=wx.ALIGN_RIGHT))
    if is_single:
        item_list_box = KeyListBox(panel, id=id_renew(item_key, update=True), keys=available_items,
                                   choices=translated_items if translated_items else available_items, style=style)
    else:
        item_list_box = KeyCheckListBox(panel, id=id_renew(item_key, update=True), keys=available_items,
                                        choices=translated_items if translated_items else available_items)
        item_list_box.Bind(wx.EVT_CHECKLISTBOX, bind['check_change'])
    item_list_box.Bind(wx.EVT_LISTBOX, bind['change'])

    section_for = active_items if not is_single else {active_items: None}
    if is_single:
        item, value = section_for.items()[0]
        if item not in item_list_box.GetItems():
            if item_list_box.GetItems():
                item_list_box.SetSelection(0)
        else:
            item_list_box.SetSelection(available_items.index(item))
    else:
        check_items = [available_items.index(item) for item in section_for if item in available_items]
        item_list_box.SetChecked(check_items)

    if item_class.description:
        adv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        adv_sizer.Add(item_list_box, 0, wx.EXPAND)

        descr_key = MODULE_KEY.join(key + ['descr_explain'])
        descr_text = wx.StaticText(panel, id=id_renew(descr_key, update=True),
                                   label=translate_key(descr_key), style=wx.ST_NO_AUTORESIZE)
        adv_sizer.Add(descr_text, 0, wx.EXPAND | wx.LEFT, 10)

        sizes = descr_text.GetSize()
        sizes[0] -= 20
        descr_text.SetMinSize(sizes)
        descr_text.Fit()
        item_sizer.Add(adv_sizer)
    else:
        item_sizer.Add(item_list_box)
    border_sizer.Add(item_sizer, 0, wx.EXPAND | wx.ALL, 5)
    return border_sizer


def create_dropdown(panel=None, value=None, key=None, bind=None, gui=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)
    choices = value.list
    item_name = MODULE_KEY.join(key)
    item_text = wx.StaticText(panel, label=translate_key(item_name))
    item_box = KeyChoice(panel, id=id_renew(item_name, update=True),
                         keys=choices, choices=choices)
    item_box.Bind(wx.EVT_CHOICE, bind)
    item_box.SetSelection(choices.index(str(value)))
    item_sizer.Add(item_text, 0, wx.ALIGN_CENTER)
    item_sizer.Add(item_box)
    return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


def create_slider(panel=None, value=None, key=None, bind=None, gui=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)
    item_name = MODULE_KEY.join(key)
    style = wx.SL_VALUE_LABEL | wx.SL_AUTOTICKS
    item_box = wx.Slider(panel, id=id_renew(item_name, update=True),
                         minValue=value.min, maxValue=value.max,
                         value=int(value), style=style)
    freq = (value.max - value.min)/5
    item_box.SetTickFreq(freq)
    item_box.SetLineSize(4)
    item_box.Bind(wx.EVT_SCROLL, bind)
    item_text = wx.StaticText(panel, label=translate_key(item_name))
    item_sizer.Add(item_text, 0, wx.ALIGN_CENTER)
    item_sizer.Add(item_box, 1, wx.EXPAND)
    return {'item': item_sizer, 'text_size': item_text.GetSize()[0], 'text_ctrl': item_text}


def create_checkbox(panel=None, value=None, key=None, bind=None, **kwargs):
    item_sizer = wx.BoxSizer(wx.HORIZONTAL)
    style = wx.ALIGN_CENTER_VERTICAL
    item_key = MODULE_KEY.join(key)
    item_box = wx.CheckBox(panel, id=id_renew(item_key, update=True),
                           label=translate_key(item_key), style=style)
    item_box.SetValue(bool(value))
    item_box.Bind(wx.EVT_CHECKBOX, bind)
    item_sizer.Add(item_box, 0, wx.ALIGN_LEFT)
    return {'item': item_sizer}


def create_panel(*args, **kwargs):
    return create_static_box(*args, **kwargs)


def create_empty(*args, **kwargs):
    return {'item': wx.BoxSizer(wx.HORIZONTAL)}
