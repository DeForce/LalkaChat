FROM python:3.8

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgtk-3-dev

COPY requires_linux.txt /root/
RUN pip install -r /root/requires_linux.txt

# Dependencies for Testing
RUN apt-get update && apt-get install -y --no-install-recommends \
        npm

RUN pip install git-lint pep8 pylint==1.9.3 junit-xml
RUN npm install -g csslint webpack webpack-merge webpack-cli
