import hashlib
import json
import os
import random
import time
from functools import lru_cache
from typing import Any, Dict, List, Tuple
from dataStructures import ProblemInstance, ShipmentPlan
from logger import get_logger
from optimization import optimizePacking, filterAlgorithmParams, formatAlgorithmParams
from solutionValidator import validateShipmentPlan
from testCaseManager import TestCaseManager

logger = get_logger("testRunner")

CACHE_FINGERPRINT_FILES: Tuple[str, ...] = (
    "optimization.py",
    "packingLogic.py",
    "dataStructures.py",
    "solutionValidator.py",
    "testRunner.py"
)
DEFAULT_CACHE_VERSION = 3
DEFAULT_BASE_SEED = 42

def generateTimeSeed() -> int:
    timestamp = int(time.time() * 1000)
    randomPart = random.randint(0, 9999)
    return timestamp + randomPart

def generateDeterministicSeed(baseSeed: int, repeatIndex: int) -> int:
    return baseSeed + max(0, repeatIndex - 1)

def get_hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

@lru_cache(maxsize=1)
def _getProjectRoot() -> str:
    return os.path.dirname(os.path.abspath(__file__))

@lru_cache(maxsize=1)
def _computeCodeFingerprint() -> str:
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
    outputConfig = config.get("output", {})
    return {
        "cacheVersion": outputConfig.get("cacheVersion", DEFAULT_CACHE_VERSION),
        "codeFingerprint": _computeCodeFingerprint()
    }

def _getCacheInvalidReason(
    cachedResult: Dict[str, Any],
    cacheIdentity: Dict[str, Any]
) -> str:
    if cachedResult.get("cacheVersion") != cacheIdentity["cacheVersion"]:
        return (
            f"cacheVersion={cachedResult.get('cacheVersion')} -> "
            f"{cacheIdentity['cacheVersion']}"
        )
    if cachedResult.get("codeFingerprint") != cacheIdentity["codeFingerprint"]:
        return "code fingerprint changed"
    return ""

def _logValidationErrors(prefix: str, errors: List[str]) -> None:
    logger.warning(f"{prefix}: detected {len(errors)} validation error(s)")
    for error in errors[:5]:
        logger.warning(f"      - {error}")
    if len(errors) > 5:
        logger.warning(f"      - ... {len(errors) - 5} more")

