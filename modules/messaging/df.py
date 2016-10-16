# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
from collections import OrderedDict

from modules.helpers.parser import self_heal
from modules.helpers.modules import MessagingModule


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
        conf_dict['prof'] = {'nothing': '([Нн]икто|[Nn]othing|\w*)'}

        conf_gui = {
            'prof': {
                'view': 'list_dual',
                'addable': True},
            'non_dynamic': ['grep.*']}
        config = self_heal(conf_file, conf_dict)
        grep_tag = 'grep'
        prof_tag = 'prof'

        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'config': conf_dict,
                             'gui': conf_gui}
        self.symbol = config.get(grep_tag, 'symbol')
        self.file = config.get(grep_tag, 'file')

        dir_name = os.path.dirname(self.file)
        if not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(self.file))

        if not os.path.isfile(self.file):
            with open(self.file, 'w'):
                pass

        self.prof = []
        for prof, regex in config.items(prof_tag):
            comp = [prof.capitalize(), self.symbol + regex.decode('utf-8')]
            self.prof.append(comp)

    def write_to_file(self, message):
        with open(self.file, 'r') as f:
            for line in f.readlines():
                if message['user'] == line.split(',')[0]:
                    return
            with open(self.file, 'a') as a_file:
                a_file.write("{0},{1}\n".format(message['user'], message['text']))

    def process_message(self, message, queue, **kwargs):
        if message:
            if 'command' in message:
                return message
            for regexp in self.prof:
                if re.search(regexp[1], message['text']):
                    comp = {'user': message['user'], 'text': regexp[0]}
                    self.write_to_file(comp)
                    break
            return message
