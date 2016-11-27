from parser import save_settings


class BaseModule:
    def __init__(self, *args, **kwargs):
        self._conf_params = kwargs.get('conf_params', {})
        self._rest_api = {}

    def conf_params(self):
        params = self._conf_params
        params['class'] = self
        return params

    def load_module(self, *args, **kwargs):
        pass

    def gui_button_press(self, *args):
        pass

    def apply_settings(self, **kwargs):
        """
        :param kwargs:
            system_exit - param provided if system is exiting
        :return:
        """
        save_settings(self.conf_params())

    def rest_api(self):
        return self._rest_api


class MessagingModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
        self._conf_params['dependencies'] = set()

    def process_message(self, message, queue, **kwargs):
        return message

    def add_depend(self, module_name):
        self._conf_params['dependencies'].add(module_name)

    def remove_depend(self, module_name):
        self._conf_params['dependencies'].discard(module_name)


class ChatModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
