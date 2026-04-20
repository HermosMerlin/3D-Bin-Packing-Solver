import json
import os
from itertools import product
from typing import List, Dict, Any
from logger import get_logger
from optimization import ALGORITHMS, getAlgorithmParamKeys

logger = get_logger("testCaseManager")

class TestCaseManager:
    def __init__(self, testPath: str):
        self.testDir: str = os.path.join(testPath, "test")

    def validateTestCase(self, testCase: Dict[str, Any], filename: str) -> bool:
        """Validate a test case before it is executed."""
        try:
            container = testCase.get("container")
            if not container:
                logger.error(f"测试用例 {filename} 缺少 'container' 定义")
                return False

            for dim in ["L", "W", "H", "maxWeight"]:
                val = container.get(dim)
                if val is None or val <= 0:
                    logger.error(
                        f"测试用例 {filename} 的容器参数 {dim}={val} 不合法（必须 > 0）"
                    )
                    return False

            itemTypes = testCase.get("itemTypes")
            if not itemTypes or not isinstance(itemTypes, list):
                logger.error(f"测试用例 {filename} 缺少 'itemTypes' 列表")
                return False

            for i, itemType in enumerate(itemTypes):
                for dim in ["l", "w", "h", "weight", "count"]:
                    val = itemType.get(dim)
                    if val is None or val <= 0:
                        logger.error(
                            f"测试用例 {filename} 的货物类型索引 {i} 参数 {dim}={val} 不合法"
                        )
                        return False

                if (
                    itemType["l"] > container["L"]
                    or itemType["w"] > container["W"]
                    or itemType["h"] > container["H"]
                ):
                    dimsItem = sorted([itemType["l"], itemType["w"], itemType["h"]])
                    dimsContainer = sorted([container["L"], container["W"], container["H"]])
                    if any(dimsItem[j] > dimsContainer[j] for j in range(3)):
                        logger.error(
                            f"测试用例 {filename} 的货物规格 "
                            f"{itemType['l']}x{itemType['w']}x{itemType['h']} 超过容器尺寸"
                        )
                        return False

            return True
        except Exception as e:
            logger.error(f"校验测试用例 {filename} 时发生异常: {e}")
            return False

    def loadTestCases(self) -> List[Dict[str, Any]]:
        """Load all JSON test cases under the test directory."""
        testCases: List[Dict[str, Any]] = []
        if not os.path.exists(self.testDir):
            os.makedirs(self.testDir)
            logger.info(f"测试目录 {self.testDir} 不存在，已创建")
            return testCases

        for filename in os.listdir(self.testDir):
            if ".." in filename or os.path.isabs(filename):
                logger.warning(f"跳过潜在不安全的文件名: {filename}")
                continue

            if filename.endswith(".json"):
                filepath = os.path.join(self.testDir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        testCase = json.load(f)

                    if not self.validateTestCase(testCase, filename):
                        logger.warning(f"跳过校验失败的测试用例: {filename}")
                        continue

                    testCaseName = os.path.splitext(filename)[0]
                    testCase["name"] = testCaseName
                    testCases.append(testCase)
                except Exception as e:
                    logger.error(f"加载测试文件 {filename} 失败: {e}")

        return testCases

    def _isRangeConfig(self, value: Any) -> bool:
        return isinstance(value, dict) and "min" in value and "max" in value

    def _getDecimalPlaces(self, value: Any) -> int:
        text = str(value)
        if "." not in text:
            return 0
        return len(text.rstrip("0").split(".")[1])

    def _expandRange(self, rangeConfig: Dict[str, Any]) -> List[Any]:
        minVal = rangeConfig["min"]
        maxVal = rangeConfig["max"]
        step = rangeConfig.get("step", 1)

        if step == 0:
            return [minVal]

        isIntegerRange = all(
            isinstance(val, int) and not isinstance(val, bool)
            for val in [minVal, maxVal, step]
        )
        if isIntegerRange:
            values = list(range(minVal, maxVal + 1, step))
            return values if values else [minVal]

        decimalPlaces = max(
            self._getDecimalPlaces(minVal),
            self._getDecimalPlaces(maxVal),
            self._getDecimalPlaces(step)
        )
        epsilon = 10 ** (-(decimalPlaces + 2))
        current = float(minVal)
        values: List[Any] = []

        while current <= float(maxVal) + epsilon:
            values.append(round(current, decimalPlaces))
            current += float(step)

        return values if values else [minVal]

    def _expandParamValues(self, value: Any) -> List[Any]:
        if isinstance(value, list):
            return value if value else []
        if self._isRangeConfig(value):
            return self._expandRange(value)
        return [value]

    def _sanitizeAlgorithmConfig(
        self,
        algorithmType: str,
        rawConfig: Dict[str, Any],
        warnUnknown: bool
    ) -> Dict[str, Any]:
        allowedKeys = set(getAlgorithmParamKeys(algorithmType))
        sanitizedConfig: Dict[str, Any] = {}

        for key, value in rawConfig.items():
            if key == "useTimeSeed" or key in allowedKeys:
                sanitizedConfig[key] = value
            elif warnUnknown:
                logger.warning(f"算法 {algorithmType} 忽略未使用的参数: {key}")

        return sanitizedConfig

    def _normalizeLegacyParamConfig(self, paramConfig: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        algorithmTypes = paramConfig.get("algorithmType", list(ALGORITHMS.keys()))
        if not isinstance(algorithmTypes, list):
            algorithmTypes = [algorithmTypes]

        sharedConfig = {
            key: value for key, value in paramConfig.items()
            if key != "algorithmType"
        }
        normalizedConfig: Dict[str, Dict[str, Any]] = {}

        for algorithmType in algorithmTypes:
            if algorithmType not in ALGORITHMS:
                logger.warning(f"忽略未知算法配置: {algorithmType}")
                continue

            normalizedConfig[algorithmType] = self._sanitizeAlgorithmConfig(
                algorithmType,
                sharedConfig,
                warnUnknown=False
            )

        return normalizedConfig

    def _normalizeAlgorithmConfigs(self, paramConfig: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        if not isinstance(paramConfig, dict) or not paramConfig:
            return {}

        nestedAlgorithmKeys = [
            key for key in paramConfig.keys()
            if key in ALGORITHMS and isinstance(paramConfig[key], dict)
        ]
        if nestedAlgorithmKeys:
            normalizedConfig: Dict[str, Dict[str, Any]] = {}
            for algorithmType in nestedAlgorithmKeys:
                normalizedConfig[algorithmType] = self._sanitizeAlgorithmConfig(
                    algorithmType,
                    paramConfig[algorithmType],
                    warnUnknown=True
                )
            return normalizedConfig

        return self._normalizeLegacyParamConfig(paramConfig)

    def generateParamCombinations(self, paramConfig: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate parameter combinations grouped by algorithm."""
        combinations: List[Dict[str, Any]] = []
        normalizedConfig = self._normalizeAlgorithmConfigs(paramConfig)

        for algorithmType, algorithmConfig in normalizedConfig.items():
            paramKeys = [
                key for key in getAlgorithmParamKeys(algorithmType)
                if key in algorithmConfig
            ]
            paramValues = [
                self._expandParamValues(algorithmConfig[key])
                for key in paramKeys
            ]
            useTimeSeed = algorithmConfig.get("useTimeSeed", True)

            if not paramKeys:
                combinations.append({
                    "algorithmType": algorithmType,
                    "params": {},
                    "useTimeSeed": useTimeSeed
                })
                continue

            for values in product(*paramValues):
                combinations.append({
                    "algorithmType": algorithmType,
                    "params": {
                        key: value for key, value in zip(paramKeys, values)
                    },
                    "useTimeSeed": useTimeSeed
                })

        return combinations

    def getEffectiveParams(self, testCaseParams: Dict[str, Any], defaultParams: Dict[str, Any]) -> Dict[str, Any]:
        """Merge per-algorithm defaults with test-case-specific overrides."""
        defaultAlgorithmConfigs = self._normalizeAlgorithmConfigs(defaultParams)
        testCaseAlgorithmConfigs = self._normalizeAlgorithmConfigs(testCaseParams)

        if not defaultAlgorithmConfigs and not testCaseAlgorithmConfigs:
            return {algorithmType: {} for algorithmType in ALGORITHMS.keys()}

        algorithmOrder = list(defaultAlgorithmConfigs.keys())
        for algorithmType in testCaseAlgorithmConfigs.keys():
            if algorithmType not in algorithmOrder:
                algorithmOrder.append(algorithmType)

        effectiveParams: Dict[str, Any] = {}
        for algorithmType in algorithmOrder:
            mergedConfig: Dict[str, Any] = {}
            if algorithmType in defaultAlgorithmConfigs:
                mergedConfig.update(defaultAlgorithmConfigs[algorithmType])
            if algorithmType in testCaseAlgorithmConfigs:
                mergedConfig.update(testCaseAlgorithmConfigs[algorithmType])
            effectiveParams[algorithmType] = mergedConfig

        return effectiveParams
