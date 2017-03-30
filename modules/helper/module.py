# Copyright (C) 2016   CzT/Vladislav Ivanov
import logging
import os
from collections import OrderedDict

from modules.helper import parser
from parser import save_settings, load_from_config_file
from system import RestApiException, CONF_FOLDER


BASE_DICT = {
    'custom_renderer': False
}

CHAT_DICT = OrderedDict()
CHAT_DICT['config'] = OrderedDict()
CHAT_DICT['config']['show_channel_names'] = True
CHAT_DICT['config']['channels_list'] = []

CHAT_GUI = {
    'config': {
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        }
    }
}

log = logging.getLogger('modules')


class BaseModule:
    def __init__(self, *args, **kwargs):
        self._conf_params = BASE_DICT.copy()
        self._conf_params['dependencies'] = set()

        self._loaded_modules = {}
        self._rest_api = {}
        self._module_name = self.__class__.__name__
        self._load_queue = {}

        if 'conf_file_name' in kwargs:
            conf_file_name = kwargs.get('conf_file_name')
        else:
            conf_file_name = os.path.join(CONF_FOLDER, "{}.cfg".format(self._module_name))
        conf_file = os.path.join(CONF_FOLDER, conf_file_name)

        self._conf_params.update(
            {'folder': CONF_FOLDER, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'config': load_from_config_file(conf_file, self._conf_settings()),
             'gui': self._gui_settings(),
             'settings': {}})

        self._conf_params.update(kwargs.get('conf_params', {}))

    def add_to_queue(self, q_type, data):
        if q_type not in self._load_queue:
            self._load_queue[q_type] = []
        self._load_queue[q_type].append(data)

    def get_queue(self, q_type):
        return self._load_queue.get(q_type, {})

    def add_depend(self, module_name):
        self._conf_params['dependencies'].add(module_name)

    def remove_depend(self, module_name):
        self._conf_params['dependencies'].discard(module_name)

    def conf_params(self):
        params = self._conf_params
        params['class'] = self
        return params

    def _conf_settings(self, *args, **kwargs):
        """
            Override this method
        :rtype: object
        """
        return {}

    def _gui_settings(self, *args, **kwargs):
        """
            Override this method
        :return: Settings for GUI (dict)
        """
        return {}

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

    def process_message(self, message, queue, **kwargs):
        return message


class ChatModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
        self.queue = kwargs.get('queue')
        self.channels = {}

        parser.update(self._conf_params['config'], CHAT_DICT, overwrite=False)
        conf_params = self._conf_params['config']
        parser.update(self._conf_params['gui'], CHAT_GUI)

        self.channels_list = conf_params['config']['channels_list']

        self.testing = kwargs.get('testing')
        if self.testing:
            self.testing = self._test_class()

    def load_module(self, *args, **kwargs):
        BaseModule.load_module(self, *args, **kwargs)
        for channel in self.channels_list:
            self._set_chat_online(channel)

        if self.testing and self.channels:
            self.testing = self.testing.start()

    def _test_class(self):
        """
            Override this method
        :return: Chat test class (object/Class)
        """
        return object()

    def apply_settings(self, **kwargs):
        BaseModule.apply_settings(self, **kwargs)
        self.refresh_channel_names()

    def refresh_channel_names(self):
        if 'gui' in self._loaded_modules:
            gui_class = self._loaded_modules['gui']['class']
            if gui_class.gui:
                if gui_class.gui.status_frame:
                    gui_class.gui.status_frame.refresh_labels(self._module_name)

    def get_viewers(self, *args, **kwargs):
        """
            Overwrite this method
        :param args: 
        :param kwargs: 
        """
        pass

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

    def _set_chat_offline(self, chat):
        """
        :param chat: 
        """
        self.set_chat_offline(chat)
        try:
            self.channels[chat].stop()
        except Exception as exc:
            log.info("Unable to stop chat %s", chat)
            log.debug(exc)
        del self.channels[chat]

    def _set_chat_online(self, chat):
        """
            Overwite this method
        :param args: 
        :param kwargs: 
        """
        self.set_chat_online(chat)

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
