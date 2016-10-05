# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import imp
import Queue
import messaging
import gui
import thread
import sys
import logging
import logging.config
from modules.helpers.parser import FlagConfigParser


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
    gui_tag = 'gui'

    # Set up logging
    log_file = os.path.join(python_folder, 'logs', 'chat_log.log')
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
    config = FlagConfigParser(allow_no_value=True)
    if not os.path.exists(main_conf_file):
        # Creating config from zero
        config.add_section(gui_tag)
        config.set(gui_tag, 'gui', 'true')
        config.set(gui_tag, 'on_top', 'true')
        config.set(gui_tag, 'language', 'english')
        config.set(gui_tag, 'show_hidden', 'true')
        config.set(gui_tag, 'reload')

        config.write(open(main_conf_file))
    config.read(main_conf_file)

    # Adding config for main module
    loaded_modules['config'] = {'folder': conf_folder,
                                'file': main_config['main_conf_file_loc'],
                                'filename': main_config['main_conf_file_name'],
                                'parser': config,
                                'root_folder': main_config['root_folder']}

    items = config.get_dict(gui_tag)  # type: dict
    gui_settings['gui'] = items.get('gui', True)
    gui_settings['on_top'] = items.get('on_top', True)
    gui_settings['language'],  null_element = config.items('language')[0]
    gui_settings['show_hidden'] = items.get('show_hidden', False)

    logger.info("Loading Messaging Handler")
    logger.info("Loading Queue for message handling")

    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    msg = messaging.Message(queue)
    loaded_modules.update(msg.load_modules(main_config))
    msg.start()

    logger.info("Loading Chats")
    module_tag = "chats"
    module_import_folder = "modules"

    # Trying to dynamically load chats that are in config file.
    chat_modules = os.path.join(conf_folder, "chat_modules.cfg")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    if not os.path.exists(chat_modules):
        config.write(open(chat_modules))
    config.read(chat_modules)
    for module in config.items(module_tag):
        logger.info("Loading chat module: {0}".format(module[0]))
        if os.path.isfile(os.path.join(module_folder, module[0] + ".py")):
            logger.info("found {0}".format(module[0]))
            # After module is find, we are initializing it.
            # Class should be named as in config
            # Also passing core folder to module so it can load it's own
            #  configuration correctly
            file_path = os.path.join(main_config['root_folder'], module_import_folder, '{0}.py'.format(module[0]))

            tmp = imp.load_source(module[0], file_path)
            chat_init = getattr(tmp, module[0])
            class_module = chat_init(queue, python_folder)
            loaded_modules[module[0]] = class_module.conf_params
            loaded_modules[module[0]]['class'] = class_module
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
