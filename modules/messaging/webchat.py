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
from scss.types import Color, Boolean, String, Number
from collections import OrderedDict
from cherrypy.lib.static import serve_file
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

from modules.helper.message import TextMessage, CommandMessage, SystemMessage, RemoveMessageByID
from modules.helper.parser import save_settings
from modules.helper.system import THREADS, PYTHON_FOLDER, CONF_FOLDER
from modules.helper.module import MessagingModule
from gui import MODULE_KEY

logging.getLogger('ws4py').setLevel(logging.ERROR)
DEFAULT_STYLE = 'default'
DEFAULT_PRIORITY = 9001
HISTORY_SIZE = 5
HTTP_FOLDER = os.path.join(PYTHON_FOLDER, "http")
s_queue = Queue.Queue()
log = logging.getLogger('webchat')
REMOVED_TRIGGER = '%%REMOVED%%'

WS_THREADS = THREADS + 3

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {
    'category': 'main',
    'id': DEFAULT_PRIORITY
}
CONF_DICT['server'] = OrderedDict()
CONF_DICT['server']['host'] = '127.0.0.1'
CONF_DICT['server']['port'] = '8080'
CONF_DICT['style_gui'] = DEFAULT_STYLE
CONF_DICT['style_gui_settings'] = OrderedDict()
CONF_DICT['style'] = DEFAULT_STYLE
CONF_DICT['style_settings'] = OrderedDict()
CONF_DICT['style_settings']['show_system_msg'] = True

TYPE_DICT = {
    TextMessage: 'message',
    CommandMessage: 'command'
}


def process_emotes(emotes):
    return [{'emote_id': emote.id, 'emote_url': emote.url} for emote in emotes]


def process_badges(badges):
    return [{'badge': badge.id, 'url': badge.url} for badge in badges]


def prepare_message(msg, style_settings, msg_class):
    message = copy.deepcopy(msg)

    if 'levels' in message:
        message['levels']['url'] = '{}?{}'.format(message['levels']['url'], style_settings['style_name'])

    if 'text' in message and message['text'] == REMOVED_TRIGGER:
        message['text'] = style_settings.get('remove_text')

    if 'type' not in message:
        for m_class, m_type in TYPE_DICT.items():
            if issubclass(msg_class, m_class):
                message['type'] = m_type

    if 'emotes' in message:
        message['emotes'] = process_emotes(message['emotes'])

    if 'badges' in message:
        message['badges'] = process_badges(message['badges'])

    if 'command' in message:
        if message['command'].startswith('replace'):
            message['text'] = style_settings['keys']['remove_text']
        return message

    message['id'] = str(message['id'])
    return message


def add_to_history(message):
    if isinstance(message, TextMessage):
        cherrypy.engine.publish('add-history', message)


def process_command(message):
    if isinstance(message, CommandMessage):
        cherrypy.engine.publish('process-command', message.command, message)


class MessagingThread(threading.Thread):
    def __init__(self, settings):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.settings = settings
        self.running = True

    def run(self):
        while self.running:
            message = s_queue.get()

            if isinstance(message, dict):
                raise Exception("Got dict message {}".format(message))

            add_to_history(message)
            process_command(message)

            if isinstance(message, SystemMessage) and not self.settings['chat']['keys'].get('show_system_msg', True):
                continue

            log.debug("%s", message.json())
            self.send_message(message, 'chat')
            self.send_message(message, 'gui')
        log.info("Messaging thread stopping")

    def stop(self):
        self.running = False

    def send_message(self, message, chat_type):
        send_message = prepare_message(message.json(), self.settings[chat_type], type(message))
        ws_list = cherrypy.engine.publish('get-clients', chat_type)[0]
        for ws in ws_list:
            try:
                ws.send(json.dumps(send_message))
            except Exception as exc:
                log.exception(exc)
                log.info(send_message)


class FireFirstMessages(threading.Thread):
    def __init__(self, ws, history, settings):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.ws = ws  # type: WebChatSocketServer
        self.history = history
        self.settings = settings

    def run(self):
        show_system_msg = self.settings['keys'].get('show_system_msg', True)
        if self.ws.stream:
            for item in self.history:
                if isinstance(item, SystemMessage) and not show_system_msg:
                    continue
                timestamp = datetime.datetime.strptime(item.timestamp, "%Y-%m-%dT%H:%M:%S.%f")
                timedelta = datetime.datetime.now() - timestamp
                timer = int(self.settings['keys'].get('timer', 0))
                if timer > 0:
                    if timedelta > datetime.timedelta(seconds=timer):
                        continue

                message = prepare_message(item.json(), self.settings, type(item))
                self.ws.send(json.dumps(message))


