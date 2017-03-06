import groovy.json.JsonSlurper

node('docker-host') {
    stage('Checkout') {
        checkout scm
    }

    stage('Build') {
        stage('Themes') {
            echo 'HelloWorld'
            // Creates themes.json
            sh 'python src/scripts/get_themes.py'
            def ThemesJson = readFile('themes.json')
            echo ThemesJson
            // def ThemesList = new JsonSlurper().parseText(ThemesJson)
            def ThemesList = []
            for (def Theme : ThemesList) {
                sh "echo 'Testing ${Theme}'; cd src/themes/${Theme}; npm install && npm test"
            }
        }
    }
    stage('Prepare Docker containers') {
        def ContainerList = ['fedora:25']
        for (def container : ContainerList) {
            docker.image(container).inside {
                sh 'cat /etc/*-release'
            }
        }
    }

    stage('Cleanup') {
        deleteDir()
    }
}
