import time
import random
import hashlib
import json
import os
from typing import List, Dict, Any, Tuple
from dataStructures import Item, Container, PackingSolution
from optimization import optimizePacking
from logger import get_logger
from testCaseManager import TestCaseManager

logger = get_logger("testRunner")

def generateTimeSeed() -> int:
    """生成基于时间的随机种子"""
    timestamp = int(time.time() * 1000)
    randomPart = random.randint(0, 9999)
    return timestamp + randomPart

def generateItemsFromTypes(itemTypes: List[Dict[str, Any]]) -> List[Item]:
    """根据货物规格和数量生成货物列表"""
    items: List[Item] = []
    itemIdCounter = 1

    for itemType in itemTypes:
        count = itemType["count"]
        for i in range(count):
            item = Item(
                id=itemIdCounter,
                l=itemType["l"],
                w=itemType["w"],
                h=itemType["h"],
                weight=itemType["weight"]
            )
            items.append(item)
            itemIdCounter += 1

    return items

def get_hash(data: Any) -> str:
    """计算数据的 SHA256 哈希"""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def runSingleTest(testCase: Dict[str, Any], config: Dict[str, Any], 
                  paramCombination: Dict[str, Any], testIndex: int, totalTests: int) -> Dict[str, Any]:
    """运行单个测试用例，并支持结果缓存"""
    
    # 获取算法参数
    algorithmType = paramCombination.get("algorithmType", "hill_climbing")
    iterations = paramCombination["iterations"]
    randomRate = paramCombination["randomRate"]
    useTimeSeed = paramCombination["useTimeSeed"]
    seed = generateTimeSeed() if useTimeSeed else 42

    # 算法特定的参数字典
    params = {
        "iterations": iterations,
        "randomRate": randomRate
    }

    # 准备缓存标识（哈希）
    outputConfig = config.get("output", {})
    enableCache = outputConfig.get("enableCache", False)
    cacheDir = outputConfig.get("cacheDir", "cache")
    
    # 输入要素：测试用例定义 + 关键算法参数
    inputData = {
        "testCase": testCase,
        "algorithmType": algorithmType,
        "params": params,
        "seed": seed
    }
    inputHash = get_hash(inputData)
    cacheFile = os.path.join(cacheDir, f"{inputHash}.json")

    # 尝试读取缓存
    if enableCache:
        if not os.path.exists(cacheDir):
            os.makedirs(cacheDir, exist_ok=True)
        
        if os.path.exists(cacheFile):
            try:
                with open(cacheFile, 'r', encoding='utf-8') as f:
                    cachedResult = json.load(f)
                
                logger.info(f"    (缓存命中: {inputHash[:8]}...)")
                
                # 重建 Container 和 Items（用于返回结果）
                containerData = testCase["container"]
                container = Container(L=containerData["L"], W=containerData["W"], H=containerData["H"], maxWeight=containerData["maxWeight"])
                items = generateItemsFromTypes(testCase["itemTypes"])
                
                # 重建 Solution
                solution = PackingSolution.from_dict(cachedResult["solution"])
                
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
                        "iterations": iterations,
                        "randomRate": randomRate,
                        "seed": seed,
                        "useTimeSeed": useTimeSeed
                    },
                    "executionTime": cachedResult.get("executionTime", 0.0),
                    "isCached": True
                }
            except Exception as e:
                logger.warning(f"    (缓存读取失败: {e})")

    # 如果没有缓存或禁用缓存，执行计算
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
        container, items, algorithmType=algorithmType, params=params, seed=seed
    )

    endTime = time.time()
    executionTime = endTime - startTime

    # 保存结果到缓存
    if enableCache:
        try:
            cacheData = {
                "solution": solution.to_dict(),
                "executionTime": executionTime,
                "inputHash": inputHash
            }
            with open(cacheFile, 'w', encoding='utf-8') as f:
                json.dump(cacheData, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"    (缓存写入失败: {e})")

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
            "iterations": iterations,
            "randomRate": randomRate,
            "seed": seed,
            "useTimeSeed": useTimeSeed
        },
        "executionTime": executionTime,
        "isCached": False
    }

def runTestSuite(testCase: Dict[str, Any], config: Dict[str, Any], 
                 testCaseManager: TestCaseManager, defaultParams: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """运行一个测试用例的所有参数组合"""
    effectiveParams = testCaseManager.getEffectiveParams(
        testCase.get("algorithmParams", {}), defaultParams
    )

    paramCombinations = testCaseManager.generateParamCombinations(effectiveParams)
    testCaseName: str = testCase["name"]

    logger.info(f"\n测试用例: {testCaseName}")
    logger.info(f"参数组合数: {len(paramCombinations)}")

    testCaseResults: List[Dict[str, Any]] = []
    for i, paramComb in enumerate(paramCombinations, 1):
        logger.info(f"  运行组合 {i}/{len(paramCombinations)}: "
                    f"迭代={paramComb['iterations']}, 随机率={paramComb['randomRate']}")

        result = runSingleTest(testCase, config, paramComb, i, len(paramCombinations))
        testCaseResults.append(result)

    return testCaseResults, testCaseName