class WebChatSocketServer(WebSocket):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        WebSocket.__init__(self, sock)
        self.daemon = True
        self.clients = []
        self.settings = cherrypy.engine.publish('get-settings', 'chat')[0]
        self.type = 'chat'

    def opened(self):
        cherrypy.engine.publish('add-client', self.peer_address, self)
        timer = threading.Timer(0.3, self.fire_history)
        timer.start()

    def closed(self, code, reason=None):
        cherrypy.engine.publish('del-client', self.peer_address, self)

    def fire_history(self):
        send_history = FireFirstMessages(self, cherrypy.engine.publish('get-history')[0],
                                         self.settings)
        send_history.start()


class WebChatGUISocketServer(WebChatSocketServer):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        WebSocket.__init__(self, sock)
        self.clients = []
        self.settings = cherrypy.engine.publish('get-settings', 'gui')[0]
        self.type = 'gui'


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
        self.bus.subscribe('get-clients', self.get_clients)
        self.bus.subscribe('add-history', self.add_history)
        self.bus.subscribe('get-history', self.get_history)
        self.bus.subscribe('del-history', self.del_history)
        self.bus.subscribe('process-command', self.process_command)

    def stop(self):
        WebSocketPlugin.stop(self)
        self.bus.unsubscribe('get-settings', self.get_settings)
        self.bus.unsubscribe('add-client', self.add_client)
        self.bus.unsubscribe('del-client', self.del_client)
        self.bus.unsubscribe('get-clients', self.get_clients)
        self.bus.unsubscribe('add-history', self.add_history)
        self.bus.unsubscribe('get-history', self.get_history)
        self.bus.unsubscribe('process-command', self.process_command)

    def add_client(self, addr, websocket):
        self.clients.append({'ip': addr[0], 'port': addr[1], 'websocket': websocket})

    def del_client(self, addr, websocket):
        try:
            self.clients.remove({'ip': addr[0], 'port': addr[1], 'websocket': websocket})
        except Exception as exc:
            log.exception("Exception %s", exc)
            log.info('Unable to delete client %s', addr)

    def get_clients(self, client_type):
        ws_list = []
        for client in self.clients:
            ws = client['websocket']
            if ws.type == client_type:
                ws_list.append(client['websocket'])
        return ws_list

    def add_history(self, message):
        self.history.append(message)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def del_history(self, msg_id):
        if len(msg_id) > 1:
            return

        for index, item in enumerate(self.history):
            if str(item.id) == msg_id[0]:
                self.history.pop(index)

    def get_settings(self, style_type):
        return self.style_settings[style_type]

    def get_history(self):
        return self.history

    def process_command(self, command, values):
        if command == 'remove_by_id':
            self._remove_by_id(values.message_ids)
        elif command == 'remove_by_user':
            self._remove_by_user(values.user)
        elif command == 'replace_by_id':
            self._replace_by_id(values.message_ids)
        elif command == 'replace_by_user':
            self._replace_by_user(values.user)

    def _remove_by_id(self, ids):
        for item in ids:
            for message in self.history:
                if message.get('id') == item:
                    self.history.remove(message)

    def _remove_by_user(self, users):
        for item in users:
            for message in reversed(self.history):
                if message.user == item:
                    self.history.remove(message)

    def _replace_by_id(self, ids):
        for item in ids:
            for index, message in enumerate(self.history):
                if message.get('id') == item:
                    self.history[index]['text'] = REMOVED_TRIGGER
                    if 'emotes' in self.history[index]:
                        del self.history[index]['emotes']
                    if 'bttv_emotes' in self.history[index]:
                        del self.history[index]['bttv_emotes']

    def _replace_by_user(self, users):
        for item in users:
            for index, message in enumerate(self.history):
                if message.get('user') == item:
                    self.history[index]['text'] = REMOVED_TRIGGER
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
    def default(self, *args, **kwargs):
        # Default error state
        message = 'Incorrect api call'
        error_code = 400

        body = cherrypy.request.body
        if cherrypy.request.method in cherrypy.request.methods_with_bodies:
            data = json.load(body)
            kwargs.update(data)

        if len(args) > 1:
            module_name = args[0]
            rest_path = args[1]
            query = args[2:] if len(args) > 2 else None
            if module_name in self._rest_modules:
                method = cherrypy.request.method
                api = self._rest_modules[module_name]
                if method in api:
                    if rest_path in api[method]:
                        return api[method][rest_path](query, **kwargs)
                error_code = 404
                message = 'Method not found'
        cherrypy.response.status = error_code
        return json.dumps({'error': 'Bad Request',
                           'status': error_code,
                           'message': message})


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
            if isinstance(value, basestring):
                if value.startswith('#'):
                    css_value = Color.from_hex(value)
                else:
                    css_value = String(value)
            elif isinstance(value, bool):
                css_value = Boolean(value)
            elif isinstance(value, int) or isinstance(value, float):
                css_value = Number(value)
            else:
                raise ValueError("Unable to find comparable values")
            css_namespace.set_variable('${}'.format(key), css_value)

        cherrypy.response.headers['Content-Type'] = 'text/css'
        with open(os.path.join(self.settings['location'], *path), 'r') as css:
            css_content = css.read()
            compiler = Compiler(namespace=css_namespace, output_style='nested')
            # Something wrong with PyScss,
            #  Syntax error: Found u'100%' but expected one of ADD.
            # Doesn't happen on next attempt, so we are doing bad thing
            attempts = 0
            while attempts < 100:
                try:
                    attempts += 1
                    ret_string = compiler.compile_string(css_content)
                    return ret_string
                except Exception as exc:
                    if attempts == 100:
                        log.debug(exc)


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
        pass


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
        self.gui_root_config = None
        self.gui_css_config = None

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
                    'tools.staticdir.dir': os.path.join(self.style_settings['chat']['location'], 'js')},
            '/img': {'tools.staticdir.on': True,
                     'tools.staticdir.dir': os.path.join(self.style_settings['chat']['location'], 'img'),
                     'tools.caching.on': True,
                     'tools.expires.on': True,
                     'tools.expires.secs': 1}}
        self.css_config = {
            '/': {}
        }
        self.rest_config = {
            '/': {}
        }

        self.gui_root_config = {
            '/ws': {'tools.websocket.on': True,
                    'tools.websocket.handler_cls': WebChatGUISocketServer},
            '/js': {'tools.staticdir.on': True,
                    'tools.staticdir.dir': os.path.join(self.style_settings['gui']['location'], 'js')},
            '/img': {'tools.staticdir.on': True,
                     'tools.staticdir.dir': os.path.join(self.style_settings['gui']['location'], 'img'),
                     'tools.caching.on': True,
                     'tools.expires.on': True,
                     'tools.expires.secs': 1}}
        self.gui_css_config = {'/': {}}

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
        cherrypy.tree.mount(CssRoot(self.style_settings['gui']), '/gui/css', self.gui_css_config)
        cherrypy.tree.mount(CssRoot(self.style_settings['chat']), '/css', self.css_config)

        cherrypy.tree.mount(HttpRoot(self.style_settings['chat']), '', self.root_config)
        cherrypy.tree.mount(HttpRoot(self.style_settings['gui']), '/gui', self.gui_root_config)

        cherrypy.tree.mount(RestRoot(self.style_settings, self.modules), '/rest', self.rest_config)


