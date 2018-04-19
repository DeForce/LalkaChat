from collections import OrderedDict

import logging
log = logging.getLogger('interface/types')


class LCObject(object):
    def __init__(self, value=None, *args, **kwargs):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class LCDict(LCObject):
    def __init__(self, *args, **kwargs):
        super(LCDict, self).__init__(*args, **kwargs)
        self._value = OrderedDict()

    def __setitem__(self, key, value):
        self._value[key] = value

    def __getitem__(self, item):
        return self._value[item]

    def __contains__(self, item):
        return item in self._value

    def get(self, key, default=None):
        return self._value.get(key, default)

    def items(self):
        return self._value.items()

    def iteritems(self):
        return self._value.iteritems()


class LCPanel(LCDict):
    def __init__(self, icon=None, *args, **kwargs):
        super(LCPanel, self).__init__(*args, **kwargs)
        self.icon = icon


class LCStaticBox(LCDict):
    def __init__(self, *args, **kwargs):
        super(LCStaticBox, self).__init__(*args, **kwargs)


class LCText(LCObject):
    def __init__(self, value=None):
        LCObject.__init__(self, value)

    def simple(self):
        return unicode(self._value)

    def __repr__(self):
        return unicode(self._value)

    def __str__(self):
        return unicode(self._value)

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __unicode__(self):
        return unicode(self._value)

    def format(self, *args):
        return self._value.format(*args)


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


class LCList(LCObject):
    def __init__(self, value=(), *args, **kwargs):
        super(LCList, self).__init__(value, *args, **kwargs)

    def __iter__(self):
        return self.value.__iter__()

    def simple(self):
        return list(self._value)


class LCButton(LCObject):
    def __init__(self, fnc=None, *args, **kwargs):
        if fnc is None:
            fnc = self.pass_function
        super(LCButton, self).__init__(fnc, *args, **kwargs)

    def __repr__(self):
        return str(self.value)

    def pass_function(self):
        pass


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


class LCGridDual(LCDict):
    def __init__(self, value=OrderedDict(), *args, **kwargs):
        super(LCGridDual, self).__init__(value, *args, **kwargs)

    def simple(self):
        return dict(self._value)


class LCGridSingle(LCObject):
    def __init__(self, value=(), *args, **kwargs):
        super(LCGridSingle, self).__init__(value, *args, **kwargs)

    def __iter__(self):
        return self._value.__iter__()

    def simple(self):
        return list(self._value)


class LCChooseSingle(LCObject):
    def __init__(self, value=(), empty_label=False, available_list=(), *args, **kwargs):
        super(LCChooseSingle, self).__init__(value, *args, **kwargs)
        self.list = available_list
        self.multiple = False
        self.keep_extension = kwargs.get('keep_extension', False)
        self.description = kwargs.get('description')
        self.empty_label = empty_label

    def simple(self):
        return self.value

    def __repr__(self):
        return str(self.value)


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
    'dropdown': LCDropdown,
    'slider': LCSlider,
    'colour_picker': LCColour,
    'list': LCList,
    'button': LCButton
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
            except:
                new_data[item] = value
    return new_data
