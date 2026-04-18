import os
from datetime import datetime
from configManager import ConfigManager
from testCaseManager import TestCaseManager
from resultSaver import ResultSaver
from visualizer import Visualizer
from testRunner import runTestSuite

def main():
    """批量测试主函数"""
    print("=" * 80)
    print("三维装箱算法批量测试程序")
    print("=" * 80)

    # 初始化各个管理器
    configManager = ConfigManager()
    testCaseManager = TestCaseManager()

    # 获取配置和测试用例
    config = configManager.getConfig()
    testCases = testCaseManager.loadTestCases()

    if len(testCases) == 0:
        print("错误: 未找到测试用例，请在test目录下添加JSON文件")
        return

    print(f"加载了 {len(testCases)} 个测试用例")

    # 获取默认参数
    defaultParams = configManager.getDefaultParams()

    # 获取基础结果目录
    outputConfig = configManager.getOutputConfig()
    baseResultsDir = outputConfig["resultsDir"]

    # 创建本次运行的顶级文件夹（以时间戳命名）
    runTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topLevelDir = os.path.join(baseResultsDir, f"{runTimestamp}")
    os.makedirs(topLevelDir, exist_ok=True)

    # 打印本次运行的目录路径
    absTopLevelDir = os.path.abspath(topLevelDir)
    print(f"本次运行结果将保存到: {absTopLevelDir}")

    # 初始化结果保存器和可视化器，使用本次运行的顶级目录
    resultSaver = ResultSaver(resultsDir=topLevelDir, outputConfig=outputConfig)
    visualizer = Visualizer(resultsDir=topLevelDir)

    # 运行所有测试
    results = []
    totalTestCount = 0
    successfulVisualizations = 0
    failedVisualizations = 0

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
        if outputConfig.get("enableVisualization", False):
            for result in testCaseResults:
                print(f"    生成可视化...")
                vizFile = visualizer.generateVisualization(result, testCaseName)
                if vizFile:
                    successfulVisualizations += 1
                    print(f"    ✓ 可视化成功: {os.path.basename(vizFile)}")
                else:
                    failedVisualizations += 1
                    print(f"    ✗ 可视化失败")
        else:
            print(f"    可视化已禁用")

        # 保存当前测试用例的结果
        resultSaver.saveResults(testCaseResults, testCaseName)

    print(f"\n{'='*80}")
    print("测试完成统计:")
    print(f"  总测试组合数: {totalTestCount}")
    print(f"  成功可视化: {successfulVisualizations}")
    print(f"  失败可视化: {failedVisualizations}")
    print(f"  结果保存目录: {absTopLevelDir}")

    # 打印目录结构
    print(f"\n目录结构:")
    for root, dirs, files in os.walk(absTopLevelDir):
        level = root.replace(absTopLevelDir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

    print(f"{'='*80}")

if __name__ == "__main__":
    main()
