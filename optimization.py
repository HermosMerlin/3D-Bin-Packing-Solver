import random
from typing import List, Optional
from packingLogic import simplePacking
from dataStructures import Item, Container, PackingSolution

def optimizePacking(
    container: Container, 
    items: List[Item], 
    iterations: int = 100, 
    randomRate: float = 0.2, 
    seed: Optional[int] = None
) -> PackingSolution:
    """
    优化装箱方案
    :param randomRate: 随机率（接受较差解的概率，用于扩展）
    :param seed: 随机种子，用于复现结果
    """
    if seed is not None:
        random.seed(seed)

    # 初始序列：按体积降序
    currentItems: List[Item] = sorted(items, key=lambda x: x.volume, reverse=True)
    bestSolution: PackingSolution = simplePacking(container, currentItems)
    bestVolumeRate: float = bestSolution.volumeRate

    for _ in range(iterations):
        # 随机交换两个货物位置
        newItems: List[Item] = currentItems.copy()
        i, j = random.sample(range(len(newItems)), 2)
        newItems[i], newItems[j] = newItems[j], newItems[i]

        # 评估新序列
        newSolution: PackingSolution = simplePacking(container, newItems)

        # 如果更好，更新
        if newSolution.volumeRate > bestVolumeRate:
            bestVolumeRate = newSolution.volumeRate
            bestSolution = newSolution
            currentItems = newItems

    return bestSolution
