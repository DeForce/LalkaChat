#!/usr/bin/env bash
VERSION="0.3.5"
APP_NAME="LalkaChat"
APP_STATE="-alpha"
SPEC_DIR=/home/defor/python/LalkaChat

cd ${SPEC_DIR}

rm -rf dist/
rm -rf build/

cmd /c pyinstaller main.spec


mkdir -p ${SPEC_DIR}/dist/main/http
echo "Building themes from source"
for folder in $(find "$SPEC_DIR/src/themes" -maxdepth 1 -type d | tail -n +2)
do
        echo ${folder}
        THEME_NAME=$( echo $folder | rev | cut -d'/' -f1 | rev )
        cd ${folder}
        npm install
        npm start
        mv dist ${SPEC_DIR}/dist/main/http/${THEME_NAME}
done

cd ${SPEC_DIR}/dist/main

rm -rf modules/chat/govno*

cd "$SPEC_DIR/dist"
STRING="${APP_NAME}_${VERSION}${APP_STATE}"
mv main ${STRING}

zip -r ${STRING}.zip ${STRING}
