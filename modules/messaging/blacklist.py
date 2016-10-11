# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
from modules.helpers.parser import self_heal
from modules.helpers.modules import MessagingModule

DEFAULT_PRIORITY = 30


class blacklist(MessagingModule):
    users = {}
    words = {}

    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "blacklist.cfg")
        config_dict = [
            {'gui_information': {
                'category': 'messaging',
                'id': DEFAULT_PRIORITY}},
            {'main': {
                'message': u'ignored message'}},
            {'users__gui': {
                'for': 'users_hide, users_block',
                'view': 'list',
                'addable': 'true'}},
            {'users_hide': {}},
            {'users_block': {
                'announce': None}},
            {'words__gui': {
                'for': 'words_hide, words_block',
                'addable': True,
                'view': 'list'}}
        ]

        config = self_heal(conf_file, config_dict)
        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'id': config.get('gui_information', 'id')}

        for item in config.sections():
            for param, value in config.items(item):
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

    def process_message(self, message, queue, **kwargs):
        if message:
            if 'command' in message:
                return message
            user = self.blacklist_user_handler(message)
            # True = Hide, False = Del, None = Do Nothing
            if user:
                message['text'] = self.message
            elif user is False:
                return

            words = self.blacklist_message_handler(message)
            if words:
                message['text'] = self.message
            elif words is False:
                return

            return message

    def blacklist_user_handler(self, message):
        user = message.get('user').lower()
        if user in self.users:
            if self.users[user] == 'h':
                return True
            else:
                return False
        return None

    def blacklist_message_handler(self, message):
        for word in self.words:
            if re.search(word, message['text'].encode('utf-8')):
                if self.words[word] == 'h':
                    return True
                else:
                    return False
        return None
