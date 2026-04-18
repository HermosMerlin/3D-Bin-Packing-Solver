import random
from packingLogic import simplePacking

def optimizePacking(container, items, iterations=100, randomRate=0.2, seed=None):
    """
    优化装箱方案
    :param randomRate: 随机率（接受较差解的概率，用于扩展）
    :param seed: 随机种子，用于复现结果
    """
    if seed is not None:
        random.seed(seed)

    # 初始序列：按体积降序
    currentItems = sorted(items, key=lambda x: x.volume, reverse=True)
    bestSolution = simplePacking(container, currentItems)
    bestVolumeRate = bestSolution.volumeRate

    for _ in range(iterations):
        # 随机交换两个货物位置
        newItems = currentItems.copy()
        i, j = random.sample(range(len(newItems)), 2)
        newItems[i], newItems[j] = newItems[j], newItems[i]

        # 评估新序列
        newSolution = simplePacking(container, newItems)

        # 如果更好，更新（未来可扩展为模拟退火，使用randomRate）
        if newSolution.volumeRate > bestVolumeRate:
            bestVolumeRate = newSolution.volumeRate
            bestSolution = newSolution
            currentItems = newItems

    return bestSolution
