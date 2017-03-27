#!/usr/bin/env bash
python src/jenkins/lint_tests/helpers/css_test.py

for file in $(find http/**/css -iname '*.css' -type f); do
    git lint -f ${file}
done
