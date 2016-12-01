FROM deforce/alpine-wxpython:latest

MAINTAINER CzT/DeForce <vlad@czt.lv>

ADD . /usr/lib/python2.7/site-packages/LalkaChat

RUN apk --update add --virtual build-deps build-base bzip2 git           \
      libstdc++ openssl-dev py2-pip python2-dev tar wget wxgtk-dev xz && \
    
    pip install requests cherrypy ws4py irc semantic_version jinja2 && \
    cd /usr/lib/python2.7/site-packages/LalkaChat                   && \
    mkdir -p ./conf                                                 && \
    mv ./docker/stubs/cefpython3 /usr/lib/python2.7/site-packages/  && \
    mv ./docker/run /usr/local/bin/                                 && \
    rm -rf ./docker                                                 && \
    python ./setup.py build                                         && \

   mv /usr/lib/python2.7/site-packages/ /usr/lib/python2.7/~site-packages/ && \
   apk del build-deps                                                      && \
   mv /usr/lib/python2.7/~site-packages/ /usr/lib/python2.7/site-packages/ && \
   rm -rf /var/cache/* /tmp/* /var/log/* ~/.cache                          && \
   mkdir -p /var/cache/apk

VOLUME /usr/lib/python2.7/site-packages/LalkaChat

CMD /usr/local/bin/run
