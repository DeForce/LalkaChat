#!/usr/bin/env bash
set -x
MASTER_DIR=${PWD}
THEME_NAME=${1}
cd src/themes/${THEME_NAME}

npm install
npm test
