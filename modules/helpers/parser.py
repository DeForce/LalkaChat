import os
from ConfigParser import RawConfigParser
from collections import OrderedDict


def self_heal(conf_file, heal_dict):
    heal_config = get_config(conf_file)
    for section, section_value in heal_dict.items():
        if not heal_config.has_section(section):
            heal_config.add_section(section)
        if type(section_value) in [OrderedDict, dict]:
            if section_value:
                for item, value in section_value.items():
                    if not heal_config.has_option(section, item):
                        heal_config.set(section, item, value)
                for item, value in heal_config.items(section):
                    heal_dict[section][item] = return_type(value)
            else:
                heal_dict[section] = OrderedDict()
                for item, value in heal_config.items(section):
                    heal_dict[section][item] = value
        else:
            if len(heal_config.items(section)) != 1:
                for r_item, r_value in heal_config.items(section):
                    heal_config.remove_option(section, r_item)
                heal_config.set(section, section_value)
            else:
                heal_dict[section] = heal_config.items(section)[0][0]

    heal_config.write(open(conf_file, 'w'))
    return heal_config


def return_type(item):
    if item:
        try:
            return int(item)
        except:
            if item.lower() == 'true':
                return True
            elif item.lower() == 'false':
                return False
    return item


def get_config(conf_file):
    dir_name = os.path.dirname(conf_file)
    if not os.path.exists(dir_name):
        os.makedirs(os.path.dirname(conf_file))

    heal_config = RawConfigParser(allow_no_value=True)
    if os.path.exists(conf_file):
        heal_config.read(conf_file)
    return heal_config
