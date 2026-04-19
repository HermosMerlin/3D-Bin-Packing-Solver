import logging
import os
import sys
import re

class PathDesensitizerFilter(logging.Filter):
    """
    日志过滤器：自动将绝对路径脱敏，防止泄露系统用户名等隐私信息
    """
    def __init__(self):
        super().__init__()
        # 匹配 Windows 和 Unix 绝对路径的正则（简化版）
        # 重点匹配 C:\Users\xxx... 或 /home/xxx...
        self.user_path_pattern = re.compile(
            r'([a-zA-Z]:\\Users\\[^\s\\]+)|(/home/[^\s/]+)', 
            re.IGNORECASE
        )

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.user_path_pattern.sub(r'<USER_HOME>', record.msg)
        return True

def setup_logging(log_level="INFO", log_file=None):
    """
    配置全局日志系统
    :param log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
    :param log_file: 日志文件路径，如果为 None 则只输出到终端
    """
    # 转换级别字符串为 logging 常量
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除现有的 handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 定义统一的日志格式
    # 终端输出使用简洁格式，文件输出使用详细格式
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s')

    # 定义统一的日志过滤器
    path_filter = PathDesensitizerFilter()

    # 1. 配置终端输出 (stdout)
    # 解决 Windows 终端可能的编码问题
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    console_handler.addFilter(path_filter)
    root_logger.addHandler(console_handler)

    # 2. 如果指定了文件，配置文件输出
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG) # 文件始终记录最详细的 DEBUG 信息
        file_handler.addFilter(path_filter)
        root_logger.addHandler(file_handler)

    return root_logger

def get_logger(name):
    """获取子模块的 logger"""
    return logging.getLogger(name)
