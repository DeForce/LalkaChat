FROM deforce/lc-fedora-build-deps

# Dependancies for Testing
RUN dnf -y install nodejs gcc python-devel redhat-rpm-config
RUN pip install git-lint pep8 pylint==1.9.3 junit-xml
RUN npm install -g csslint webpack webpack-merge webpack-cli