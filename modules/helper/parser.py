import os
from ConfigParser import RawConfigParser


def load_from_config_file(conf_file, conf_dict):
    config_parser = get_config(conf_file)

    for section in config_parser.sections():
        if section not in conf_dict.keys():
            continue

        if isinstance(conf_dict[section], dict):
            tmp_dict = {}
            for item, value in config_parser.items(section):
                tmp_dict[item] = return_type(value)
            conf_dict[section].update(tmp_dict)
        elif isinstance(conf_dict[section], list):
            pass
        else:
            conf_dict[section] = return_type(config_parser.items(section)[0][0])
    return config_parser


def return_type(item):
    if item:
        if isinstance(item, bool):
            return item
        elif isinstance(item, int):
            return str(item)
        elif item.lower() == 'true':
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


def save_settings(conf_dict, ignored_sections=()):
    if 'parser' not in conf_dict:
        return
    if 'config' not in conf_dict:
        return

    parser = conf_dict.get('parser')  # type: RawConfigParser
    config = conf_dict.get('config')

    for section, section_object in config.iteritems():
        if section in ignored_sections:
            continue

        if parser.has_section(section):
            parser.remove_section(section)
        parser.add_section(section)

        if isinstance(section_object, dict):
            for item, value in section_object.iteritems():
                parser.set(section, item, value)
        else:
            parser.set(section, section_object)

    with open(conf_dict.get('file'), 'w+') as conf_file:
        parser.write(conf_file)
