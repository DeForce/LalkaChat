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
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, CONFIG_FILE)

        # Ordered because order matters
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'test',
            'id': DEFAULT_PRIORITY}

        config = load_from_config_file(conf_file, conf_dict)
        self._conf_params.update({
            'folder': conf_folder, 'file': conf_file,
            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
            'parser': config,
            'id': conf_dict['gui_information']['id'],
            'config': OrderedDict(conf_dict),
            'custom_renderer': True
        })

    def render(self, *args, **kwargs):
        print "HelloWorld"
        pass
