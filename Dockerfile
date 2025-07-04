# 使用Python 3.11官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p data/temp logs data/rclone_configs

# 复制启动脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 设置环境变量
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV DOCKER_ENV=true
ENV RCLONE_CONFIG_DIR=/app/data/rclone_configs

# 暴露端口
EXPOSE 5000

# 设置启动命令
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "run.py"]
