# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import queue
import logging
import logging.config
import logging.handlers
import os
import sys
import threading
from collections import OrderedDict
from time import sleep
import semantic_version
from modules.helper.functions import get_class_from_iname, get_modules_in_folder
from modules.helper.module import ConfigModule
from modules.helper.parser import load_from_config_file
from modules.helper.system import load_translations_keys, PYTHON_FOLDER, CONF_FOLDER, MAIN_CONF_FILE, MODULE_FOLDER, \
    LOG_FOLDER, GUI_TAG, TRANSLATION_FOLDER, LOG_FILE, LOG_FORMAT, get_language, get_languages, VERSION
from modules.helper.updater import get_available_versions
from modules.interface.types import LCStaticBox, LCText, LCBool, LCButton, LCPanel, LCSlider, LCChooseMultiple, \
    LCDropdown
from modules.message_handler import Message

if sys.platform.lower().startswith('win'):
    import ctypes

    def hide_console():
        """
        Hides the console window in GUI mode. Necessary for frozen application, because
        this application support both, command line processing AND GUI mode and theirfor
        cannot be run via pythonw.exe.
        """

        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)

    def show_console():
        """Unhides console window"""
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 1)

SEM_VERSION = semantic_version.Version(VERSION)
LOG_FILES_COUNT = 5
HIDDEN_CHATS = ['hitbox', 'beampro']


def load_modules(modules, base_config):
    for module_name, f_module in modules.items():
        f_module.load_module(main_settings=base_config, loaded_modules=modules)
        logging.debug('loaded module %s', module_name)


if os.path.exists('default_branch'):
    with open('default_branch') as branch_file:
        DEFAULT_BRANCH, DEFAULT_VERSION = branch_file.read().strip().split(',')
else:
    DEFAULT_BRANCH, DEFAULT_VERSION = ('develop', 1)


class MainModule(ConfigModule):
    def __init__(self, *args, **kwargs):
        super(MainModule, self).__init__(*args, **kwargs)
        self._update = False
        self._update_config = {}

    @property
    def language(self):
        return self.get_config('gui', 'language').value

    def apply_settings(self, **kwargs):
        changes = kwargs.get('changes', {})
        if 'main.system.release_channel' in changes:
            self._conf_params['config']['system']['current_version'] = 0

        ConfigModule.apply_settings(self, **kwargs)

    @property
    def update(self):
        return self._update

    def set_update(self, url, version):
        self._update_config = {'url': url, 'version': version}
        self._update = True

    def get_update_url(self):
        return self._update_config['url']
    
    def get_version(self):
        return self._update_config['version']


def button_test(event):
    logging.info('HelloWorld')


