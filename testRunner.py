import hashlib
import json
import os
import random
import time
from functools import lru_cache
from typing import List, Dict, Any, Tuple
from dataStructures import Item, Container, PackingSolution
from optimization import optimizePacking, filterAlgorithmParams, formatAlgorithmParams
from logger import get_logger
from testCaseManager import TestCaseManager
from solutionValidator import validatePackingSolution

logger = get_logger("testRunner")

CACHE_FINGERPRINT_FILES: Tuple[str, ...] = (
    "optimization.py",
    "packingLogic.py",
    "dataStructures.py",
    "testRunner.py"
)
DEFAULT_CACHE_VERSION = 1

def generateTimeSeed() -> int:
    """Generate a seed based on the current time."""
    timestamp = int(time.time() * 1000)
    randomPart = random.randint(0, 9999)
    return timestamp + randomPart

def generateItemsFromTypes(itemTypes: List[Dict[str, Any]]) -> List[Item]:
    """Build item instances from the test-case item specification."""
    items: List[Item] = []
    itemIdCounter = 1

    for itemType in itemTypes:
        count = itemType["count"]
        for _ in range(count):
            item = Item(
                id=itemIdCounter,
                l=itemType["l"],
                w=itemType["w"],
                h=itemType["h"],
                weight=itemType["weight"],
                typeId=itemType.get("typeId")
            )
            items.append(item)
            itemIdCounter += 1

    return items

