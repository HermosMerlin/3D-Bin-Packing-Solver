import argparse
import csv
import copy
import fnmatch
import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List
from configManager import ConfigManager
from logger import get_logger, setup_logging
from resultSaver import ResultSaver
from testCaseManager import TestCaseManager
from optimization import ALGORITHMS, getAlgorithmParamKeys
from testRunner import buildCacheIdentity, runTestSuite
from validation.runner import runValidationSuite
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

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="装箱实验批量测试程序")
    parser.add_argument("--case", action="append", dest="cases", help="只运行指定测试集，可重复传入")
    parser.add_argument("--case-pattern", action="append", dest="case_patterns", help="按通配符匹配测试集")
    parser.add_argument("--algorithm", help="只运行指定算法")
    parser.add_argument("--iterations", type=int, help="覆盖算法迭代次数")
    parser.add_argument("--repeat", type=int, help="覆盖重复次数")
    parser.add_argument("--parallel", action="store_true", help="强制开启参数组/重复组并行")
    parser.add_argument("--serial", action="store_true", help="强制关闭并行，使用串行调度")
    parser.add_argument("--workers", type=int, help="覆盖并行 worker 数，0 表示自动")
    parser.add_argument("--no-viz", action="store_true", help="关闭可视化")
    parser.add_argument("--no-cache", action="store_true", help="关闭缓存")
    parser.add_argument("--output-tag", help="结果目录追加标签")
    parser.add_argument("--run-validation", action="store_true", help="先运行功能验证套件")
    parser.add_argument("--validation-only", action="store_true", help="只运行功能验证套件")
    return parser.parse_args()

def _filter_test_cases(
    testCases: List[Dict[str, Any]],
    args: argparse.Namespace
) -> List[Dict[str, Any]]:
    selected = testCases
    if args.cases:
        allowed = set(args.cases)
        selected = [testCase for testCase in selected if testCase["name"] in allowed]
    if args.case_patterns:
        selected = [
            testCase for testCase in selected
            if any(fnmatch.fnmatch(testCase["name"], pattern) for pattern in args.case_patterns)
        ]
    return selected

def _override_algorithm_config(
    algorithmConfig: Dict[str, Any],
    args: argparse.Namespace
) -> Dict[str, Any]:
    updated = dict(algorithmConfig)
    if args.iterations is not None:
        updated["iterations"] = args.iterations
    if args.repeat is not None:
        updated["repeatCount"] = args.repeat
    return updated

def _make_default_algorithm_config(algorithmType: str) -> Dict[str, Any]:
    config: Dict[str, Any] = {
        "useTimeSeed": False,
        "baseSeed": 42,
        "repeatCount": 1
    }
    for key in getAlgorithmParamKeys(algorithmType):
        if key == "iterations":
            config[key] = 10
        elif key == "initialTemp":
            config[key] = 50.0
        elif key == "coolingRate":
            config[key] = 0.95
        elif key == "minTemp":
            config[key] = 0.1
        elif key == "populationSize":
            config[key] = 8
        elif key == "eliteCount":
            config[key] = 2
        elif key == "tournamentSize":
            config[key] = 3
        elif key == "mutationRate":
            config[key] = 0.25
        elif key == "crossoverRate":
            config[key] = 0.85
        elif key == "localSearchSteps":
            config[key] = 2
    return config

def _apply_runtime_overrides(
    config: Dict[str, Any],
    testCases: List[Dict[str, Any]],
    args: argparse.Namespace
) -> Dict[str, Any]:
    overridden = copy.deepcopy(config)
    overridden.setdefault("execution", {})
    overridden["execution"].setdefault("parallel", {})
    if args.no_viz:
        overridden["output"]["enableVisualization"] = False
    if args.no_cache:
        overridden["output"]["enableCache"] = False
    if args.parallel:
        overridden["execution"]["parallel"]["enabled"] = True
    if args.serial:
        overridden["execution"]["parallel"]["enabled"] = False
    if args.workers is not None:
        overridden["execution"]["parallel"]["maxWorkers"] = args.workers

    if args.algorithm:
        selectedAlgorithm = args.algorithm
        defaultAlgorithms = overridden.get("algorithmDefaults", {})
        if selectedAlgorithm not in ALGORITHMS:
            raise ValueError(f"未知算法: {selectedAlgorithm}")
        baseAlgorithmConfig = defaultAlgorithms.get(
            selectedAlgorithm,
            _make_default_algorithm_config(selectedAlgorithm)
        )
        overridden["algorithmDefaults"] = {
            selectedAlgorithm: _override_algorithm_config(
                baseAlgorithmConfig,
                args
            )
        }
        for testCase in testCases:
            caseAlgorithms = testCase.get("algorithmParams", {})
            if caseAlgorithms:
                filtered = {
                    selectedAlgorithm: _override_algorithm_config(
                        caseAlgorithms.get(selectedAlgorithm, baseAlgorithmConfig),
                        args
                    )
                }
                testCase["algorithmParams"] = filtered
    elif args.iterations is not None or args.repeat is not None:
        overridden["algorithmDefaults"] = {
            algorithmType: _override_algorithm_config(algorithmConfig, args)
            for algorithmType, algorithmConfig in overridden.get("algorithmDefaults", {}).items()
        }
        for testCase in testCases:
            if testCase.get("algorithmParams"):
                testCase["algorithmParams"] = {
                    algorithmType: _override_algorithm_config(algorithmConfig, args)
                    for algorithmType, algorithmConfig in testCase["algorithmParams"].items()
                }

    return overridden