def main(root_logger):
    def close():
        for l_module, l_module_dict in loaded_modules.items():
            l_module_dict['class'].apply_settings(system_exit=True)

        if window:
            window.gui.on_close('Closing Program from console')
        else:
            os._exit(0)

    log = logging.getLogger('main')
    root_logger.setLevel(level=logging.INFO)

    # For system compatibility, loading chats
    loaded_modules = OrderedDict()
    gui_settings = {}
    window = None

    # Creating dict with folder settings
    base_config = {'root_folder': PYTHON_FOLDER,
                   'conf_folder': CONF_FOLDER,
                   'main_conf_file': MAIN_CONF_FILE,
                   'main_conf_file_loc': MAIN_CONF_FILE,
                   'main_conf_file_name': ''.join(os.path.basename(MAIN_CONF_FILE).split('.')[:-1]),
                   'update': False}

    if not os.path.isdir(MODULE_FOLDER):
        logging.error("Was not able to find modules folder, check you installation")
        exit()

    # Trying to load config file.
    # Create folder if doesn't exist
    if not os.path.isdir(CONF_FOLDER):
        log.error("Could not find %s folder", CONF_FOLDER)
        try:
            os.mkdir(CONF_FOLDER)
        except Exception as exc:
            log.debug("Exception: %s", exc)
            log.error("Was unable to create %s folder.", CONF_FOLDER)
            exit()

    log.info("Loading basic configuration")
    main_config_dict = LCPanel()
    main_config_dict['gui_information'] = LCStaticBox()
    main_config_dict['gui_information']['width'] = LCText('450')
    main_config_dict['gui_information']['height'] = LCText('500')
    main_config_dict['gui_information']['pos_x'] = LCText('10')
    main_config_dict['gui_information']['pos_y'] = LCText('10')
    main_config_dict['system'] = LCStaticBox()
    main_config_dict['system']['log_level'] = LCDropdown('INFO', available_list=['DEBUG', 'INFO', 'ERROR'])
    main_config_dict['system']['testing_mode'] = LCBool(False)
    main_config_dict['system']['check_updates'] = LCBool(True)
    main_config_dict['system']['current_version'] = LCText(DEFAULT_VERSION)
    main_config_dict['system']['release_channel'] = LCDropdown(DEFAULT_BRANCH)
    main_config_dict['system']['icon'] = LCText(os.path.join('img', 'lalka_cup.png'))
    main_config_dict['gui'] = LCStaticBox()
    main_config_dict['gui']['language'] = LCDropdown(get_language(), get_languages())
    main_config_dict['gui']['cli'] = LCBool(False)
    main_config_dict['gui']['show_icons'] = LCBool(False)
    main_config_dict['gui']['show_hidden'] = LCBool(False)
    main_config_dict['gui']['gui'] = LCBool(True)
    main_config_dict['gui']['on_top'] = LCBool(True)
    main_config_dict['gui']['show_browser'] = LCBool(True)
    main_config_dict['gui']['show_counters'] = LCBool(True)
    main_config_dict['gui']['show_console'] = LCBool(False)
    main_config_dict['gui']['transparency'] = LCSlider(0, min_v=0, max_v=90)
    main_config_dict['gui']['borderless'] = LCBool(False)
    main_config_dict['gui']['reload'] = LCButton(button_test)

    main_config_gui = {
        'system': {
            'hidden': ['log_level', 'testing_mode', 'current_version', 'icon'],
        },
        'gui': {
            'hidden': ['cli'],
        },
        'ignored_sections': ['gui.reload'],
        'non_dynamic': [
            'language.list_box',
            'gui.borderless',
            'gui.cli',
            'gui.gui',
            'gui.show_browser',
            'gui.show_hidden',
            'gui.language',
            'system.*'
        ]
    }
    # Adding config for main module
    main_class = MainModule(
        conf_params={
            'root_folder': base_config['root_folder'],
            'logs_folder': LOG_FOLDER,
        },
        config=main_config_dict,
        gui=main_config_gui,
        conf_file='config.cfg',
        category='main'
    )
    loaded_modules['main'] = main_class
    main_config = main_class.get_config()
    root_logger.setLevel(level=logging.getLevelName(str(main_config['system'].get('log_level', 'INFO'))))

    if sys.platform.lower().startswith('win'):
        if getattr(sys, 'frozen', False):
            if not main_class.get_config('gui', 'show_console'):
                hide_console()

    # Checking for updates
    log.info("Checking for updates")
    if main_class.get_config('system', 'check_updates'):
        versions = get_available_versions()
        if versions:
            main_class.get_config('system', 'release_channel').list = versions.keys()
            channel = main_class.get_config('system', 'release_channel').simple()
            current_version = main_class.get_config('system', 'current_version')
            channel_versions = versions.get(channel, {})
            if channel_versions:
                latest_version = str(max(map(int, channel_versions.keys())))
                if int(latest_version) > int(current_version):
                    main_class.set_update(versions[channel][latest_version]['url'], latest_version)

    if main_class.update:
        log.info("There is new update, please update!")

    logging.info('Current Version: %s', main_class.get_config('system', 'current_version'))

    # Main GUI Settings
    gui_settings['gui'] = main_config[GUI_TAG].get('gui')
    gui_settings['on_top'] = main_config[GUI_TAG].get('on_top')
    gui_settings['transparency'] = main_config[GUI_TAG].get('transparency')
    gui_settings['borderless'] = main_config[GUI_TAG].get('borderless')
    gui_settings['language'] = main_config[GUI_TAG].get('language')
    gui_settings['show_hidden'] = main_config[GUI_TAG].get('show_hidden')
    gui_settings['size'] = (int(main_config['gui_information']['width']),
                            int(main_config['gui_information']['height']))
    gui_settings['position'] = (int(main_config['gui_information']['pos_x']),
                                int(main_config['gui_information']['pos_y']))
    gui_settings['show_browser'] = main_config['gui'].get('show_browser')

    # Starting modules
    log.info("Loading Messaging Handler")
    log.info("Loading Queue for message handling")

    try:
        load_translations_keys(TRANSLATION_FOLDER, gui_settings['language'])
    except Exception as exc:
        log.debug("Exception: %s", exc)
        log.exception("Failed loading translations")

    # Creating queues for messaging transfer between chat threads
    m_queue = queue.Queue()
    # Loading module for message processing...
    msg = Message(m_queue)
    loaded_modules.update(msg.load_modules(base_config, loaded_modules['main']))
    msg.start()

    log.info("Loading Chats")
    # Trying to dynamically load chats that are in config file.
    chat_modules_file = os.path.join(CONF_FOLDER, "chat_modules.cfg")
    chat_location = os.path.join(MODULE_FOLDER, "chat")
    chat_conf_dict = OrderedDict()
    chat_conf_dict['chats'] = LCChooseMultiple(get_modules_in_folder('chat'),
                                               available_list=get_modules_in_folder('chat'))

    chat_conf_gui = {'non_dynamic': ['chat.chats']}

    chat_init_module = ConfigModule(
        config=load_from_config_file(chat_modules_file, chat_conf_dict),
        gui=chat_conf_gui,
        conf_file='chat_modules.cfg',
        category='chat'
    )
    loaded_modules['chat'] = chat_init_module

    for chat_module_name in chat_conf_dict['chats'].list:
        log.info("Loading chat module: %s", chat_module_name)
        module_location = os.path.join(chat_location, chat_module_name + ".py")
        if os.path.isfile(module_location):
            log.info("found %s", chat_module_name)
            # After module is find, we are initializing it.
            # Class should be named same as module(Case insensitive)
            # Also passing core folder to module so it can load it's own
            #  configuration correctly

            chat_init = get_class_from_iname(module_location, chat_module_name)
            class_module = chat_init(queue=m_queue,
                                     conf_folder=CONF_FOLDER,
                                     conf_file=os.path.join(CONF_FOLDER, f'{chat_module_name}.cfg'),
                                     testing=main_config_dict['system']['testing_mode'])
            if chat_module_name in HIDDEN_CHATS:
                chat_conf_dict['chats'].skip[chat_module_name] = True
            loaded_modules[chat_module_name.lower()] = class_module
        else:
            log.error("Unable to find {0} module")

    log.info('LalkaChat loaded successfully')

    if gui_settings['gui']:
        from modules import gui
        log.info("Loading GUI Interface")
        window = gui.GuiThread(gui_settings=gui_settings,
                               main_module=loaded_modules['main'],
                               loaded_modules=loaded_modules,
                               queue=m_queue)
        loaded_modules['gui'] = window

        module_load_thread = threading.Thread(target=load_modules, args=[loaded_modules, base_config])
        module_load_thread.daemon = True
        module_load_thread.start()

        window.run()
    else:
        if main_config_dict['gui']['cli']:
            try:
                while True:
                    console = input("> ")
                    log.info(console)
                    if console == "exit":
                        log.info("Exiting now!")
                        close()
                    else:
                        log.info("Incorrect Command")
            except (KeyboardInterrupt, SystemExit):
                log.info("Exiting now")
                close()
            except Exception as exc:
                log.info(exc)
        else:
            try:
                while True:
                    sleep(1)
            except (KeyboardInterrupt, SystemExit):
                log.info("Exiting now")
                close()


def init():
    root_logger = logging.getLogger()
    # Logging level
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1000*1024, backupCount=LOG_FILES_COUNT)
    file_handler.setFormatter(LOG_FORMAT)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LOG_FORMAT)
    root_logger.addHandler(console_handler)
    logging.getLogger('requests').setLevel(logging.ERROR)
    main(root_logger)


if __name__ == '__main__':
    init()
