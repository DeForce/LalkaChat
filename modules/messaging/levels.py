# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import logging
import math
import os
import random
import sqlite3
import xml.etree.ElementTree as ElementTree
from modules.helpers.parser import self_heal
from modules.helpers.system import system_message, ModuleLoadException
from modules.helpers.modules import MessagingModule

logger = logging.getLogger('levels')


class levels(MessagingModule):
    @staticmethod
    def create_db(db_location):
        if not os.path.exists(db_location):
            db = sqlite3.connect(db_location)
            cursor = db.cursor()
            logger.info("Creating new tables for levels")
            cursor.execute('CREATE TABLE UserLevels (User, "Experience")')
            cursor.close()
            db.commit()
            db.close()

    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Creating filter and replace strings.
        main_settings = kwargs.get('main_settings')

        conf_file = os.path.join(conf_folder, "levels.cfg")
        conf_dict = [
            {'gui_information': {
                'category': u'messaging'}},
            {'config': {
                'message': u'{0} has leveled up, now he is {1}',
                'db': u'levels.db',
                'experience': u'geometrical',
                'exp_for_level': 200}}
        ]
        config = self_heal(conf_file, conf_dict)

        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config}
        tag_config = 'config'

        self.conf_folder = conf_folder
        self.experience = config.get(tag_config, 'experience')
        self.exp_for_level = int(config.get(tag_config, 'exp_for_level'))
        self.exp_for_message = 1
        self.filename = os.path.abspath(os.path.join(main_settings['http_folder'], 'levels.xml'))
        self.levels = []
        self.special_levels = {}
        self.db_location = os.path.join(conf_folder, config.get(tag_config, 'db'))
        self.message = config.get(tag_config, 'message').decode('utf-8')

        # Load levels
        if not os.path.exists(self.filename):
            logger.error("{0} not found, generating from template".format(self.filename))
            raise ModuleLoadException("{0} not found, generating from template".format(self.filename))

        if self.experience == 'random':
            self.db_location += '.random'
        self.create_db(self.db_location)

        tree = ElementTree.parse(os.path.join(conf_folder, self.filename))
        lvl_xml = tree.getroot()

        for level_data in lvl_xml:
            level_count = float(len(self.levels) + 1)
            if 'nick' in level_data.attrib:
                self.special_levels[level_data.attrib['nick']] = level_data.attrib
            else:
                if self.experience == 'geometrical':
                    level_exp = math.floor(self.exp_for_level * (pow(level_count, 1.8)/2.0))
                else:
                    level_exp = self.exp_for_level * level_count
                level_data.attrib['exp'] = level_exp
                self.levels.append(level_data.attrib)

    def set_level(self, user, queue):
        if user == 'System':
            return []
        db = sqlite3.connect(self.db_location)

        cursor = db.cursor()
        user_select = cursor.execute('SELECT User, Experience FROM UserLevels WHERE User = ?', [user])
        user_select = user_select.fetchall()

        experience = 1
        if len(user_select) == 1:
            row = user_select[0]
            experience = int(row[1]) + self.exp_for_message
            cursor.execute('UPDATE UserLevels SET Experience = ? WHERE User = ? ', [experience, user])
        elif len(user_select) > 1:
            logger.error("Select yielded more than one User")
        else:
            cursor.execute('INSERT INTO UserLevels VALUES (?, ?)', [user, experience])
        db.commit()

        max_level = 0
        for level in self.levels:
            if level['exp'] < experience:
                max_level += 1
        if max_level >= len(self.levels):
            max_level -= 1

        if experience >= self.levels[max_level]['exp']:
            if self.experience == 'random':
                max_level = random.randint(0, len(self.levels) - 1)
                experience = self.levels[max_level]['exp'] - self.exp_for_level
                cursor.execute('UPDATE UserLevels SET Experience = ? WHERE User = ? ', [experience, user])
                db.commit()
            else:
                max_level += 1
            system_message(self.message.format(user, self.levels[max_level]['name']), queue)
        cursor.close()
        return self.levels[max_level]

    def process_message(self, message, queue, **kwargs):
        if message:
            if 'command' in message:
                return message
            if 'system_msg' not in message or not message['system_msg']:
                if 'user' in message and message['user'] in self.special_levels:
                    level_info = self.special_levels[message['user']]
                    if 's_levels' in message:
                        message['s_levels'].append(level_info)
                    else:
                        message['s_levels'] = [level_info]

                message['levels'] = self.set_level(message['user'], queue)
            return message
