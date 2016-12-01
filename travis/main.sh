#!/usr/bin/env bash
if [ $USER != "travis" ]
then
    echo "This script is not designed to run locally."
    exit 1
fi

case "$TEST_SUITE" in
    'runtime')
        export DISPLAY=':99.0'
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
        # TODO: Create DockerHub autobuild ==============================================================================
        printf "BUILDING_LALKACHAT_BUILD_DEPS"
        printf '=%.0s' {1..71}
        echo
        docker pull deforce/alpine-wxpython:latest
        docker build -t deforce/lalkachat-build-deps:latest "${TRAVIS_BUILD_DIR}/docker/Dockerfiles/lalkachat-build-deps"
        if [ $? -ne 0 ]
        then
            echo "\"docker build -t deforce/lalkachat-build-deps:latest ...\" failed!"
            exit 1
        fi
        # ===============================================================================================================
        printf "BUILDING_LALKACHAT"
        printf '=%.0s' {1..82}
        echo
        # docker pull lalkachat-build-deps:latest
        docker build -t deforce/lalkachat:testing -f Dockerfile_test "${TRAVIS_BUILD_DIR}"
        if [ $? -ne 0 ]
        then
            echo "\"docker build -t deforce/lalkachat:testing ...\" failed!"
            exit 1
        fi
        printf "TESTING"
        printf '=%.0s' {1..93}
        echo
        xhost + > /dev/null 2>&1
        id=$(docker run -d -t -v "${TRAVIS_BUILD_DIR}/travis/test-conf:/usr/lib/python2.7/site-packages/LalkaChat/conf" -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY --net=host deforce/lalkachat:testing)
        sleep 10
        printf "LALKA_LOGS"
        printf '=%.0s' {1..90}
        echo
        # We can add logs assertions here
        docker logs $id
        printf '=%.0s' {1..110}
        echo
        echo "Chat is alive ?"
        if ! docker top $id &>/dev/null
        then
            echo "Czt kills kittens..."
            exit 1
        fi
        echo "Yeah!"
        echo "127.0.0.1:8080 is up and its response contains '<title>Lalka - chat</title>' ?"
        if curl -s "127.0.0.1:8080" | grep "<title>Lalka - chat</title>"
        then
            echo "Great success!"
        else
            echo "127.0.0.1:8080 where is <title>Lalka - chat</title>?"
            exit 1
        fi
        printf '=%.0s' {1..100}
        echo
        echo "phantomjs test goes here"
        echo $(phantomjs --version)
        printf '=%.0s' {1..100}
        echo
        exit 0
        ;;
    'pylint')
        docker pull eeacms/pylint:latest
        docker run -v "${TRAVIS_BUILD_DIR}":/code eeacms/pylint:latest --max-line-length=99 --output-format=colorized /code
        exit $?
        ;;
    'jslint')
        docker pull eeacms/csslint:latest
        docker run -v "${TRAVIS_BUILD_DIR}/http":/code eeacms/jslint:latest --color /code/**/*.js
        exit $?
        ;;
    'csslint')
        docker pull eeacms/jslint:latest
        docker run -v "${TRAVIS_BUILD_DIR}":/code eeacms/csslint:latest --format=text /code
        exit $?
        ;;
    *)
        echo "TEST_SUITE env variable specifies unknown test suite: \"${TEST_SUITE}\""
        exit 1
        ;;
esac
