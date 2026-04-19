import time
import random
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

def runSingleTest(testCase: Dict[str, Any], config: Dict[str, Any], 
                  paramCombination: Dict[str, Any], testIndex: int, totalTests: int) -> Dict[str, Any]:
    """运行单个测试用例"""
    startTime = time.time()

    containerData = testCase["container"]
    container = Container(
        L=containerData["L"],
        W=containerData["W"],
        H=containerData["H"],
        maxWeight=containerData["maxWeight"]
    )

    items = generateItemsFromTypes(testCase["itemTypes"])
    iterations = paramCombination["iterations"]
    randomRate = paramCombination["randomRate"]
    useTimeSeed = paramCombination["useTimeSeed"]

    seed = generateTimeSeed() if useTimeSeed else 42

    solution: PackingSolution = optimizePacking(
        container, items, iterations=iterations, randomRate=randomRate, seed=seed
    )

    endTime = time.time()
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
        "executionTime": endTime - startTime
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
