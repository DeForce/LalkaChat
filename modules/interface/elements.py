import wx
import wx.grid

from modules.helper.system import MODULE_KEY, translate_key


def create_button(source_class=None, panel=None, key=None, value=None,
                  bind=None, enabled=True, **kwargs):
    item_sizer = wx.BoxSizer(wx.VERTICAL)
    item_name = MODULE_KEY.join(key)
    c_button = wx.Button(panel, label=translate_key(item_name))
    if not enabled:
        c_button.Disable()

    if item_name in source_class.buttons:
        source_class.buttons[item_name].append(c_button)
    else:
        source_class.buttons[item_name] = [c_button]

    if value:
        # TODO: Implement button function pressing
        if callable(value.value):
            c_button.Bind(wx.EVT_BUTTON, value.value)
    else:
        c_button.Bind(wx.EVT_BUTTON, bind, id=c_button.Id)

    item_sizer.Add(c_button)
    return {'item': item_sizer}
