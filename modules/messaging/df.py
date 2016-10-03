# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
from modules.helpers.parser import FlagConfigParser


class df:
    def __init__(self, conf_folder):
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "df.cfg")

        grep_tag = 'grep'
        prof_tag = 'prof'
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('grep')
            config.set('grep', 'symbol', '#')
            config.set('grep', 'file', 'df.txt')

            config.add_section('prof')
            config.set('prof', 'Nothing', '([Нн]икто|[Nn]othing|\w*)')
            config.write(open(conf_file, 'w'))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        self.symbol = config.get_or_default(grep_tag, 'symbol', '#')
        self.file = config.get_or_default(grep_tag, 'file', 'df.txt')

        if not os.path.isfile(self.file):
            with open(self.file, 'w'):
                pass

        self.prof = []
        for prof in config.get_items(prof_tag):
            comp = [prof[0].capitalize(), self.symbol + prof[1].decode('utf-8')]
            self.prof.append(comp)

    def write_to_file(self, message):
        with open(self.file, 'r') as f:
            for line in f.readlines():
                if message['user'] == line.split(',')[0]:
                    return
            with open(self.file, 'a') as a_file:
                a_file.write("{0},{1}\n".format(message['user'], message['text']))

    def get_message(self, message, queue):
        if message:
            for regexp in self.prof:
                if re.search(regexp[1], message['text']):
                    comp = {'user': message['user'], 'text': regexp[0]}
                    self.write_to_file(comp)
                    break
            return message
