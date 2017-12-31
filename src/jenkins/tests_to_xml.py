import json

import sys
from junit_xml import TestCase, TestSuite

if __name__ == '__main__':
    docker_image = sys.argv[1]
    test_cases = []
    with open('results/chat_test.txt') as chat_tests:
        test_data = json.loads(chat_tests.read())
        for test_name, test_result in test_data.items():
            test_cases.append(TestCase(test_name.split('/')[-1].split('.')[0], docker_image, 1, ''))

    suite = TestSuite('Python Tests', test_cases)
    with open('results/chat_tests.xml', 'w') as f:
        TestSuite.to_file(f, [suite], prettyprint=False)