import os
import ConfigParser
import importlib
import Queue
import messaging
import gui
import thread


def init():
    # For system compatibility, loading chats
    python_folder = os.path.dirname(os.path.abspath(__file__))
    conf_folder = os.path.join(python_folder, "conf")
    module_conf_file = os.path.join(conf_folder, "chat_modules.cfg")

    main_conf_file = os.path.join(conf_folder, "config.cfg")
    gui_tag = 'gui'
    module_folder = os.path.join(python_folder, "modules")

    main_config = {'python': python_folder,
                   'conf': conf_folder,
                   'main': main_conf_file}

    # Trying to load config file.
    if not os.path.isdir(conf_folder):
        print "[Error] Could not find %s folder" % conf_folder
        exit()
    if not os.path.isfile(main_conf_file):
        print "[Error] Could not find %s" % main_conf_file
        exit()
    if not os.path.isfile(module_conf_file):
        print "[Error] Could not find %s" % module_conf_file
        exit()
    if not os.path.isdir(module_folder):
        print "[Error] Could not find %s folder" % module_folder
        exit()

    print "Loading basic configuration"
    config = ConfigParser.ConfigParser(allow_no_value=True)
    config.read(main_conf_file)
    gui_settings = {}
    for param, value in config.items(gui_tag):
        # print param, value
        if param == 'enabled' and value == 'true':
            gui_settings['gui'] = True
        elif param == 'on_top' and value == 'true':
            gui_settings['on_top'] = True
        elif param == 'language' and value == 'true':
            gui_settings['language'] = True

    print "Loading Messaging Handler"
    print "Loading Queue for message handling"

    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    messaging.Message(queue)

    print "Loading Chats Configuration File"
    module_tag = "chats"
    module_import_folder = "modules"

    loaded_modules = {}

    # Trying to dynamically load chats that are in config file.
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(module_conf_file)
    for module in config.items(module_tag):
        print "Loading chat module: %s" % module[0]
        if module[1] is not None:
            print "[Error] unable to load module %s: has parameters" % module[0]
            exit()
        if os.path.isfile(os.path.join(module_folder, module[0] + ".py")):
            print "found %s" % module[0]
            # After module is find, we are initializing it.
            # Module should have __init__ function not in class.
            # Class should be threaded if it needs to run "infinitely"
            loaded_modules[module[0]] = importlib.import_module(module_import_folder + '.' + module[0])
            # Also passing core folder to module so it can load it's own
            # configuration correctly
            loaded_modules[module[0]].__init__(queue, python_folder)
        else:
            # If module find/load fails exit all program
            print "[Error] %s module not found" % module[0]
            exit()

    if gui_settings.get('gui', False):
        print "STARTING GUI"
        window = gui.GuiThread(gui_settings, main_config)
        window.start()
    try:
        while True:
            console = raw_input("> ")
            print console
            if console == "exit":
                print "Exiting now!"
                # exit()
                thread.interrupt_main()
            else:
                print "Incorrect Command"
    except (KeyboardInterrupt, SystemExit):
        print "Exiting now!"
        thread.interrupt_main()
        # exit()
    except Exception as exc:
        print exc


if __name__ == '__main__':
    init()
