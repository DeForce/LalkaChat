# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import random
import sqlite3
import math
import xml.etree.ElementTree as ElementTree
from modules.helpers.parser import FlagConfigParser


class levels():
    def __init__(self, conf_folder):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "levels.cfg")

        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('config')
            config.set('config', 'experience', 'static')
            config.set('config', 'exp_for_level', 100)
            config.set('config', 'levels', 'levels.xml')
            config.set('config', 'db', 'levels.db')
            config.set('config', 'message', '{0} has leveled up, now he is {1}')

            config.write(open(conf_file))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        tag_config = 'config'

        self.conf_folder = conf_folder
        self.experience = config.get_or_default(tag_config, 'experience', 'static')
        self.exp_for_level = int(config.get_or_default(tag_config, 'exp_for_level', 100))
        self.filename = config.get_or_default(tag_config, 'filename', 'levels.xml')
        self.levels = []
        self.special_levels = []
        self.db = None
        self.db_location = config.get_or_default(tag_config, 'db', None)
        self.cursor = None
        self.message = config.get_or_default(tag_config, 'message', u'{0} has leveled up, now he is {1}').decode('utf-8')

        exists = False
        if self.experience == 'random':
                self.db_location += '.random'
        if os.path.exists(os.path.join(conf_folder, self.db_location)):
            exists = True

        if not exists:
            self.db = sqlite3.connect(os.path.join(conf_folder, self.db_location))
            cursor = self.db.cursor()
            print "Creating new tables"
            cursor.execute('CREATE TABLE UserLevels (User, Experience)')
            cursor.close()
            self.db.commit()
            self.db.close()
            self.db = None

        # Load levels
        tree = ElementTree.parse(os.path.join(conf_folder, self.filename))
        lvl_xml = tree.getroot()

        level_c = 1.0
        level_exp = 0
        for level in lvl_xml:
            if 'nick' in level.attrib:
                self.special_levels.append(level.attrib)
            else:
                if self.experience == 'static':
                    level_exp = eval('self.exp_for_level * level_c')
                    level_c += 1
                    # print level_exp
                elif self.experience == 'geometrical':
                    lvl_old = level_exp
                    level_exp = math.floor(eval('self.exp_for_level * (pow(level_c, 1.8)/2.0)'))
                    level_c += 1
                    # print level_exp - lvl_old
                    # print level_exp
                elif self.experience == 'random':
                    level_exp = eval('self.exp_for_level * level_c')
                    level_c += 1
                level.attrib['exp'] = level_exp
                self.levels.append(level.attrib)

    def set_level(self, user, queue):
        if user == 'System':
            return []
        if self.db is None:
            self.db = sqlite3.connect(os.path.join(self.conf_folder, self.db_location))

        cursor = self.db.cursor()
        user_select = cursor.execute('SELECT User, Experience FROM UserLevels WHERE User = ?', [user])
        user_select = user_select.fetchall()

        add_exp = 1
        if len(user_select) == 1:
            row = user_select[0]

            experience = int(row[1]) + add_exp

            cursor.execute('UPDATE UserLevels SET Experience = ? WHERE User = ? ', [experience, user])
            self.db.commit()
        elif len(user_select) > 1:
            print "wtf, this should not happen"
        else:
            experience = 1

            cursor.execute('INSERT INTO UserLevels VALUES (?, ?)', [user, experience])
            self.db.commit()

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
                self.db.commit()
            else:
                max_level += 1
            lvlup_message = {'source': 'tw',
                             'user': u'System',
                             'text':
                                 self.message.format(user, self.levels[max_level]['name'])}
            queue.put(lvlup_message)
        cursor.close()
        return self.levels[max_level]

    def get_message(self, message, queue):
        if message is None:
            # print "levels recieved empty message"
            return
        else:
            message['s_levels'] = []

            for user in self.special_levels:
                if message['user'] == user['nick']:
                    level_info = {'name': user['name'], 'url': user['url']}
                    message['s_levels'].append(level_info)

            message['levels'] = self.set_level(message['user'], queue)

            if not len(message['s_levels']):
                message.pop('s_levels')
            if not len(message['levels']):
                message.pop('levels')

            return message
