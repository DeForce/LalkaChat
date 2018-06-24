# Copyright (C) 2016   CzT/Vladislav Ivanov
import collections

import os

import rtyaml
from ConfigParser import RawConfigParser

from modules.interface.types import *

DICT_MAPPING = {
    LCPanel: dict,
    LCStaticBox: dict,
}


def update(dst, src, overwrite=True):
    for k, v in src.items():
        has_key = k in dst
        dst_type = type(dst.get(k, v))

        if isinstance(v, (LCDict, collections.Mapping)):
            r = update(dst.get(k, {}), v, overwrite=overwrite)
            dst[k] = r
        else:
            if has_key and not overwrite:
                if isinstance(v, LCObject) and not isinstance(dst.get(k), LCObject):
                    dst[k] = type(v)(dst.get(k))
                continue
            elif has_key:
                if isinstance(dst.get(k), LCObject):
                    if hasattr(dst[k], '_value'):
                        dst[k].value = v.value if isinstance(v, LCObject) else v
                    else:
                        dst[k] = dst_type(v)
                else:
                    dst[k] = v
            else:
                dst[k] = dst_type(v)
    return dst


def lc_replace(dst, src):
    for k, v in src.items():
        if isinstance(v, LCDict):
            dst[k] = update(dst[k], v)
        else:
            item_value = dst[k].value if k in dst else src[k].value
            dst[k] = src[k]
            dst[k].value = item_value


def load_from_config_file(conf_file, conf_dict=None):
    if not os.path.exists(conf_file):
        return conf_dict
    with open(conf_file, 'r') as conf_f:
        loaded_dict = rtyaml.load(conf_f.read())
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


def convert_to_dict(source, ignored_keys=(), ordered=True):
    output = OrderedDict() if ordered else {}
    if not source:
        return output

    for item, value in source.items():
        if item in ignored_keys:
            continue
        if type(value) in DICT_MAPPING:
            output[item] = convert_to_dict(
                value,
                [key.replace('{}.'.format(item), '') for key in ignored_keys if key.startswith(item)],
                ordered=ordered)
        else:
            try:
                output[item] = value.simple()
            except Exception as exc:
                logging.debug(exc)
                output[item] = value
    return output


def save_settings(conf_dict, ignored_sections=()):
    if 'file' not in conf_dict:
        return
    output = convert_to_dict(conf_dict.get('config'), ignored_sections)
    with open(conf_dict.get('file'), 'w+') as conf_file:
        dump_text = rtyaml.dump(output)
        conf_file.write(dump_text)
