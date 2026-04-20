import copy
import json
import os
from itertools import product
from typing import Any, Dict, List
from dataStructures import (
    ContainerType,
    GlobalConstraints,
    Item,
    ItemConstraints,
    ItemType,
    ObjectiveSpec,
    ProblemInstance
)
from logger import get_logger
from optimization import ALGORITHMS, getAlgorithmParamKeys

logger = get_logger("testCaseManager")

DEFAULT_BASE_SEED = 42
DEFAULT_REPEAT_COUNT = 1
CONTROL_CONFIG_KEYS = {"useTimeSeed", "baseSeed", "repeatCount"}
PRIMARY_TAGS = {"standard", "fragile", "oriented"}
SUPPORTED_SCHEMA_VERSION = 2
REQUIRED_UNITS = {
    "lengthUnit": "cm",
    "weightUnit": "kg",
    "bearingPressureUnit": "kg/m^2",
    "clearanceUnit": "cm"
}

TAG_CONSTRAINT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "allowedRotations": [0, 1, 2, 3, 4, 5],
        "canSupportOthers": True,
        "allowedSupportSources": ["floor", "standard", "oriented"],
        "requiredSupportAreaRatio": 0.0,
        "requiredSupportProjectionContainment": False
    },
    "fragile": {
        "allowedRotations": [0, 1, 2, 3, 4, 5],
        "canSupportOthers": False,
        "allowedSupportSources": ["floor", "standard"],
        "requiredSupportAreaRatio": 1.0,
        "requiredSupportProjectionContainment": False
    },
    "oriented": {
        "allowedRotations": [0],
        "canSupportOthers": True,
        "allowedSupportSources": ["floor", "standard", "oriented"],
        "requiredSupportAreaRatio": 0.0,
        "requiredSupportProjectionContainment": True
    }
}

