/**
 * [INPUT]: 依赖 Jenkins Credentials 插件、sshpass
 * [OUTPUT]: 手动触发部署 skyeye-bot 到 EC2
 * [POS]: CI/CD 配置，Jenkins Pipeline 脚本
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

pipeline {
    agent any

    environment {
        EC2_HOST = '54.90.190.19'
        EC2_USER = 'root'
        DEPLOY_PATH = '/opt/skyeye-bot'
    }

    stages {
        stage('Deploy to EC2') {
            steps {
                withCredentials([string(credentialsId: 'ec2-skyeye-password', variable: 'EC2_PASS')]) {
                    sh """
                        sshpass -p "\${EC2_PASS}" ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} '
                            set -e

                            echo "==== 1. 进入项目目录 ===="
                            cd ${DEPLOY_PATH}

                            echo "==== 2. 拉取最新代码 ===="
                            git pull origin main

                            echo "==== 3. 停止旧容器 ===="
                            docker-compose -f docker/docker-compose.yml down || true

                            echo "==== 4. 清理 Docker 缓存 ===="
                            docker system prune -af --volumes --filter "label!=keep"
                            docker builder prune -af

                            echo "==== 5. 重新构建并启动 ===="
                            docker-compose -f docker/docker-compose.yml --env-file .env up -d --build

                            echo "==== 6. 检查容器状态 ===="
                            sleep 10
                            docker ps
                            docker logs skyeye-bot --tail 20

                            echo "==== 部署完成 ===="
                        '
                    """
                }
            }
        }
    }

    post {
        success {
            echo '✅ 部署成功!'
        }
        failure {
            echo '❌ 部署失败，请检查日志'
        }
    }
}
