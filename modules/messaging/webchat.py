# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
import threading
import json
import Queue
import socket
import cherrypy
import logging
import datetime
import copy
from scss import Compiler
from scss.namespace import Namespace
from scss.types import Value, Boolean, String, Number
from collections import OrderedDict
from cherrypy.lib.static import serve_file
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from modules.helper.parser import load_from_config_file, save_settings
from modules.helper.system import THREADS, PYTHON_FOLDER, CONF_FOLDER
from modules.helper.module import MessagingModule
from gui import MODULE_KEY

DEFAULT_STYLE = 'default'
DEFAULT_PRIORITY = 9001
HISTORY_SIZE = 20
HISTORY_TYPES = ['system_message', 'message']
HTTP_FOLDER = os.path.join(PYTHON_FOLDER, "http")
s_queue = Queue.Queue()
logging.getLogger('ws4py').setLevel(logging.ERROR)
log = logging.getLogger('webchat')
SCSS_MAP = {
    basestring: String,
    bool: Boolean,
    int: Number,
    float: Number
}


def prepare_message(msg, theme_name):
    message = copy.deepcopy(msg)

    if 'levels' in message:
        message['levels']['url'] = '{}?{}'.format(message['levels']['url'], theme_name)

    return message


class MessagingThread(threading.Thread):
    def __init__(self, settings):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.settings = settings
        self.running = True

    def run(self):
        while self.running:
            message = s_queue.get()
            if 'timestamp' not in message:
                message['timestamp'] = datetime.datetime.now().isoformat()

            if message['type'] in HISTORY_TYPES:
                cherrypy.engine.publish('add-history', message)
            elif message['type'] == 'command':
                cherrypy.engine.publish('process-command', message['command'], message)

            if message['type'] == 'system_message' and not self.settings['keys'].get('show_system_msg', True):
                continue

            send_message = prepare_message(message, self.settings['name'])

            cherrypy.engine.publish('websocket-broadcast', json.dumps(send_message))
        log.info("Messaging thread stopping")

    def stop(self):
        self.running = False


