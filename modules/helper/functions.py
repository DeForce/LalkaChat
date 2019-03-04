import collections

import imp

import os

from modules.helper.system import PYTHON_FOLDER


def find_by_type(data, type_to_find):
    found = collections.OrderedDict()
    for key, value in data.items():
        if isinstance(value, type_to_find):
            found[key] = None
        if isinstance(value, collections.Mapping):
            types = find_by_type(data.get(key, {}), type_to_find)
            if types:
                found[key] = types
                continue
    return found


def parse_keys_to_string(data):
    keys = []
    for name, value in data.items():
        keys.append(name)
        if isinstance(value, collections.Mapping):
            keys_from_dict = parse_keys_to_string(data.get(name, {}))
            if keys_from_dict:
                keys.extend(['.'.join([name] + [item]) for item in keys_from_dict])
    return keys


def get_config_item_path(*keys):
    new_list = list(*keys)
    return new_list


def get_modules_in_folder(folder):
    item_path = os.path.join(PYTHON_FOLDER, 'modules', folder)
    return [item.strip('.py') for item in os.listdir(item_path)
            if os.path.isfile(os.path.join(item_path, item))
            and not item.startswith('_')
            and not item.endswith('.pyc')]


def get_themes():
    item_path = os.path.join(PYTHON_FOLDER, 'http')
    return [item for item in os.listdir(item_path)
            if os.path.isdir(os.path.join(item_path, item))]


def get_class_from_iname(python_module_path, name):
    python_module = imp.load_source(name, python_module_path)
    python_module_items = [item.upper() for item in dir(python_module)]
    if name.upper() in python_module_items:
        class_name = dir(python_module)[python_module_items.index(name.upper())]
        return getattr(python_module, class_name)
    raise ValueError('Unable to find class from name')
