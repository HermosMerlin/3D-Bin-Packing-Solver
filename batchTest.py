import os
from datetime import datetime
from typing import List, Dict, Any
from configManager import ConfigManager
from testCaseManager import TestCaseManager
from resultSaver import ResultSaver
from visualizer import Visualizer
from testRunner import runTestSuite
from logger import setup_logging, get_logger

# 初始化日志记录器
logger = get_logger("batchTest")

def main() -> None:
    """批量测试主函数"""
    # 临时配置基础日志以便输出初始化信息
    setup_logging(log_level="INFO")
    
    logger.info("=" * 80)
    logger.info("三维装箱算法批量测试程序")
    logger.info("=" * 80)

    # 初始化各个管理器
    scriptDir: str = os.path.dirname(os.path.abspath(__file__))
    configManager: ConfigManager = ConfigManager(configPath=scriptDir)
    testCaseManager: TestCaseManager = TestCaseManager(testPath=scriptDir)

    # 获取配置和测试用例
    config: Dict[str, Any] = configManager.getConfig()
    testCases: List[Dict[str, Any]] = testCaseManager.loadTestCases()

    if len(testCases) == 0:
        logger.error("未找到测试用例，请在test目录下添加JSON文件")
        return

    logger.info(f"加载了 {len(testCases)} 个测试用例")

    # 获取默认参数
    defaultParams: Dict[str, Any] = configManager.getDefaultParams()

    # 获取基础结果目录
    outputConfig: Dict[str, Any] = configManager.getOutputConfig()
    loggingConfig: Dict[str, Any] = outputConfig.get("logging", {})
    baseResultsDir: str = outputConfig.get("resultsDir", "results")

    # 创建本次运行的顶级文件夹（以时间戳命名）
    runTimestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    topLevelDir: str = os.path.join(scriptDir, baseResultsDir, runTimestamp)
    os.makedirs(topLevelDir, exist_ok=True)

    # 重新配置正式日志系统（包含文件输出）
    logFile: str = None
    if loggingConfig.get("saveToFile", True):
        logFile = os.path.join(topLevelDir, "run.log")
    
    setup_logging(
        log_level=loggingConfig.get("consoleLevel", "INFO"),
        log_file=logFile
    )

    # 打印本次运行的目录路径
    absTopLevelDir: str = os.path.abspath(topLevelDir)
    logger.info(f"本次运行结果将保存到: {absTopLevelDir}")

    # 初始化结果保存器和可视化器，使用本次运行的顶级目录
    resultSaver: ResultSaver = ResultSaver(resultsDir=topLevelDir, outputConfig=outputConfig)
    visualizer: Visualizer = Visualizer(resultsDir=topLevelDir, outputConfig=outputConfig)

    # 运行所有测试
    results: List[Dict[str, Any]] = []
    totalTestCount: int = 0
    successfulVisualizations: int = 0
    failedVisualizations: int = 0

    for testCase in testCases:
        # 使用testRunner运行测试用例
        testCaseResults, testCaseName = runTestSuite(
            testCase, config, testCaseManager, defaultParams
        )

        # 更新总测试计数
        totalTestCount += len(testCaseResults)

        # 添加到总结果列表
        results.extend(testCaseResults)

        # 生成可视化（如果启用）
        if outputConfig.get("enableVisualization", True):
            for result in testCaseResults:
                logger.info(f"    生成可视化...")
                vizFile = visualizer.generateVisualization(result, testName=testCaseName)
                if vizFile:
                    successfulVisualizations += 1
                    logger.info(f"    [OK] 可视化成功: {os.path.basename(vizFile)}")
                else:
                    failedVisualizations += 1
                    logger.warning("    [FAIL] 可视化失败")
        else:
            logger.info(f"    可视化已禁用")

        # 保存当前测试用例的结果
        resultSaver.saveResults(testCaseResults, testCaseName)

    logger.info(f"\n{'='*80}")
    logger.info("测试完成统计:")
    logger.info(f"  总测试组合数: {totalTestCount}")
    logger.info(f"  成功可视化: {successfulVisualizations}")
    logger.info(f"  失败可视化: {failedVisualizations}")
    logger.info(f"  结果保存目录: {absTopLevelDir}")

    # 打印目录结构
    logger.info(f"\n目录结构:")
    for root, dirs, files in os.walk(absTopLevelDir):
        level = root.replace(absTopLevelDir, '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")

    logger.info(f"{'='*80}")

if __name__ == "__main__":
    main()
