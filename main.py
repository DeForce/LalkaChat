# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import imp
import Queue
import messaging
import gui
import sys
import logging
import logging.config
from modules.helpers.parser import self_heal
from modules.helpers.system import load_translations_keys


if hasattr(sys, 'frozen'):
    PYTHON_FOLDER = os.path.dirname(sys.executable)
else:
    PYTHON_FOLDER = os.path.dirname(os.path.abspath('__file__'))
TRANSLATION_FOLDER = os.path.join(PYTHON_FOLDER, "translations")
CONF_FOLDER = os.path.join(PYTHON_FOLDER, "conf")
MODULE_FOLDER = os.path.join(PYTHON_FOLDER, "modules")
MAIN_CONF_FILE = os.path.join(CONF_FOLDER, "config.cfg")
HTTP_FOLDER = os.path.join(PYTHON_FOLDER, "http")
GUI_TAG = 'gui'

LOG_FOLDER = os.path.join(PYTHON_FOLDER, "logs")
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, 'chat_log.log')
LOG_FORMAT = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s]  %(message)s")

root_logger = logging.getLogger()
# Logging level
root_logger.setLevel(level=logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(LOG_FORMAT)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
root_logger.addHandler(console_handler)

logger = logging.getLogger('main')


def init():
    def close():
        if window:
            window.gui.on_close('Closing Program from console')
        else:
            os._exit(0)
    # For system compatibility, loading chats
    loaded_modules = {}
    gui_settings = {}
    window = None

    # Creating dict with folder settings
    main_config = {'root_folder': PYTHON_FOLDER,
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
            'category': 'main',
            'width': 450,
            'height': 500}},
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
        {'style__gui': {
            'check': 'http',
            'check_type': 'dir',
            'for': 'style',
            'view': 'choose_single'}},
        {'style': 'czt'},
        {'language': 'en'}
    ]
    config = self_heal(MAIN_CONF_FILE, main_config_dict)
    # Adding config for main module
    loaded_modules['config'] = {'folder': CONF_FOLDER,
                                'file': main_config['main_conf_file_loc'],
                                'filename': main_config['main_conf_file_name'],
                                'parser': config,
                                'root_folder': main_config['root_folder'],
                                'logs_folder': LOG_FOLDER}

    gui_settings['gui'] = config.getboolean(GUI_TAG, 'gui')
    gui_settings['on_top'] = config.getboolean(GUI_TAG, 'gui')
    gui_settings['language'],  null_element = config.items('language')[0]
    gui_settings['show_hidden'] = config.getboolean(GUI_TAG, 'show_hidden')
    gui_settings['size'] = (config.getint('gui_information', 'width'),
                            config.getint('gui_information', 'height'))
    # Fallback if style folder not found
    fallback_style = 'czt'
    if len(config.items('style')) > 0:
        style, null_element = config.items('style')[0]
        path = os.path.abspath(os.path.join(HTTP_FOLDER, style))
        if os.path.exists(path):
            gui_settings['style'] = style
        else:
            gui_settings['style'] = fallback_style
    else:
        gui_settings['style'] = fallback_style
    loaded_modules['config']['http_folder'] = os.path.join(HTTP_FOLDER, gui_settings['style'])

    logger.info("Loading Messaging Handler")
    logger.info("Loading Queue for message handling")

    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    msg = messaging.Message(queue)
    loaded_modules.update(msg.load_modules(main_config, loaded_modules['config']))
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
            class_module = chat_init(queue, PYTHON_FOLDER)
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
                               loaded_modules=loaded_modules,
                               queue=queue)
        window.start()
    try:
        while True:
            console = raw_input("> ")
            logger.info(console)
            if console == "exit":
                logger.info("Exiting now!")
                close()
            else:
                logger.info("Incorrect Command")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting now!")
        close()
    except Exception as exc:
        logger.info(exc)

if __name__ == '__main__':
    init()
