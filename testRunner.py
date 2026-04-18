import time
import random
from dataStructures import Item, Container
from optimization import optimizePacking

def generateTimeSeed():
    """生成基于时间的随机种子"""
    timestamp = int(time.time() * 1000)
    randomPart = random.randint(0, 9999)
    return timestamp + randomPart

def generateItemsFromTypes(itemTypes):
    """根据货物规格和数量生成货物列表"""
    items = []
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

def runSingleTest(testCase, config, paramCombination, testIndex, totalTests):
    """
    运行单个测试用例的单个参数组合
    :param testCase: 测试用例数据
    :param config: 配置信息
    :param paramCombination: 参数组合
    :param testIndex: 测试索引
    :param totalTests: 总测试数
    :return: 测试结果
    """
    startTime = time.time()

    # 创建集装箱
    containerData = testCase["container"]
    container = Container(
        L=containerData["L"],
        W=containerData["W"],
        H=containerData["H"],
        maxWeight=containerData["maxWeight"]
    )

    # 根据货物规格生成货物列表
    items = generateItemsFromTypes(testCase["itemTypes"])

    # 获取参数组合
    iterations = paramCombination["iterations"]
    randomRate = paramCombination["randomRate"]
    useTimeSeed = paramCombination["useTimeSeed"]

    # 生成随机种子
    if useTimeSeed:
        seed = generateTimeSeed()
    else:
        seed = 42

    # 运行优化算法
    solution = optimizePacking(
        container,
        items,
        iterations=iterations,
        randomRate=randomRate,
        seed=seed
    )

    # 计算运行时间
    endTime = time.time()
    executionTime = endTime - startTime

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
        "executionTime": executionTime
    }

def runTestSuite(testCase, config, testCaseManager, defaultParams):
    """
    运行一个测试用例的所有参数组合
    :param testCase: 测试用例数据
    :param config: 配置信息
    :param testCaseManager: 测试用例管理器
    :param defaultParams: 默认参数
    :return: 该测试用例的所有结果
    """
    # 获取有效参数（测试集参数优先，否则使用默认值）
    effectiveParams = testCaseManager.getEffectiveParams(
        testCase.get("algorithmParams", {}),
        defaultParams
    )

    # 生成参数组合
    paramCombinations = testCaseManager.generateParamCombinations(effectiveParams)
    testCaseName = testCase["name"]

    print(f"\n测试用例: {testCaseName}")
    print(f"参数组合数: {len(paramCombinations)}")

    # 存储当前测试用例的所有结果
    testCaseResults = []

    # 运行每个参数组合
    for i, paramComb in enumerate(paramCombinations, 1):
        print(f"  运行组合 {i}/{len(paramCombinations)}: "
              f"迭代={paramComb['iterations']}, 随机率={paramComb['randomRate']}")

        result = runSingleTest(
            testCase,
            config,
            paramComb,
            i,
            len(paramCombinations)
        )
        testCaseResults.append(result)

    return testCaseResults, testCaseName
