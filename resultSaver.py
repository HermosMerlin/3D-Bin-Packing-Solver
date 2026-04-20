import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from logger import get_logger
from optimization import buildPlanRankKey, formatAlgorithmParams

logger = get_logger("resultSaver")

class ResultSaver:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir = resultsDir
        self.outputConfig = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

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

    @staticmethod
    def _mean(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _std(values: List[float]) -> Optional[float]:
        if not values:
            return None
        if len(values) == 1:
            return 0.0
        meanValue = ResultSaver._mean(values)
        variance = sum((value - meanValue) ** 2 for value in values) / (len(values) - 1)
        return variance ** 0.5

    @staticmethod
    def _formatPercent(value: Optional[float]) -> str:
        if value is None:
            return "N/A"
        return f"{value:.2%}"

    @staticmethod
    def _formatFloat(value: Optional[float], digits: int = 3) -> str:
        if value is None:
            return "N/A"
        return f"{value:.{digits}f}"

    def _isHigherObjectiveBetter(self, result: Dict[str, Any]) -> bool:
        return result["problem"].objective.primaryOrder == "max"

    def _resultRankKey(self, result: Dict[str, Any]) -> Tuple[float, ...]:
        return buildPlanRankKey(result["problem"], result["plan"])

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

    def _groupResultsByCombination(self, results: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        grouped: Dict[Tuple[int, str, str], List[Dict[str, Any]]] = {}
        for result in results:
            algorithmInfo = result["algorithmParams"]
            key = (
                result["combinationIndex"],
                algorithmInfo.get("algorithmType", "unknown"),
                json.dumps(algorithmInfo.get("params", {}), sort_keys=True, ensure_ascii=False)
            )
            grouped.setdefault(key, []).append(result)
        return sorted(grouped.values(), key=lambda group: group[0]["combinationIndex"])

    def buildAnalysisTables(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        runRows: List[Dict[str, Any]] = []
        containerRows: List[Dict[str, Any]] = []
        placementRows: List[Dict[str, Any]] = []

        for result in results:
            algorithmInfo = result["algorithmParams"]
            metrics = result["metrics"]
            paramValues = dict(algorithmInfo.get("params", {}))
            baseRow = {
                "testName": result["testName"],
                "runIndex": result["runIndex"],
                "combinationIndex": result["combinationIndex"],
                "repeatIndex": result["repeatIndex"],
                "algorithmType": algorithmInfo.get("algorithmType", "unknown"),
                "algorithmParams": formatAlgorithmParams(
                    algorithmInfo.get("algorithmType", "unknown"),
                    algorithmInfo.get("params", {})
                ),
                "seed": algorithmInfo.get("seed"),
                "useTimeSeed": algorithmInfo.get("useTimeSeed", False),
                "baseSeed": algorithmInfo.get("baseSeed"),
                "isValid": result["isValid"],
                "isCached": result["isCached"],
                "executionTime": result["executionTime"],
                "objectiveName": result["objectiveName"],
                "objectiveValue": result["objectiveValue"],
                "totalCost": result["totalCost"],
                "volumeRate": result["volumeRate"],
                "weightRate": result["weightRate"],
                "placedCount": result["placedCount"],
                "unpackedCount": result["unpackedCount"],
                "usedContainerCount": result["usedContainerCount"],
                "usedContainerTypeCount": metrics.usedContainerTypeCount,
                "avgContainerFillRate": metrics.avgContainerFillRate,
                "maxContainerFillRate": metrics.maxContainerFillRate,
                "avgContainerWeightRate": metrics.avgContainerWeightRate
            }
            baseRow.update(result.get("scenarioMetadata", {}))
            baseRow.update(paramValues)
            runRows.append(baseRow)

            for containerRow in result.get("containerRows", []):
                row = dict(baseRow)
                row.update(containerRow)
                containerRows.append(row)

            for placementRecord in result.get("placementRecords", []):
                item = placementRecord["item"]
                row = dict(baseRow)
                row.update({
                    "containerIndex": placementRecord["containerIndex"],
                    "containerInstanceId": placementRecord["containerInstanceId"],
                    "containerTypeId": placementRecord["containerTypeId"],
                    "placementOrder": placementRecord["placementOrder"],
                    "itemId": placementRecord["itemId"],
                    "itemTypeId": placementRecord["itemTypeId"],
                    "tags": ",".join(placementRecord["tags"]),
                    "x": placementRecord["x"],
                    "y": placementRecord["y"],
                    "z": placementRecord["z"],
                    "rotation": placementRecord["rotation"],
                    "placedL": placementRecord["placedDims"][0] if placementRecord["placedDims"] else None,
                    "placedW": placementRecord["placedDims"][1] if placementRecord["placedDims"] else None,
                    "placedH": placementRecord["placedDims"][2] if placementRecord["placedDims"] else None,
                    "originalL": item.l if item is not None else None,
                    "originalW": item.w if item is not None else None,
                    "originalH": item.h if item is not None else None,
                    "weight": item.weight if item is not None else None,
                    "supportSource": placementRecord["supportSource"],
                    "supportAreaRatio": placementRecord["supportAreaRatio"],
                    "bearingPressure": placementRecord["bearingPressure"],
                    "topClearanceCm": placementRecord["topClearanceCm"],
                    "projectionContained": placementRecord["projectionContained"]
                })
                placementRows.append(row)

        groupRows: List[Dict[str, Any]] = []
        for groupResults in self._groupResultsByCombination(results):
            firstResult = groupResults[0]
            algorithmInfo = firstResult["algorithmParams"]
            objectiveOrder = firstResult["problem"].objective.primaryOrder
            paramValues = dict(algorithmInfo.get("params", {}))
            validResults = self._getValidResults(groupResults)
            bestValidResult = self._getBestValidResult(groupResults)
            objectiveValues = [result["objectiveValue"] for result in validResults]
            totalCosts = [result["totalCost"] for result in validResults]
            fillRates = [result["volumeRate"] for result in validResults]
            executionTimes = [result["executionTime"] for result in groupResults]
            placedCounts = [float(result["placedCount"]) for result in validResults]
            unpackedCounts = [float(result["unpackedCount"]) for result in validResults]

            row = {
                "testName": firstResult["testName"],
                "combinationIndex": firstResult["combinationIndex"],
                "algorithmType": algorithmInfo.get("algorithmType", "unknown"),
                "algorithmParams": formatAlgorithmParams(
                    algorithmInfo.get("algorithmType", "unknown"),
                    algorithmInfo.get("params", {})
                ),
                "repeatCount": len(groupResults),
                "validCount": len(validResults),
                "invalidCount": len(groupResults) - len(validResults),
                "objectiveName": firstResult["objectiveName"],
                "objectiveOrder": objectiveOrder,
                "avgObjectiveValue": self._mean(objectiveValues),
                "stdObjectiveValue": self._std(objectiveValues),
                "bestObjectiveValue": (
                    bestValidResult["objectiveValue"] if bestValidResult is not None else None
                ),
                "avgTotalCost": self._mean(totalCosts),
                "stdTotalCost": self._std(totalCosts),
                "avgFillRate": self._mean(fillRates),
                "stdFillRate": self._std(fillRates),
                "avgPlacedCount": self._mean(placedCounts),
                "stdPlacedCount": self._std(placedCounts),
                "avgUnpackedCount": self._mean(unpackedCounts),
                "avgExecutionTime": self._mean(executionTimes),
                "stdExecutionTime": self._std(executionTimes)
            }
            row.update(firstResult.get("scenarioMetadata", {}))
            row.update(paramValues)
            groupRows.append(row)

        return {
            "run": runRows,
            "group": groupRows,
            "container": containerRows,
            "placement": placementRows
        }

    def _writeCsv(self, path: str, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        fieldnames = sorted({key for row in rows for key in row.keys()})
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _writeJson(self, path: str, rows: List[Dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def _writeAnalysisExports(
        self,
        testFolder: str,
        timestamp: str,
        tables: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        if not self.outputConfig.get("exportSummaryData", True):
            return

        for level, rows in tables.items():
            if not rows:
                continue
            csvPath = os.path.abspath(os.path.join(testFolder, f"{level}_{timestamp}.csv"))
            jsonPath = os.path.abspath(os.path.join(testFolder, f"{level}_{timestamp}.json"))
            self._writeCsv(csvPath, rows)
            self._writeJson(jsonPath, rows)
            logger.info(f"{level} CSV 已生成: {csvPath}")
            logger.info(f"{level} JSON 已生成: {jsonPath}")

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
            filename = (
                f"plan_best_{safeAlgorithm}_g{result['combinationIndex']:02d}_"
                f"r{result['repeatIndex']:02d}_{timestamp}.txt"
            )
        else:
            filename = (
                f"plan_g{result['combinationIndex']:02d}_r{result['repeatIndex']:02d}_"
                f"{safeAlgorithm}_{timestamp}.txt"
            )

        filePath = os.path.abspath(os.path.join(solutionFolder, filename))
        with open(filePath, "w", encoding="utf-8") as f:
            f.write("# Shipment Plan\n")
            f.write("schema_version: 2\n")
            f.write(f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"test_case: {testName}\n")
            f.write(f"algorithm: {algorithmType}\n")
            f.write(
                f"algorithm_params: {formatAlgorithmParams(algorithmType, result['algorithmParams'].get('params', {}))}\n"
            )
            f.write(f"objective_name: {result['objectiveName']}\n")
            f.write(f"objective_value: {result['objectiveValue']}\n")
            f.write(f"total_cost: {result['totalCost']}\n")
            f.write(f"used_container_count: {result['usedContainerCount']}\n")
            f.write(f"placed_count: {result['placedCount']}\n")
            f.write(f"unpacked_count: {result['unpackedCount']}\n")
            f.write(f"fill_rate: {result['volumeRate']:.6f}\n")
            f.write(f"execution_time_s: {result['executionTime']:.6f}\n")
            f.write("\n# Containers\n")

            for containerRow in result.get("containerRows", []):
                f.write(
                    f"- container_index={containerRow['containerIndex']}, "
                    f"container_instance_id={containerRow['containerInstanceId']}, "
                    f"container_type_id={containerRow['containerTypeId']}, "
                    f"trip_cost={containerRow['tripCost']}, "
                    f"placed_count={containerRow['placedCount']}, "
                    f"fill_rate={containerRow['fillRate']:.6f}, "
                    f"weight_rate={containerRow['weightRate']:.6f}\n"
                )

            f.write("\n# Placements\n")
            f.write(
                "container_index,placement_order,item_id,item_type_id,tags,"
                "x,y,z,rotation,placed_l,placed_w,placed_h,support_source,"
                "support_area_ratio,bearing_pressure,top_clearance_cm,projection_contained\n"
            )
            for record in result.get("placementRecords", []):
                dims = record["placedDims"] or (None, None, None)
                f.write(
                    f"{record['containerIndex']},"
                    f"{record['placementOrder']},"
                    f"{record['itemId']},"
                    f"{record['itemTypeId']},"
                    f"{'|'.join(record['tags'])},"
                    f"{record['x']},"
                    f"{record['y']},"
                    f"{record['z']},"
                    f"{record['rotation']},"
                    f"{dims[0]},"
                    f"{dims[1]},"
                    f"{dims[2]},"
                    f"{record['supportSource']},"
                    f"{record['supportAreaRatio']},"
                    f"{record['bearingPressure']},"
                    f"{record['topClearanceCm']},"
                    f"{record['projectionContained']}\n"
                )

        logger.info(f"解文本已生成: {filePath}")
        return filePath

    def saveResults(self, results: List[Dict[str, Any]], testName: str) -> Dict[str, Any]:
        testFolder = os.path.join(self.resultsDir, testName)
        os.makedirs(testFolder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reportPath = os.path.abspath(os.path.join(testFolder, f"results_{timestamp}.txt"))
        bestValidResult = self._getBestValidResult(results)
        solutionTextResults = self._selectSolutionTextResults(results, bestValidResult)
        tables = self.buildAnalysisTables(results)
        groupRows = tables["group"]

        with open(reportPath, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"装箱实验综合报告 - {testName}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("【1. 参数组统计】\n")
            f.write(
                "| 组 | 算法 | 参数 | 重复 | 合法 | 平均目标值 | 平均总成本 | 平均满容率 | 平均耗时 |\n"
            )
            f.write("|---| ---| ---| ---| ---| ---| ---| ---| ---|\n")
            for row in groupRows:
                f.write(
                    f"| {row['combinationIndex']} | {row['algorithmType']} | {row['algorithmParams']} | "
                    f"{row['repeatCount']} | {row['validCount']}/{row['repeatCount']} | "
                    f"{self._formatFloat(row['avgObjectiveValue'])} | "
                    f"{self._formatFloat(row['avgTotalCost'])} | "
                    f"{self._formatPercent(row['avgFillRate'])} | "
                    f"{self._formatFloat(row['avgExecutionTime'])}s |\n"
                )
            f.write("\n")

            f.write("【2. 单次运行明细】\n")
            for row in tables["run"]:
                f.write(
                    f">> 运行 {row['runIndex']} | 组 {row['combinationIndex']} | "
                    f"{row['algorithmType']} | 目标={row['objectiveValue']} | "
                    f"成本={row['totalCost']:.3f} | 满容率={row['volumeRate']:.2%} | "
                    f"已装={row['placedCount']} | 未装={row['unpackedCount']} | "
                    f"容器数={row['usedContainerCount']} | "
                    f"耗时={row['executionTime']:.3f}s | "
                    f"{'VALID' if row['isValid'] else 'INVALID'}"
                )
                if row["isCached"]:
                    f.write(" | CACHED")
                f.write("\n")
            f.write("\n")

            f.write("【3. 结论】\n")
            if bestValidResult is not None:
                f.write(
                    f"最优合法方案: 组 {bestValidResult['combinationIndex']} / "
                    f"重复 {bestValidResult['repeatIndex']}\n"
                )
                f.write(f"算法: {bestValidResult['algorithmParams']['algorithmType']}\n")
                f.write(f"目标值: {bestValidResult['objectiveValue']}\n")
                f.write(f"总成本: {bestValidResult['totalCost']}\n")
                f.write(f"总满容率: {bestValidResult['volumeRate']:.2%}\n")
                f.write(f"已用容器数: {bestValidResult['usedContainerCount']}\n")
            else:
                f.write("没有找到合法方案。\n")

            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"对比报告已生成: {reportPath}")
        self._writeAnalysisExports(testFolder, timestamp, tables)

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

        return {
            "reportPath": reportPath,
            "tables": tables,
            "bestValidResult": bestValidResult
        }