def socket_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    return sock.connect_ex((host, int(port)))


class webchat(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        conf_params = self._conf_params['config']

        self._conf_params.update({
            'host': conf_params['server']['host'],
            'port': conf_params['server']['port'],

            'style_settings': {
                'gui': {
                    'style_name': None,
                    'location': None,
                    'keys': {}
                },
                'chat': {
                    'style_name': None,
                    'location': None,
                    'keys': {}
                }
            }})
        self.prepare_style_settings()
        self.style_settings = self._conf_params['style_settings']

        self.s_thread = None
        self.queue = None
        self.message_threads = []

        # Rest Api Settings
        self.rest_add('GET', 'style', self.rest_get_style_settings)
        self.rest_add('GET', 'style_gui', self.rest_get_style_settings)
        self.rest_add('GET', 'history', self.rest_get_history)
        self.rest_add('DELETE', 'chat', self.rest_delete_history)

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

            for thread in range(WS_THREADS):
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
        self.queue.put(CommandMessage('reload'))

    def apply_settings(self, **kwargs):
        save_settings(self.conf_params(), ignored_sections=self._conf_params['gui'].get('ignored_sections', ()))
        if 'system_exit' in kwargs:
            return

        style_changed = False

        chat_style = self._conf_params['config']['style']
        gui_style = self._conf_params['config']['style_gui']
        style_config = self._conf_params['style_settings']

        self.update_style_settings(chat_style, gui_style)
        self.reload_chat()

        if chat_style != style_config['chat']['style_name']:
            log.info("changing chat style")
            self._conf_params['style_settings']['chat']['style_name'] = chat_style
            self._conf_params['style_settings']['chat']['location'] = self.get_style_path(chat_style)
            style_changed = True

        if gui_style != style_config['gui']['style_name']:
            log.info("changing gui style")
            self._conf_params['style_settings']['gui']['style_name'] = gui_style
            self._conf_params['style_settings']['gui']['location'] = self.get_style_path(gui_style)
            style_changed = True

        if style_changed:
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

    def process_message(self, message, **kwargs):
        if not hasattr(message, 'hidden'):
            s_queue.put(message)
        return message

    def rest_get_style_settings(self, *args):
        return json.dumps(self._conf_params['style_settings'][args[0][0]]['keys'])

    def rest_get_history(self, *args, **kwargs):
        return json.dumps(
            [prepare_message(
                message.json(),
                self.style_settings['chat'],
                type(message))
                for message in cherrypy.engine.publish('get-history')[0]]
        )

    @staticmethod
    def rest_delete_history(path, **kwargs):
        cherrypy.engine.publish('del-history', path)
        cherrypy.engine.publish('websocket-broadcast',
                                RemoveMessageByID(list(path)).json())

    def get_style_from_file(self, style_name):
        file_path = os.path.join(self.get_style_path(style_name), 'settings.json')
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r') as style_file:
                return json.load(style_file, object_pairs_hook=OrderedDict)
        return {}

    def write_style_to_file(self, style_name, style_type):
        file_path = os.path.join(self.get_style_path(style_name), 'settings.json')
        with open(file_path, 'w') as style_file:
            json.dump(self._conf_params['style_settings'][style_type]['keys'], style_file, indent=2)

    def get_style_gui_from_file(self, style_name):
        file_path = os.path.join(self.get_style_path(style_name), 'settings_gui.json')
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r') as gui_file:
                return json.load(gui_file)
        return {}

    def load_style_settings(self, style_name, style_type=None, keys=None):
        if keys:
            style_type = keys['all_settings']['type']
        settings_path = 'style_settings' if style_type == 'chat' else 'style_gui_settings'

        self._conf_params['config'][settings_path] = self.get_style_from_file(style_name)
        self._conf_params['style_settings'][style_type]['keys'] = self._conf_params['config']['style_settings']
        self._conf_params['gui'][settings_path] = self.get_style_gui_from_file(style_name)
        return self._conf_params['config'][settings_path]

    def update_style_settings(self, chat_style, gui_style):
        self._conf_params['style_settings']['chat']['keys'] = self._conf_params['config']['style_settings']
        self._conf_params['style_settings']['gui']['keys'] = self._conf_params['config']['style_gui_settings']
        self.write_style_to_file(chat_style, 'chat')
        self.write_style_to_file(gui_style, 'gui')

    def prepare_style_settings(self):
        style_settings = self._conf_params['style_settings']['chat']
        gui_style_settings = self._conf_params['style_settings']['gui']

        config_style = self._conf_params['config']['style']
        gui_config_style = self._conf_params['config']['style_gui']

        style_settings['style_name'] = config_style
        style_settings['location'] = self.get_style_path(config_style)
        style_settings['keys'] = self.load_style_settings(config_style, 'chat')

        gui_style_settings['style_name'] = gui_config_style
        gui_style_settings['location'] = self.get_style_path(gui_config_style)
        gui_style_settings['keys'] = self.load_style_settings(gui_config_style, 'gui')

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self):
        return {
            'style_gui': {
                'check': 'http',
                'check_type': 'dir',
                'view': 'choose_single'
            },
            'style_gui_settings': {},
            'style': {
                'check': 'http',
                'check_type': 'dir',
                'view': 'choose_single'
            },
            'style_settings': {},
            'non_dynamic': ['server.*'],
            'ignored_sections': ['style_settings', 'style_gui_settings'],
            'redraw': {
                'style_settings': {
                    'redraw_trigger': ['style'],
                    'type': 'chat',
                    'get_config': self.load_style_settings,
                    'get_gui': self.get_style_gui_from_file
                },
                'style_gui_settings': {
                    'redraw_trigger': ['style_gui'],
                    'type': 'gui',
                    'get_config': self.load_style_settings,
                    'get_gui': self.get_style_gui_from_file
                },
            }
        }

