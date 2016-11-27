# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
from collections import OrderedDict

from modules.helper.parser import load_from_config_file
from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES


class df(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "df.cfg")

        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {'category': 'messaging'}
        conf_dict['grep'] = OrderedDict()
        conf_dict['grep']['symbol'] = '#'
        conf_dict['grep']['file'] = 'logs/df.txt'
        conf_dict['prof'] = OrderedDict()

        conf_gui = {
            'prof': {
                'view': 'list_dual',
                'addable': True},
            'non_dynamic': ['grep.*']}
        config = load_from_config_file(conf_file, conf_dict)

        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'config': conf_dict,
             'gui': conf_gui})
        self.file = conf_dict['grep']['file']

        dir_name = os.path.dirname(self.file)
        if not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(self.file))

        if not os.path.isfile(self.file):
            with open(self.file, 'w'):
                pass

    def write_to_file(self, user, role):
        with open(self.file, 'r') as f:
            for line in f.readlines():
                if user == line.split(',')[0]:
                    return
        with open(self.file, 'a') as a_file:
            a_file.write("{0},{1}\n".format(user, role))

    def process_message(self, message, queue, **kwargs):
        if message:
            if message['type'] in IGNORED_TYPES:
                return message
            for role, regexp in self._conf_params['config']['prof'].iteritems():
                if re.search('{0}{1}'.format(self._conf_params['config']['grep']['symbol'], regexp).decode('utf-8'),
                             message['text']):
                    self.write_to_file(message['user'], role.capitalize())
                    break
            return message
