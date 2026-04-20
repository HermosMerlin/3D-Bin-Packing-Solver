import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from logger import get_logger
from optimization import formatAlgorithmParams
from solutionValidator import buildPlacementRecords

logger = get_logger("resultSaver")

class ResultSaver:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir: str = resultsDir
        self.outputConfig: Dict[str, Any] = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

    @staticmethod
    def _resultRankKey(result: Dict[str, Any]) -> tuple:
        return (
            result.get("volumeRate", 0.0),
            result.get("weightRate", 0.0),
            result.get("placedCount", 0),
            -result.get("executionTime", float("inf"))
        )

    @staticmethod
    def _normalizeSolutionTextMode(value: Any) -> str:
        if value is True:
            return "true"
        if value is False or value is None:
            return "false"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "false", "only-best"}:
                return normalized
        return "false"

    @staticmethod
    def _sanitizeFileNamePart(value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)

    def _getValidResults(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [result for result in results if result.get("isValid", False)]

    def _getBestValidResult(self, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        validResults = self._getValidResults(results)
        if not validResults:
            return None
        return max(validResults, key=self._resultRankKey)

    def _selectSolutionTextResults(
        self,
        results: List[Dict[str, Any]],
        bestValidResult: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        mode = self._normalizeSolutionTextMode(
            self.outputConfig.get("saveSolutionText", False)
        )
        if mode == "false":
            return []
        if mode == "true":
            return self._getValidResults(results)
        if mode == "only-best" and bestValidResult is not None:
            return [bestValidResult]
        return []

    def _writeSolutionText(
        self,
        result: Dict[str, Any],
        testName: str,
        testFolder: str,
        timestamp: str,
        isBestOverall: bool
    ) -> str:
        solutionFolder = os.path.join(testFolder, "solutions")
        os.makedirs(solutionFolder, exist_ok=True)

        algorithmType = result["algorithmParams"].get("algorithmType", "unknown")
        safeAlgorithm = self._sanitizeFileNamePart(algorithmType)
        if isBestOverall:
            filename = f"solution_best_{safeAlgorithm}_{timestamp}.txt"
        else:
            filename = f"solution_{result['testIndex']:02d}_{safeAlgorithm}_{timestamp}.txt"

        filePath = os.path.abspath(os.path.join(solutionFolder, filename))
        placementRecords = buildPlacementRecords(result["items"], result["solution"])
        paramSummary = formatAlgorithmParams(
            algorithmType,
            result["algorithmParams"].get("params", {})
        )
        seedMode = "time-based" if result["algorithmParams"].get("useTimeSeed", True) else "fixed"
        container = result["container"]

        with open(filePath, "w", encoding="utf-8") as f:
            f.write("# Packing Solution\n")
            f.write("schema_version: 1\n")
            f.write(f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"test_case: {testName}\n")
            f.write(f"combination_index: {result['testIndex']}/{result['totalTests']}\n")
            f.write(f"algorithm: {algorithmType}\n")
            f.write(f"algorithm_params: {paramSummary}\n")
            f.write(f"seed: {result['algorithmParams'].get('seed')} ({seedMode})\n")
            f.write(f"is_valid: {str(result.get('isValid', False)).lower()}\n")
            f.write("\n")

            f.write("# Container\n")
            f.write(f"L: {container.L}\n")
            f.write(f"W: {container.W}\n")
            f.write(f"H: {container.H}\n")
            f.write(f"maxWeight: {container.maxWeight}\n")
            f.write("\n")

            f.write("# Summary\n")
            f.write(f"placed_count: {result['placedCount']}\n")
            f.write(f"total_item_count: {len(result['items'])}\n")
            f.write(f"volume_rate: {result['volumeRate']:.6f}\n")
            f.write(f"weight_rate: {result['weightRate']:.6f}\n")
            f.write(f"execution_time_s: {result['executionTime']:.6f}\n")
            f.write("\n")

            f.write("# Columns\n")
            f.write(
                "placement_order,item_id,type_id,origin_x,origin_y,origin_z,"
                "placed_l,placed_w,placed_h,rotation_id,original_l,original_w,original_h,weight\n"
            )
            for record in placementRecords:
                item = record["item"]
                placedDims = record["placedDims"] or ("NA", "NA", "NA")
                originalDims = (
                    (item.l, item.w, item.h) if item is not None else ("NA", "NA", "NA")
                )
                weight = item.weight if item is not None else "NA"
                typeId = record["typeId"] if record["typeId"] is not None else ""
                f.write(
                    f"{record['placementOrder']},"
                    f"{record['itemId']},"
                    f"{typeId},"
                    f"{record['x']},"
                    f"{record['y']},"
                    f"{record['z']},"
                    f"{placedDims[0]},"
                    f"{placedDims[1]},"
                    f"{placedDims[2]},"
                    f"{record['rotation']},"
                    f"{originalDims[0]},"
                    f"{originalDims[1]},"
                    f"{originalDims[2]},"
                    f"{weight}\n"
                )

        logger.info(f"解文本已生成: {filePath}")
        return filePath

    def saveResults(self, results: List[Dict[str, Any]], testName: str) -> str:
        """Save a comparison report and optional text solutions for a single test case."""
        testFolder = os.path.join(self.resultsDir, testName)
        os.makedirs(testFolder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resultFile = os.path.join(testFolder, f"results_{timestamp}.txt")
        absResultFile = os.path.abspath(resultFile)

        bestValidResult = self._getBestValidResult(results)
        solutionTextResults = self._selectSolutionTextResults(results, bestValidResult)

        with open(absResultFile, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"三维装箱算法综合对比报告 - {testName}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("【1. 性能汇总对比】\n")
            header = (
                "| 索引 | 算法类型 | 参数 | 合法性 | 空间利用率 | 重量利用率 | "
                "装载数 | 运行耗时 | 状态 |"
            )
            f.write(header + "\n")
            f.write("|" + "---| " * 9 + "|\n")

            for result in results:
                if not result.get("isValid", False):
                    status = "INVALID"
                elif result == bestValidResult:
                    status = "BEST"
                else:
                    status = ""

                algorithmInfo = result["algorithmParams"]
                algorithmType = algorithmInfo.get("algorithmType", "unknown")
                paramSummary = formatAlgorithmParams(
                    algorithmType,
                    algorithmInfo.get("params", {})
                )
                validLabel = "valid" if result.get("isValid", False) else "invalid"
                line = (
                    f"| {result['testIndex']:^4} | {algorithmType:<19} | {paramSummary} | "
                    f"{validLabel:^7} | {result['volumeRate']:>9.2%} | "
                    f"{result['weightRate']:>9.2%} | "
                    f"{result['placedCount']:>3}/{len(result['items']):<3} | "
                    f"{result['executionTime']:>7.3f}s | {status:^7} |"
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
                f.write(
                    f"   合法性: {'VALID' if result.get('isValid', False) else 'INVALID'}\n"
                )

                if result.get("isCached"):
                    f.write("   状态: 从缓存加载\n")

                if not result.get("isValid", False):
                    for error in result.get("validationErrors", []):
                        f.write(f"   校验错误: {error}\n")

                if self.outputConfig.get("showPlacementText", True) and self.outputConfig.get("saveDetailedLog", False):
                    f.write("   放置序列(前10个): ")
                    placementSummary = "; ".join(
                        [f"{itemId}" for itemId, *_ in result["solution"].placedItems[:10]]
                    )
                    f.write(f"{placementSummary}...\n")

                f.write("-" * 40 + "\n")

            if bestValidResult:
                bestAlgorithm = bestValidResult["algorithmParams"].get("algorithmType", "unknown")
                bestParams = formatAlgorithmParams(
                    bestAlgorithm,
                    bestValidResult["algorithmParams"].get("params", {})
                )
                f.write("\n【3. 测试结论】\n")
                f.write(f"本次测试中表现最优的合法算法是: {bestAlgorithm}\n")
                f.write(f"最高空间利用率达到: {bestValidResult['volumeRate']:.2%}\n")
                f.write(f"最优参数: {bestParams}\n")
            else:
                f.write("\n【3. 测试结论】\n")
                f.write("本次测试中没有找到合法解。\n")

            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"对比报告已生成: {absResultFile}")

        if solutionTextResults:
            logger.info(
                f"导出解文本: {len(solutionTextResults)} "
                f"(mode={self._normalizeSolutionTextMode(self.outputConfig.get('saveSolutionText', False))})"
            )
        for result in solutionTextResults:
            self._writeSolutionText(
                result=result,
                testName=testName,
                testFolder=testFolder,
                timestamp=timestamp,
                isBestOverall=(result == bestValidResult)
            )

        return absResultFile
