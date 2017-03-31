# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
import collections
import yaml
from collections import OrderedDict
from ConfigParser import RawConfigParser


def update(d, u, overwrite=True):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v, overwrite=overwrite)
            d[k] = r
        else:
            if not overwrite:
                if k not in d:
                    d[k] = u[k]
                else:
                    continue
            else:
                d[k] = u[k]
    return d


def load_from_config_file(conf_file, conf_dict={}):
    if not os.path.exists(conf_file):
        return conf_dict
    with open(conf_file, 'r') as conf_f:
        loaded_dict = yaml.safe_load(conf_f.read())
    if loaded_dict:
        update(conf_dict, loaded_dict)

    if conf_dict:
        return conf_dict


def return_type(item):
    if item:
        if isinstance(item, bool):
            return item
        elif isinstance(item, int):
            return item
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


def convert_to_yaml(source, ignored_keys):
    output = {}
    if not source:
        return output

    for item, value in source.items():
        if item in ignored_keys:
            continue
        if isinstance(value, OrderedDict):
            output[item] = convert_to_yaml(
                value,
                [key.replace('{}.'.format(item), '') for key in ignored_keys if key.startswith(item)]
            )
        else:
            output[item] = value
    return output


def save_settings(conf_dict, ignored_sections=()):
    if 'file' not in conf_dict:
        return
    output = convert_to_yaml(conf_dict.get('config'), ignored_sections)
    with open(conf_dict.get('file'), 'w+') as conf_file:
        dump_text = yaml.safe_dump(output, default_flow_style=False, allow_unicode=True)
        conf_file.write(dump_text)
