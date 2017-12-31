FROM fedora:25

# Misc packages
RUN dnf -y install pwgen tar psmisc procps findutils iputils net-tools wget logrotate zip findutils git

# Dependencies for LalkaChat
COPY requires_linux.txt /root/
RUN dnf -y install wxPython
RUN pip install -r /root/requires_linux.txt
