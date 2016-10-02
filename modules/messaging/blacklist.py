# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
from modules.helpers.parser import FlagConfigParser


class blacklist:
    users = {}
    words = {}

    def __init__(self, conf_folder):
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "blacklist.cfg")

        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('main')
            config.set('main', 'message', 'Trying to say something but has a trout in his mouth')
            config.add_section('users_gui')
            config.set('users_gui', 'for', 'users_hide, users_block')
            config.set('users_gui', 'view', 'list')
            config.set('users_gui', 'addable', 'true')

            config.add_section('users_hide')
            config.add_section('users_block')

            config.add_section('words_gui')
            config.set('words_gui', 'for', 'users_hide, users_block')
            config.set('words_gui', 'view', 'list')
            config.set('words_gui', 'addable', 'true')

            config.add_section('words_hide')
            config.add_section('words_block')
            config.write(open(conf_file, 'w'))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        sections = config._sections
        for item in sections:
            for param, value in config.get_items(item):
                if item == 'main':
                    if param == 'message':
                        self.message = value.decode('utf-8')
                elif item == 'users_hide':
                    self.users[param] = 'h'
                elif item == 'words_hide':
                    self.words[param] = 'h'
                elif item == 'users_block':
                    self.users[param] = 'b'
                elif item == 'words_block':
                    self.words[param] = 'b'

    def get_message(self, message, queue):
        if message is None:
            return
        else:
            user = self.process_user(message)
            # True = Hide, False = Del, None = Do Nothing
            if user:
                message['text'] = self.message
            elif user == False:
                return

            words = self.process_message(message)
            if words:
                message['text'] = self.message
            elif words == False:
                return

            return message

    def process_user(self, message):
        user = message.get('user').lower()
        if user in self.users:
            if self.users[user] == 'h':
                return True
            else:
                return False
        return None

    def process_message(self, message):
        for word in self.words:
            if re.search(word, message['text'].encode('utf-8')):
                if self.words[word] == 'h':
                    return True
                else:
                    return False
        return None
