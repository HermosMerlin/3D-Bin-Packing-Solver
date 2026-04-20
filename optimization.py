import math
import random
from typing import Any, Dict, List, Optional, Tuple
from dataStructures import (
    ContainerInstance,
    ContainerType,
    Item,
    ObjectiveRule,
    PlanMetrics,
    ProblemInstance,
    ShipmentPlan
)
from packingLogic import createEmptyLoad, findBestPlacement
from solutionValidator import computePlanMetrics

ALGORITHM_PARAM_KEYS: Dict[str, Tuple[str, ...]] = {
    "greedy_search": ("iterations",),
    "simulated_annealing": ("iterations", "initialTemp", "coolingRate", "minTemp")
}

def getAlgorithmParamKeys(algorithmType: str) -> Tuple[str, ...]:
    return ALGORITHM_PARAM_KEYS.get(algorithmType, tuple())

def filterAlgorithmParams(
    algorithmType: str,
    params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    params = params or {}
    allowedKeys = getAlgorithmParamKeys(algorithmType)
    if not allowedKeys:
        return dict(params)
    return {key: params[key] for key in allowedKeys if key in params}

def formatAlgorithmParams(
    algorithmType: str,
    params: Optional[Dict[str, Any]]
) -> str:
    filteredParams = filterAlgorithmParams(algorithmType, params)
    if not filteredParams:
        return "(default)"
    return ", ".join(f"{key}={value}" for key, value in filteredParams.items())

def _get_metric_value(metrics: PlanMetrics, metricName: str) -> float:
    value = getattr(metrics, metricName, None)
    if value is None:
        return 0.0
    return float(value)

def _build_objective_rules(problem: ProblemInstance) -> List[ObjectiveRule]:
    return [
        ObjectiveRule(problem.objective.primaryMetric, problem.objective.primaryOrder),
        *problem.objective.tieBreakers
    ]

def evaluateObjective(problem: ProblemInstance, plan: ShipmentPlan) -> PlanMetrics:
    metrics = computePlanMetrics(problem, plan)
    metrics.objectiveName = problem.objective.name or problem.objective.primaryMetric
    metrics.objectiveValue = _get_metric_value(metrics, problem.objective.primaryMetric)
    plan.metrics = metrics
    return metrics

def _rank_transform(value: float, order: str) -> float:
    return value if order == "max" else -value

def buildPlanRankKey(problem: ProblemInstance, plan: ShipmentPlan) -> Tuple[float, ...]:
    metrics = evaluateObjective(problem, plan)
    return tuple(
        _rank_transform(_get_metric_value(metrics, rule.metric), rule.order)
        for rule in _build_objective_rules(problem)
    )

def isPlanBetter(
    problem: ProblemInstance,
    candidate: ShipmentPlan,
    baseline: Optional[ShipmentPlan]
) -> bool:
    if baseline is None:
        return True
    return buildPlanRankKey(problem, candidate) > buildPlanRankKey(problem, baseline)

def _make_container_instance(containerType: ContainerType, instanceIndex: int) -> ContainerInstance:
    return ContainerInstance(
        instanceId=f"{containerType.typeId}_{instanceIndex:03d}",
        containerTypeId=containerType.typeId,
        L=containerType.L,
        W=containerType.W,
        H=containerType.H,
        maxWeight=containerType.maxWeight,
        tripCost=containerType.tripCost,
        metadata=dict(containerType.metadata)
    )

def _container_type_sort_key(
    problem: ProblemInstance,
    containerType: ContainerType,
    item: Item
) -> Tuple[float, ...]:
    objectiveMetric = problem.objective.primaryMetric
    if objectiveMetric == "totalCost":
        return (containerType.tripCost, containerType.volume, containerType.maxWeight)
    fillRate = item.volume / containerType.volume if containerType.volume > 0 else 0.0
    return (-fillRate, containerType.tripCost, containerType.volume)

def buildPlanFromOrder(
    problem: ProblemInstance,
    orderedItems: List[Item]
) -> ShipmentPlan:
    plan = ShipmentPlan()
    typeUsageCount: Dict[str, int] = {}

    for item in orderedItems:
        bestExistingChoice = None
        bestExistingScore = None

        for load in plan.containerLoads:
            placement, feedback = findBestPlacement(
                load=load,
                item=item,
                allItems=problem.items,
                globalConstraints=problem.globalConstraints
            )
            if placement is None or feedback is None:
                continue

            projectedFillRate = (
                (load.totalVolume + item.volume) / load.container.volume
                if load.container.volume > 0 else 0.0
            )
            score = (
                projectedFillRate,
                -load.weightRate,
                -load.totalWeight
            )
            if bestExistingScore is None or score > bestExistingScore:
                bestExistingScore = score
                bestExistingChoice = (load, placement)

        if bestExistingChoice is not None:
            chosenLoad, placement = bestExistingChoice
            chosenLoad.add_placement(item, placement)
            continue

        feasibleNewLoads = []
        for containerType in sorted(
            problem.containerTypes,
            key=lambda container: _container_type_sort_key(problem, container, item)
        ):
            currentUsage = typeUsageCount.get(containerType.typeId, 0)
            if containerType.maxInstances is not None and currentUsage >= containerType.maxInstances:
                continue

            containerInstance = _make_container_instance(containerType, currentUsage + 1)
            newLoad = createEmptyLoad(containerInstance)
            placement, feedback = findBestPlacement(
                load=newLoad,
                item=item,
                allItems=problem.items,
                globalConstraints=problem.globalConstraints
            )
            if placement is None or feedback is None:
                continue

            projectedFillRate = item.volume / containerType.volume if containerType.volume > 0 else 0.0
            score = (
                -containerType.tripCost if problem.objective.primaryMetric == "totalCost" else projectedFillRate,
                projectedFillRate,
                -containerType.tripCost
            )
            feasibleNewLoads.append((score, containerType, newLoad, placement))

        if not feasibleNewLoads:
            plan.unpackedItemIds.append(item.id)
            continue

        feasibleNewLoads.sort(key=lambda row: row[0], reverse=True)
        _, containerType, newLoad, placement = feasibleNewLoads[0]
        typeUsageCount[containerType.typeId] = typeUsageCount.get(containerType.typeId, 0) + 1
        newLoad.add_placement(item, placement)
        plan.containerLoads.append(newLoad)

    evaluateObjective(problem, plan)
    return plan

def greedySearch(
    problem: ProblemInstance,
    items: List[Item],
    params: Dict[str, Any]
) -> ShipmentPlan:
    iterations = int(params.get("iterations", 20))
    currentItems = sorted(items, key=lambda item: item.volume, reverse=True)
    bestPlan = buildPlanFromOrder(problem, currentItems)

    for _ in range(iterations):
        if len(currentItems) < 2:
            break
        newItems = currentItems.copy()
        indexA, indexB = random.sample(range(len(newItems)), 2)
        newItems[indexA], newItems[indexB] = newItems[indexB], newItems[indexA]
        candidatePlan = buildPlanFromOrder(problem, newItems)
        if isPlanBetter(problem, candidatePlan, bestPlan):
            bestPlan = candidatePlan
            currentItems = newItems

    return bestPlan

def _objective_energy(problem: ProblemInstance, plan: ShipmentPlan) -> float:
    metrics = evaluateObjective(problem, plan)
    primaryValue = _get_metric_value(metrics, problem.objective.primaryMetric)
    if problem.objective.primaryOrder == "max":
        return -primaryValue
    return primaryValue

def simulatedAnnealing(
    problem: ProblemInstance,
    items: List[Item],
    params: Dict[str, Any]
) -> ShipmentPlan:
    maxIterations = int(params.get("iterations", 50))
    initialTemp = float(params.get("initialTemp", 100.0))
    coolingRate = float(params.get("coolingRate", 0.95))
    minTemp = float(params.get("minTemp", 0.01))

    currentItems = sorted(items, key=lambda item: item.volume, reverse=True)
    currentPlan = buildPlanFromOrder(problem, currentItems)
    bestPlan = currentPlan
    currentTemp = initialTemp

    for _ in range(maxIterations):
        if currentTemp < minTemp or len(currentItems) < 2:
            break

        newItems = currentItems.copy()
        indexA, indexB = random.sample(range(len(newItems)), 2)
        newItems[indexA], newItems[indexB] = newItems[indexB], newItems[indexA]
        newPlan = buildPlanFromOrder(problem, newItems)

        deltaEnergy = _objective_energy(problem, newPlan) - _objective_energy(problem, currentPlan)
        if deltaEnergy < 0:
            currentPlan = newPlan
            currentItems = newItems
            if isPlanBetter(problem, newPlan, bestPlan):
                bestPlan = newPlan
        else:
            acceptanceProb = math.exp(-deltaEnergy / max(currentTemp, 1e-9))
            if random.random() < acceptanceProb:
                currentPlan = newPlan
                currentItems = newItems

        currentTemp *= coolingRate

    return bestPlan

ALGORITHMS = {
    "greedy_search": greedySearch,
    "simulated_annealing": simulatedAnnealing
}

def optimizePacking(
    problem: ProblemInstance,
    algorithmType: str = "greedy_search",
    params: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None
) -> ShipmentPlan:
    if seed is not None:
        random.seed(seed)

    params = params or {}
    algorithm = ALGORITHMS.get(algorithmType)
    if algorithm is None:
        raise ValueError(f"未知的算法类型: {algorithmType}")

    return algorithm(problem, problem.items, params)
