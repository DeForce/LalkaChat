# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import imp
import Queue
import messaging
import gui
import thread
import sys
import logging
import logging.config
from modules.helpers.parser import self_heal
from modules.helpers.system import load_translations_keys


if hasattr(sys, 'frozen'):
    python_folder = os.path.dirname(sys.executable)
else:
    python_folder = os.path.dirname(os.path.abspath('__file__'))
TRANSLATION_FOLDER = os.path.join(python_folder, "translations")
CONF_FOLDER = os.path.join(python_folder, "conf")
MODULE_FOLDER = os.path.join(python_folder, "modules")
MAIN_CONF_FILE = os.path.join(CONF_FOLDER, "config.cfg")
GUI_TAG = 'gui'

LOG_FOLDER = os.path.join(python_folder, "logs")
LOG_FILE = os.path.join(LOG_FOLDER, 'chat_log.log')
LOG_FORMAT = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s]  %(message)s")

root_logger = logging.getLogger()
root_logger.setLevel(level=logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(LOG_FORMAT)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
root_logger.addHandler(console_handler)

logger = logging.getLogger('main')


def init():
    # For system compatibility, loading chats
    loaded_modules = {}
    gui_settings = {}

    # Creating dict with folder settings
    main_config = {'root_folder': python_folder,
                   'conf_folder': CONF_FOLDER,
                   'main_conf_file': MAIN_CONF_FILE,
                   'main_conf_file_loc': MAIN_CONF_FILE,
                   'main_conf_file_name': ''.join(os.path.basename(MAIN_CONF_FILE).split('.')[:-1])}

    if not os.path.isdir(MODULE_FOLDER):
        logging.error("Was not able to find modules folder, check you installation")
        exit()

    # Trying to load config file.
    # Create folder if doesn't exist
    if not os.path.isdir(CONF_FOLDER):
        logger.error("Could not find {0} folder".format(CONF_FOLDER))
        try:
            os.mkdir(CONF_FOLDER)
        except:
            logger.error("Was unable to create {0} folder.".format(CONF_FOLDER))
            exit()

    logger.info("Loading basic configuration")
    main_config_dict = [
            {'gui_information': {
                'category': 'main'}},
            {'language__gui': {
                'for': 'language',
                'view': 'choose_single',
                'check_type': 'dir',
                'check': 'translations'
            }},
            {'gui': {
                'show_hidden': True,
                'gui': True,
                'on_top': True,
                'reload': None
            }},
            {'language': 'english'}
    ]
    config = self_heal(MAIN_CONF_FILE, main_config_dict)
    # Adding config for main module
    loaded_modules['config'] = {'folder': CONF_FOLDER,
                                'file': main_config['main_conf_file_loc'],
                                'filename': main_config['main_conf_file_name'],
                                'parser': config,
                                'root_folder': main_config['root_folder'],
                                'logs_folder': LOG_FOLDER}

    gui_settings['gui'] = config.get(GUI_TAG, 'gui')
    gui_settings['on_top'] = config.get(GUI_TAG, 'gui')
    gui_settings['language'],  null_element = config.items('language')[0]
    gui_settings['show_hidden'] = config.get(GUI_TAG, 'show_hidden')

    logger.info("Loading Messaging Handler")
    logger.info("Loading Queue for message handling")

    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    msg = messaging.Message(queue)
    loaded_modules.update(msg.load_modules(main_config))
    msg.start()

    logger.info("Loading Chats")
    # Trying to dynamically load chats that are in config file.
    chat_modules = os.path.join(CONF_FOLDER, "chat_modules.cfg")
    chat_tag = "chats"
    chat_location = os.path.join(MODULE_FOLDER, "chats")
    chat_conf_dict = [
        {'gui_information': {
            'category': 'main'}},
        {'chats__gui': {
            'for': 'chats',
            'view': 'choose_multiple',
            'check_type': 'files',
            'check': 'modules/chats',
            'file_extension': False}},
        {'chats': {}}
    ]

    chat_config = self_heal(chat_modules, chat_conf_dict)
    loaded_modules['chat_modules'] = {'folder': CONF_FOLDER, 'file': chat_modules,
                                      'filename': ''.join(os.path.basename(chat_modules).split('.')[:-1]),
                                      'parser': chat_config}

    for module, settings in chat_config.items(chat_tag):
        logger.info("Loading chat module: {0}".format(module))
        module_location = os.path.join(chat_location, module + ".py")
        if os.path.isfile(module_location):
            logger.info("found {0}".format(module))
            # After module is find, we are initializing it.
            # Class should be named as in config
            # Also passing core folder to module so it can load it's own
            #  configuration correctly

            tmp = imp.load_source(module, module_location)
            chat_init = getattr(tmp, module)
            class_module = chat_init(queue, python_folder)
            loaded_modules[module] = class_module.conf_params
            loaded_modules[module]['class'] = class_module
        else:
            logger.error("Unable to find {0} module")
    try:
        load_translations_keys(TRANSLATION_FOLDER, gui_settings['language'])
    except:
        logger.exception("Failed loading translations")

    if gui_settings['gui']:
        logger.info("Loading GUI Interface")
        window = gui.GuiThread(gui_settings=gui_settings,
                               main_config=loaded_modules['config'],
                               loaded_modules=loaded_modules)
        window.start()
    try:
        while True:
            console = raw_input("> ")
            logger.info(console)
            if console == "exit":
                logger.info("Exiting now!")
                thread.interrupt_main()
            else:
                logger.info("Incorrect Command")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting now!")
        thread.interrupt_main()
    except Exception as exc:
        logger.info(exc)


if __name__ == '__main__':
    init()
