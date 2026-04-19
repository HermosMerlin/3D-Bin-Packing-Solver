import json
import os
from typing import Dict, Any
from logger import get_logger

logger = get_logger("configManager")

class ConfigManager:
    def __init__(self, configPath: str):
        self.configFile: str = os.path.join(configPath, "config.json")
        self.config: Dict[str, Any] = self.loadConfig()

    def loadConfig(self) -> Dict[str, Any]:
        """加载全局配置"""
        if not os.path.exists(self.configFile):
            logger.warning(f"配置文件未找到，使用默认配置")
            # 创建默认配置文件
            defaultConfig = {
                "algorithmDefaults": {
                    "iterations": {"min": 10, "max": 10, "step": 50},
                    "randomRate": {"min": 0.1, "max": 0.1, "step": 0.1},
                    "useTimeSeed": True
                },
                "output": {
                    "resultsDir": "results",
                    "cacheDir": "cache",
                    "enableCache": True,
                    "saveDetailedLog": False,
                    "showPlacementText": False,
                    "enableVisualization": True,
                    "saveStaticImage": False,
                    "logging": {
                        "consoleLevel": "INFO",
                        "fileLevel": "DEBUG",
                        "saveToFile": True
                    }
                }
            }
            
            # 使用临时文件并原子替换，防止并发写入导致损坏
            tempFile = self.configFile + ".tmp"
            try:
                with open(tempFile, 'w', encoding='utf-8') as f:
                    json.dump(defaultConfig, f, indent=2)
                os.replace(tempFile, self.configFile)
            except Exception as e:
                logger.error(f"保存默认配置失败: {e}")
                if os.path.exists(tempFile):
                    os.remove(tempFile)
                
            return defaultConfig

        try:
            with open(self.configFile, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用内存默认值")
            return {}

    def getConfig(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config

    def getOutputConfig(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.config.get("output", {})

    def getDefaultParams(self) -> Dict[str, Any]:
        """获取默认算法参数"""
        return self.config.get("algorithmDefaults", {})
