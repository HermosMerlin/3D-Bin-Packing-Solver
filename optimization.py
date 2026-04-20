import math
import random
from typing import List, Optional, Dict, Any, Callable, Tuple
from packingLogic import simplePacking
from dataStructures import Item, Container, PackingSolution

ALGORITHM_PARAM_KEYS: Dict[str, Tuple[str, ...]] = {
    "greedy_search": ("iterations",),
    "simulated_annealing": ("iterations", "initialTemp", "coolingRate", "minTemp")
}

def getAlgorithmParamKeys(algorithmType: str) -> Tuple[str, ...]:
    """Return ordered parameter names supported by the algorithm."""
    return ALGORITHM_PARAM_KEYS.get(algorithmType, tuple())

def filterAlgorithmParams(
    algorithmType: str,
    params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Keep only parameters that are meaningful to the selected algorithm."""
    params = params or {}
    allowedKeys = getAlgorithmParamKeys(algorithmType)
    if not allowedKeys:
        return dict(params)
    return {key: params[key] for key in allowedKeys if key in params}

def formatAlgorithmParams(
    algorithmType: str,
    params: Optional[Dict[str, Any]]
) -> str:
    """Format algorithm parameters for logs and reports."""
    filteredParams = filterAlgorithmParams(algorithmType, params)
    if not filteredParams:
        return "(default)"
    return ", ".join(f"{key}={value}" for key, value in filteredParams.items())

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
    模拟退火算法 (Simulated Annealing)
    通过允许以一定概率接受较差解，尝试跳出局部最优。
    """
    # 1. 初始化参数
    # 迭代总数建议在 100-500 之间以平衡时间与效果
    max_iterations = params.get("iterations", 50)
    # 初始温度建议 100.0
    initial_temp = params.get("initialTemp", 100.0)
    # 冷却率建议 0.9 - 0.99
    cooling_rate = params.get("coolingRate", 0.95)
    # 终止温度
    min_temp = params.get("minTemp", 0.01)

    # 2. 初始化状态
    # 初始序列：按体积降序
    current_items = sorted(items, key=lambda x: x.volume, reverse=True)
    current_solution = simplePacking(container, current_items)
    
    best_solution = current_solution
    best_items = current_items
    
    current_temp = initial_temp
    
    # 为了让 iterations 参数在退火中也有意义，我们将 iterations 作为退火的主循环步数
    for iteration in range(max_iterations):
        if current_temp < min_temp:
            break
            
        # 3. 产生邻域解（随机扰动：交换两个位置）
        new_items = current_items.copy()
        idx1, idx2 = random.sample(range(len(new_items)), 2)
        new_items[idx1], new_items[idx2] = new_items[idx2], new_items[idx1]
        
        # 4. 评估新解
        new_solution = simplePacking(container, new_items)
        
        # 计算能量差 (我们要最大化 volumeRate，所以能量 E = -volumeRate)
        # delta_e = new_energy - current_energy
        delta_e = current_solution.volumeRate - new_solution.volumeRate
        
        # 5. 接受准则 (Metropolis)
        # 如果新解更好，或者以一定概率接受较差解
        if delta_e < 0:
            # 找到更好的解，接受！
            current_solution = new_solution
            current_items = new_items
            
            # 更新全局最优
            if new_solution.volumeRate > best_solution.volumeRate:
                best_solution = new_solution
                best_items = new_items
        else:
            # 这是一个较差的解，计算接受概率
            # 概率 P = exp(-delta_e / T)，注意 delta_e 这里是正值
            # 为了防止数值溢出，delta_e 需要映射到一个合理的范围
            acceptance_prob = math.exp(-delta_e * 100 / current_temp)
            if random.random() < acceptance_prob:
                current_solution = new_solution
                current_items = new_items
        
        # 6. 降温
        current_temp *= cooling_rate

    return best_solution

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
