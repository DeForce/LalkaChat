# Copyright (C) 2016   CzT/Vladislav Ivanov
import Queue

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
        self._load_queue = {}

    def add_to_queue(self, q_type, data):
        if q_type not in self._load_queue:
            self._load_queue[q_type] = []
        self._load_queue[q_type].append(data)

    def get_queue(self, q_type):
        return self._load_queue.get(q_type, {})

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
        save_settings(self.conf_params(),
                      ignored_sections=self.conf_params().get('gui', {}).get('ignored_sections', ()))

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

    def apply_settings(self, **kwargs):
        BaseModule.apply_settings(self, **kwargs)
        self.refresh_channel_names()

    def refresh_channel_names(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.refresh_labels(self._module_name)

    def set_viewers(self, channel, viewers):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_viewers(self._module_name, channel, viewers)

    def set_online(self, channel):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_online(self._module_name, channel)
        else:
            self.add_to_queue('status_frame', {'name': self._module_name, 'channel': channel, 'action': 'set_online'})

    def set_offline(self, channel):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_offline(self._module_name, channel)
        else:
            self.add_to_queue('status_frame', {'name': self._module_name, 'channel': channel, 'action': 'set_offline'})

    def set_chat_online(self, channel):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_chat_online(self._module_name, channel)
        else:
            self.add_to_queue('status_frame', {'name': self._module_name, 'channel': channel, 'action': 'add'})

    def set_chat_offline(self, channel):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.set_chat_offline(self._module_name, channel)
        else:
            self.add_to_queue('status_frame', {'name': self._module_name, 'channel': channel, 'action': 'remove'})

    def _set_chat_offline(self, *args, **kwargs):
        """
            Overwite this method
        :param args: 
        :param kwargs: 
        """
        pass

    def _set_chat_online(self, *args, **kwargs):
        """
            Overwite this method
        :param args: 
        :param kwargs: 
        """
        pass

    def _check_chats(self, online_chats):
        chats = self._conf_params['config']['config']['channels_list']

        chats_to_set_offline = [chat for chat in online_chats if chat not in chats]
        [self._set_chat_offline(chat) for chat in chats_to_set_offline]

        chats_to_set_online = [chat for chat in chats if chat not in online_chats]
        [self._set_chat_online(chat) for chat in chats_to_set_online]

    def get_remove_text(self):
        remove_dict = {}
        st_settings = self._loaded_modules['webchat']['style_settings']
        if st_settings['gui']['keys'].get('remove_message'):
            remove_dict['gui'] = st_settings['gui']['keys'].get('remove_text')
        if st_settings['chat']['keys'].get('remove_message'):
            remove_dict['chat'] = st_settings['chat']['keys'].get('remove_text')
        return remove_dict
