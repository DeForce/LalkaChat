# Copyright (C) 2016   CzT/Vladislav Ivanov
import copy
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

DEFAULT = LCPanel()
DEFAULT['system'] = LCStaticBox(label=False)
DEFAULT['system']['enabled'] = LCBool(True, always_on=True)

CHAT_DICT = LCPanel()
CHAT_DICT['config'] = LCStaticBox()
CHAT_DICT['config']['show_channel_names'] = LCBool(False)

CHAT_GUI = {'system': {'hidden': ['enabled']}}

log = logging.getLogger('modules')


class BaseModule(object):
    def __init__(self, config=None, gui=None, queue=None, category=None,
                 conf_file=None, *args, **kwargs):
        if gui is None:
            gui = {}
        if config is None:
            config = LCPanel()

        self._module_name = self.__class__.__name__.lower()

        self._config = config
        self._gui = gui

        self._custom_render = False
        self._dependencies = set()

        self._category = category
        self._loaded_modules = {}
        self._rest_api = {}
        self._load_queue = {}
        self._msg_queue = queue

        if conf_file is None:
            conf_file = os.path.join(CONF_FOLDER, "{}.cfg".format(self._module_name.lower()))
        conf_file = os.path.join(CONF_FOLDER, conf_file)
        self._config = load_from_config_file(conf_file, self._config)

        self._conf_params = {
            'folder': CONF_FOLDER, 'file': conf_file,
            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
            'config': self._config,
            'gui': gui,
            'settings': {}
        }
        self._conf_params.update(kwargs.get('conf_params', {}))

    def add_to_queue(self, q_type, data):
        if q_type not in self._load_queue:
            self._load_queue[q_type] = []
        self._load_queue[q_type].append(data)

    def get_queue(self, q_type):
        return self._load_queue.get(q_type, {})

    def add_depend(self, module_name):
        self._dependencies.add(module_name)

    def remove_depend(self, module_name):
        self._dependencies.discard(module_name)

    @property
    def conf_params(self):
        params = self._conf_params
        params['class'] = self
        return params

    @property
    def custom_render(self):
        return self._custom_render

    @property
    def category(self):
        return self._category

    @property
    def config(self):
        return self._config

    @property
    def enabled(self):
        return True

    def disable(self):
        pass

    def enable(self):
        pass

    def get_config(self, *keys):
        return deep_get(self._conf_params['config'], *keys)

    def get_loaded_module_config(self, module, *keys):
        return deep_get(self._loaded_modules[module]['config'], *keys)

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
        save_settings(self.conf_params,
                      ignored_sections=self.conf_params.get('gui', {}).get('ignored_sections', ()))

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


class DefaultModule(BaseModule):
    def __init__(self, config=None, *args, **kwargs):
        if config is None:
            config = LCPanel()

        def_config = copy.deepcopy(DEFAULT)
        def_config.icon = config.icon
        parser.update(def_config, config, overwrite=True)

        super(DefaultModule, self).__init__(config=def_config, *args, **kwargs)

    @property
    def enabled(self):
        return self.get_config('system', 'enabled').simple()

    def enable(self):
        self.config['system']['enabled'].value = True
        self.config.enable_all()

    def disable(self):
        self.config['system']['enabled'].value = False
        self.config.disable_all()


class MessagingModule(DefaultModule):
    def __init__(self, *args, **kwargs):
        super(MessagingModule, self).__init__(category='messaging', *args, **kwargs)
        self._load_priority = DEFAULT_PRIORITY

    @property
    def load_priority(self):
        return self._load_priority

    def process_message(self, message, **kwargs):
        """
        :param message: Received Message class
        :type message: TextMessage
        :return: Message Class, could be None if message is "cleared"
        :rtype: Message
        """
        if self.enabled:
            return self._process_message(message, **kwargs)
        return message

    def _process_message(self, message, **kwargs):
        raise NotImplementedError()


class ChatModule(DefaultModule):
    def __init__(self, config=LCPanel(), gui=None, *args, **kwargs):
        def_config = copy.deepcopy(CHAT_DICT)
        def_config.icon = config.icon
        parser.update(def_config, config, overwrite=True)
        def_config['config']['channels_list'] = LCList()

        if gui is None:
            gui = {}
        gui.update(CHAT_GUI)

        super(ChatModule, self).__init__(config=def_config, gui=gui, category='chat', *args, **kwargs)
        self.queue = kwargs.get('queue')
        self.channels = {}

        self.channels_list = self.get_config('config', 'channels_list')

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
        raise NotImplementedError()

    def _check_chats(self, online_chats):
        chats = self.get_config('config', 'channels_list')

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
