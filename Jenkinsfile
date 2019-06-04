pipeline {
    agent {
        node {
            label 'docker-host'
        }
    }
    stages {
        stage('Init') {
            steps {
                sh 'mkdir -p results'
                sh 'mkdir -p http'
                sh 'rsync -az src/jenkins/root/ ./'
                writeFile file: 'default_branch', text: "${BRANCH_NAME},${BUILD_NUMBER}"
            }
        }
        stage('Build Themes') {
            agent {
              dockerfile {
                dir '.'
                filename 'docker/runner/Dockerfile'
                reuseNode true
              }
            }
            environment {
                // Fix for NPM in docker
                HOME = "."
            }
            steps {
                echo 'Building Themes!'
                sh 'src/jenkins/build_themes.sh'
            }
        }
        stage('Testing') {
            stages {
                stage('Themes') {
                    when {
                        changeset 'src/themes/**'
                    }
                    steps {
                        echo 'Testing themes'
                    }
                }
                stage('Chat') {
                    when {
                        changeset 'modules/**'
                    }
                    steps {
                        echo 'Testing Chat'
                    }
                }
            }
        }
        stage('Publish') {
            environment {
                ZIP_NAME = "LalkaChat-${BRANCH_NAME}-${BUILD_NUMBER}"
                THEME_NAME = "themes-${BRANCH_NAME}"
                UPLOAD_DIR = "/mnt/lc"
                BUILDER = "deforce/lc-builder"
                SECRETS_FILE = "http://repo.intra.czt.lv/lalkachat/secrets.yaml"
            }
            steps {
                echo "Building Builder"
                sh "docker build -t \${BUILDER} -f docker/windows-builder/Dockerfile ."
                sh "cp requires_windows.txt requirements.txt"
                sh "wget ${SECRETS_FILE}"
                sh """docker run -v "\$(pwd):/src/" \${BUILDER}"""
                sh "sudo /bin/chown -R jenkins.jenkins ./"
                sh "cp -r http/ dist/windows/main/http/"
                dir('dist/windows') {
                    sh "mv main LalkaChat"
                    sh "zip -r \${ZIP_NAME}.zip LalkaChat"
                    sh "chmod 664 \${ZIP_NAME}.zip"
                    sh "mv \${ZIP_NAME}.zip \$UPLOAD_DIR/"
                }
            }
        }
    }
    post {
        cleanup {
            cleanWs()
        }
    }
}