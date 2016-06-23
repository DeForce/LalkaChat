import ConfigParser
import os
import threading
import requests
from flask import Flask, request


# Flask Side
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/message/get', methods=['POST'])
def process_message():
    print "Recieved Message"
    return request.form['user']


class FlaskThread(threading.Thread):
    def __init__(self, host, port):
        super(self.__class__, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        app.run(host=self.host, port=self.port)


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

        # Run WebSocket Thread


    def get_message(self, message):
        # url = 'http://{0}:{1}{2}'.format(self.host, self.port, '/message/get')
        # req = requests.post(url, data=message)
        # print req.text
        return message
