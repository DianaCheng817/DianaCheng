# ============================================================
# 种植灌溉与农事记录 · 调研智能体 MVP 镜像
# 构建：docker build -t planting-agent .
# 运行：docker run -p 8000:8000 --env-file .env planting-agent
# ============================================================
FROM python:3.11-slim

# 不生成 pyc 文件、日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# 先复制依赖清单，利用镜像层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制工程代码与文档
COPY . .

# 容器内监听所有网卡，便于平台/宿主机访问
EXPOSE 8000

# 启动 ASGI 服务；端口由平台注入的 PORT 环境变量决定
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
