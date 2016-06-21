import os
import ConfigParser
import importlib
import threading
import Queue
import messaging


def init():

    # For system compatibility
    python_folder = os.path.dirname(os.path.abspath(__file__))
    conf_folder = os.path.join(python_folder, "conf")
    conf_file = os.path.join(conf_folder, "modules.cfg")
    module_folder = os.path.join(python_folder, "modules")
    
    # Trying to load config file.
    if os.path.isdir(conf_folder):
        if os.path.isfile(conf_file):
            if not os.path.isdir(module_folder):
                print "[Error] Could not find %s folder" % module_folder
                exit()
        else: 
            print "[Error] Could not find %s" % conf_file
            exit()
    else: 
        print "[Error] Could not find %s" % conf_folder
        exit()
    
    print "Loading Messaging Handler"
    print "Loading Queue for message handling"
    
    # Creating queues for messaging transfer between chat threads
    queue = Queue.Queue()
    # Loading module for message processing...
    msg_module = messaging.Message(queue)
    
    print "Loading Configuration File"
    module_tag = "modules"
    
    loaded_modules = {}
    
    # Trying to dynamically load modules that are in config file.
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(conf_file)
    for module in config.items(module_tag):
        print "Loading chat module: %s" % module[0]
        if module[1] is not None:
            print "[Error] unable to load module %s: has parameters" % module[0]
            exit()
        if os.path.isfile(os.path.join(module_folder, module[0]+ ".py")):
            print "found %s" % module[0]
            # After module is find, we are initializing it.
            # Module should have __init__ function not in class.
            # Class should be threaded if it needs to run "infinitely"
            loaded_modules[module[0]] = importlib.import_module(module_tag + '.' + module[0])
            # Also passing core folder to module so it can load it's own
            # configuration correctly
            loaded_modules[module[0]].__init__(queue, python_folder)
        else: 
            # If module find/load fails exit all programm
            print "[Error] %s module not found" % module[0]
            exit()
    
    while True:
        try:
            console = raw_input("> ")
            print console
            if console == "exit":
                print "Exiting now!"
                exit()
            else:
                print "Incorrect Command"
        except KeyboardInterrupt:
            print "Exiting now!"
            exit()
