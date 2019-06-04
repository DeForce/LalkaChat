import json
import os

docker = {}
for docker_type in os.listdir('docker/dockerfiles'):
    if docker_type.startswith('_'):
        continue
    docker_list = {docker_type: []}
    if os.path.isfile('docker/dockerfiles/{}/build_order.json'.format(docker_type)):
        with open('docker/dockerfiles/{}/build_order.json'.format(docker_type), 'r') as json_order:
            docker[docker_type] = json.load(json_order)

with open('docker/build_order.json', 'w') as order_file:
    json.dump(docker, order_file)
