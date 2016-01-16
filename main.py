import os, ConfigParser, importlib, threading, Queue

def init():

	# For system compatibility
	pythonFolder=os.path.dirname(os.path.abspath(__file__))
	confFolder=os.path.join(pythonFolder, "conf")
	confFile=os.path.join(confFolder, "modules.cfg")
	moduleFolder=os.path.join(pythonFolder, "modules")
	
	# Trying to load config file.
	if os.path.isdir(confFolder):
		if os.path.isfile(confFile):
			if not os.path.isdir(moduleFolder):
				print "[Error] Could not find %s folder" % moduleFolder
				exit()
		else: 
			print "[Error] Could not find %s" % confFile
			exit()
	else: 
		print "[Error] Could not find %s" % confFolder
		exit()
	
	print "Loading Messaging Handler"
	print "Loading Queue for message handling"
	
	# Creating queues for messaging tranfer between chat threads
	queue = Queue.Queue()
	# Loading module for message processing...
	msgModule=importlib.import_module("messaging").Message(queue)
	
	print "Loading Configuration File"
	moduleTag="modules"	
	
	loadedModules={}
	
	# Trying to dynamically load modules that are in config file.
	config = ConfigParser.RawConfigParser(allow_no_value=True)
	config.read(confFile)
	for module in config.items(moduleTag):
		print "Loading chat module: %s" % module[0]
		if module[1] is not None:
			print "[Error] unable to load module %s: has parameters" % module[0]
			exit()
		if os.path.isfile(os.path.join(moduleFolder, module[0]+".py")):
			print "found %s" %module[0]
			# After module is find, we are initializing it.
			# Module should have __init__ function not in class.
			# Class should be threaded if it needs to run "infinitely"
			loadedModules[module[0]] = importlib.import_module(moduleTag + '.' + module[0])
			# Also passing core folder to module so it can load it's own
			# configuration correctly
			loadedModules[module[0]].__init__(queue, pythonFolder)
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