import random
from typing import List, Optional, Dict, Any, Callable
from packingLogic import simplePacking
from dataStructures import Item, Container, PackingSolution

def greedySearch(
    container: Container, 
    items: List[Item], 
    params: Dict[str, Any]
) -> PackingSolution:
    """
    基于贪心启发式的序列扰动搜索 (Greedy Heuristic with Sequence Shuffling)
    """
    iterations = params.get("iterations", 10)
    
    # 初始序列：按体积降序 (Classic First-Fit Decreasing)
    currentItems: List[Item] = sorted(items, key=lambda x: x.volume, reverse=True)
    bestSolution: PackingSolution = simplePacking(container, currentItems)
    bestVolumeRate: float = bestSolution.volumeRate

    for _ in range(iterations):
        # 随机交换两个货物位置（随机扰动）
        newItems: List[Item] = currentItems.copy()
        i, j = random.sample(range(len(newItems)), 2)
        newItems[i], newItems[j] = newItems[j], newItems[i]

        # 使用贪心策略评估新序列
        newSolution: PackingSolution = simplePacking(container, newItems)

        # 如果更好，更新
        if newSolution.volumeRate > bestVolumeRate:
            bestVolumeRate = newSolution.volumeRate
            bestSolution = newSolution
            currentItems = newItems

    return bestSolution

def simulatedAnnealing(
    container: Container, 
    items: List[Item], 
    params: Dict[str, Any]
) -> PackingSolution:
    """
    模拟退火算法 (Simulated Annealing) - 占位实现
    """
    # 暂时重用 greedySearch 的逻辑，但参数略有不同以示区分
    new_params = params.copy()
    new_params["iterations"] = params.get("iterations", 10) // 2
    return greedySearch(container, items, new_params)

# 算法注册表
ALGORITHMS: Dict[str, Callable] = {
    "greedy_search": greedySearch,
    "simulated_annealing": simulatedAnnealing
}

def optimizePacking(
    container: Container, 
    items: List[Item], 
    algorithmType: str = "greedy_search",
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
