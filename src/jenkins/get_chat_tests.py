import json
import os

tests = []
for test in os.listdir('src/jenkins/chat_tests'):
    tests.append('src/jenkins/chat_tests/{}'.format(test))

with open('chat_tests.json', 'w') as tests_file:
    json.dump(tests, tests_file)
