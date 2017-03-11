FROM fedora

RUN dnf -y install pwgen tar psmisc procps findutils iputils net-tools wget logrotate zip
RUN dnf -y install git nodejs wxPython findutils

COPY requires_linux.txt /root/
RUN pip install -r /root/requires_linux.txt
