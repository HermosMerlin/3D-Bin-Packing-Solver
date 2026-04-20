import os
from datetime import datetime
from typing import List, Dict, Any
from configManager import ConfigManager
from testCaseManager import TestCaseManager
from resultSaver import ResultSaver
from visualizer import Visualizer
from testRunner import runTestSuite, buildCacheIdentity
from logger import setup_logging, get_logger

logger = get_logger("batchTest")

def _resultRankKey(result: Dict[str, Any]) -> tuple:
    """Select the best result using report-consistent metrics."""
    return (
        result.get("volumeRate", 0.0),
        result.get("weightRate", 0.0),
        result.get("placedCount", 0),
        -result.get("executionTime", float("inf"))
    )

def _selectVisualizationResults(
    testCaseResults: List[Dict[str, Any]],
    outputConfig: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Optionally visualize only the best result of each algorithm."""
    validResults = [result for result in testCaseResults if result.get("isValid", False)]
    skippedInvalidCount = len(testCaseResults) - len(validResults)
    if skippedInvalidCount > 0:
        logger.info(f"    跳过非法结果的可视化: {skippedInvalidCount}")

    if not validResults:
        return []

    if not outputConfig.get("visualizeBestPerAlgorithmOnly", False):
        return validResults

    bestByAlgorithm: Dict[str, Dict[str, Any]] = {}
    for result in validResults:
        algorithmType = result.get("algorithmParams", {}).get("algorithmType", "unknown")
        currentBest = bestByAlgorithm.get(algorithmType)
        if currentBest is None or _resultRankKey(result) > _resultRankKey(currentBest):
            bestByAlgorithm[algorithmType] = result

    selectedResults = sorted(
        bestByAlgorithm.values(),
        key=lambda result: result.get("testIndex", 0)
    )
    logger.info(
        f"    仅渲染每个算法的最佳方案: "
        f"{len(selectedResults)}/{len(validResults)}"
    )
    return selectedResults

def main() -> None:
    """批量执行所有测试用例。"""
    setup_logging(log_level="INFO")

    logger.info("=" * 80)
    logger.info("三维装箱算法批量测试程序")
    logger.info("=" * 80)

    scriptDir: str = os.path.dirname(os.path.abspath(__file__))
    configManager: ConfigManager = ConfigManager(configPath=scriptDir)
    testCaseManager: TestCaseManager = TestCaseManager(testPath=scriptDir)

    config: Dict[str, Any] = configManager.getConfig()
    testCases: List[Dict[str, Any]] = testCaseManager.loadTestCases()

    if len(testCases) == 0:
        logger.error("未找到测试用例，请在 test 目录下添加 JSON 文件")
        return

    logger.info(f"加载了 {len(testCases)} 个测试用例")

    defaultParams: Dict[str, Any] = configManager.getDefaultParams()
    outputConfig: Dict[str, Any] = configManager.getOutputConfig()
    cacheIdentity: Dict[str, Any] = buildCacheIdentity(config)
    loggingConfig: Dict[str, Any] = outputConfig.get("logging", {})
    baseResultsDir: str = outputConfig.get("resultsDir", "results")

    runTimestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    topLevelDir: str = os.path.join(scriptDir, baseResultsDir, runTimestamp)
    os.makedirs(topLevelDir, exist_ok=True)

    logFile: str = None
    if loggingConfig.get("saveToFile", True):
        logFile = os.path.join(topLevelDir, "run.log")

    setup_logging(
        log_level=loggingConfig.get("consoleLevel", "INFO"),
        log_file=logFile
    )

    absTopLevelDir: str = os.path.abspath(topLevelDir)
    logger.info(f"本次运行结果将保存到: {absTopLevelDir}")
    if outputConfig.get("enableCache", False):
        logger.info(
            f"缓存版本: {cacheIdentity['cacheVersion']}, "
            f"代码指纹: {cacheIdentity['codeFingerprint'][:12]}"
        )

    resultSaver: ResultSaver = ResultSaver(resultsDir=topLevelDir, outputConfig=outputConfig)
    visualizer: Visualizer = Visualizer(resultsDir=topLevelDir, outputConfig=outputConfig)

    totalTestCount: int = 0
    successfulVisualizations: int = 0
    failedVisualizations: int = 0

    for testCase in testCases:
        testCaseResults, testCaseName = runTestSuite(
            testCase,
            config,
            testCaseManager,
            defaultParams,
            cacheIdentity
        )

        totalTestCount += len(testCaseResults)

        if outputConfig.get("enableVisualization", True):
            visualizationResults = _selectVisualizationResults(
                testCaseResults,
                outputConfig
            )
            for result in visualizationResults:
                logger.info("    生成可视化...")
                vizFile = visualizer.generateVisualization(result, testName=testCaseName)
                if vizFile:
                    successfulVisualizations += 1
                    logger.info(f"    [OK] 可视化成功: {os.path.basename(vizFile)}")
                else:
                    failedVisualizations += 1
                    logger.warning("    [FAIL] 可视化失败")
        else:
            logger.info("    可视化已禁用")

        resultSaver.saveResults(testCaseResults, testCaseName)

    logger.info(f"\n{'=' * 80}")
    logger.info("测试完成统计:")
    logger.info(f"  总测试组合数: {totalTestCount}")
    logger.info(f"  成功可视化: {successfulVisualizations}")
    logger.info(f"  失败可视化: {failedVisualizations}")
    logger.info(f"  结果保存目录: {absTopLevelDir}")

    logger.info("\n目录结构:")
    for root, dirs, files in os.walk(absTopLevelDir):
        level = root.replace(absTopLevelDir, "").count(os.sep)
        indent = " " * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")

    logger.info("=" * 80)

if __name__ == "__main__":
    main()
