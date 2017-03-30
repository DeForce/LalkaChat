# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
from collections import OrderedDict
from modules.helper.parser import load_from_config_file
from modules.helper.module import MessagingModule

DEFAULT_PRIORITY = 30
CONFIG_FILE = 'test_module.cfg'


class test_module(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)

    def render(self, *args, **kwargs):
        print "HelloWorld"
