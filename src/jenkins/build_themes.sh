#!/bin/bash
DIR_ROOT=$(pwd)
THEME_ROOT=${DIR_ROOT}/src/themes
cd $THEME_ROOT

for folder in $(find $THEME_ROOT -maxdepth 1 -mindepth 1 -type d -printf '%f\n')
do
        echo "Building theme: ${folder}"
        THEME_NAME=${folder}
        cd ${folder}
        npm install
        npm start
        cp -r dist ${DIR_ROOT}/http/${THEME_NAME}
        cd ${THEME_ROOT}
done
