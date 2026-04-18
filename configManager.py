import json
import os

class ConfigManager:
    def __init__(self, configPath):
        self.configFile = os.path.join(configPath, "config.json")
        self.config = self.loadConfig()

    def loadConfig(self):
        """加载全局配置"""
        if not os.path.exists(self.configFile):
            print(f"配置文件未找到，使用默认配置")
            # 创建默认配置文件
            defaultConfig = {
                "algorithmDefaults": {
                    "iterations": {
                        "min": 50,
                        "max": 50,
                        "step": 50
                    },
                    "randomRate": {
                        "min": 0.1,
                        "max": 0.1,
                        "step": 0.1
                    },
                    "useTimeSeed": True
                },
                "output": {
                    "resultsDir": "results",
                    "saveDetailedLog": True,
                    "showPlacementText": True,
                    "enableVisualization": False
                }
            }
            with open(self.configFile, 'w', encoding='utf-8') as f:
                json.dump(defaultConfig, f, indent=2)
            return defaultConfig

        with open(self.configFile, 'r', encoding='utf-8') as f:
            return json.load(f)

    def getConfig(self):
        """获取配置"""
        return self.config

    def getOutputConfig(self):
        """获取输出配置"""
        return self.config.get("output", {})

    def getDefaultParams(self):
        """获取默认算法参数"""
        return self.config.get("algorithmDefaults", {})
