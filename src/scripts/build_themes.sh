#!/bin/bash
DIR_ROOT=/home/defor/python/LalkaChat
THEME_ROOT=${DIR_ROOT}/src/themes


for folder in $(find "$THEME_ROOT" -maxdepth 1 -type d | tail -n +2)
do
        echo ${folder}
        THEME_NAME=$( echo $folder | rev | cut -d'/' -f1 | rev )
        cd ${folder}
        npm install
        npm start
        rm -rf ${DIR_ROOT}/http/${THEME_NAME}
        mv dist ${DIR_ROOT}/http/${THEME_NAME}
        cd ${THEME_ROOT}
done
