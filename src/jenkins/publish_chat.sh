#!/usr/bin/env bash
cp requires_windows.txt requirements.txt

docker run -v "$(pwd):/src/" ${BUILDER_CONTAINER}

cp -r http/ dist/windows/main/http/
# Rename to chat name
mv dist/windows/main dist/windows/LalkaChat

# Because windows
chmod a+x -R dist/windows/LalkaChat/

cd dist/windows
zip -r ${ZIP_NAME}.zip LalkaChat
chmod 664 ${ZIP_NAME}.zip
sudo mv ${ZIP_NAME}.zip $UPLOAD_DIR/
