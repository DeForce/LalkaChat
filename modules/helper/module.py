from parser import save_settings


class BaseModule:
    def __init__(self, *args, **kwargs):
        self._conf_params = kwargs.get('conf_params', {})
        self._loaded_modules = None
        self._rest_api = {}
        self._module_name = self.__class__.__name__

    def conf_params(self):
        params = self._conf_params
        params['class'] = self
        return params

    def load_module(self, *args, **kwargs):
        self._loaded_modules = kwargs.get('loaded_modules')

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

    def set_viewers(self, viewers):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui.status_frame:
                gui_class.gui.status_frame.set_viewers(self._module_name, viewers)

    def set_online(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui.status_frame:
                gui_class.gui.status_frame.set_online(self._module_name)

    def set_offline(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui.status_frame:
                gui_class.gui.status_frame.set_offline(self._module_name)
