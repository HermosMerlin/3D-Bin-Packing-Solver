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
        """Load global configuration."""
        if not os.path.exists(self.configFile):
            logger.warning("配置文件未找到，使用默认配置")
            defaultConfig = {
                "algorithmDefaults": {
                    "greedy_search": {
                        "iterations": {"min": 10, "max": 10, "step": 50},
                        "useTimeSeed": True
                    },
                    "simulated_annealing": {
                        "iterations": {"min": 10, "max": 10, "step": 50},
                        "initialTemp": 100.0,
                        "coolingRate": 0.95,
                        "minTemp": 0.01,
                        "useTimeSeed": True
                    }
                },
                "output": {
                    "resultsDir": "results",
                    "cacheDir": "cache",
                    "enableCache": True,
                    "cacheVersion": 1,
                    "saveDetailedLog": False,
                    "showPlacementText": False,
                    "enableVisualization": True,
                    "saveStaticImage": False,
                    "visualizeBestPerAlgorithmOnly": False,
                    "logging": {
                        "consoleLevel": "INFO",
                        "fileLevel": "DEBUG",
                        "saveToFile": True
                    }
                }
            }

            tempFile = self.configFile + ".tmp"
            try:
                with open(tempFile, "w", encoding="utf-8") as f:
                    json.dump(defaultConfig, f, indent=2)
                os.replace(tempFile, self.configFile)
            except Exception as e:
                logger.error(f"保存默认配置失败: {e}")
                if os.path.exists(tempFile):
                    os.remove(tempFile)

            return defaultConfig

        try:
            with open(self.configFile, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用空配置")
            return {}

    def getConfig(self) -> Dict[str, Any]:
        """Return full configuration."""
        return self.config

    def getOutputConfig(self) -> Dict[str, Any]:
        """Return output configuration."""
        return self.config.get("output", {})

    def getDefaultParams(self) -> Dict[str, Any]:
        """Return algorithm default parameters."""
        return self.config.get("algorithmDefaults", {})
