import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List
from configManager import ConfigManager
from logger import get_logger, setup_logging
from resultSaver import ResultSaver
from testCaseManager import TestCaseManager
from testRunner import buildCacheIdentity, runTestSuite
from visualizer import Visualizer

logger = get_logger("batchTest")

def _writeCsv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def _writeJson(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def _aggregateTables(
    aggregate: Dict[str, List[Dict[str, Any]]],
    tables: Dict[str, List[Dict[str, Any]]]
) -> None:
    for level, rows in tables.items():
        aggregate.setdefault(level, []).extend(rows)

def _selectVisualizationResults(testCaseResults: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    validResults = [result for result in testCaseResults if result.get("isValid", False)]
    if not validResults:
        return []

    bestByAlgorithm: Dict[str, Dict[str, Any]] = {}
    for result in validResults:
        algorithmType = result["algorithmParams"].get("algorithmType", "unknown")
        currentBest = bestByAlgorithm.get(algorithmType)
        if currentBest is None:
            bestByAlgorithm[algorithmType] = result
            continue

        order = result["problem"].objective.primaryOrder
        if order == "max":
            if result["objectiveValue"] > currentBest["objectiveValue"]:
                bestByAlgorithm[algorithmType] = result
        else:
            if result["objectiveValue"] < currentBest["objectiveValue"]:
                bestByAlgorithm[algorithmType] = result

    return sorted(bestByAlgorithm.values(), key=lambda result: result["combinationIndex"])

def main() -> None:
    setup_logging(log_level="INFO")
    logger.info("=" * 80)
    logger.info("装箱实验批量测试程序")
    logger.info("=" * 80)

    scriptDir = os.path.dirname(os.path.abspath(__file__))
    configManager = ConfigManager(configPath=scriptDir)
    testCaseManager = TestCaseManager(testPath=scriptDir)

    config = configManager.getConfig()
    testCases = testCaseManager.loadTestCases()
    if not testCases:
        logger.error("未找到测试用例，请在 test 目录下添加 JSON 文件")
        return

    defaultParams = configManager.getDefaultParams()
    outputConfig = configManager.getOutputConfig()
    cacheIdentity = buildCacheIdentity(config)
    loggingConfig = outputConfig.get("logging", {})
    baseResultsDir = outputConfig.get("resultsDir", "results")

    runTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topLevelDir = os.path.join(scriptDir, baseResultsDir, runTimestamp)
    os.makedirs(topLevelDir, exist_ok=True)
    logsDir = os.path.join(topLevelDir, "logs")
    aggregateCsvDir = os.path.join(topLevelDir, "aggregate", "tables", "csv")
    aggregateJsonDir = os.path.join(topLevelDir, "aggregate", "tables", "json")
    os.makedirs(logsDir, exist_ok=True)
    os.makedirs(aggregateCsvDir, exist_ok=True)
    os.makedirs(aggregateJsonDir, exist_ok=True)

    logFile = None
    if loggingConfig.get("saveToFile", True):
        logFile = os.path.join(logsDir, "run.log")
    setup_logging(
        log_level=loggingConfig.get("consoleLevel", "INFO"),
        log_file=logFile
    )

    logger.info(f"本次运行结果将保存到: {os.path.abspath(topLevelDir)}")
    if outputConfig.get("enableCache", False):
        logger.info(
            f"缓存版本: {cacheIdentity['cacheVersion']}, "
            f"代码指纹: {cacheIdentity['codeFingerprint'][:12]}"
        )

    resultSaver = ResultSaver(resultsDir=topLevelDir, outputConfig=outputConfig)
    visualizer = Visualizer(resultsDir=topLevelDir, outputConfig=outputConfig)

    totalRunCount = 0
    totalCombinationCount = 0
    packingVisualizationCount = 0
    analysisVisualizationCount = 0
    aggregateTables: Dict[str, List[Dict[str, Any]]] = {
        "run": [],
        "group": [],
        "container": [],
        "placement": []
    }

    for testCase in testCases:
        testCaseResults, testCaseName = runTestSuite(
            testCase=testCase,
            config=config,
            testCaseManager=testCaseManager,
            defaultParams=defaultParams,
            cacheIdentity=cacheIdentity
        )
        totalRunCount += len(testCaseResults)
        totalCombinationCount += len({
            result["combinationIndex"] for result in testCaseResults
        })

        saveInfo = resultSaver.saveResults(testCaseResults, testCaseName)
        _aggregateTables(aggregateTables, saveInfo["tables"])

        if outputConfig.get("enableVisualization", True):
            for result in _selectVisualizationResults(testCaseResults):
                files = visualizer.generatePackingVisualization(result, testCaseName)
                packingVisualizationCount += len(files)

            analysisFiles = visualizer.generateAnalysisVisualizations(
                saveInfo["tables"],
                testCase.get("analysis", {}),
                testCaseName
            )
            analysisVisualizationCount += len(analysisFiles)

    if outputConfig.get("exportSummaryData", True):
        for level, rows in aggregateTables.items():
            if not rows:
                continue
            csvPath = os.path.abspath(os.path.join(aggregateCsvDir, f"all_{level}.csv"))
            jsonPath = os.path.abspath(os.path.join(aggregateJsonDir, f"all_{level}.json"))
            _writeCsv(csvPath, rows)
            _writeJson(jsonPath, rows)
            logger.info(f"聚合 {level} CSV 已生成: {csvPath}")
            logger.info(f"聚合 {level} JSON 已生成: {jsonPath}")

    combinedAnalysisCharts = outputConfig.get("analysisCharts", [])
    if combinedAnalysisCharts:
        combinedFiles = visualizer.generateAnalysisVisualizations(
            aggregateTables,
            {"scatterPlots": combinedAnalysisCharts},
            "_combined"
        )
        analysisVisualizationCount += len(combinedFiles)

    logger.info(f"\n{'=' * 80}")
    logger.info("测试完成统计:")
    logger.info(f"  参数组总数: {totalCombinationCount}")
    logger.info(f"  总运行次数: {totalRunCount}")
    logger.info(f"  装箱可视化文件数: {packingVisualizationCount}")
    logger.info(f"  分析图文件数: {analysisVisualizationCount}")
    logger.info(f"  结果保存目录: {os.path.abspath(topLevelDir)}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
