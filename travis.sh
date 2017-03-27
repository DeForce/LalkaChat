#!/usr/bin/env bash
if [ $USER != "travis" ]
then
    echo "This script is not designed to run locally."
    exit 1
fi

case "$TEST_SUITE" in
    'pylint')
        docker pull eeacms/pylint
        docker run -v "${TRAVIS_BUILD_DIR}":/code eeacms/pylint:latest --max-line-length=99 --output-format=colorized /code
        exit $?
        ;;
    'eslint')
        docker pull markocelan/eslint
        docker run -v "${TRAVIS_BUILD_DIR}/src":/src markocelan/eslint --color.
        exit $?
        ;;
    'scsslint')
        docker pull rvip/scss-lint
        docker run -v "${TRAVIS_BUILD_DIR}/src/themes/default/assets/css":/app rvip/scss-lint --color
        exit $?
        ;;
    *)
        echo "TEST_SUITE env variable specifies unknown test suite: \"${TEST_SUITE}\""
        exit 1
        ;;
esac
