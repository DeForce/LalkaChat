# Copyright (C) 2016   CzT/Vladislav Ivanov
import logging
import os

from modules.helper import parser
from modules.helper.message import TextMessage, Message
from modules.interface.types import LCPanel, LCStaticBox, LCBool, LCList, deep_get
from parser import save_settings, load_from_config_file
from system import RestApiException, CONF_FOLDER

DEFAULT_PRIORITY = 30

CHANNEL_ONLINE = 'online'
CHANNEL_OFFLINE = 'offline'
CHANNEL_PENDING = 'pending'
CHANNEL_STATUSES = [CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING]
CHANNEL_NO_VIEWERS = 'N/A'

BASE_DICT = {
    'custom_renderer': False
}

CHAT_DICT = LCPanel()
CHAT_DICT['config'] = LCStaticBox()
CHAT_DICT['config']['show_channel_names'] = LCBool(False)
CHAT_DICT['config']['channels_list'] = LCList()

CHAT_GUI = {}

log = logging.getLogger('modules')


class BaseModule(object):
    def __init__(self, config=None, gui=None, queue=None, category='main',
                 *args, **kwargs):
        if gui is None:
            gui = {}
        if config is None:
            config = dict()

        self._conf_params = BASE_DICT.copy()
        self._conf_params['dependencies'] = set()

        self.__conf_settings = config
        self.__gui_settings = gui

        self._loaded_modules = {}
        self._rest_api = {}
        self._module_name = self.__class__.__name__.lower()
        self._load_queue = {}
        self._msg_queue = queue
        self._category = category

        if 'conf_file_name' in kwargs:
            conf_file_name = kwargs.get('conf_file_name')
        else:
            conf_file_name = os.path.join(CONF_FOLDER, "{}.cfg".format(self._module_name.lower()))
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

    @property
    def category(self):
        return self._category

    @property
    def config(self):
        return self._conf_params.get('config', {})

    def _conf_settings(self, *args, **kwargs):
        """
            Override this method
        :rtype: LCPanel
        """
        return self.__conf_settings

    def _gui_settings(self, *args, **kwargs):
        """
            Override this method
        :return: Settings for GUI (dict)
        """
        return self.__gui_settings

    def get(self, *keys):
        return deep_get(self._conf_params['config'], *keys)

    def load_module(self, *args, **kwargs):
        self._loaded_modules = kwargs.get('loaded_modules')

    def gui_button_press(self, *args):
        pass

    def apply_settings(self, system_exit=False, changes=None, **kwargs):
        """
        :param changes: dictionary of keys that were changed
        :param system_exit: are we exiting finally
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


class ConfigModule(BaseModule):
    def __init__(self, *args, **kwargs):
        super(ConfigModule, self).__init__(*args, **kwargs)


class UIModule(BaseModule):
    pass


class MessagingModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
        self._category = 'messaging'
        self._load_priority = DEFAULT_PRIORITY

    @property
    def load_priority(self):
        return self._load_priority

    def process_message(self, message, queue=None):
        """

        :param message: Received Message class
        :type message: TextMessage
        :param queue: Main queue
        :type queue: Queue.Queue
        :return: Message Class, could be None if message is "cleared"
        :rtype: Message
        """
        return message


class ChatModule(BaseModule):
    def __init__(self, *args, **kwargs):
        BaseModule.__init__(self, *args, **kwargs)
        self._category = 'chat'
        self.queue = kwargs.get('queue')
        self.channels = {}

        parser.update(self._conf_params['config'], CHAT_DICT, overwrite=False)
        conf_params = self._conf_params['config']
        parser.update(self._conf_params['gui'], CHAT_GUI)

        self.channels_list = conf_params['config']['channels_list']

        self.testing = kwargs.get('testing')
        if self.testing:
            self.testing = self._test_class()

    @property
    def viewers(self):
        return {}

    def _test_class(self):
        """
            Override this method
        :return: Chat test class (object/Class)
        """
        return {}

    def _remove_channel(self, chat):
        """
        :param chat:
        """
        try:
            self.channels[chat].stop()
        except Exception as exc:
            log.info("Unable to stop chat %s", chat)
            log.debug(exc)
        del self.channels[chat]

    def _add_channel(self, chat):
        """
            Overwite this method
        """

    def _check_chats(self, online_chats):
        chats = self._conf_params['config']['config']['channels_list']

        chats_to_set_offline = [chat for chat in online_chats if chat not in chats]
        [self._remove_channel(chat) for chat in chats_to_set_offline]

        chats_to_set_online = [chat for chat in chats if chat not in online_chats]
        [self._add_channel(chat) for chat in chats_to_set_online]

    def load_module(self, *args, **kwargs):
        BaseModule.load_module(self, *args, **kwargs)
        for channel in self.channels_list:
            self._add_channel(channel)

        if self.testing and self.channels:
            self.testing = self.testing.start()

    def apply_settings(self, **kwargs):
        BaseModule.apply_settings(self, **kwargs)
        self._check_chats(self.channels.keys())

    def get_remove_text(self):
        remove_dict = {}
        st_settings = self._loaded_modules['webchat']['style_settings']
        if st_settings['gui_chat']['keys'].get('remove_message'):
            remove_dict['gui_chat'] = st_settings['gui_chat']['keys'].get('remove_text')
        if st_settings['server_chat']['keys'].get('remove_message'):
            remove_dict['server_chat'] = st_settings['server_chat']['keys'].get('remove_text')
        return remove_dict


class Channel(object):
    def __init__(self, channel):
        self._viewers = None
        self._status = CHANNEL_OFFLINE
        self._channel = channel

    @property
    def channel(self):
        return self._channel

    @property
    def viewers(self):
        return self._viewers

    @viewers.setter
    def viewers(self, value):
        self._viewers = value

    def get_viewers(self):
        """
        Overwrite this.
        :return:
        """

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value in CHANNEL_STATUSES:
            self._status = value
        else:
            raise TypeError('Invalid channel status: {}', value)
