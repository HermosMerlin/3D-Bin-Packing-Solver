import json
import os
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("testCaseManager")

class TestCaseManager:
    def __init__(self, testPath: str):
        self.testDir: str = os.path.join(testPath, "test")

    def validateTestCase(self, testCase: Dict[str, Any], filename: str) -> bool:
        """校验测试用例的合法性"""
        try:
            # 校验容器
            container = testCase.get("container")
            if not container:
                logger.error(f"测试用例 {filename} 缺少 'container' 定义")
                return False
            
            for dim in ["L", "W", "H", "maxWeight"]:
                val = container.get(dim)
                if val is None or val <= 0:
                    logger.error(f"测试用例 {filename} 的容器参数 {dim}={val} 不合法（必须 > 0）")
                    return False

            # 校验货物类型
            itemTypes = testCase.get("itemTypes")
            if not itemTypes or not isinstance(itemTypes, list):
                logger.error(f"测试用例 {filename} 缺少 'itemTypes' 列表")
                return False

            for i, it in enumerate(itemTypes):
                for dim in ["l", "w", "h", "weight", "count"]:
                    val = it.get(dim)
                    if val is None or val <= 0:
                        logger.error(f"测试用例 {filename} 的货物类型索引 {i} 参数 {dim}={val} 不合法")
                        return False
                
                # 校验单件货物是否能塞进容器（初步校验）
                if it["l"] > container["L"] or it["w"] > container["W"] or it["h"] > container["H"]:
                    # 注意：由于支持旋转，这里其实需要 6 种姿态都塞不进才算非法，
                    # 但如果三维中最长边超过了容器最长边，那肯定塞不进。
                    dims_item = sorted([it["l"], it["w"], it["h"]])
                    dims_cont = sorted([container["L"], container["W"], container["H"]])
                    if any(dims_item[j] > dims_cont[j] for j in range(3)):
                        logger.error(f"测试用例 {filename} 的货物规格 {it['l']}x{it['w']}x{it['h']} 超过容器尺寸")
                        return False

            return True
        except Exception as e:
            logger.error(f"校验测试用例 {filename} 时发生异常: {e}")
            return False

    def loadTestCases(self) -> List[Dict[str, Any]]:
        """加载测试目录下的所有JSON文件"""
        testCases: List[Dict[str, Any]] = []
        if not os.path.exists(self.testDir):
            os.makedirs(self.testDir)
            logger.info(f"测试目录 {self.testDir} 不存在，已创建")
            return testCases

        for filename in os.listdir(self.testDir):
            # 安全检查：防止路径遍历（虽然 listdir 限制了范围，但在组合路径时仍需谨慎）
            if ".." in filename or os.path.isabs(filename):
                logger.warning(f"跳过潜在不安全的文件名: {filename}")
                continue

            if filename.endswith(".json"):
                filepath = os.path.join(self.testDir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        testCase = json.load(f)
                        
                        # 执行校验
                        if not self.validateTestCase(testCase, filename):
                            logger.warning(f"跳过校验失败的测试用例: {filename}")
                            continue

                        testCaseName = os.path.splitext(filename)[0]
                        testCase["name"] = testCaseName
                        testCases.append(testCase)
                except Exception as e:
                    logger.error(f"加载测试文件 {filename} 失败: {e}")

        return testCases

    def generateParamCombinations(self, paramConfig: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成参数组合列表"""
        combinations: List[Dict[str, Any]] = []

        # 处理算法类型
        algorithmTypes = paramConfig.get("algorithmType", "hill_climbing")
        if not isinstance(algorithmTypes, list):
            algorithmTypes = [algorithmTypes]

        # 处理迭代次数
        if isinstance(paramConfig.get("iterations"), dict):
            iterConfig = paramConfig["iterations"]
            minVal = iterConfig.get("min", 10)
            maxVal = iterConfig.get("max", 10)
            step = iterConfig.get("step", 50)
            iterationsList = list(range(minVal, maxVal + 1, step))
            if not iterationsList: iterationsList = [minVal]
        else:
            iterationsList = [paramConfig.get("iterations", 10)]

        # 处理随机率
        if isinstance(paramConfig.get("randomRate"), dict):
            rateConfig = paramConfig["randomRate"]
            minVal = rateConfig.get("min", 0.1)
            maxVal = rateConfig.get("max", 0.1)
            step = rateConfig.get("step", 0.1)
            current = minVal
            randomRates = []
            while current <= maxVal + 1e-9:
                randomRates.append(round(current, 2))
                current += step
            if not randomRates: randomRates = [minVal]
        else:
            randomRates = [paramConfig.get("randomRate", 0.1)]

        useTimeSeed = paramConfig.get("useTimeSeed", True)

        for algType in algorithmTypes:
            for iterVal in iterationsList:
                for rateVal in randomRates:
                    combinations.append({
                        "algorithmType": algType,
                        "iterations": iterVal,
                        "randomRate": rateVal,
                        "useTimeSeed": useTimeSeed
                    })

        return combinations

    def getEffectiveParams(self, testCaseParams: Dict[str, Any], defaultParams: Dict[str, Any]) -> Dict[str, Any]:
        """获取有效参数"""
        effectiveParams: Dict[str, Any] = {}
        for key in ["algorithmType", "iterations", "randomRate", "useTimeSeed"]:
            if key in testCaseParams:
                effectiveParams[key] = testCaseParams[key]
            elif key in defaultParams:
                effectiveParams[key] = defaultParams[key]
        return effectiveParams
