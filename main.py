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
    loaded_module_config = []
    loaded_modules = {}
    gui_settings = {}

    if hasattr(sys, 'frozen'):
        python_folder = os.path.dirname(sys.executable)
    else:
        python_folder = os.path.dirname(os.path.abspath('__file__'))
    conf_folder = os.path.join(python_folder, "conf")
    module_folder = os.path.join(python_folder, "modules")

    chats_conf_file = os.path.join(conf_folder, "chat_modules.cfg")
    main_conf_file = os.path.join(conf_folder, "config.cfg")
    gui_tag = 'gui'

    # Set up logging
    log_file = os.path.join(python_folder, 'logs', 'chat_log.log')
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('main')

    main_config = {'python': python_folder,
                   'conf': conf_folder,
                   'main': main_conf_file,
                   'file_loc': main_conf_file,
                   'filename': ''.join(os.path.basename(main_conf_file).split('.')[:-1])}

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

    loaded_module_config.append({'config': {'folder': conf_folder, 'file': main_config['file_loc'],
                                            'filename': ''.join(os.path.basename(main_config['file_loc']).split('.')[:-1]),
                                            'parser': config}})

    items = config.get_dict(gui_tag)  # type: dict
    gui_settings['gui'] = items.get('enabled', True)
    gui_settings['on_top'] = items.get('on_top', True)
    gui_settings['language'] = items.get('language', 'english')

    logger.info("Loading Messaging Handler")
    logger.info("Loading Queue for message handling")

    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    msg = messaging.Message(queue)

    loaded_module_config += msg.modules_configs

    logger.info("Loading Chats Configuration File")
    module_tag = "chats"
    module_import_folder = "modules"

    # Trying to dynamically load chats that are in config file.
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    if not os.path.exists(chats_conf_file):
        config.write(open(chats_conf_file))
    config.read(chats_conf_file)
    module_id = 1
    for module in config.items(module_tag):
        logger.info("Loading chat module: {0}".format(module[0]))
        if os.path.isfile(os.path.join(module_folder, module[0] + ".py")):
            logger.info("found {0}".format(module[0]))
            # After module is find, we are initializing it.
            # Class should be named as in config
            # Also passing core folder to module so it can load it's own
            #  configuration correctly
            file_path = os.path.join(main_config['python'], module_import_folder, '{0}.py'.format(module[0]))

            tmp = imp.load_source(module[0], file_path)
            class_name = getattr(tmp, module[0])
            loaded_modules[module[0]] = class_name(queue, python_folder)
            loaded_module_config.insert(module_id, {module[0]: loaded_modules[module[0]].conf_params})
            module_id += 1
    if gui_settings['gui']:
        logger.info("STARTING GUI")
        window = gui.GuiThread(gui_settings=gui_settings, main_config=main_config, modules_configs=loaded_module_config)
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
