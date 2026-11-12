"""日志模块。

统一出格式，避免各模块各自 basicConfig 导致重复 handler。
"""

from __future__ import annotations   # 类型注解延迟求值

import logging   # 标准库日志，不引入第三方
import sys       # 需要拿到 stdout 句柄，交给 StreamHandler

from app.core.config import config   # 读取 debug 开关决定日志级别

# 日志格式：时间 级别 模块名 消息
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"   # 统一格式，便于 grep 与排查


def _build_logger() -> logging.Logger:
    """构建进程级根 logger。

    入参：无（读取全局 config 的 debug 开关）。
    出参：已配置好的 logging.Logger。
    失败行为：若重复调用，先清理已有 handler，避免日志重复打印。
    """
    root = logging.getLogger("planting")                              # 固定根名，所有子日志都挂在这棵树下
    root.setLevel(logging.DEBUG if config.app.debug else logging.INFO)  # debug 时放行 DEBUG 级

    # 清空可能由 import 顺序造成的重复 handler
    for handler in list(root.handlers):   # 复制一份再遍历，避免边遍历边改
        root.removeHandler(handler)       # 逐个摘除，保证只有一处输出

    stream = logging.StreamHandler(stream=sys.stdout)   # 输出到 stdout，由 uvicorn/进程管理器统一收集
    stream.setFormatter(logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))   # 显式指定时间格式
    root.addHandler(stream)   # 挂载唯一 handler

    # 避免向 uvicorn 的 root logger 重复传播
    root.propagate = False   # 关掉向上传播，否则同一条日志会打印两次
    return root              # 返回配置完成的根 logger


logger: logging.Logger = _build_logger()   # import 期完成一次构建


def get_logger(name: str) -> logging.Logger:
    """获取带模块名的子 logger。

    入参：name 子 logger 名称，一般传 __name__。
    出参：logging.Logger 子实例。
    失败行为：不抛异常。
    """
    return logger.getChild(name)   # 继承根配置，只额外带上模块名
