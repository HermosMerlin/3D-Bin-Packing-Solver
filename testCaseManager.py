import json
import os
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("testCaseManager")

class TestCaseManager:
    def __init__(self, testPath: str):
        self.testDir: str = os.path.join(testPath, "test")

    def loadTestCases(self) -> List[Dict[str, Any]]:
        """加载测试目录下的所有JSON文件"""
        testCases: List[Dict[str, Any]] = []
        if not os.path.exists(self.testDir):
            os.makedirs(self.testDir)
            logger.info(f"测试目录 {self.testDir} 不存在，已创建")
            return testCases

        for filename in os.listdir(self.testDir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.testDir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        testCase = json.load(f)
                        testCaseName = os.path.splitext(filename)[0]
                        testCase["name"] = testCaseName
                        testCases.append(testCase)
                except Exception as e:
                    logger.error(f"加载测试文件 {filename} 失败: {e}")

        return testCases

    def generateParamCombinations(self, paramConfig: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成参数组合列表"""
        combinations: List[Dict[str, Any]] = []

        # 处理迭代次数
        if isinstance(paramConfig.get("iterations"), dict):
            iterConfig = paramConfig["iterations"]
            minVal = iterConfig.get("min", 50)
            maxVal = iterConfig.get("max", 150)
            step = iterConfig.get("step", 50)
            iterationsList = list(range(minVal, maxVal + 1, step))
        else:
            iterationsList = [paramConfig.get("iterations", 100)]

        # 处理随机率
        if isinstance(paramConfig.get("randomRate"), dict):
            rateConfig = paramConfig["randomRate"]
            minVal = rateConfig.get("min", 0.1)
            maxVal = rateConfig.get("max", 0.3)
            step = rateConfig.get("step", 0.1)
            current = minVal
            randomRates = []
            while current <= maxVal + 1e-9:
                randomRates.append(round(current, 2))
                current += step
        else:
            randomRates = [paramConfig.get("randomRate", 0.2)]

        useTimeSeed = paramConfig.get("useTimeSeed", True)

        for iterVal in iterationsList:
            for rateVal in randomRates:
                combinations.append({
                    "iterations": iterVal,
                    "randomRate": rateVal,
                    "useTimeSeed": useTimeSeed
                })

        return combinations

    def getEffectiveParams(self, testCaseParams: Dict[str, Any], defaultParams: Dict[str, Any]) -> Dict[str, Any]:
        """获取有效参数"""
        effectiveParams: Dict[str, Any] = {}
        for key in ["iterations", "randomRate", "useTimeSeed"]:
            if key in testCaseParams:
                effectiveParams[key] = testCaseParams[key]
            elif key in defaultParams:
                effectiveParams[key] = defaultParams[key]
        return effectiveParams
