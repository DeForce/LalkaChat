# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import math
import os
import random
import sqlite3
import xml.etree.ElementTree as ElementTree
import datetime

import sys

from modules.helper.message import process_text_messages, SystemMessage, ignore_system_messages
from modules.helper.parser import save_settings
from modules.helper.system import ModuleLoadException
from modules.helper.module import MessagingModule
from modules.interface.types import *

log = logging.getLogger('levels')

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['message'] = LCText(u'{0} has leveled up, now he is {1}')
CONF_DICT['config']['db'] = LCText(os.path.join('conf', 'levels.db'))
CONF_DICT['config']['experience'] = LCDropdown('geometrical', ['geometrical', 'static', 'random'])
CONF_DICT['config']['exp_for_level'] = LCSpin(200)
CONF_DICT['config']['exp_for_message'] = LCSpin(1, min=0, max=sys.maxsize)
CONF_DICT['config']['decrease_window'] = LCSpin(1, min=0, max=sys.maxsize)

CONF_GUI = {
    'non_dynamic': ['config.db']
}


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
        MessagingModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)

        self.level_file = None
        self.levels = None
        self.special_levels = None
        self.db_location = None
        self.threshold_users = None

    @property
    def db_path(self):
        return self.get_config('config', 'db').simple()

    @property
    def decrease_window(self):
        return self.get_config('config', 'decrease_window').simple()

    @property
    def experience(self):
        return self.get_config('config', 'experience').simple()

    @property
    def exp_for_level(self):
        return self.get_config('config', 'exp_for_level').simple()

    @property
    def exp_for_message(self):
        return self.get_config('config', 'exp_for_message').simple()

    @property
    def message(self):
        return self.get_config('config', 'message')

    def load_module(self, *args, **kwargs):
        MessagingModule.load_module(self, *args, **kwargs)
        self._loaded_modules['webchat'].add_depend('levels')

        self.level_file = None
        self.levels = []
        self.special_levels = {}
        self.db_location = self.db_path
        self.threshold_users = {}

        # Load levels
        webchat_location = self._loaded_modules['webchat'].style_settings['gui_chat']['location']
        if webchat_location and os.path.exists(webchat_location):
            self.level_file = os.path.join(webchat_location, 'levels.xml')
        else:
            log.error("%s not found, generating from template", self.level_file)
            raise ModuleLoadException(f"{self.level_file} not found, generating from template")

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
                self._loaded_modules['webchat'].style_settings['gui_chat']['location'], 'levels.xml'
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
                    level_data.attrib['url'] = f'/{level_data.attrib["url"]}'

                self.levels.append(level_data.attrib)

    def apply_settings(self, **kwargs):
        MessagingModule.apply_settings(self, **kwargs)
        self.load_levels()

    def set_level(self, user):
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
            self.send_system_message(self.message.format(user, self.levels[max_level]['name']))
        cursor.close()
        return self.levels[max_level].copy()

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        if message.user in self.special_levels:
            level_info = self.special_levels[message.user]
            try:
                message.s_levels.append(level_info.copy())
            except AttributeError:
                message.s_levels = [level_info.copy()]
                message.jsonable.append('s_levels')

        message.levels = self.set_level(message.user)
        message.jsonable.append('levels')
        return message

    def calculate_experience(self, user):
        exp_to_add = self.exp_for_message
        if user in self.threshold_users:
            multiplier = (datetime.datetime.now() - self.threshold_users[user]).seconds / float(self.decrease_window)
            exp_to_add *= multiplier if multiplier <= 1 else 1
        self.threshold_users[user] = datetime.datetime.now()
        return exp_to_add
