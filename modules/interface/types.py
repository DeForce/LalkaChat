from collections import OrderedDict

import logging


class LCObject(object):
    def __init__(self, value, *args, **kwargs):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class LCPanel(OrderedDict, LCObject):
    def __init__(self, icon=None, *args, **kwargs):
        self.icon = icon
        OrderedDict.__init__(self, *args, **kwargs)


class LCStaticBox(OrderedDict, LCObject):
    def __init__(self, *args, **kwargs):
        OrderedDict.__init__(self, *args, **kwargs)


class LCText(unicode, LCObject):
    def __init__(self, value=None):
        unicode.__init__(value)

    def simple(self):
        return unicode(self)


class LCColour(LCObject):
    def __init__(self, *args, **kwargs):
        super(LCColour, self).__init__(*args, **kwargs)

    def __repr__(self):
        return str(self._value)

    def __getitem__(self, item):
        return str(self._value)[item]

    def simple(self):
        return unicode(self._value)

    def startswith(self, value):
        return str(self._value).startswith(value)


class LCBool(LCObject):
    def __init__(self, value, *args, **kwargs):
        super(LCBool, self).__init__(value, *args, **kwargs)

    def __nonzero__(self):
        return bool(self._value)

    def __repr__(self):
        return str(bool(self._value))

    def simple(self):
        return bool(self)


class LCList(list, LCObject):
    def __init__(self, value=()):
        list.__init__(self, value)

    def simple(self):
        return list(self)


class LCButton(LCObject):
    def __init__(self, fnc=None, *args, **kwargs):
        super(LCButton, self).__init__(fnc, *args, **kwargs)

    def __repr__(self):
        return str(self.value)


class LCSpin(LCObject):
    def __init__(self, value, min_v=0, max_v=100, *args, **kwargs):
        super(LCSpin, self).__init__(value, *args, **kwargs)
        self.min = min_v
        self.max = max_v

    def __repr__(self):
        return str(self._value)

    def __int__(self):
        return self.value

    def simple(self):
        return int(self.value)


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


class LCDropdown(LCObject):
    def __init__(self, value, available_list=()):
        super(LCDropdown, self).__init__(value)
        self.list = available_list

    def __repr__(self):
        return self._value

    def simple(self):
        return str(self._value)


class LCGridDual(OrderedDict, LCObject):
    def __init__(self, *args, **kwargs):
        OrderedDict.__init__(self, *args, **kwargs)

    def simple(self):
        return OrderedDict(self)


class LCGridSingle(list, LCObject):
    def __init__(self, value=list()):
        list.__init__(self, value)

    def simple(self):
        return list(self)


class LCChooseSingle(LCObject):
    def __init__(self, value=(), check_type=None, empty_label=False, *args, **kwargs):
        super(LCChooseSingle, self).__init__(value, *args, **kwargs)
        self.multiple = False
        self.check_type = check_type
        self.keep_extension = kwargs.get('keep_extension', False)
        self.description = kwargs.get('description')
        self.empty_label = empty_label
        if check_type in ['dir', 'folder', 'files']:
            self.folder = kwargs.get('folder')

    def simple(self):
        return self.value


class LCChooseMultiple(LCChooseSingle):
    def __init__(self, value=(), *args, **kwargs):
        super(LCChooseMultiple, self).__init__(value, *args, **kwargs)
        self.multiple = True

    def simple(self):
        return list(self.value)

TYPE_TO_LC = {
    OrderedDict: LCStaticBox,
    bool: LCBool,
    str: LCText,
    unicode: LCText,
    int: LCText,
    'spin': LCSpin,
    'dropdown': list,
    'slider': int,
    'colour_picker': LCColour,
    'list': list,
    'button': LCButton
}


def alter_data_to_lc_style(data, gui):
    new_data = LCStaticBox()
    for item, value in data.items():
        item_type = gui.get(item, {}).get('view', type(value))
        logging.info('item: %s, value: %s, type: %s', item, value, item_type)
        if item_type not in TYPE_TO_LC:
            new_data[item] = value
        else:
            try:
                new_data[item] = TYPE_TO_LC[item_type](value, **gui.get(item, {}))
            except:
                new_data[item] = value
    return new_data
