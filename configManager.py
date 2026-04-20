import json
import os
from typing import Any, Dict
from logger import get_logger

logger = get_logger("configManager")

DEFAULT_CONFIG: Dict[str, Any] = {
    "algorithmDefaults": {
        "greedy_search": {
            "iterations": {"min": 20, "max": 40, "step": 20},
            "useTimeSeed": False,
            "baseSeed": 42,
            "repeatCount": 1
        },
        "simulated_annealing": {
            "iterations": {"min": 20, "max": 40, "step": 20},
            "initialTemp": 50.0,
            "coolingRate": 0.95,
            "minTemp": 0.1,
            "useTimeSeed": False,
            "baseSeed": 42,
            "repeatCount": 1
        }
    },
    "output": {
        "resultsDir": "results",
        "cacheDir": "cache",
        "enableCache": True,
        "cacheVersion": 3,
        "exportSummaryData": True,
        "saveSolutionText": "only-best",
        "saveDetailedLog": False,
        "showPlacementText": False,
        "enableVisualization": True,
        "saveStaticImage": False,
        "analysisCharts": [],
        "logging": {
            "consoleLevel": "INFO",
            "fileLevel": "DEBUG",
            "saveToFile": True
        }
    }
}

class ConfigManager:
    def __init__(self, configPath: str):
        self.configFile = os.path.join(configPath, "config.json")
        self.config = self.loadConfig()

    def loadConfig(self) -> Dict[str, Any]:
        if not os.path.exists(self.configFile):
            logger.warning("配置文件未找到，使用默认配置")
            return DEFAULT_CONFIG

        try:
            with open(self.configFile, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged["algorithmDefaults"] = loaded.get(
                "algorithmDefaults",
                DEFAULT_CONFIG["algorithmDefaults"]
            )
            merged["output"] = dict(DEFAULT_CONFIG["output"])
            merged["output"].update(loaded.get("output", {}))
            return merged
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用默认配置")
            return DEFAULT_CONFIG

    def getConfig(self) -> Dict[str, Any]:
        return self.config

    def getOutputConfig(self) -> Dict[str, Any]:
        return self.config.get("output", {})

    def getDefaultParams(self) -> Dict[str, Any]:
        return self.config.get("algorithmDefaults", {})
