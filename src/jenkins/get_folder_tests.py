import json
import os
import sys

folder = sys.argv[1]
test_name = sys.argv[2]
tests = []
for test in os.listdir(folder):
    if os.path.isfile(os.path.join(folder, test)):
        tests.append('{}/{}'.format(folder, test))

with open('{}_tests.json'.format(test_name), 'w') as tests_file:
    json.dump(tests, tests_file)
