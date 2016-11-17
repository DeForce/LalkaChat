FROM alpine:edge

MAINTAINER CzT/DeForce <vlad@czt.lv>

ENV WXPY_SRC_URL http://heanet.dl.sourceforge.net/project/wxpython/wxPython/3.0.2.0/wxPython-src-3.0.2.0.tar.bz2
ENV XPRA_URL="https://www.xpra.org/dists/xenial/main/binary-amd64/xpra_0.17.6-r14318-1_amd64.deb"

ADD . /usr/lib/python2.7/site-packages/LalkaChat

RUN echo "http://nl.alpinelinux.org/alpine/edge/main"         \
      >> /etc/apk/repositories                             && \
    echo "http://nl.alpinelinux.org/alpine/edge/testing"      \
      >> /etc/apk/repositories                             && \
    echo "http://nl.alpinelinux.org/alpine/edge/community"    \
      >> /etc/apk/repositories                             && \

    apk --update add libgcc python2 wxgtk xpra                        && \
    apk --update add --virtual build-deps build-base bzip2 git           \
      libstdc++ openssl-dev py2-pip python2-dev tar wget wxgtk-dev xz && \

    cd /tmp/                                             && \
    wget -q -O xpra.deb "${XPRA_URL}"                    && \
    ar x xpra.deb                                        && \
    tar xJf ./data.tar.xz                                && \
    mv ./usr/share/xpra/www/include /usr/share/xpra/www/ && \
    rm -rf /tmp/*                                        && \
    
    wget -qO- "${WXPY_SRC_URL}" | tar xj -C /tmp/ && \
    cd /tmp/wxPython-src-*                        && \
    cd ./wxPython                                 && \
    python ./setup.py build                       && \
    python ./setup.py install                     && \
    
    pip install requests cherrypy ws4py irc wxpython                  \
        semantic_version jinja2 websockify                         && \
    cd /usr/lib/python2.7/site-packages/LalkaChat                  && \
    mv ./docker/stubs/cefpython3 /usr/lib/python2.7/site-packages/ && \
    mv ./docker/run /usr/local/bin/                                && \
    rm -rf ./docker                                                && \
    python ./setup.py build                                        && \

   mv /usr/lib/python2.7/site-packages/ /usr/lib/python2.7/~site-packages/ && \
   apk del build-deps                                                      && \
   mv /usr/lib/python2.7/~site-packages/ /usr/lib/python2.7/site-packages/ && \
   rm -rf /var/cache/* /tmp/* /var/log/* ~/.cache

ENV XPRA_HTML_PORT="10000" \
    XPRA_PASSWORD=""


EXPOSE $XPRA_HTML_PORT 8080

CMD xpra start :14 \
     --xvfb="Xorg\
       -noreset\
       -nolisten tcp\
       +extension GLX\
       +extension RANDR\
       +extension RENDER\
       -logfile /tmp/Xorg.log\
       -config /etc/xpra/xorg.conf"\
     --html=on\
     --bind-tcp=0.0.0.0:"${XPRA_HTML_PORT}"\
     --daemon=no\
     --exit-with-children\
     --dbus-proxy=no\
     --dbus-control=no\
     --printing=no\
     --pulseaudio=no\
     --speaker=disabled\
     --compress=0\
     --encoding=png\
     --microphone=no\
     --sharing=no\
     --dbus-launch=\
     --auth=env\
     --start-child="sh /usr/local/bin/run"
