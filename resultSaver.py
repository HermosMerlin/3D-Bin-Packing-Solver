import os
from datetime import datetime
from typing import List, Dict, Any
from logger import get_logger
from optimization import formatAlgorithmParams

logger = get_logger("resultSaver")

class ResultSaver:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir: str = resultsDir
        self.outputConfig: Dict[str, Any] = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

    def saveResults(self, results: List[Dict[str, Any]], testName: str) -> str:
        """Save a comparison report for a single test case."""
        testFolder = os.path.join(self.resultsDir, testName)
        os.makedirs(testFolder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resultFile = os.path.join(testFolder, f"results_{timestamp}.txt")
        absResultFile = os.path.abspath(resultFile)

        bestResult = max(results, key=lambda x: x["volumeRate"]) if results else None

        with open(absResultFile, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"三维装箱算法综合对比报告 - {testName}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("【1. 性能汇总对比】\n")
            header = (
                "| 索引 | 算法类型 | 参数 | 空间利用率 | 重量利用率 | "
                "装载数 | 运行耗时 | 状态 |"
            )
            f.write(header + "\n")
            f.write("|" + "---| " * 8 + "|\n")

            for result in results:
                status = " BEST " if result == bestResult and len(results) > 1 else "      "
                algorithmInfo = result["algorithmParams"]
                algorithmType = algorithmInfo.get("algorithmType", "unknown")
                paramSummary = formatAlgorithmParams(
                    algorithmType,
                    algorithmInfo.get("params", {})
                )
                line = (
                    f"| {result['testIndex']:^4} | {algorithmType:<19} | {paramSummary} | "
                    f"{result['volumeRate']:>9.2%} | {result['weightRate']:>9.2%} | "
                    f"{result['placedCount']:>3}/{len(result['items']):<3} | "
                    f"{result['executionTime']:>7.3f}s | {status:^6} |"
                )
                f.write(line + "\n")
            f.write("\n")

            f.write("【2. 算法执行详情】\n")
            for result in results:
                algorithmInfo = result["algorithmParams"]
                algorithmType = algorithmInfo.get("algorithmType", "unknown")
                paramSummary = formatAlgorithmParams(
                    algorithmType,
                    algorithmInfo.get("params", {})
                )
                seedMode = "time-based" if algorithmInfo.get("useTimeSeed", True) else "fixed"

                f.write(
                    f">> 组合 {result['testIndex']}/{result['totalTests']} "
                    f"[{algorithmType}]\n"
                )

                container = result["container"]
                f.write(
                    f"   容器: {container.L}x{container.W}x{container.H}, "
                    f"最大载重={container.maxWeight}\n"
                )
                f.write(f"   参数: {paramSummary}\n")
                f.write(f"   Seed: {algorithmInfo.get('seed')} ({seedMode})\n")
                f.write(
                    f"   结果: 空间={result['volumeRate']:.2%}, "
                    f"重量={result['weightRate']:.2%}, "
                    f"耗时={result['executionTime']:.3f}s\n"
                )

                if result.get("isCached"):
                    f.write("   状态: 从缓存加载\n")

                if self.outputConfig.get("showPlacementText", True) and self.outputConfig.get("saveDetailedLog", False):
                    f.write("   放置序列(前10个): ")
                    placementSummary = "; ".join(
                        [f"{itemId}" for itemId, *_ in result["solution"].placedItems[:10]]
                    )
                    f.write(f"{placementSummary}...\n")

                f.write("-" * 40 + "\n")

            if bestResult:
                bestAlgorithm = bestResult["algorithmParams"].get("algorithmType", "unknown")
                bestParams = formatAlgorithmParams(
                    bestAlgorithm,
                    bestResult["algorithmParams"].get("params", {})
                )
                f.write("\n【3. 测试结论】\n")
                f.write(f"本次测试中表现最优的算法是: {bestAlgorithm}\n")
                f.write(f"最高空间利用率达到: {bestResult['volumeRate']:.2%}\n")
                f.write(f"最优参数: {bestParams}\n")

            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"对比报告已生成: {absResultFile}")
        return absResultFile
