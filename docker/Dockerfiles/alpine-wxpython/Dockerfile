FROM alpine:edge

MAINTAINER CzT/DeForce <vlad@czt.lv>

# docker build --build-arg WXPY_SRC_URL=http://heanet.dl.sourceforge.net/project/wxpython/wxPython/3.0.1.0/wxPython-src-3.0.1.0.tar.bz2 -t deforce/alpine-wxpython:3.0.1.0 .
ARG WXPY_SRC_URL="http://heanet.dl.sourceforge.net/project/wxpython/wxPython/3.0.2.0/wxPython-src-3.0.2.0.tar.bz2"

RUN echo "http://nl.alpinelinux.org/alpine/edge/main"         \
      >> /etc/apk/repositories                             && \
    echo "http://nl.alpinelinux.org/alpine/edge/testing"      \
      >> /etc/apk/repositories                             && \
    echo "http://nl.alpinelinux.org/alpine/edge/community"    \
      >> /etc/apk/repositories                             && \

    apk --update add font-misc-misc libgcc mesa-gl python2 wxgtk && \

    apk --update add --virtual build-deps build-base                \
      bzip2 libstdc++ python2-dev tar wget wxgtk-dev xz          && \
    
    wget -qO- "${WXPY_SRC_URL}" | tar xj -C /tmp/ && \
    cd /tmp/wxPython-src-*                        && \
    cd ./wxPython                                 && \
    python ./setup.py build                       && \
    python ./setup.py install                     && \

   apk del build-deps                             && \
   rm -rf /var/cache/* /tmp/* /var/log/* ~/.cache && \
   mkdir -p /var/cache/apk