class FireFirstMessages(threading.Thread):
    def __init__(self, ws, history, settings):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.ws = ws  # type: WebChatSocketServer
        self.history = history
        self.settings = settings

    def run(self):
        show_system_msg = cherrypy.engine.publish('get-settings')[0]['keys'].get('show_system_msg', True)
        if self.ws.stream:
            for item in self.history:
                if item['type'] == 'system_message' and not show_system_msg:
                    continue
                timestamp = datetime.datetime.strptime(item['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
                timedelta = datetime.datetime.now() - timestamp
                timer = int(self.settings['keys'].get('timer', 0))
                if timer > 0:
                    if timedelta > datetime.timedelta(seconds=timer):
                        continue

                message = prepare_message(item, self.settings['name'])
                self.ws.send(json.dumps(message))


class WebChatSocketServer(WebSocket):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        WebSocket.__init__(self, sock)
        self.daemon = True
        self.clients = []
        self.settings = cherrypy.engine.publish('get-settings')

    def opened(self):
        cherrypy.engine.publish('add-client', self.peer_address, self)
        timer = threading.Timer(0.3, self.fire_history)
        timer.start()

    def closed(self, code, reason=None):
        cherrypy.engine.publish('del-client', self.peer_address)

    def fire_history(self):
        send_history = FireFirstMessages(self, cherrypy.engine.publish('get-history')[0],
                                         cherrypy.engine.publish('get-settings')[0])
        send_history.start()


class WebChatPlugin(WebSocketPlugin):
    def __init__(self, bus, settings):
        WebSocketPlugin.__init__(self, bus)
        self.daemon = True
        self.clients = []
        self.style_settings = settings
        self.history = []
        self.history_size = HISTORY_SIZE

    def start(self):
        WebSocketPlugin.start(self)
        self.bus.subscribe('get-settings', self.get_settings)
        self.bus.subscribe('add-client', self.add_client)
        self.bus.subscribe('del-client', self.del_client)
        self.bus.subscribe('add-history', self.add_history)
        self.bus.subscribe('get-history', self.get_history)
        self.bus.subscribe('process-command', self.process_command)

    def stop(self):
        WebSocketPlugin.stop(self)
        self.bus.unsubscribe('get-settings', self.get_settings)
        self.bus.unsubscribe('add-client', self.add_client)
        self.bus.unsubscribe('del-client', self.del_client)
        self.bus.unsubscribe('add-history', self.add_history)
        self.bus.unsubscribe('get-history', self.get_history)
        self.bus.ubsubscribe('process-command', self.process_command)

    def add_client(self, addr, websocket):
        self.clients.append({'ip': addr[0], 'port': addr[1], 'websocket': websocket})

    def del_client(self, addr):
        try:
            self.clients.remove({'ip': addr[0], 'port': addr[1]})
        except:
            pass

    def add_history(self, message):
        self.history.append(message)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def get_settings(self):
        return self.style_settings

    def get_history(self):
        return self.history

    def process_command(self, command, values):
        if command == 'remove_by_id':
            self._remove_by_id(values['ids'])
        elif command == 'remove_by_user':
            self._remove_by_user(values['user'])
        elif command == 'replace_by_id':
            self._replace_by_id(values['ids'])
        elif command == 'replace_by_user':
            self._replace_by_user(values['user'])

    def _remove_by_id(self, ids):
        for item in ids:
            for message in self.history:
                if message.get('id') == item:
                    self.history.remove(message)

    def _remove_by_user(self, users):
        for item in users:
            for message in reversed(self.history):
                if message.get('item') == item:
                    self.history.remove(message)

    def _replace_by_id(self, ids):
        for item in ids:
            for index, message in enumerate(self.history):
                if message.get('id') == item:
                    self.history[index]['text'] = self.style_settings['keys']['remove_text']
                    if 'emotes' in self.history[index]:
                        del self.history[index]['emotes']
                    if 'bttv_emotes' in self.history[index]:
                        del self.history[index]['bttv_emotes']

    def _replace_by_user(self, users):
        for item in users:
            for index, message in enumerate(self.history):
                if message.get('user') == item:
                    self.history[index]['text'] = self.style_settings['keys']['remove_text']
                    if 'emotes' in self.history[index]:
                        del self.history[index]['emotes']
                    if 'bttv_emotes' in self.history[index]:
                        del self.history[index]['bttv_emotes']


class RestRoot(object):
    def __init__(self, settings, modules):
        self.settings = settings
        self._rest_modules = {}

        for name, params in modules.iteritems():
            module_class = params.get('class', None)
            if module_class:
                api = params['class'].rest_api()
                if api:
                    self._rest_modules[name] = api

    @cherrypy.expose
    def default(self, *args):
        if len(args) > 0:
            module_name = args[0]
            query = args[1:]
            if module_name in self._rest_modules:
                method = cherrypy.request.method
                api = self._rest_modules[module_name]
                if method in api:
                    return api[method](query)
        return json.dumps({'error': 'Bad Request',
                           'status': 400,
                           'message': 'Unable to find module'})


class CssRoot(object):
    def __init__(self, settings):
        self.css_map = {
            'css': self.style_css,
            'scss': self.style_scss
        }
        self.settings = settings

    @cherrypy.expose
    def default(self, *args):
        cherrypy.response.headers['Content-Type'] = 'text/css'
        path = ['css']
        path.extend(args)
        file_type = args[-1].split('.')[-1]
        if file_type in self.css_map:
            return self.css_map[file_type](*path)
        return

    def style_css(self, *path):
        cherrypy.response.headers['Content-Type'] = 'text/css'
        with open(os.path.join(self.settings['location'], *path), 'r') as css:
            return css.read()

    def style_scss(self, *path):
        css_namespace = Namespace()
        for key, value in self.settings['keys'].items():
            for baseclass, scss_class in SCSS_MAP.items():
                if isinstance(value, baseclass):
                    css_namespace.set_variable('${}'.format(key), scss_class(value))
                    break

        cherrypy.response.headers['Content-Type'] = 'text/css'
        with open(os.path.join(self.settings['location'], *path), 'r') as css:
            css_content = css.read()
            compiler = Compiler(namespace=css_namespace, output_style='compressed')
            return compiler.compile_string(css_content)


class HttpRoot(object):
    def __init__(self, style_settings):
        self.settings = style_settings

    @cherrypy.expose
    def index(self):
        cherrypy.response.headers["Expires"] = -1
        cherrypy.response.headers["Pragma"] = "no-cache"
        cherrypy.response.headers["Cache-Control"] = "private, max-age=0, no-cache, no-store, must-revalidate"
        if os.path.exists(self.settings['location']):
            return serve_file(os.path.join(self.settings['location'], 'index.html'), 'text/html')
        else:
            return "Style not found"

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler


class SocketThread(threading.Thread):
    def __init__(self, host, port, root_folder, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.host = host
        self.port = port
        self.root_folder = root_folder
        self.style_settings = kwargs['style_settings']
        self.modules = kwargs.pop('modules')

        self.root_config = None
        self.css_config = None
        self.rest_config = None

        cherrypy.config.update({'server.socket_port': int(self.port), 'server.socket_host': self.host,
                                'engine.autoreload.on': False})
        self.websocket = WebChatPlugin(cherrypy.engine, self.style_settings)
        self.websocket.subscribe()
        cherrypy.tools.websocket = WebSocketTool()

    def update_settings(self):
        self.root_config = {
            '/ws': {'tools.websocket.on': True,
                    'tools.websocket.handler_cls': WebChatSocketServer},
            '/js': {'tools.staticdir.on': True,
                    'tools.staticdir.dir': os.path.join(self.style_settings['location'], 'js')},
            '/img': {'tools.staticdir.on': True,
                     'tools.staticdir.dir': os.path.join(self.style_settings['location'], 'img'),
                     'tools.caching.on': True,
                     'tools.expires.on': True,
                     'tools.expires.secs': 1}}
        self.css_config = {
            '/': {}
        }
        self.rest_config = {
            '/': {}
        }

    def run(self):
        cherrypy.log.access_file = ''
        cherrypy.log.error_file = ''
        cherrypy.log.screen = False

        # Removing Access logs
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.setLevel(logging.ERROR)

        self.update_settings()
        self.mount_dirs()
        cherrypy.engine.start()

    def mount_dirs(self):
        cherrypy.tree.mount(HttpRoot(self.style_settings), '', self.root_config)
        cherrypy.tree.mount(CssRoot(self.style_settings), '/css', self.css_config)
        cherrypy.tree.mount(RestRoot(self.style_settings, self.modules), '/rest', self.rest_config)


def socket_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    return sock.connect_ex((host, int(port)))


class webchat(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Module configuration
        conf_file = os.path.join(conf_folder, "webchat.cfg")
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'main',
            'id': DEFAULT_PRIORITY
        }
        conf_dict['server'] = OrderedDict()
        conf_dict['server']['host'] = '127.0.0.1'
        conf_dict['server']['port'] = '8080'
        conf_dict['style'] = DEFAULT_STYLE
        conf_dict['style_settings'] = OrderedDict()
        conf_dict['style_settings']['show_system_msg'] = True

        conf_gui = {
            'style': {
                'check': 'http',
                'check_type': 'dir',
                'view': 'choose_single'
            },
            'style_settings': {},
            'non_dynamic': ['server.*'],
            'ignored_sections': ['style_settings'],
            'redraw': {
                'style_settings': {
                    'redraw_trigger': ['style'],
                    'get_config': self.load_style_settings,
                    'get_gui': self.get_style_gui_from_file
                },
            }
        }

        parser = load_from_config_file(conf_file, conf_dict)

        style_path = self.get_style_path(conf_dict['style'])
        style_name = style_path.split(os.sep)[-1] if style_path else None

        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': parser,
             'id': conf_dict['gui_information']['id'],
             'config': conf_dict,
             'gui': conf_gui,
             'host': conf_dict['server']['host'],
             'port': conf_dict['server']['port'],
             'style_settings': {
                 'name': style_name,
                 'location': style_path,
                 'keys': None
             }})

        self.load_style_settings(style_name)

        self.s_thread = None
        self.queue = None
        self.message_threads = []

        # Rest Api Settings
        self._rest_api['GET'] = self.rest_get

    def load_module(self, *args, **kwargs):
        MessagingModule.load_module(self, *args, **kwargs)
        self.queue = kwargs.get('queue')
        self.start_webserver()

    def start_webserver(self):
        host = self._conf_params['host']
        port = self._conf_params['port']
        if socket_open(host, port):
            self.s_thread = SocketThread(host, port, CONF_FOLDER,
                                         style_settings=self._conf_params['style_settings'],
                                         modules=self._loaded_modules)
            self.s_thread.start()

            for thread in range(THREADS+5):
                self.message_threads.append(MessagingThread(self._conf_params['style_settings']))
                self.message_threads[thread].start()
        else:
            log.error("Port is already used, please change webchat port")

    @staticmethod
    def get_style_path(style):
        path = os.path.abspath(os.path.join(HTTP_FOLDER, style))
        if os.path.exists(path):
            return path
        elif os.path.exists(os.path.join(HTTP_FOLDER, DEFAULT_STYLE)):
            return os.path.join(HTTP_FOLDER, DEFAULT_STYLE)
        else:
            dirs = os.listdir(HTTP_FOLDER)
            if dirs:
                return os.path.join(HTTP_FOLDER, dirs[0])
        return None

    def reload_chat(self):
        self.queue.put({'type': 'command', 'command': 'reload'})

    def apply_settings(self, **kwargs):
        save_settings(self.conf_params(), ignored_sections=self._conf_params['gui'].get('ignored_sections'))
        if 'system_exit' in kwargs:
            return

        self.update_style_settings(self._conf_params['config']['style'])
        self.reload_chat()

        if self._conf_params['config']['style'] != self._conf_params['style_settings']['name']:
            log.info("changing style")
            style_name = self._conf_params['config']['style']
            self._conf_params['style_settings']['name'] = style_name
            self._conf_params['style_settings']['location'] = self.get_style_path(style_name)
            self.s_thread.update_settings()
            self.s_thread.mount_dirs()

        if self._conf_params['dependencies']:
            for module in self._conf_params['dependencies']:
                self._loaded_modules[module]['class'].apply_settings(from_depend='webchat')

    def gui_button_press(self, gui_module, event, list_keys):
        log.debug("Received button press for id {0}".format(event.GetId()))
        keys = MODULE_KEY.join(list_keys)
        if keys == 'menu.reload':
            self.reload_chat()
        event.Skip()

    def process_message(self, message, queue, **kwargs):
        if message:
            if 'flags' in message:
                if 'hidden' in message['flags']:
                    return message
            s_queue.put(message)
            return message

    def rest_get(self, *args):
        return json.dumps(self._conf_params['style_settings']['keys'])

    def get_style_from_file(self, style_name):
        file_path = os.path.join(self.get_style_path(style_name), 'settings.json')
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r') as style_file:
                return json.load(style_file, object_pairs_hook=OrderedDict)
        return {}

    def write_style_to_file(self, style_name):
        file_path = os.path.join(self.get_style_path(style_name), 'settings.json')
        with open(file_path, 'w') as style_file:
            json.dump(self._conf_params['style_settings']['keys'], style_file, indent=2)

    def get_style_gui_from_file(self, style_name):
        file_path = os.path.join(self.get_style_path(style_name), 'settings_gui.json')
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r') as gui_file:
                return json.load(gui_file)
        return {}

    def load_style_settings(self, style_name):
        self._conf_params['config']['style_settings'] = self.get_style_from_file(style_name)
        self._conf_params['style_settings']['keys'] = self._conf_params['config']['style_settings']
        self._conf_params['gui']['style_settings'] = self.get_style_gui_from_file(style_name)
        return self._conf_params['config']['style_settings']

    def update_style_settings(self, style_name):
        self._conf_params['style_settings']['keys'] = self._conf_params['config']['style_settings']
        self.write_style_to_file(style_name)
