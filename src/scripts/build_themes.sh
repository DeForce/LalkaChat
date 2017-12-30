#!/bin/bash
DIR_ROOT=$(pwd)
THEME_ROOT=${DIR_ROOT}/src/themes
[ ! -d ${DIR_ROOT}/http ] && mkdir ${DIR_ROOT}/http

if ! which npm; then
    sudo yum install npm -y
fi

for folder in $(find "$THEME_ROOT" -maxdepth 1 -type d | tail -n +2)
do
        echo ${folder}
        THEME_NAME=$( echo $folder | rev | cut -d'/' -f1 | rev )
        cd ${folder}
        rm -rf ./dist
        npm install
        npm start
        rm -rf ${DIR_ROOT}/http/${THEME_NAME}
        cp -r dist ${DIR_ROOT}/http/${THEME_NAME}
        rm -rf ${DIR_ROOT}/http/${THEME_NAME}_gui
        cp -r dist ${DIR_ROOT}/http/${THEME_NAME}_gui
        cd ${THEME_ROOT}
done
