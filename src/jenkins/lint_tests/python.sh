#!/usr/bin/env bash
git lint -f $(find ./ -iname '*.py' | grep -v 'setup.py' | grep -v '__')
