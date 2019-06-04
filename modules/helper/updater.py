import glob
import json
import logging
import os
import shutil
import subprocess
import zipfile

import requests

from modules.helper.system import PYTHON_FOLDER, HTTP_FOLDER

CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008

UPDATE_URL = 'http://lalkachat.czt.lv/list'

SRC_DIR = 'LalkaChat'
UPDATE_FOLDER = 'dl'
UPDATE_FILE = 'dl.zip'


def get_available_versions():
    req = requests.get(UPDATE_URL, timeout=1)
    if req.ok:
        return req.json()
    else:
        logging.warning('Unable to check for updates')
    return {}


def prepare_update():
    dst_path = os.path.join(UPDATE_FOLDER, SRC_DIR)

    # Clean old update
    if os.path.exists(dst_path):
        shutil.rmtree(dst_path)

    zip_path = os.path.join(UPDATE_FOLDER, UPDATE_FILE)
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        zip_file.extractall(UPDATE_FOLDER)
    os.remove(zip_path)

    old_http_folder = os.path.join(HTTP_FOLDER.split(os.sep)[-1])
    http_folder = os.path.join(dst_path, HTTP_FOLDER.split(os.sep)[-1])
    for style in os.listdir(http_folder):
        json_files = glob.glob(os.path.join(http_folder, style, '*.json'))
        for item in json_files:
            json_file = item.split(os.sep)[-1]
            old_json_file = os.path.join(old_http_folder, style, json_file)
            with open(old_json_file, 'r') as old_json:
                old_data = json.load(old_json)
            with open(item, 'r') as json_item:
                new_data = json.load(json_item)
                new_data.update(old_data)
            with open(item, 'w') as json_item:
                json.dump(new_data, json_item, indent=2)


def do_update():
    subprocess.Popen(['cmd', '/c', 'scripts\\update.bat',
                      os.path.join(UPDATE_FOLDER, SRC_DIR), os.path.join(PYTHON_FOLDER)],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE,
                     creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                     cwd=PYTHON_FOLDER)
