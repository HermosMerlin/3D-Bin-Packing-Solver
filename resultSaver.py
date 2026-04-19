import os
from datetime import datetime
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("resultSaver")

class ResultSaver:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir: str = resultsDir
        self.outputConfig: Dict[str, Any] = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

    def saveResults(self, results: List[Dict[str, Any]], testName: str) -> str:
        """保存测试结果到文件，并生成综合对比报告"""
        testFolder = os.path.join(self.resultsDir, testName)
        os.makedirs(testFolder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resultFile = os.path.join(testFolder, f"results_{timestamp}.txt")
        absResultFile = os.path.abspath(resultFile)

        # 找出最优方案（以空间利用率为准）
        bestResult = max(results, key=lambda x: x['volumeRate']) if results else None

        with open(absResultFile, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"三维装箱算法综合对比报告 - {testName}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            # 1. 性能对比汇总表
            f.write("【1. 性能汇总对比】\n")
            header = "| 索引 | 算法类型 | 空间利用率 | 重量利用率 | 装载数 | 运行耗时 | 状态 |"
            f.write(header + "\n")
            f.write("|" + "---| " * 7 + "|\n")
            
            for r in results:
                status = " BEST " if r == bestResult and len(results) > 1 else "      "
                alg_name = r['algorithmParams'].get('algorithmType', 'unknown')
                line = (f"| {r['testIndex']:^4} | {alg_name:<10} | {r['volumeRate']:>9.2%} | "
                        f"{r['weightRate']:>9.2%} | {r['placedCount']:>3}/{len(r['items']):<3} | "
                        f"{r['executionTime']:>7.3f}s | {status:^6} |")
                f.write(line + "\n")
            f.write("\n")

            # 2. 算法详情
            f.write("【2. 算法执行详情】\n")
            for result in results:
                f.write(f">> 组合 {result['testIndex']}/{result['totalTests']} [{result['algorithmParams'].get('algorithmType')}]\n")
                
                # 容器信息
                c = result['container']
                f.write(f"   容器: {c.L}x{c.W}x{c.H}, 最大载重 {c.maxWeight}\n")
                
                # 算法具体参数
                params = result['algorithmParams']
                param_str = ", ".join([f"{k}={v}" for k, v in params.items() if k not in ['algorithmType', 'seed']])
                f.write(f"   参数: {param_str} (Seed: {params.get('seed')})\n")
                
                # 结果指标
                f.write(f"   结果: 空间={result['volumeRate']:.2%}, 重量={result['weightRate']:.2%}, ")
                f.write(f"耗时={result['executionTime']:.3f}秒\n")

                # 如果开启了详细记录，且有缓存命中，则说明一下
                if result.get('isCached'):
                    f.write("   状态: (从缓存加载)\n")

                if self.outputConfig.get("showPlacementText", True) and self.outputConfig.get("saveDetailedLog", False):
                    f.write("   放置序列(前10个): ")
                    placement_summary = "; ".join([f"{pid}" for pid, *_ in result['solution'].placedItems[:10]])
                    f.write(f"{placement_summary}...\n")

                f.write("-" * 40 + "\n")

            # 3. 结论
            if bestResult:
                f.write("\n【3. 测试结论】\n")
                f.write(f"本次测试中表现最优的算法是: {bestResult['algorithmParams'].get('algorithmType')}\n")
                f.write(f"最高空间利用率达到: {bestResult['volumeRate']:.2%}\n")
                
            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"对比报告已生成: {absResultFile}")
        return absResultFile
