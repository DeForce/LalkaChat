FROM cdrx/pyinstaller-windows:python2

MAINTAINER CzT/DeForce <vlad@czt.lv>

RUN apt-get install -y xvfb
RUN wget -qO /root/wxpython.exe http://downloads.sourceforge.net/wxpython/wxPython3.0-win32-3.0.2.0-py27.exe
RUN (Xvfb :1 -screen 0 800x600x24&)                     && \
    sleep 3                                             && \
    DISPLAY=:1 wine /root/wxpython.exe /SP- /VERYSILENT
