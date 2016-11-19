FROM deforce/alpine-wxpython:latest

MAINTAINER CzT/DeForce <vlad@czt.lv>

RUN apk --update add --virtual build-deps build-base bzip2 git           \
      libstdc++ openssl-dev py2-pip python2-dev tar wget wxgtk-dev xz && \
    
    pip install requests cherrypy ws4py irc semantic_version jinja2