class TestCaseManager:
    def __init__(self, testPath: str):
        self.testDir: str = os.path.join(testPath, "test")

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
            if key in CONTROL_CONFIG_KEYS or key in allowedKeys:
                sanitizedConfig[key] = value
            elif warnUnknown:
                logger.warning(f"算法 {algorithmType} 忽略未使用的参数: {key}")

        return sanitizedConfig

    def _normalizeBaseSeed(self, value: Any) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        logger.warning(f"无效的 baseSeed={value}，将回退到 {DEFAULT_BASE_SEED}")
        return DEFAULT_BASE_SEED

    def _normalizeRepeatCount(self, value: Any) -> int:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        logger.warning(f"无效的 repeatCount={value}，将回退到 {DEFAULT_REPEAT_COUNT}")
        return DEFAULT_REPEAT_COUNT

    def _normalizeAlgorithmConfigs(self, paramConfig: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        if not isinstance(paramConfig, dict) or not paramConfig:
            return {}

        normalizedConfig: Dict[str, Dict[str, Any]] = {}
        for algorithmType, rawConfig in paramConfig.items():
            if algorithmType not in ALGORITHMS:
                logger.warning(f"忽略未知算法配置: {algorithmType}")
                continue
            if not isinstance(rawConfig, dict):
                logger.warning(f"算法 {algorithmType} 的配置不是对象，已忽略")
                continue
            normalizedConfig[algorithmType] = self._sanitizeAlgorithmConfig(
                algorithmType,
                rawConfig,
                warnUnknown=True
            )
        return normalizedConfig

    def getEffectiveParams(
        self,
        testCaseParams: Dict[str, Any],
        defaultParams: Dict[str, Any]
    ) -> Dict[str, Any]:
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

    def generateParamCombinations(self, paramConfig: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            useTimeSeed = bool(algorithmConfig.get("useTimeSeed", False))
            baseSeed = self._normalizeBaseSeed(
                algorithmConfig.get("baseSeed", DEFAULT_BASE_SEED)
            )
            repeatCount = self._normalizeRepeatCount(
                algorithmConfig.get("repeatCount", DEFAULT_REPEAT_COUNT)
            )

            if not paramKeys:
                combinations.append({
                    "algorithmType": algorithmType,
                    "params": {},
                    "useTimeSeed": useTimeSeed,
                    "baseSeed": baseSeed,
                    "repeatCount": repeatCount
                })
                continue

            for values in product(*paramValues):
                combinations.append({
                    "algorithmType": algorithmType,
                    "params": {
                        key: value for key, value in zip(paramKeys, values)
                    },
                    "useTimeSeed": useTimeSeed,
                    "baseSeed": baseSeed,
                    "repeatCount": repeatCount
                })

        return combinations

    def _resolve_primary_tag(self, tags: List[str]) -> str:
        for tag in tags:
            if tag in PRIMARY_TAGS:
                return tag
        return "standard"

    def _build_item_constraints(self, tags: List[str], rawConstraints: Dict[str, Any]) -> ItemConstraints:
        primaryTag = self._resolve_primary_tag(tags)
        merged = dict(TAG_CONSTRAINT_DEFAULTS[primaryTag])
        merged.update(rawConstraints or {})
        return ItemConstraints.from_dict(merged)

    def _normalize_item_tags(self, rawTags: Any) -> List[str]:
        if not rawTags:
            return ["standard"]
        if isinstance(rawTags, list):
            tags = [str(tag) for tag in rawTags]
        else:
            tags = [str(rawTags)]
        if not any(tag in PRIMARY_TAGS for tag in tags):
            tags.insert(0, "standard")
        return tags

    def _validate_container_types(
        self,
        testCase: Dict[str, Any],
        filename: str
    ) -> bool:
        containerTypes = testCase.get("containerTypes")
        if not containerTypes or not isinstance(containerTypes, list):
            logger.error(f"测试用例 {filename} 缺少 'containerTypes' 列表")
            return False

        seenIds = set()
        for index, containerType in enumerate(containerTypes):
            typeId = containerType.get("typeId")
            if not typeId or not isinstance(typeId, str):
                logger.error(f"测试用例 {filename} 的容器类型索引 {index} 缺少合法 typeId")
                return False
            if typeId in seenIds:
                logger.error(f"测试用例 {filename} 的容器类型重复: {typeId}")
                return False
            seenIds.add(typeId)

            for dim in ["L", "W", "H", "maxWeight", "tripCost"]:
                val = containerType.get(dim)
                if val is None or float(val) <= 0:
                    logger.error(
                        f"测试用例 {filename} 的容器类型 {typeId} 参数 {dim}={val} 不合法"
                    )
                    return False

            maxInstances = containerType.get("maxInstances")
            if maxInstances is not None and (
                not isinstance(maxInstances, int) or maxInstances <= 0
            ):
                logger.error(
                    f"测试用例 {filename} 的容器类型 {typeId} 的 maxInstances={maxInstances} 不合法"
                )
                return False

        return True

    def _validate_schema_contract(
        self,
        testCase: Dict[str, Any],
        filename: str
    ) -> bool:
        schemaVersion = testCase.get("schemaVersion")
        if schemaVersion != SUPPORTED_SCHEMA_VERSION:
            logger.error(
                f"测试用例 {filename} 的 schemaVersion={schemaVersion} 不受支持，"
                f"当前仅支持 {SUPPORTED_SCHEMA_VERSION}"
            )
            return False

        units = testCase.get("units")
        if not isinstance(units, dict):
            logger.error(f"测试用例 {filename} 缺少 'units' 定义")
            return False

        for key, expectedValue in REQUIRED_UNITS.items():
            actualValue = units.get(key)
            if actualValue != expectedValue:
                logger.error(
                    f"测试用例 {filename} 的 units.{key}={actualValue} 不合法，"
                    f"当前要求 {expectedValue}"
                )
                return False

        return True

    def _validate_item_types(
        self,
        testCase: Dict[str, Any],
        filename: str
    ) -> bool:
        itemTypes = testCase.get("itemTypes")
        if not itemTypes or not isinstance(itemTypes, list):
            logger.error(f"测试用例 {filename} 缺少 'itemTypes' 列表")
            return False

        seenIds = set()
        for index, itemType in enumerate(itemTypes):
            typeId = itemType.get("typeId")
            if not typeId or not isinstance(typeId, str):
                logger.error(f"测试用例 {filename} 的货物类型索引 {index} 缺少合法 typeId")
                return False
            if typeId in seenIds:
                logger.error(f"测试用例 {filename} 的货物类型重复: {typeId}")
                return False
            seenIds.add(typeId)

            for dim in ["l", "w", "h", "weight", "count"]:
                val = itemType.get(dim)
                if val is None or float(val) <= 0:
                    logger.error(
                        f"测试用例 {filename} 的货物类型 {typeId} 参数 {dim}={val} 不合法"
                    )
                    return False

            tags = self._normalize_item_tags(itemType.get("tags"))
            constraints = self._build_item_constraints(
                tags,
                itemType.get("constraints", {})
            )
            if not constraints.allowedRotations:
                logger.error(f"测试用例 {filename} 的货物类型 {typeId} 没有合法旋转姿态")
                return False

        return True

    def _validate_objective(
        self,
        testCase: Dict[str, Any],
        filename: str
    ) -> bool:
        objective = testCase.get("objective")
        if not isinstance(objective, dict):
            logger.error(f"测试用例 {filename} 缺少 'objective' 定义")
            return False
        if not objective.get("primaryMetric"):
            logger.error(f"测试用例 {filename} 的 objective 缺少 primaryMetric")
            return False
        return True

    def validateTestCase(self, testCase: Dict[str, Any], filename: str) -> bool:
        try:
            if not self._validate_schema_contract(testCase, filename):
                return False
            if not self._validate_container_types(testCase, filename):
                return False
            if not self._validate_item_types(testCase, filename):
                return False
            if not self._validate_objective(testCase, filename):
                return False
            return True
        except Exception as e:
            logger.error(f"校验测试用例 {filename} 时发生异常: {e}")
            return False

    def _expandTestCaseVariants(
        self,
        testCase: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        expansion = testCase.get("expansion", {})
        if not isinstance(expansion, dict) or not expansion.get("perContainerType", False):
            return [testCase]

        expandedCases: List[Dict[str, Any]] = []
        baseName = str(testCase["name"])
        for containerType in testCase["containerTypes"]:
            expandedCase = copy.deepcopy(testCase)
            expandedCase["containerTypes"] = [copy.deepcopy(containerType)]
            expandedCase["name"] = f"{baseName}__{containerType['typeId']}"
            scenarioMetadata = dict(expandedCase.get("scenarioMetadata", {}))
            scenarioMetadata["expandedFrom"] = baseName
            scenarioMetadata["expandedContainerTypeId"] = containerType["typeId"]
            expandedCase["scenarioMetadata"] = scenarioMetadata
            expandedCases.append(expandedCase)
        return expandedCases

    def loadTestCases(self) -> List[Dict[str, Any]]:
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
                    testCases.extend(self._expandTestCaseVariants(testCase))
                except Exception as e:
                    logger.error(f"加载测试文件 {filename} 失败: {e}")

        return testCases

    def buildProblemInstance(self, testCase: Dict[str, Any]) -> ProblemInstance:
        globalConstraints = GlobalConstraints.from_dict(
            testCase.get("globalConstraints")
        )
        containerTypes = [
            ContainerType(
                typeId=str(containerType["typeId"]),
                L=float(containerType["L"]),
                W=float(containerType["W"]),
                H=float(containerType["H"]),
                maxWeight=float(containerType["maxWeight"]),
                tripCost=float(containerType["tripCost"]),
                maxInstances=(
                    int(containerType["maxInstances"])
                    if containerType.get("maxInstances") is not None else None
                ),
                metadata=dict(containerType.get("metadata", {}))
            )
            for containerType in testCase["containerTypes"]
        ]

        itemTypes: List[ItemType] = []
        items: List[Item] = []
        nextItemId = 1
        for rawItemType in testCase["itemTypes"]:
            tags = self._normalize_item_tags(rawItemType.get("tags"))
            constraints = self._build_item_constraints(
                tags,
                rawItemType.get("constraints", {})
            )
            itemType = ItemType(
                typeId=str(rawItemType["typeId"]),
                l=float(rawItemType["l"]),
                w=float(rawItemType["w"]),
                h=float(rawItemType["h"]),
                weight=float(rawItemType["weight"]),
                count=int(rawItemType["count"]),
                tags=tags,
                constraints=constraints,
                metadata=dict(rawItemType.get("metadata", {}))
            )
            itemTypes.append(itemType)

            for _ in range(itemType.count):
                items.append(
                    Item(
                        id=nextItemId,
                        typeId=itemType.typeId,
                        l=itemType.l,
                        w=itemType.w,
                        h=itemType.h,
                        weight=itemType.weight,
                        tags=list(itemType.tags),
                        constraints=ItemConstraints.from_dict(itemType.constraints.to_dict()),
                        metadata=dict(itemType.metadata)
                    )
                )
                nextItemId += 1

        scenarioMetadata = dict(testCase.get("scenarioMetadata", {}))
        scenarioMetadata.setdefault("itemTypeCount", len(itemTypes))
        scenarioMetadata.setdefault("itemCountTotal", len(items))
        scenarioMetadata.setdefault("containerTypeCount", len(containerTypes))
        scenarioMetadata.setdefault(
            "containerAspectRatio",
            max(
                (containerType.aspectRatio for containerType in containerTypes),
                default=0.0
            )
        )
        scenarioMetadata.setdefault(
            "fragileRatio",
            sum(item.has_tag("fragile") for item in items) / len(items) if items else 0.0
        )
        scenarioMetadata.setdefault(
            "orientedRatio",
            sum(item.has_tag("oriented") for item in items) / len(items) if items else 0.0
        )

        return ProblemInstance(
            name=str(testCase["name"]),
            schemaVersion=int(testCase["schemaVersion"]),
            units=dict(testCase["units"]),
            containerTypes=containerTypes,
            itemTypes=itemTypes,
            items=items,
            globalConstraints=globalConstraints,
            objective=ObjectiveSpec.from_dict(testCase["objective"]),
            analysis=dict(testCase.get("analysis", {})),
            scenarioMetadata=scenarioMetadata,
            algorithmParams=dict(testCase.get("algorithmParams", {}))
        )
