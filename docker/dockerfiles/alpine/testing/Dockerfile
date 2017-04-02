FROM deforce/lc-alpine-build-deps

MAINTAINER CzT/DeForce <vlad@czt.lv>

# Deps for testing
RUN apk --update add curl bash nodejs-npm rsync
RUN pip install git-lint pep8 pylint junit-xml
RUN npm install -g csslint
