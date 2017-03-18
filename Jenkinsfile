import groovy.json.JsonBuilder
import groovy.json.JsonSlurperClassic

node('docker-host') {
    stage('Checkout') {
        checkout scm
        sh 'mkdir -p results'
        sh 'rsync -avz src/jenkins/root/ ./'
    }
    def stable = true
    try {
        def containersToBuild = []
        stage('Prepare Docker containers') {
            sh 'python src/scripts/docker_build.py'
            def ContainerFile = readFile('docker/build_order.json')
            def ContainerMap = mapToList(new JsonSlurperClassic().parseText(ContainerFile))
            for (architecture in ContainerMap) {
                def archName = architecture.getKey()
                def archData = architecture.getValue()
                echo "Running builds for ${archName}"
                stage(archName) {
                    for (image in archData) {
                        echo "Building ${image} from ${archName}"
                        def buildName = "deforce/lc-${archName}-${image}"
                        buildDockerImage(archName, image, buildName)
                        if (image.equals('testing')) {
                            containersToBuild.add(buildName)
                        }
                    }
                }
            }
        }
        stage('Build') {
            def container = containersToBuild[0]
            stage(container) {
                echo "Running Build for ${container}"
                def docker_image = docker.image(container)
                docker_image.inside {
                    stage('Themes') {
                        buildThemes()
                    }
                    stage('Configuration') {
                        sh '/bin/sh src/jenkins/prep_config.sh'
                    }
                }
            }
        }
        stage('Testing') {
            for (container in containersToBuild) {
                stage(container) {
                    echo "Running Build for ${container}"
                    def docker_image = docker.image(container)
                    docker_image.inside {
                        try {
                            stage('Run Chat') {
                                sh '/bin/sh src/jenkins/run_chat.sh'
                                sh 'ps aux | grep -v grep | grep main.py'
                            }
                            stage('Run Tests') {
                                stage('Chat Tests') {
                                    runTests('src/jenkins/chat_tests', 'chat', false)
                                }
                            }
                            stage('Lint Tests') {
                                try {
                                    runTests('src/jenkins/lint_tests', 'lint', true)
                                } catch(exc) {
                                    stable = false
                                }
                            }
                        } finally {
                            sh 'cat chat.log'
                            archive 'results/**'
                        }
                    }
                }
            }
        }
    }
    finally {
        stage('Cleanup') {
            if(!stable) {
                currentBuild.result = 'UNSTABLE'
            }
            sh 'docker rmi -f $(docker images | grep \'^<none>\' | awk \'{print \$3}\') || true'
            // deleteDir()
        }
    }
}

def buildThemes() {
    // Creates themes.json
    sh 'python src/jenkins/get_themes.py'
    def ThemesJson = readFile('themes.json')
    def ThemesList = new JsonSlurperClassic().parseText(ThemesJson)
    echo "${ThemesList}"
    for (def Theme : ThemesList) {
        sh "/bin/sh src/jenkins/test_theme.sh ${Theme}"
        sh "/bin/sh src/jenkins/build_theme.sh ${Theme}"
    }
}

def runTests(folder, name, skip) {
    sh "python src/jenkins/get_folder_tests.py ${folder} ${name}"
    def TestJson = readFile("${name}_tests.json")
    def TestsList = new JsonSlurperClassic().parseText(TestJson)
    def TestResults = [:]
    for (def Test : TestsList) {
        echo "Running ${Test} test"
        def result = false
        try {
            def Test_Name = Test.split('/').last().split("\\.").first()
            if(Test.endsWith('.py')) {
                sh "set -o pipefail && python ${Test} 2>&1 | tee results/${name}_${Test_Name}_results.txt"
            } else {
                sh "set -o pipefail && /bin/bash ${Test} 2>&1 | tee results/${name}_${Test_Name}_results.txt"
            }
            result = true
        } catch(exc) {
            if(!skip) {
                error('Test didn\'t pass')
            }
        }
        finally {
            TestResults[Test] = result
        }
    }
    writeFile(file: "results/${name}_test.txt", text: new JsonBuilder(TestResults).toPrettyString())
}

def buildDockerImage(archName, image, buildName) {
    sh "docker build -t ${buildName} -f docker/dockerfiles/${archName}/${image}/Dockerfile ."
}

@NonCPS
def mapToList(depmap) {
    def dlist = []
    for (def entry2 in depmap) {
        dlist.add(new java.util.AbstractMap.SimpleImmutableEntry(entry2.key, entry2.value))
    }
    dlist
}