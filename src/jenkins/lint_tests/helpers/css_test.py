import json
import os

from scss import Compiler
from scss.namespace import Namespace
from scss.types import String, Boolean, Number
SCSS_MAP = {
    basestring: String,
    bool: Boolean,
    int: Number,
    float: Number
}


def render_scss_file(filename, namespace):
    root_dir = os.path.dirname(filename)
    base_name, base_extension = os.path.splitext(os.path.basename(filename))
    render_filename = os.path.join(root_dir, 'render_{}.css'.format(base_name))
    with open(filename, 'r') as css_file, open(render_filename, 'w') as render_file:
        css_content = css_file.read()
        compiler = Compiler(namespace=namespace, output_style='compressed')
        render_file.write(compiler.compile_string(css_content))


if __name__ == '__main__':
    for folder in os.listdir('http'):
        # Load keys
        cur_path = os.path.join('http', folder)
        with open(os.path.join(cur_path, 'settings.json'), 'r') as json_settings:
            setting_keys = json.load(json_settings)

        css_namespace = Namespace()
        for key, value in setting_keys.items():
            for base_class, scss_class in SCSS_MAP.items():
                if isinstance(value, base_class):
                    css_namespace.set_variable('${}'.format(key), scss_class(value))
                    break

        for item in os.listdir(os.path.join(cur_path, 'css')):
            if item.endswith('.css'):
                pass
            elif item.endswith('.scss'):
                render_scss_file(os.path.join(cur_path, 'css', item), css_namespace)
            else:
                pass
