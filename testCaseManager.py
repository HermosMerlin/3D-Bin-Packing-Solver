import json
import os

class TestCaseManager:
    def __init__(self, testPath):
        self.testDir = "test"
        self.testDir = os.path.join(testPath, self.testDir)

    def loadTestCases(self):
        """加载测试目录下的所有JSON文件"""
        testCases = []
        if not os.path.exists(self.testDir):
            os.makedirs(self.testDir)
            print(f"测试目录 {self.testDir} 不存在，已创建")
            return testCases

        for filename in os.listdir(self.testDir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.testDir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        testCase = json.load(f)
                        testCaseName = os.path.splitext(filename)[0]
                        testCase["name"] = testCaseName
                        testCases.append(testCase)
                except Exception as e:
                    print(f"加载测试文件 {filename} 失败: {e}")

        return testCases

    def generateParamCombinations(self, paramConfig):
        """
        生成参数组合列表
        :param paramConfig: 参数配置，可以是单值、范围或默认值
        :return: 参数组合列表
        """
        combinations = []

        # 处理迭代次数
        if isinstance(paramConfig.get("iterations"), dict):
            # 范围格式
            iterConfig = paramConfig["iterations"]
            minVal = iterConfig.get("min", 50)
            maxVal = iterConfig.get("max", 150)
            step = iterConfig.get("step", 50)
            iterationsList = list(range(minVal, maxVal + 1, step))
        else:
            # 单值格式
            iterationsList = [paramConfig.get("iterations", 100)]

        # 处理随机率
        if isinstance(paramConfig.get("randomRate"), dict):
            # 范围格式
            rateConfig = paramConfig["randomRate"]
            minVal = rateConfig.get("min", 0.1)
            maxVal = rateConfig.get("max", 0.3)
            step = rateConfig.get("step", 0.1)
            # 生成浮点数列表，避免精度问题
            current = minVal
            randomRates = []
            while current <= maxVal + 1e-9:  # 加上小误差避免浮点数精度问题
                randomRates.append(round(current, 2))
                current += step
        else:
            # 单值格式
            randomRates = [paramConfig.get("randomRate", 0.2)]

        # 处理useTimeSeed（单值）
        useTimeSeed = paramConfig.get("useTimeSeed", True)

        # 生成所有组合
        for iterVal in iterationsList:
            for rateVal in randomRates:
                combinations.append({
                    "iterations": iterVal,
                    "randomRate": rateVal,
                    "useTimeSeed": useTimeSeed
                })

        return combinations

    def getEffectiveParams(self, testCaseParams, defaultParams):
        """
        获取有效参数（测试集参数优先，否则使用默认值）
        """
        effectiveParams = {}

        # 合并参数（测试集参数覆盖默认参数）
        for key in ["iterations", "randomRate", "useTimeSeed"]:
            if key in testCaseParams:
                effectiveParams[key] = testCaseParams[key]
            elif key in defaultParams:
                effectiveParams[key] = defaultParams[key]

        return effectiveParams
