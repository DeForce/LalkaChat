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

import yaml

from modules.helper.message import process_text_messages, SystemMessage, ignore_system_messages
from modules.helper.parser import save_settings
from modules.helper.system import ModuleLoadException
from modules.helper.module import MessagingModule
from modules.interface.types import *

log = logging.getLogger('levels')

levels_file = 'levels.yaml'

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
        self.levels = []
        self.exp_dict = {}
        self.users = {}
        self.special_levels = {}
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
        self.db_location = self.db_path
        self.threshold_users = {}

        # Load levels
        webchat_location = self._loaded_modules['webchat'].style_settings['gui_chat']['location']
        if webchat_location and os.path.exists(webchat_location):
            self.level_file = os.path.join(webchat_location, levels_file)
        else:
            log.error("%s not found, generating from template", self.level_file)
            raise ModuleLoadException(f"{self.level_file} not found, generating from template")

        if self.experience == 'random':
            self.db_location += '.random'
        self.create_db(self.db_location)

        self.load_levels()
        self.load_players()

    def load_players(self):
        db = sqlite3.connect(self.db_location)

        cursor = db.cursor()
        users_select = cursor.execute('SELECT User, Experience FROM UserLevels')
        users_select = users_select.fetchall()
        for user_q in users_select:
            self.users[user_q[0]] = user_q[1]
        pass

    def load_levels(self):
        if self.levels:
            self.levels = []

        if self.special_levels:
            self.special_levels = {}

        self.level_file = os.path.abspath(
            os.path.join(
                self._loaded_modules['webchat'].style_settings['gui_chat']['location'], levels_file
            )
        )
        with open(self.level_file, 'r', encoding='utf-8') as level_file:
            items = yaml.safe_load(level_file)
        for level_data in items.get('levels', {}):
            level_count = float(len(self.levels) + 1)
            if 'nick' in level_data:
                self.special_levels[level_data['nick']] = level_data
            else:
                if self.experience == 'geometrical':
                    level_exp = math.floor(self.exp_for_level * (pow(level_count, 1.8)/2.0))
                else:
                    level_exp = self.exp_for_level * level_count
                level_data['exp'] = level_exp
                if not level_data['url'].startswith('/'):
                    level_data['url'] = f'/{level_data.get("url", "")}'

                self.levels.append(level_data)
        self.exp_dict = {level['exp']: level for level in self.levels}

    def save_users(self):
        db = sqlite3.connect(self.db_location)
        cursor = db.cursor()
        for user, experience in self.users.items():
            cursor.execute('REPLACE INTO UserLevels (User, Experience) VALUES (?, ?)', [user, experience])
        db.commit()

    def apply_settings(self, **kwargs):
        MessagingModule.apply_settings(self, **kwargs)
        self.save_users()
        self.load_levels()

    def set_level(self, user):
        exp_to_add = self.calculate_experience(user)
        experience = int(self.users.get(user, self.exp_for_message))

        next_level_exp = next((level_exp for level_exp in self.exp_dict.keys() if level_exp > experience),
                              max(self.exp_dict.keys()))
        next_level = self.exp_dict.get(next_level_exp)
        next_level_index = list(self.exp_dict.keys()).index(next_level_exp)
        current_level = self.levels[next_level_index - 1]

        experience = experience + exp_to_add
        # TODO: Figure out better leveling algorithm
        if experience >= next_level_exp:
            if self.experience == 'random':
                current_level = random.choice(self.levels)
                experience = current_level['exp']
            else:
                current_level = next_level
            self.send_system_message(self.message.format(user, current_level['name']))
        self.users[user] = experience
        return current_level.copy()

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
