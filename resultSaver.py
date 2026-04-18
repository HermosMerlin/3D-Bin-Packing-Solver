import os
from datetime import datetime

class ResultSaver:
    def __init__(self, resultsDir="results", outputConfig=None):
        self.resultsDir = resultsDir
        self.outputConfig = outputConfig or {}
        # 确保结果目录存在
        os.makedirs(self.resultsDir, exist_ok=True)

    def saveResults(self, results, testName):
        """保存测试结果到文件"""
        # 创建测试用例文件夹 - 确保路径正确
        testFolder = os.path.join(self.resultsDir, testName)
        os.makedirs(testFolder, exist_ok=True)

        # 生成时间戳文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resultFile = os.path.join(testFolder, f"results_{timestamp}.txt")
        absResultFile = os.path.abspath(resultFile)

        with open(absResultFile, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"三维装箱算法测试结果 - {testName}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            totalExecutionTime = 0

            for result in results:
                # 显示集装箱尺寸而不是对象
                containerInfo = f"{result['container'].L}x{result['container'].W}x{result['container'].H}, 最大载重{result['container'].maxWeight}"

                f.write(f"组合 {result['testIndex']}/{result['totalTests']}\n")
                f.write(f"集装箱尺寸: {containerInfo}\n")

                # 输出货物规格信息
                f.write("货物规格:\n")
                totalItems = 0
                for itemType in result['itemTypes']:
                    count = itemType["count"]
                    totalItems += count
                    f.write(f"  类型{itemType['typeId']}: {itemType['l']}x{itemType['w']}x{itemType['h']}, ")
                    f.write(f"重量{itemType['weight']}, 数量{count}\n")
                f.write(f"货物总数: {totalItems}\n")

                # 显示算法参数
                algoParams = result['algorithmParams']
                f.write(f"算法参数: 迭代次数={algoParams['iterations']}, ")
                f.write(f"随机率={algoParams['randomRate']}, ")
                f.write(f"种子={algoParams['seed']}\n")

                f.write(f"已放置货物: {result['placedCount']}/{totalItems}\n")
                f.write(f"满容率: {result['volumeRate']:.2%}\n")
                f.write(f"满载率: {result['weightRate']:.2%}\n")
                f.write(f"运行时间: {result['executionTime']:.3f} 秒\n")

                totalExecutionTime += result['executionTime']

                # 文字化显示放置方案（带开关）
                if self.outputConfig.get("showPlacementText", True) and self.outputConfig.get("saveDetailedLog", True):
                    # 密集格式显示
                    f.write("放置方案(密集格式):\n")
                    placementData = []
                    # 修复：solution是对象，不是字典
                    for itemId, x, y, z, rotation in result['solution'].placedItems:
                        placementData.append(f"{itemId}:({x},{y},{z},{rotation})")

                    # 每行显示多个货物，用分号分隔
                    line = ""
                    for i, data in enumerate(placementData):
                        if len(line) + len(data) + 2 < 80:
                            line += data + "; "
                        else:
                            f.write(f"  {line}\n")
                            line = data + "; "
                    if line:
                        f.write(f"  {line}\n")

                f.write("-" * 80 + "\n\n")

            # 综合统计
            f.write("综合统计:\n")
            avgVolumeRate = sum(r['volumeRate'] for r in results) / len(results)
            avgWeightRate = sum(r['weightRate'] for r in results) / len(results)
            avgExecutionTime = totalExecutionTime / len(results)

            f.write(f"总组合数: {len(results)}\n")
            f.write(f"平均满容率: {avgVolumeRate:.2%}\n")
            f.write(f"平均满载率: {avgWeightRate:.2%}\n")
            f.write(f"总运行时间: {totalExecutionTime:.3f} 秒\n")
            f.write(f"平均运行时间: {avgExecutionTime:.3f} 秒\n")

        print(f"测试用例 '{testName}' 的结果已保存到: {absResultFile}")
        return absResultFile
