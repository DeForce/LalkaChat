#!/usr/bin/env bash
MASTER_DIR=${PWD}
THEME_NAME=${1}
cd src/themes/${THEME_NAME}

npm install
npm start

[ ! -d ${MASTER_DIR}/http ] && mkdir ${MASTER_DIR}/http

if [ ! -d ${MASTER_DIR}/http/${THEME_NAME} ]; then
    mv dist ${MASTER_DIR}/http/${THEME_NAME}
fi
