FROM fedora:25

# Misc packages
RUN dnf -y install pwgen tar psmisc procps findutils iputils net-tools wget logrotate zip findutils git python-pip

# Dependencies for LalkaChat
RUN dnf -y install wxPython
COPY requires_linux.txt /root/
RUN pip install -r /root/requires_linux.txt