def _buildResultPayload(
    problem: ProblemInstance,
    plan: ShipmentPlan,
    algorithmType: str,
    params: Dict[str, Any],
    baseSeed: int,
    seed: int,
    useTimeSeed: bool,
    executionTime: float,
    isCached: bool,
    runIndex: int,
    totalRuns: int,
    combinationIndex: int,
    totalCombinations: int,
    repeatIndex: int,
    repeatCount: int
) -> Dict[str, Any]:
    validation = validateShipmentPlan(problem, plan)
    if not validation["isValid"]:
        sourceLabel = "cached plan" if isCached else "computed plan"
        _logValidationErrors(f"    ({sourceLabel} invalid)", validation["errors"])

    metrics = validation["metrics"]
    return {
        "testName": problem.name,
        "testIndex": runIndex,
        "totalTests": totalRuns,
        "runIndex": runIndex,
        "totalRuns": totalRuns,
        "combinationIndex": combinationIndex,
        "totalCombinations": totalCombinations,
        "repeatIndex": repeatIndex,
        "repeatCount": repeatCount,
        "problem": problem,
        "plan": plan,
        "containerLoads": plan.containerLoads,
        "items": problem.items,
        "itemTypes": problem.itemTypes,
        "containerTypes": problem.containerTypes,
        "analysis": problem.analysis,
        "scenarioMetadata": problem.scenarioMetadata,
        "volumeRate": metrics.totalFillRate,
        "weightRate": metrics.avgContainerWeightRate,
        "placedCount": metrics.packedItemCount,
        "unpackedCount": metrics.unpackedItemCount,
        "totalCost": metrics.totalCost,
        "usedContainerCount": metrics.usedContainerCount,
        "objectiveName": metrics.objectiveName,
        "objectiveValue": metrics.objectiveValue,
        "metrics": metrics,
        "containerRows": validation["containerRows"],
        "placementRecords": validation["placementRecords"],
        "algorithmParams": {
            "algorithmType": algorithmType,
            "params": params,
            "baseSeed": baseSeed,
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
    combinationIndex: int,
    totalCombinations: int,
    repeatIndex: int,
    repeatCount: int,
    runIndex: int,
    totalRuns: int,
    cacheIdentity: Dict[str, Any],
    testCaseManager: TestCaseManager
) -> Dict[str, Any]:
    algorithmType = paramCombination.get("algorithmType", "greedy_search")
    params = filterAlgorithmParams(algorithmType, paramCombination.get("params", {}))
    useTimeSeed = bool(paramCombination.get("useTimeSeed", False))
    baseSeed = paramCombination.get("baseSeed", DEFAULT_BASE_SEED)
    seed = (
        generateTimeSeed()
        if useTimeSeed
        else generateDeterministicSeed(baseSeed, repeatIndex)
    )

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
        os.makedirs(cacheDir, exist_ok=True)
        if os.path.exists(cacheFile):
            try:
                with open(cacheFile, "r", encoding="utf-8") as f:
                    cachedResult = json.load(f)
                invalidReason = _getCacheInvalidReason(cachedResult, cacheIdentity)
                if not invalidReason:
                    problem = testCaseManager.buildProblemInstance(testCase)
                    plan = ShipmentPlan.from_dict(cachedResult["plan"])
                    resultPayload = _buildResultPayload(
                        problem=problem,
                        plan=plan,
                        algorithmType=algorithmType,
                        params=params,
                        baseSeed=baseSeed,
                        seed=seed,
                        useTimeSeed=useTimeSeed,
                        executionTime=float(cachedResult.get("executionTime", 0.0)),
                        isCached=True,
                        runIndex=runIndex,
                        totalRuns=totalRuns,
                        combinationIndex=combinationIndex,
                        totalCombinations=totalCombinations,
                        repeatIndex=repeatIndex,
                        repeatCount=repeatCount
                    )
                    if resultPayload["isValid"]:
                        logger.info(f"    (缓存命中: {inputHash[:8]}...)")
                        return resultPayload
                    invalidReason = "cached plan failed validation"
                logger.info(f"    (缓存失效: {invalidReason})")
            except Exception as e:
                logger.warning(f"    (缓存读取失败: {e})")

    problem = testCaseManager.buildProblemInstance(testCase)
    startTime = time.time()
    plan = optimizePacking(
        problem=problem,
        algorithmType=algorithmType,
        params=params,
        seed=seed
    )
    executionTime = time.time() - startTime

    resultPayload = _buildResultPayload(
        problem=problem,
        plan=plan,
        algorithmType=algorithmType,
        params=params,
        baseSeed=baseSeed,
        seed=seed,
        useTimeSeed=useTimeSeed,
        executionTime=executionTime,
        isCached=False,
        runIndex=runIndex,
        totalRuns=totalRuns,
        combinationIndex=combinationIndex,
        totalCombinations=totalCombinations,
        repeatIndex=repeatIndex,
        repeatCount=repeatCount
    )

    if enableCache and resultPayload["isValid"]:
        try:
            cacheData = {
                "plan": plan.to_dict(),
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
        logger.warning("    (跳过缓存写入: plan failed validation)")

    return resultPayload

def runTestSuite(
    testCase: Dict[str, Any],
    config: Dict[str, Any],
    testCaseManager: TestCaseManager,
    defaultParams: Dict[str, Any],
    cacheIdentity: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], str]:
    effectiveParams = testCaseManager.getEffectiveParams(
        testCase.get("algorithmParams", {}),
        defaultParams
    )
    paramCombinations = testCaseManager.generateParamCombinations(effectiveParams)
    totalRuns = sum(
        max(1, int(paramCombination.get("repeatCount", 1)))
        for paramCombination in paramCombinations
    )
    testCaseName = testCase["name"]

    logger.info(f"\n测试用例: {testCaseName}")
    logger.info(f"参数组数: {len(paramCombinations)}")
    logger.info(f"总运行次数: {totalRuns}")

    results: List[Dict[str, Any]] = []
    currentRunIndex = 0
    for combinationIndex, paramCombination in enumerate(paramCombinations, start=1):
        algorithmType = paramCombination["algorithmType"]
        paramSummary = formatAlgorithmParams(
            algorithmType,
            paramCombination.get("params", {})
        )
        repeatCount = max(1, int(paramCombination.get("repeatCount", 1)))
        useTimeSeed = bool(paramCombination.get("useTimeSeed", False))
        baseSeed = paramCombination.get("baseSeed", DEFAULT_BASE_SEED)
        if useTimeSeed:
            seedMode = "time"
        elif repeatCount == 1:
            seedMode = f"fixed({baseSeed})"
        else:
            seedMode = f"fixed({baseSeed}..{generateDeterministicSeed(baseSeed, repeatCount)})"

        logger.info(
            f"  参数组 {combinationIndex}/{len(paramCombinations)} [{algorithmType}]: "
            f"{paramSummary}; repeats={repeatCount}; seed={seedMode}"
        )

        for repeatIndex in range(1, repeatCount + 1):
            currentRunIndex += 1
            seedPreview = (
                "time-based" if useTimeSeed
                else str(generateDeterministicSeed(baseSeed, repeatIndex))
            )
            logger.info(
                f"    重复 {repeatIndex}/{repeatCount} -> "
                f"run {currentRunIndex}/{totalRuns}; seed={seedPreview}"
            )
            result = runSingleTest(
                testCase=testCase,
                config=config,
                paramCombination=paramCombination,
                combinationIndex=combinationIndex,
                totalCombinations=len(paramCombinations),
                repeatIndex=repeatIndex,
                repeatCount=repeatCount,
                runIndex=currentRunIndex,
                totalRuns=totalRuns,
                cacheIdentity=cacheIdentity,
                testCaseManager=testCaseManager
            )
            results.append(result)

    return results, testCaseName
