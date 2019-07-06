FROM fedora:25

# Misc packages
RUN dnf -y install pwgen tar psmisc procps findutils iputils net-tools wget logrotate zip findutils git python-pip

# Dependencies for LalkaChat
RUN dnf -y install wxPython
COPY requires_linux.txt /root/
RUN pip install -r /root/requires_linux.txt

# Dependencies for Testing
RUN dnf -y install nodejs gcc python-devel redhat-rpm-config
RUN pip install git-lint pep8 pylint==1.9.3 junit-xml
RUN npm install -g csslint webpack webpack-merge webpack-cli
