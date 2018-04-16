# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import math
import os
import random
import sqlite3
import xml.etree.ElementTree as ElementTree
import datetime

from modules.helper.message import process_text_messages, SystemMessage, ignore_system_messages
from modules.helper.parser import save_settings
from modules.helper.system import ModuleLoadException
from modules.helper.module import MessagingModule
from modules.interface.types import *

log = logging.getLogger('levels')

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['message'] = LCText(u'{0} has leveled up, now he is {1}')
CONF_DICT['config']['db'] = LCText(os.path.join('conf', u'levels.db'))
CONF_DICT['config']['experience'] = LCDropdown('geometrical', ['geometrical', 'static', 'random'])
CONF_DICT['config']['exp_for_level'] = LCText(200)
CONF_DICT['config']['exp_for_message'] = LCText(1)
CONF_DICT['config']['decrease_window'] = LCText(1)


CONF_GUI = {
    'non_dynamic': [
        'config.db', 'config.experience',
        'config.exp_for_level', 'config.exp_for_message',
        'decrease_window'],
    'config': {
        'experience': {
            'view': 'dropdown',
            'choices': ['static', 'geometrical', 'random']},
        'exp_for_level': {
            'view': 'spin',
            'min': 0,
            'max': 100000
        },
        'exp_for_message': {
            'view': 'spin',
            'min': 0,
            'max': 100000
        },
        'decrease_window': {
            'view': 'spin',
            'min': 0,
            'max': 100000
        }
    }}


class Levels(MessagingModule):
    @staticmethod
    def create_db(db_location):
        if not os.path.exists(db_location):
            db = sqlite3.connect(db_location)
            cursor = db.cursor()
            log.info("Creating new tables for levels")
            cursor.execute('CREATE TABLE UserLevels (User, "Experience")')
            cursor.close()
            db.commit()
            db.close()

    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)

        self.experience = None
        self.exp_for_level = None
        self.exp_for_message = None
        self.level_file = None
        self.levels = None
        self.special_levels = None
        self.db_location = None
        self.decrease_window = None
        self.threshold_users = None

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def load_module(self, *args, **kwargs):
        MessagingModule.load_module(self, *args, **kwargs)
        if 'webchat' not in self._loaded_modules:
            raise ModuleLoadException("Unable to find webchat module that is needed for level module")
        else:
            self._loaded_modules['webchat']['class'].add_depend('levels')

        conf_dict = self._conf_params['config']

        self.experience = conf_dict['config'].get('experience')
        self.exp_for_level = float(conf_dict['config'].get('exp_for_level'))
        self.exp_for_message = float(conf_dict['config'].get('exp_for_message'))
        self.level_file = None
        self.levels = []
        self.special_levels = {}
        self.db_location = str(os.path.join(conf_dict['config'].get('db')))
        self.decrease_window = int(conf_dict['config'].get('decrease_window'))
        self.threshold_users = {}

        # Load levels
        webchat_location = self._loaded_modules['webchat']['style_settings']['gui']['location']
        if webchat_location and os.path.exists(webchat_location):
            self.level_file = os.path.join(webchat_location, 'levels.xml')
        else:
            log.error("{0} not found, generating from template".format(self.level_file))
            raise ModuleLoadException("{0} not found, generating from template".format(self.level_file))

        if self.experience == 'random':
            self.db_location += '.random'
        self.create_db(self.db_location)

        self.load_levels()

    def load_levels(self):
        if self.levels:
            self.levels = []

        if self.special_levels:
            self.special_levels = {}

        self.level_file = os.path.abspath(
            os.path.join(
                self._loaded_modules['webchat']['style_settings']['gui']['location'], 'levels.xml'
            )
        )
        tree = ElementTree.parse(self.level_file)
        for level_data in tree.getroot():
            level_count = float(len(self.levels) + 1)
            if 'nick' in level_data.attrib:
                self.special_levels[level_data.attrib['nick']] = level_data.attrib
            else:
                if self.experience == 'geometrical':
                    level_exp = math.floor(self.exp_for_level * (pow(level_count, 1.8)/2.0))
                else:
                    level_exp = self.exp_for_level * level_count
                level_data.attrib['exp'] = level_exp
                if not level_data.attrib['url'].startswith('/'):
                    level_data.attrib['url'] = '/{}'.format(level_data.attrib['url'])

                self.levels.append(level_data.attrib)

    def apply_settings(self, **kwargs):
        save_settings(self.conf_params(), ignored_sections=self._conf_params['gui'].get('ignored_sections', ()))
        if 'webchat' in kwargs.get('from_depend', []):
            self.load_levels()

    def set_level(self, user, queue):
        db = sqlite3.connect(self.db_location)

        cursor = db.cursor()
        user_select = cursor.execute('SELECT User, Experience FROM UserLevels WHERE User = ?', [user])
        user_select = user_select.fetchall()

        experience = self.exp_for_message
        exp_to_add = self.calculate_experience(user)
        if len(user_select) == 1:
            row = user_select[0]
            experience = int(row[1]) + exp_to_add
            cursor.execute('UPDATE UserLevels SET Experience = ? WHERE User = ? ', [experience, user])
        elif len(user_select) > 1:
            log.error("Select yielded more than one User")
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
            queue.put(
                SystemMessage(
                    self._conf_params['config']['config']['message'].decode('utf-8').format(
                        user,
                        self.levels[max_level]['name']),
                    category='module'
                )
            )
        cursor.close()
        return self.levels[max_level].copy()

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, queue=None, **kwargs):
        if message.user in self.special_levels:
            level_info = self.special_levels[message.user]
            try:
                message.s_levels.append(level_info.copy())
            except AttributeError:
                message.s_levels = [level_info.copy()]
                message.jsonable.append('s_levels')

        message.levels = self.set_level(message.user, queue)
        message.jsonable.append('levels')
        return message

    def calculate_experience(self, user):
        exp_to_add = self.exp_for_message
        if user in self.threshold_users:
            multiplier = (datetime.datetime.now() - self.threshold_users[user]).seconds / float(self.decrease_window)
            exp_to_add *= multiplier if multiplier <= 1 else 1
        self.threshold_users[user] = datetime.datetime.now()
        return exp_to_add
