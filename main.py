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


def init():
    # For system compatibility, loading chats
    loaded_modules = {}
    gui_settings = {}

    # Setting folder settings
    if hasattr(sys, 'frozen'):
        python_folder = os.path.dirname(sys.executable)
    else:
        python_folder = os.path.dirname(os.path.abspath('__file__'))
    conf_folder = os.path.join(python_folder, "conf")
    module_folder = os.path.join(python_folder, "modules")
    main_conf_file = os.path.join(conf_folder, "config.cfg")
    log_folder = os.path.join(python_folder, "logs")
    gui_tag = 'gui'

    # Set up logging
    log_file = os.path.join(log_folder, 'chat_log.log')
    # debug level
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('main')

    # Creating dict with folder settings
    main_config = {'root_folder': python_folder,
                   'conf_folder': conf_folder,
                   'main_conf_file': main_conf_file,
                   'main_conf_file_loc': main_conf_file,
                   'main_conf_file_name': ''.join(os.path.basename(main_conf_file).split('.')[:-1])}

    if not os.path.isdir(module_folder):
        logging.error("Was not able to find modules folder, check you installation")
        exit()

    # Trying to load config file.
    # Create folder if doesn't exist
    if not os.path.isdir(conf_folder):
        logger.error("Could not find {0} folder".format(conf_folder))
        try:
            os.mkdir(conf_folder)
        except:
            logger.error("Was unable to create {0} folder.".format(conf_folder))
            exit()

    logger.info("Loading basic configuration")
    main_config_dict = [
            {'gui_information': {
                'category': 'main'}},
            {'language__gui': {
                'for': 'language',
                'view': 'choose_single',
                'check_type': 'sections',
                'check': 'conf/translations.cfg'
            }},
            {'gui': {
                'show_hidden': True,
                'gui': True,
                'on_top': True,
                'reload': None
            }},
            {'language': 'english'}
    ]
    config = self_heal(main_conf_file, main_config_dict)
    # Adding config for main module
    loaded_modules['config'] = {'folder': conf_folder,
                                'file': main_config['main_conf_file_loc'],
                                'filename': main_config['main_conf_file_name'],
                                'parser': config,
                                'root_folder': main_config['root_folder'],
                                'logs_folder': log_folder}

    gui_settings['gui'] = config.get(gui_tag, 'gui')
    gui_settings['on_top'] = config.get(gui_tag, 'gui')
    gui_settings['language'],  null_element = config.items('language')[0]
    gui_settings['show_hidden'] = config.get(gui_tag, 'show_hidden')

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
    chat_modules = os.path.join(conf_folder, "chat_modules.cfg")
    chat_tag = "chats"
    chat_location = os.path.join(module_folder, "chats")
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
    loaded_modules['chat_modules'] = {'folder': conf_folder, 'file': chat_modules,
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
