import ConfigParser
import os
import threading
import requests
import Queue

from flask import Flask, request
from flask_sockets import Sockets

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler


# Flask Side
app = Flask(__name__)
sockets = Sockets(app)
s_queue = Queue.Queue()


@sockets.route('/message/ws')
def echo_socket(ws):
    while True:
        message = s_queue.get()
        try:
            ws.send(message)
        except:
            pass


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/message/get', methods=['POST'])
def process_message():
    print "Received Message"
    return request.form['user']


class FlaskThread(threading.Thread):
    def __init__(self, host, port):
        super(self.__class__, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        app.run(host=self.host, port=self.port)


class SocketThread(threading.Thread):
    def __init__(self, host, port):
        super(self.__class__, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        server = pywsgi.WSGIServer((self.host, self.port), app, handler_class=WebSocketHandler)
        server.serve_forever()


class webchat():
    def __init__(self, conf_folder):
        conf_file = os.path.join(conf_folder, "webchat.cfg")

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(conf_file)

        tag_server = 'server'
        for item in config.items(tag_server):
            if item[0] == 'host':
                self.host = item[1]
            if item[0] == 'port':
                self.port = item[1]

        # Run Flask Thread
        f_thread = FlaskThread(self.host, self.port)
        f_thread.start()

        s_port = int(self.port) + 1
        s_thread = SocketThread(self.host, s_port)
        s_thread.start()

    def get_message(self, message):
        if message is None:
            # print "webchat received empty message"
            return
        else:
            if 'flags' in message:
                if message['flags'] == 'hidden':
                    return message
            s_queue.put(message)
            return message