def _build_output_root(scriptDir: str, config: Dict[str, Any], args: argparse.Namespace) -> str:
    baseResultsDir = config.get("output", {}).get("resultsDir", "results")
    runTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output_tag:
        runTimestamp = f"{runTimestamp}_{args.output_tag}"
    return os.path.join(scriptDir, baseResultsDir, runTimestamp)

def _write_manifest(path: str, manifest: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

def _write_summary(path: str, manifest: Dict[str, Any]) -> None:
    lines = [
        f"# Run Summary",
        f"- CreatedAt: {manifest['createdAt']}",
        f"- GitBranch: {manifest.get('gitBranch', 'unknown')}",
        f"- GitCommit: {manifest.get('gitCommit', 'unknown')}",
        f"- CaseCount: {manifest['caseCount']}",
        f"- TotalCombinationCount: {manifest['totalCombinationCount']}",
        f"- TotalRunCount: {manifest['totalRunCount']}",
        f"- PackingVisualizationCount: {manifest['packingVisualizationCount']}",
        f"- AnalysisVisualizationCount: {manifest['analysisVisualizationCount']}",
        f"- ValidationPassed: {manifest['validation'].get('passed') if manifest.get('validation') else 'not-run'}",
        "",
        "## Cases"
    ]
    for caseName in manifest["cases"]:
        lines.append(f"- {caseName}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def _get_git_metadata(scriptDir: str) -> Dict[str, str]:
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=scriptDir,
            text=True,
            encoding="utf-8"
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=scriptDir,
            text=True,
            encoding="utf-8"
        ).strip()
        return {"gitBranch": branch, "gitCommit": commit}
    except Exception:
        return {"gitBranch": "unknown", "gitCommit": "unknown"}

def main() -> None:
    args = _parse_args()
    setup_logging(log_level="INFO")
    logger.info("=" * 80)
    logger.info("装箱实验批量测试程序")
    logger.info("=" * 80)

    scriptDir = os.path.dirname(os.path.abspath(__file__))
    configManager = ConfigManager(configPath=scriptDir)
    testCaseManager = TestCaseManager(testPath=scriptDir)

    baseConfig = configManager.getConfig()
    testCases = testCaseManager.loadTestCases()
    testCases = _filter_test_cases(testCases, args)

    config = _apply_runtime_overrides(baseConfig, testCases, args)

    defaultParams = configManager.getDefaultParams()
    outputConfig = configManager.getOutputConfig()
    defaultParams = config.get("algorithmDefaults", defaultParams)
    outputConfig = config.get("output", outputConfig)
    cacheIdentity = buildCacheIdentity(config)
    loggingConfig = outputConfig.get("logging", {})
    parallelConfig = config.get("execution", {}).get("parallel", {})

    topLevelDir = _build_output_root(scriptDir, config, args)
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
    logger.info(
        "并行调度: "
        f"enabled={parallelConfig.get('enabled', False)}, "
        f"maxWorkers={parallelConfig.get('maxWorkers', 0)}, "
        f"minTasksForParallel={parallelConfig.get('minTasksForParallel', 2)}"
    )

    validationSummary = None
    validationConfig = config.get("validation", {})
    shouldRunValidation = (
        args.run_validation or
        args.validation_only or
        (
            validationConfig.get("enableValidationSuite", False)
            and validationConfig.get("runBeforeBatch", False)
        )
    )
    if shouldRunValidation:
        validationSummary = runValidationSuite(
            scriptDir=scriptDir,
            config=config,
            outputDir=topLevelDir
        )
        if args.validation_only:
            return
        if (
            validationSummary["enabled"]
            and not validationSummary["passed"]
            and config.get("validation", {}).get("stopOnValidationFailure", True)
        ):
            logger.error("功能验证套件失败，按配置终止正式批量运行")
            return

    if not testCases:
        logger.error("未找到测试用例，请在 test 目录下添加 JSON 文件")
        return

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

    manifest = {
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resultsDir": os.path.abspath(topLevelDir),
        "caseCount": len(testCases),
        "cases": [testCase["name"] for testCase in testCases],
        "runtimeArgs": vars(args),
        "parallelExecution": parallelConfig,
        "validation": validationSummary,
        "totalCombinationCount": totalCombinationCount,
        "totalRunCount": totalRunCount,
        "packingVisualizationCount": packingVisualizationCount,
        "analysisVisualizationCount": analysisVisualizationCount
    }
    manifest.update(_get_git_metadata(scriptDir))
    _write_manifest(os.path.join(topLevelDir, "manifest.json"), manifest)
    _write_summary(os.path.join(topLevelDir, "summary.md"), manifest)

if __name__ == "__main__":
    main()
