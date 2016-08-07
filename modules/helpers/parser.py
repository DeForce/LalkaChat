from ConfigParser import ConfigParser


class FlagConfigParser(ConfigParser):
    keyword = '/'
    flag_keyword = ','
    section_keyword = ':'

    def items_skip_flags(self, section):
        items = self.items(section)
        return [(param.split(self.keyword)[0], value) for param, value in items]

    def items_with_flags(self, section):
        items = self.items(section)
        for param, value in items:
            split_param = param.split(self.keyword)
            # print split_param
            if len(split_param) > 1:
                yield split_param[0], value, split_param[1].split(self.flag_keyword)
            else:
                yield split_param[0], value, []

    def get_items(self, section, flags=False, s_flags=False):
        if flags:
            return self.items_with_flags(section)
        else:
            return self.items_skip_flags(section)