def get_hash(data: Any) -> str:
    """Calculate a SHA256 hash for cache addressing."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@lru_cache(maxsize=1)
def _getProjectRoot() -> str:
    return os.path.dirname(os.path.abspath(__file__))

@lru_cache(maxsize=1)
def _computeCodeFingerprint() -> str:
    """Hash only the solver files that can affect packing results."""
    hasher = hashlib.sha256()
    projectRoot = _getProjectRoot()

    for relativePath in CACHE_FINGERPRINT_FILES:
        filePath = os.path.join(projectRoot, relativePath)
        hasher.update(relativePath.encode("utf-8"))

        if not os.path.exists(filePath):
            hasher.update(b"<missing>")
            continue

        with open(filePath, "rb") as f:
            hasher.update(f.read())

    return hasher.hexdigest()

def buildCacheIdentity(config: Dict[str, Any]) -> Dict[str, Any]:
    """Build cache metadata once per run."""
    outputConfig = config.get("output", {})
    return {
        "cacheVersion": outputConfig.get("cacheVersion", DEFAULT_CACHE_VERSION),
        "codeFingerprint": _computeCodeFingerprint()
    }

def _getCacheInvalidReason(
    cachedResult: Dict[str, Any],
    cacheIdentity: Dict[str, Any]
) -> str:
    cachedVersion = cachedResult.get("cacheVersion")
    currentVersion = cacheIdentity["cacheVersion"]
    if cachedVersion != currentVersion:
        return f"cacheVersion={cachedVersion} -> {currentVersion}"

    cachedFingerprint = cachedResult.get("codeFingerprint")
    currentFingerprint = cacheIdentity["codeFingerprint"]
    if cachedFingerprint != currentFingerprint:
        if cachedFingerprint is None:
            return "missing codeFingerprint"
        return "code fingerprint changed"

    return ""

def _logValidationErrors(prefix: str, errors: List[str]) -> None:
    logger.warning(f"{prefix}: detected {len(errors)} validation error(s)")
    for error in errors[:5]:
        logger.warning(f"      - {error}")
    if len(errors) > 5:
        logger.warning(f"      - ... {len(errors) - 5} more")

def _buildResultPayload(
    testCase: Dict[str, Any],
    container: Container,
    items: List[Item],
    solution: PackingSolution,
    algorithmType: str,
    params: Dict[str, Any],
    seed: int,
    useTimeSeed: bool,
    executionTime: float,
    isCached: bool,
    testIndex: int,
    totalTests: int
) -> Dict[str, Any]:
    validation = validatePackingSolution(container, items, solution)
    if not validation["isValid"]:
        sourceLabel = "cached solution" if isCached else "computed solution"
        _logValidationErrors(f"    ({sourceLabel} invalid)", validation["errors"])

    return {
        "testName": testCase["name"],
        "testIndex": testIndex,
        "totalTests": totalTests,
        "container": container,
        "items": items,
        "itemTypes": testCase["itemTypes"],
        "solution": solution,
        "volumeRate": solution.volumeRate,
        "weightRate": solution.weightRate,
        "placedCount": len(solution.placedItems),
        "algorithmParams": {
            "algorithmType": algorithmType,
            "params": params,
            "seed": seed,
            "useTimeSeed": useTimeSeed
        },
        "executionTime": executionTime,
        "isCached": isCached,
        "isValid": validation["isValid"],
        "validationErrors": validation["errors"]
    }

def runSingleTest(
    testCase: Dict[str, Any],
    config: Dict[str, Any],
    paramCombination: Dict[str, Any],
    testIndex: int,
    totalTests: int,
    cacheIdentity: Dict[str, Any]
) -> Dict[str, Any]:
    """Run one concrete algorithm/parameter combination."""
    algorithmType = paramCombination.get("algorithmType", "greedy_search")
    params = filterAlgorithmParams(
        algorithmType,
        paramCombination.get("params", {})
    )
    useTimeSeed = paramCombination.get("useTimeSeed", True)
    seed = generateTimeSeed() if useTimeSeed else 42

    outputConfig = config.get("output", {})
    enableCache = outputConfig.get("enableCache", False)
    cacheDir = outputConfig.get("cacheDir", "cache")

    inputData = {
        "testCase": testCase,
        "algorithmType": algorithmType,
        "params": params,
        "seed": seed
    }
    inputHash = get_hash(inputData)
    cacheFile = os.path.join(cacheDir, f"{inputHash}.json")

    if enableCache:
        if not os.path.exists(cacheDir):
            os.makedirs(cacheDir, exist_ok=True)

        if os.path.exists(cacheFile):
            try:
                with open(cacheFile, "r", encoding="utf-8") as f:
                    cachedResult = json.load(f)

                invalidReason = _getCacheInvalidReason(cachedResult, cacheIdentity)
                if not invalidReason:
                    containerData = testCase["container"]
                    container = Container(
                        L=containerData["L"],
                        W=containerData["W"],
                        H=containerData["H"],
                        maxWeight=containerData["maxWeight"]
                    )
                    items = generateItemsFromTypes(testCase["itemTypes"])
                    solution = PackingSolution.from_dict(cachedResult["solution"])
                    resultPayload = _buildResultPayload(
                        testCase=testCase,
                        container=container,
                        items=items,
                        solution=solution,
                        algorithmType=algorithmType,
                        params=params,
                        seed=seed,
                        useTimeSeed=useTimeSeed,
                        executionTime=cachedResult.get("executionTime", 0.0),
                        isCached=True,
                        testIndex=testIndex,
                        totalTests=totalTests
                    )

                    if resultPayload["isValid"]:
                        logger.info(f"    (缓存命中: {inputHash[:8]}...)")
                        return resultPayload

                    invalidReason = "cached solution failed validation"

                logger.info(f"    (缓存失效: {invalidReason})")
            except Exception as e:
                logger.warning(f"    (缓存读取失败: {e})")

    startTime = time.time()

    containerData = testCase["container"]
    container = Container(
        L=containerData["L"],
        W=containerData["W"],
        H=containerData["H"],
        maxWeight=containerData["maxWeight"]
    )
    items = generateItemsFromTypes(testCase["itemTypes"])

    solution: PackingSolution = optimizePacking(
        container,
        items,
        algorithmType=algorithmType,
        params=params,
        seed=seed
    )

    executionTime = time.time() - startTime
    resultPayload = _buildResultPayload(
        testCase=testCase,
        container=container,
        items=items,
        solution=solution,
        algorithmType=algorithmType,
        params=params,
        seed=seed,
        useTimeSeed=useTimeSeed,
        executionTime=executionTime,
        isCached=False,
        testIndex=testIndex,
        totalTests=totalTests
    )

    if enableCache and resultPayload["isValid"]:
        try:
            cacheData = {
                "solution": solution.to_dict(),
                "executionTime": executionTime,
                "inputHash": inputHash,
                "cacheVersion": cacheIdentity["cacheVersion"],
                "codeFingerprint": cacheIdentity["codeFingerprint"]
            }
            with open(cacheFile, "w", encoding="utf-8") as f:
                json.dump(cacheData, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"    (缓存写入失败: {e})")
    elif enableCache and not resultPayload["isValid"]:
        logger.warning("    (跳过缓存写入: solution failed validation)")

    return resultPayload

def runTestSuite(
    testCase: Dict[str, Any],
    config: Dict[str, Any],
    testCaseManager: TestCaseManager,
    defaultParams: Dict[str, Any],
    cacheIdentity: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], str]:
    """Run all parameter combinations for a test case."""
    effectiveParams = testCaseManager.getEffectiveParams(
        testCase.get("algorithmParams", {}),
        defaultParams
    )

    paramCombinations = testCaseManager.generateParamCombinations(effectiveParams)
    testCaseName: str = testCase["name"]

    logger.info(f"\n测试用例: {testCaseName}")
    logger.info(f"参数组合数: {len(paramCombinations)}")

    testCaseResults: List[Dict[str, Any]] = []
    for i, paramCombination in enumerate(paramCombinations, 1):
        algorithmType = paramCombination["algorithmType"]
        paramSummary = formatAlgorithmParams(
            algorithmType,
            paramCombination.get("params", {})
        )
        seedMode = "time" if paramCombination.get("useTimeSeed", True) else "fixed(42)"
        logger.info(
            f"  运行组合 {i}/{len(paramCombinations)} [{algorithmType}]: "
            f"{paramSummary}; seed={seedMode}"
        )

        result = runSingleTest(
            testCase,
            config,
            paramCombination,
            i,
            len(paramCombinations),
            cacheIdentity
        )
        testCaseResults.append(result)

    return testCaseResults, testCaseName
