import wx
import wx.grid

from modules.helper.system import MODULE_KEY, translate_key, log
from modules.interface.controls import GuiCreationError, CustomColourPickerCtrl, KeyListBox, KeyCheckListBox, KeyChoice, \
    id_renew
from modules.interface.types import LCPanel


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
    else:
        c_button.Bind(wx.EVT_BUTTON, bind, id=button_id)

    item_sizer.Add(c_button)
    return {'item': item_sizer}
