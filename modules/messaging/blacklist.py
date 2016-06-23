# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import re
import os
import ConfigParser


class blacklist():
    def __init__(self, conf_folder):
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "blacklist.cfg")

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(conf_file)

        tag_config = 'main'
        tag_users = 'users'
        tag_users_hide = 'users_hide'
        tag_words = 'words'
        tag_words_hide = 'words_hide'

        for item in config.items(tag_config):
            if item[0] == 'message':
                self.blacklist_message = item[1].decode('utf-8')

        self.users = []
        for user in config.items(tag_users):
            comp = {'type': user[0], 'filter': user[1].split(',')}
            comp['filter'] = map(lambda x: x.strip().decode('utf-8'), comp['filter'])
            self.users.append(comp)
        for user in config.items(tag_users_hide):
            comp = {'type': 'hide', 'filter': user[1].split(',')}
            comp['filter'] = map(lambda x: x.strip().decode('utf-8'), comp['filter'])
            self.users.append(comp)

        self.words = []
        for word in config.items(tag_words):
            comp = {'type': word[0], 'filter': word[1]}
            self.words.append(comp)
        for word in config.items(tag_words_hide):
            comp = {'type': 'hide', 'filter': word[1]}
            self.words.append(comp)

    def get_message(self, message):
        if message is None:
            # print "Blackist recieved no message"
            return
        else:
            for regexp in self.users:
                for re_item in regexp['filter']:
                    if message['user'] == re_item:
                        if regexp['type'] == 'hide':
                            message['flags'] = 'hide'
                        else:
                            message['flags'] = 'blacklist'
                        break

            for regexp in self.words:
                if re.search(regexp['filter'], message['text']):
                    if regexp['type'] == 'hide':
                        message['flags'] = 'hide'
                    else:
                        message['flags'] = 'blacklist'
                    break

            if message['flags'] == 'blacklist':
                message['text'] = self.blacklist_message

            if message['flags'] == 'hide':
                return
            return message
