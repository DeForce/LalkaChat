# Copyright (C) 2016   CzT/Vladislav Ivanov
from parser import save_settings
from system import RestApiException
BASE_DICT = {
    'custom_renderer': False
}


class BaseModule:
    def __init__(self, *args, **kwargs):
        self._conf_params = BASE_DICT.copy()
        self._conf_params.update(kwargs.get('conf_params', {}))
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

    def render(self, *args, **kwargs):
        pass

    def rest_add(self, method, path, function_to_call):
        """
        Rest add function will take method, path, function and
          register with that to restApi handler
        :param method: HTTP Method to trigger function
        :param path: HTTP Path (/rest/%module_name%/$path)
        :param function_to_call: what function rest api will trigger when it
          receives path with correct method
        """
        if method not in self._rest_api:
            self._rest_api[method] = {}

        if path in self._rest_api[method]:
            raise RestApiException('Path already taken')

        self._rest_api[method][path] = function_to_call


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
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_viewers(self._module_name, viewers)

    def set_online(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_online(self._module_name)

    def set_offline(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_offline(self._module_name)

    def get_remove_text(self):
        remove_dict = {}
        st_settings = self._loaded_modules['webchat']['style_settings']
        if st_settings['gui']['keys'].get('remove_message'):
            remove_dict['gui'] = st_settings['gui']['keys'].get('remove_text')
        if st_settings['chat']['keys'].get('remove_message'):
            remove_dict['chat'] = st_settings['chat']['keys'].get('remove_text')
        return remove_dict
