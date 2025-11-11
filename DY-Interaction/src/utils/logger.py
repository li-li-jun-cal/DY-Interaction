#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
统一管理项目日志
"""

import logging
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = __name__, config_path: str = "config/config.json") -> logging.Logger:
    """配置并返回logger实例
    
    Args:
        name: logger名称
        config_path: 配置文件路径
        
    Returns:
        配置好的logger实例
    """
    # 加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        log_config = config.get('logging', {})
    except FileNotFoundError:
        log_config = {
            'level': 'INFO',
            'file': 'logs/app.log',
            'max_size_mb': 10,
            'backup_count': 5
        }
    
    # 创建日志目录
    log_file = Path(log_config.get('file', 'logs/app.log'))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 文件handler（带轮转）
    max_bytes = log_config.get('max_size_mb', 10) * 1024 * 1024
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=log_config.get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

