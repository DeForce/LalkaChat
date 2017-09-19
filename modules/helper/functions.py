import collections

import imp


def find_by_type(data, type_to_find):
    found = collections.OrderedDict()
    for key, value in data.iteritems():
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


def deep_get(dictionary, *keys):
    return reduce(lambda d, key: d.get(key, None) if isinstance(d, collections.Mapping) else None, keys, dictionary)


def get_config_item_path(*keys):
    new_list = list(*keys)
    new_list.insert(1, 'config')
    return new_list


def get_class_from_iname(python_module_path, name):
    python_module = imp.load_source(name, python_module_path)
    python_module_items = [item.upper() for item in dir(python_module)]
    if name.upper() in python_module_items:
        class_name = dir(python_module)[python_module_items.index(name.upper())]
        return getattr(python_module, class_name)
    raise ValueError('Unable to find class from name')
