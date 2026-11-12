"""服务启动脚本。

用法：
    python run.py            # 按 config.yaml 启动
    python run.py --port 8080
"""

from __future__ import annotations   # 允许在类型注解里使用新语法，避免运行期求值

import argparse                     # 解析命令行参数，不硬编码端口

import uvicorn                      # ASGI 服务器，FastAPI 的运行时载体

from app.core.config import config  # 读取全局配置（host/port/reload 全部来自 yaml）


def main() -> None:
    """解析参数并启动 uvicorn。

    入参：命令行参数（可选 --host / --port / --reload）。
    出参：无（阻塞运行）。
    失败行为：端口被占用时 uvicorn 抛 OSError，进程退出。
    """
    parser = argparse.ArgumentParser(description="启动调研智能体服务")   # 构造参数解析器
    parser.add_argument("--host", default=config.service.host, help="监听地址")          # 默认取配置文件
    parser.add_argument("--port", type=int, default=config.service.port, help="监听端口")  # 默认取配置文件
    parser.add_argument("--reload", action="store_true", default=config.service.reload, help="热重载")  # 仅调试用
    args = parser.parse_args()   # 执行解析，得到最终生效参数

    uvicorn.run(                 # 启动 ASGI 服务
        "app.main:app",          # 以字符串形式指向应用实例，便于热重载重新导入
        host=args.host,          # 监听地址（默认 127.0.0.1，不对外暴露）
        port=args.port,          # 监听端口
        reload=args.reload,      # 热重载开关
        log_level="info",        # 日志级别，与 app/core/logger.py 保持一致
    )


if __name__ == "__main__":   # 仅在直接执行本文件时启动，被 import 时不启动
    main()                   # 进入启动流程
