import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataStructures import ShipmentPlan
from logger import get_logger
from optimization import optimizePacking
from solutionValidator import validateShipmentPlan
from testCaseManager import TestCaseManager

logger = get_logger("validationRunner")

def _write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _write_text(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def _match_expected_errors(errors: List[str], expectedSnippets: List[str]) -> bool:
    for snippet in expectedSnippets:
        if not any(snippet in error for error in errors):
            return False
    return True

def _run_plan_validation(
    manager: TestCaseManager,
    caseData: Dict[str, Any]
) -> Dict[str, Any]:
    problem = manager.buildProblemInstance(caseData)
    plan = ShipmentPlan.from_dict(caseData["validationPlan"])
    validation = validateShipmentPlan(problem, plan)
    expect = caseData.get("validationExpect", {})
    shouldBeValid = bool(expect.get("planShouldBeValid", True))
    expectedErrors = list(expect.get("expectedErrorContains", []))
    passed = (
        validation["isValid"] == shouldBeValid and
        _match_expected_errors(validation["errors"], expectedErrors)
    )
    return {
        "mode": "plan",
        "passed": passed,
        "shouldBeValid": shouldBeValid,
        "actualIsValid": validation["isValid"],
        "errors": validation["errors"]
    }

def _run_solver_validation(
    manager: TestCaseManager,
    caseData: Dict[str, Any]
) -> Dict[str, Any]:
    problem = manager.buildProblemInstance(caseData)
    solverConfig = dict(caseData.get("solverConfig", {}))
    algorithmType = str(solverConfig.get("algorithmType", "greedy_search"))
    params = dict(solverConfig.get("params", {"iterations": 1}))
    seed = int(solverConfig.get("seed", 42))
    plan = optimizePacking(
        problem=problem,
        algorithmType=algorithmType,
        params=params,
        seed=seed
    )
    validation = validateShipmentPlan(problem, plan)
    expect = caseData.get("validationExpect", {})
    shouldBeValid = bool(expect.get("solverShouldBeValid", True))
    passed = validation["isValid"] == shouldBeValid
    return {
        "mode": "solver",
        "passed": passed,
        "algorithmType": algorithmType,
        "params": params,
        "seed": seed,
        "shouldBeValid": shouldBeValid,
        "actualIsValid": validation["isValid"],
        "errors": validation["errors"],
        "objectiveName": validation["metrics"].objectiveName,
        "objectiveValue": validation["metrics"].objectiveValue
    }

def runValidationSuite(
    scriptDir: str,
    config: Dict[str, Any],
    outputDir: Optional[str] = None
) -> Dict[str, Any]:
    validationConfig = config.get("validation", {})
    casesDir = os.path.join(
        scriptDir,
        validationConfig.get("casesDir", "validation/cases")
    )
    manager = TestCaseManager(testPath=scriptDir)

    if not os.path.exists(casesDir):
        logger.warning(f"验证目录不存在，跳过: {casesDir}")
        return {
            "enabled": False,
            "casesDir": casesDir,
            "passed": True,
            "totalCases": 0,
            "passedCases": 0,
            "failedCases": 0,
            "results": []
        }

    caseFiles = sorted(
        filename for filename in os.listdir(casesDir)
        if filename.endswith(".json")
    )
    logger.info(f"开始运行功能验证套件，共 {len(caseFiles)} 个用例")

    results: List[Dict[str, Any]] = []
    for filename in caseFiles:
        path = os.path.join(casesDir, filename)
        with open(path, "r", encoding="utf-8") as f:
            caseData = json.load(f)

        caseName = os.path.splitext(filename)[0]
        caseData["name"] = caseName
        schemaValid = manager.validateTestCase(caseData, filename)
        expect = caseData.get("validationExpect", {})
        schemaShouldPass = bool(expect.get("schemaShouldPass", True))
        schemaPassed = schemaValid == schemaShouldPass

        caseResult: Dict[str, Any] = {
            "caseName": caseName,
            "schemaPassed": schemaPassed,
            "schemaShouldPass": schemaShouldPass,
            "schemaActual": schemaValid,
            "checks": []
        }

        if not schemaPassed:
            logger.error(
                f"[Validation][FAIL] {caseName}: schema expectation mismatch "
                f"(expected {schemaShouldPass}, got {schemaValid})"
            )
            caseResult["passed"] = False
            results.append(caseResult)
            continue

        if schemaValid and "validationPlan" in caseData:
            check = _run_plan_validation(manager, caseData)
            caseResult["checks"].append(check)
        if schemaValid and caseData.get("solverConfig"):
            check = _run_solver_validation(manager, caseData)
            caseResult["checks"].append(check)

        caseResult["passed"] = all(check["passed"] for check in caseResult["checks"]) if caseResult["checks"] else schemaPassed
        if caseResult["passed"]:
            logger.info(f"[Validation][PASS] {caseName}")
        else:
            logger.error(f"[Validation][FAIL] {caseName}")
        results.append(caseResult)

    summary = {
        "enabled": True,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "casesDir": casesDir,
        "passed": all(result["passed"] for result in results),
        "totalCases": len(results),
        "passedCases": sum(1 for result in results if result["passed"]),
        "failedCases": sum(1 for result in results if not result["passed"]),
        "results": results
    }

    if outputDir and validationConfig.get("exportValidationSummary", True):
        validationOutputDir = os.path.join(outputDir, "validation")
        os.makedirs(validationOutputDir, exist_ok=True)
        jsonPath = os.path.join(validationOutputDir, "summary.json")
        textPath = os.path.join(validationOutputDir, "summary.txt")
        _write_json(jsonPath, summary)
        textLines = [
            f"Validation Cases: {summary['totalCases']}",
            f"Passed: {summary['passedCases']}",
            f"Failed: {summary['failedCases']}",
            f"Overall: {'PASS' if summary['passed'] else 'FAIL'}",
            ""
        ]
        for result in results:
            textLines.append(
                f"[{'PASS' if result['passed'] else 'FAIL'}] {result['caseName']}"
            )
            for check in result["checks"]:
                textLines.append(
                    f"  - {check['mode']}: {'PASS' if check['passed'] else 'FAIL'}"
                )
        _write_text(textPath, textLines)
        logger.info(f"验证汇总已生成: {jsonPath}")
        logger.info(f"验证汇总已生成: {textPath}")

    return summary
