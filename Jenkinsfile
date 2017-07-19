import groovy.json.JsonBuilder
import groovy.json.JsonSlurperClassic

def UploadPath = "jenkins@czt.lv:/usr/local/nginx/html/czt.lv/lalkachat/"

def stage = { String stageName, Closure body ->
    // It's stage that prints its name
    stage(stageName) {
        echo "Stage: ${stageName}"
        body.call()
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
    def TestsList
    try {
        def TestJson = readFile("${name}_tests.json")
        TestsList = new JsonSlurperClassic().parseText(TestJson)
    }
    catch (exc) {
        echo "No json file, exiting"
        return
    }
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
                echo "Exception: $exc"
                error("Test didn't pass")
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
static def mapToList(depmap) {
    def dlist = []
    for (def entry2 in depmap) {
        dlist.add(new java.util.AbstractMap.SimpleImmutableEntry(entry2.key, entry2.value))
    }
    dlist
}

node('docker-host') {
    stage('Checkout') {
        checkout scm
        sh 'mkdir -p results'
        sh 'rsync -avz src/jenkins/root/ ./'

        // This comment is needed until I refactor Jenkinsfile to support proper error throwing
        // def deps = 'asdas/asdasddas/asdasda/asdasd'.split('/').last().split("\\.").first()
    }
    def stable = true
    env.PYTHONPATH = pwd()
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
        stage('PreBuild') {
            def container = containersToBuild[0]
            stage(container) {
                echo "Running Build for ${container}"
                def docker_image = docker.image(container)
                docker_image.inside {
                    stage('Themes') {
                        buildThemes()
                        junit 'results/javascript-tests/*.xml'
                    }
                    stage('Configuration') {
                        sh '/bin/sh src/jenkins/prep_config.sh'
                    }
                }
            }
        }
        stage('Testing') {
            def lintRun = false
            for (container in containersToBuild) {
                stage(container) {
                    echo "Running Build for ${container}"
                    def docker_image = docker.image(container)
                    docker_image.inside {
                        try {
                            stage('Run Chat') {
                                sh '/bin/sh src/jenkins/run_chat.sh'
                            }
                            stage('Run Tests') {
                                stage('Chat Tests') {
                                    runTests('src/jenkins/chat_tests', 'chat', false)
                                }
                                stage('Module Tests') {
                                    echo 'Module Tests'
                                }
                            }
                            stage('Lint Tests') {
                                try {
                                    if(!lintRun) {
                                        runTests('src/jenkins/lint_tests', 'lint', true)
                                        lintRun = true
                                    }
                                } catch(exc) {
                                    stable = false
                                }
                            }
                        } catch(exc) {
                            echo "${exc}"
                        }
                        finally {
                            echo "Chat logs"
                            sh 'cat chat.log'
                            try {
                                sh "python src/jenkins/tests_to_xml.py ${container}"
                                junit 'results/chat_tests.xml'
                                archive 'results/**'
                            } catch (exc) {
                                echo "Got Exception, skipping"
                            }
                        }
                    }
                }
            }
        }
        stage('Build') {
            if (env.BRANCH_NAME == 'develop' || env.BRANCH_NAME == 'master') {
                def ZipName = env.BUILD_TAG.replace('jenkins-', '')
                echo ZipName
                def container = 'deforce/lc-ubuntu-builder'
                sh "cp requires_windows.txt requirements.txt"
                def binariesLocation = "http://repo.intra.czt.lv/lalkachat/"
                sh "wget -r --cut-dirs=1 -nH -np --reject index.html ${binariesLocation} "
                sh "docker run -v \"\$(pwd):/src/\" ${container}"
                sh "sh src/jenkins/build_default_themes.sh"
                sh "cp -r http/ dist/windows/main/http/"
                sh "chmod a+x -R dist/windows/main/"
                sh "mv dist/windows/main dist/windows/LalkaChat"
                dir('dist/windows/') {
                    sh "zip -r ${ZipName}.zip LalkaChat"
                }
                archive "dist/windows/${ZipName}.zip"
                sh "chmod 664 dist/windows/${ZipName}.zip"
                sh "scp dist/windows/${ZipName}.zip ${UploadPath}"
                sh "tar -zcvf themes-${BRANCH_NAME.replace('/', '-')}.tar.gz http/"
                sh "scp themes-${BRANCH_NAME.replace('/', '-')}.tar.gz ${UploadPath}"
            }
        }
    }
    finally {
        stage('Cleanup') {
            if(!stable) {
                currentBuild.result = 'UNSTABLE'
            }
            sh 'rm -rf dist/'
            sh 'docker rm $(docker ps -aq) || true'
            sh 'docker rmi -f $(docker images -a | grep \'^<none>\' | awk \'{print \$3}\') || true'
            deleteDir()
        }
    }
}
