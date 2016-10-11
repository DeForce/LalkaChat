

class BaseModule:
    def __init__(self, *args, **kwargs):
        self._conf_params = {}

    def conf_params(self):
        params = self._conf_params
        params['class'] = self
        return params

    def gui_button_press(self, *args):
        pass


class MessagingModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)

    def process_message(self, message, queue, **kwargs):
        return message


class ChatModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
