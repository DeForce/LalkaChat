FROM deforce/lc-alpine-wxpython

MAINTAINER CzT/DeForce <vlad@czt.lv>

COPY requires_linux.txt /root/

RUN apk --update add build-base bzip2 git libstdc++ openssl-dev py2-pip python2-dev tar wget wxgtk-dev xz nodejs-npm
RUN pip install -r /root/requires_linux.txt
