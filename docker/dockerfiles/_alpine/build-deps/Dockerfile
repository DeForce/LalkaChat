FROM deforce/lc-alpine-wxpython

MAINTAINER CzT/DeForce <vlad@czt.lv>

# Misc Packages
RUN apk --update add build-base bzip2 git libstdc++ openssl-dev tar wget wxgtk-dev xz

# Deps for chat
RUN apk --update add py2-pip python2-dev
COPY requires_linux.txt /root/
RUN pip install -r /root/requires_linux.txt

