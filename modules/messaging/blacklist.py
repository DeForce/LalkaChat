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

        users_tag = 'users'
        words_tag = 'words'

        self.users = []
        for user in config.items(users_tag):
            comp = [user[0], user[1]]
            self.users.append(comp)

        self.words = []
        for word in config.items(words_tag):
            comp = [word[0], word[1]]
            self.words.append(comp)

    def get_message(self, message):
        for regexp in self.users:
            if re.search(regexp[1], message['user']):
                message['flags'] = 'hidden'
                break

        for regexp in self.words:
            if re.search(regexp[1], message['text']):
                message['flags'] = 'hidden'
                break

        return message
