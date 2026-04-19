import random
from typing import List, Optional, Dict, Any, Callable
from packingLogic import simplePacking
from dataStructures import Item, Container, PackingSolution

def hillClimbing(
    container: Container, 
    items: List[Item], 
    params: Dict[str, Any]
) -> PackingSolution:
    """
    随机爬山算法（原方案逻辑）
    """
    iterations = params.get("iterations", 100)
    
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

# 算法注册表
ALGORITHMS: Dict[str, Callable] = {
    "hill_climbing": hillClimbing
}

def optimizePacking(
    container: Container, 
    items: List[Item], 
    algorithmType: str = "hill_climbing",
    params: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None
) -> PackingSolution:
    """
    优化算法统一入口（策略模式）
    """
    if seed is not None:
        random.seed(seed)

    if params is None:
        params = {}

    alg_func = ALGORITHMS.get(algorithmType)
    if not alg_func:
        raise ValueError(f"未知的算法类型: {algorithmType}")

    return alg_func(container, items, params)
