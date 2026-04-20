import math
import random
from typing import Any, Dict, List, Optional, Tuple
from dataStructures import (
    ContainerLoad,
    ContainerInstance,
    ContainerType,
    Item,
    Placement,
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

def _get_objective_name(problem: ProblemInstance) -> str:
    return problem.objective.name or problem.objective.primaryMetric

def _plan_metrics_ready(problem: ProblemInstance, plan: ShipmentPlan) -> bool:
    metrics = plan.metrics
    return (
        metrics is not None and
        metrics.objectiveName == _get_objective_name(problem) and
        metrics.usedContainerCount == sum(1 for load in plan.containerLoads if load.placements) and
        metrics.packedItemCount == sum(len(load.placements) for load in plan.containerLoads) and
        metrics.unpackedItemCount == len(plan.unpackedItemIds)
    )

def evaluateObjective(problem: ProblemInstance, plan: ShipmentPlan) -> PlanMetrics:
    if _plan_metrics_ready(problem, plan):
        return plan.metrics
    metrics = computePlanMetrics(problem, plan)
    metrics.objectiveName = _get_objective_name(problem)
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

def _clone_container_instance(container: ContainerInstance) -> ContainerInstance:
    return ContainerInstance(
        instanceId=container.instanceId,
        containerTypeId=container.containerTypeId,
        L=container.L,
        W=container.W,
        H=container.H,
        maxWeight=container.maxWeight,
        tripCost=container.tripCost,
        metadata=dict(container.metadata)
    )

def _clone_placement(placement: Placement) -> Placement:
    return Placement(
        itemId=placement.itemId,
        x=placement.x,
        y=placement.y,
        z=placement.z,
        rotation=placement.rotation,
        supportSource=placement.supportSource,
        supportInstanceIds=list(placement.supportInstanceIds),
        supportAreaRatio=placement.supportAreaRatio,
        bearingPressure=placement.bearingPressure,
        topClearanceCm=placement.topClearanceCm,
        projectionContained=placement.projectionContained
    )

def _clone_container_load(load: ContainerLoad) -> ContainerLoad:
    return ContainerLoad(
        container=_clone_container_instance(load.container),
        placements=[_clone_placement(placement) for placement in load.placements],
        totalVolume=load.totalVolume,
        totalWeight=load.totalWeight,
        fillRate=load.fillRate,
        weightRate=load.weightRate
    )

def _clone_plan(plan: ShipmentPlan) -> ShipmentPlan:
    clonedMetrics = PlanMetrics.from_dict(plan.metrics.to_dict()) if plan.metrics is not None else PlanMetrics()
    return ShipmentPlan(
        containerLoads=[_clone_container_load(load) for load in plan.containerLoads],
        unpackedItemIds=list(plan.unpackedItemIds),
        metrics=clonedMetrics
    )

def _get_problem_item_lookup(problem: ProblemInstance) -> Dict[int, Item]:
    return {item.id: item for item in problem.items}

def _recalculate_load_totals(
    load: ContainerLoad,
    itemLookup: Dict[int, Item]
) -> None:
    load.totalVolume = 0.0
    load.totalWeight = 0.0
    for placement in load.placements:
        item = itemLookup.get(placement.itemId)
        if item is None:
            continue
        load.totalVolume += item.volume
        load.totalWeight += item.weight
    load.recalculate_rates()

def _remove_item_from_load(
    load: ContainerLoad,
    itemId: int,
    itemLookup: Dict[int, Item]
) -> Optional[Placement]:
    for index, placement in enumerate(load.placements):
        if placement.itemId == itemId:
            removed = load.placements.pop(index)
            _recalculate_load_totals(load, itemLookup)
            return removed
    return None

def _pack_items_into_container(
    problem: ProblemInstance,
    container: ContainerInstance,
    orderedItems: List[Item]
) -> Optional[ContainerLoad]:
    load = createEmptyLoad(container)
    for item in orderedItems:
        placement, _ = findBestPlacement(
            load=load,
            item=item,
            allItems=problem.items,
            globalConstraints=problem.globalConstraints
        )
        if placement is None:
            return None
        load.add_placement(item, placement)
    return load

def _cleanup_empty_loads(plan: ShipmentPlan) -> None:
    plan.containerLoads = [load for load in plan.containerLoads if load.placements]

def _choose_target_load_indices(
    problem: ProblemInstance,
    plan: ShipmentPlan,
    sourceIndex: int
) -> List[int]:
    if problem.objective.primaryMetric == "totalCost":
        return sorted(
            [index for index in range(len(plan.containerLoads)) if index != sourceIndex],
            key=lambda index: (
                -plan.containerLoads[index].fillRate,
                plan.containerLoads[index].container.tripCost
            )
        )
    return sorted(
        [index for index in range(len(plan.containerLoads)) if index != sourceIndex],
        key=lambda index: (
            plan.containerLoads[index].fillRate,
            plan.containerLoads[index].container.tripCost
        ),
        reverse=True
    )

def _try_relocate_item(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> Optional[ShipmentPlan]:
    if not plan.containerLoads:
        return None

    itemLookup = _get_problem_item_lookup(problem)
    candidate = _clone_plan(plan)
    nonEmptyIndices = [index for index, load in enumerate(candidate.containerLoads) if load.placements]
    if len(nonEmptyIndices) < 1:
        return None

    sourceIndex = random.choice(nonEmptyIndices)
    sourceLoad = candidate.containerLoads[sourceIndex]
    sourcePlacement = random.choice(sourceLoad.placements)
    item = itemLookup.get(sourcePlacement.itemId)
    if item is None:
        return None

    removed = _remove_item_from_load(sourceLoad, sourcePlacement.itemId, itemLookup)
    if removed is None:
        return None

    for targetIndex in _choose_target_load_indices(problem, candidate, sourceIndex):
        targetLoad = candidate.containerLoads[targetIndex]
        placement, _ = findBestPlacement(
            load=targetLoad,
            item=item,
            allItems=problem.items,
            globalConstraints=problem.globalConstraints
        )
        if placement is None:
            continue
        targetLoad.add_placement(item, placement)
        _cleanup_empty_loads(candidate)
        candidate.unpackedItemIds = []
        candidate.metrics = PlanMetrics()
        evaluateObjective(problem, candidate)
        return candidate

    # Rollback if no target accepted the item.
    sourceLoad.placements.append(removed)
    _recalculate_load_totals(sourceLoad, itemLookup)
    return None

def _try_change_container_type(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> Optional[ShipmentPlan]:
    if not plan.containerLoads:
        return None

    candidate = _clone_plan(plan)
    itemLookup = _get_problem_item_lookup(problem)
    targetIndex = random.randrange(len(candidate.containerLoads))
    load = candidate.containerLoads[targetIndex]
    if not load.placements:
        return None

    loadItems = [
        itemLookup[placement.itemId]
        for placement in load.placements
        if placement.itemId in itemLookup
    ]
    currentTypeId = load.container.containerTypeId
    alternatives = [
        containerType for containerType in problem.containerTypes
        if containerType.typeId != currentTypeId
    ]
    if not alternatives:
        return None

    if problem.objective.primaryMetric == "totalCost":
        alternatives.sort(key=lambda containerType: containerType.tripCost)
    else:
        alternatives.sort(key=lambda containerType: containerType.volume)

    for containerType in alternatives:
        replacement = _make_container_instance(
            containerType,
            targetIndex + 1
        )
        repackedLoad = _pack_items_into_container(problem, replacement, loadItems)
        if repackedLoad is None:
            continue
        candidate.containerLoads[targetIndex] = repackedLoad
        candidate.metrics = PlanMetrics()
        evaluateObjective(problem, candidate)
        return candidate

    return None

def _try_close_container(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> Optional[ShipmentPlan]:
    if len(plan.containerLoads) <= 1:
        return None

    itemLookup = _get_problem_item_lookup(problem)
    candidate = _clone_plan(plan)
    nonEmptyLoads = [
        (index, load) for index, load in enumerate(candidate.containerLoads)
        if load.placements
    ]
    if len(nonEmptyLoads) <= 1:
        return None

    if problem.objective.primaryMetric == "totalCost":
        nonEmptyLoads.sort(
            key=lambda row: (
                row[1].fillRate,
                -row[1].container.tripCost
            )
        )
    else:
        nonEmptyLoads.sort(key=lambda row: row[1].fillRate)

    sourceIndex, sourceLoad = nonEmptyLoads[0]
    sourceItems = [
        itemLookup[placement.itemId]
        for placement in sourceLoad.placements
        if placement.itemId in itemLookup
    ]
    sourceItems.sort(key=lambda item: item.volume, reverse=True)

    remainingLoads = [
        load for index, load in enumerate(candidate.containerLoads)
        if index != sourceIndex
    ]
    if not remainingLoads:
        return None

    for item in sourceItems:
        placed = False
        targetIndices = sorted(
            range(len(remainingLoads)),
            key=lambda idx: (
                -remainingLoads[idx].fillRate,
                remainingLoads[idx].container.tripCost
            )
        )
        for targetIndex in targetIndices:
            targetLoad = remainingLoads[targetIndex]
            placement, _ = findBestPlacement(
                load=targetLoad,
                item=item,
                allItems=problem.items,
                globalConstraints=problem.globalConstraints
            )
            if placement is None:
                continue
            targetLoad.add_placement(item, placement)
            placed = True
            break
        if not placed:
            return None

    candidate.containerLoads = remainingLoads
    _cleanup_empty_loads(candidate)
    candidate.metrics = PlanMetrics()
    evaluateObjective(problem, candidate)
    return candidate

def _generate_neighbor_plan(
    problem: ProblemInstance,
    currentPlan: ShipmentPlan,
    currentItems: List[Item]
) -> Tuple[ShipmentPlan, Optional[List[Item]], str]:
    actions = ["swap_order", "relocate_item", "change_container_type", "close_container"]
    action = random.choice(actions)

    if action == "swap_order" and len(currentItems) >= 2:
        newItems = currentItems.copy()
        indexA, indexB = random.sample(range(len(newItems)), 2)
        newItems[indexA], newItems[indexB] = newItems[indexB], newItems[indexA]
        return buildPlanFromOrder(problem, newItems), newItems, action

    if action == "relocate_item":
        candidate = _try_relocate_item(problem, currentPlan)
        if candidate is not None:
            return candidate, None, action

    if action == "change_container_type":
        candidate = _try_change_container_type(problem, currentPlan)
        if candidate is not None:
            return candidate, None, action

    if action == "close_container":
        candidate = _try_close_container(problem, currentPlan)
        if candidate is not None:
            return candidate, None, action

    return currentPlan, None, "no_op"

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
    failedPlacementCache: Dict[Tuple[int, int, str], bool] = {}

    for item in orderedItems:
        bestExistingChoice = None
        bestExistingScore = None

        for loadIndex, load in enumerate(plan.containerLoads):
            cacheKey = (loadIndex, len(load.placements), item.typeId)
            if failedPlacementCache.get(cacheKey):
                continue
            placement, feedback = findBestPlacement(
                load=load,
                item=item,
                allItems=problem.items,
                globalConstraints=problem.globalConstraints
            )
            if placement is None or feedback is None:
                failedPlacementCache[cacheKey] = True
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
            failedPlacementCache.clear()
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
        failedPlacementCache.clear()

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
    currentPlan = bestPlan

    for _ in range(iterations):
        candidatePlan, newItems, action = _generate_neighbor_plan(
            problem,
            currentPlan,
            currentItems
        )
        if action == "no_op":
            continue
        if isPlanBetter(problem, candidatePlan, bestPlan):
            bestPlan = candidatePlan
        if isPlanBetter(problem, candidatePlan, currentPlan):
            currentPlan = candidatePlan
            if newItems is not None:
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
        if currentTemp < minTemp:
            break

        newPlan, newItems, action = _generate_neighbor_plan(
            problem,
            currentPlan,
            currentItems
        )
        if action == "no_op":
            currentTemp *= coolingRate
            continue

        deltaEnergy = _objective_energy(problem, newPlan) - _objective_energy(problem, currentPlan)
        if deltaEnergy < 0:
            currentPlan = newPlan
            if newItems is not None:
                currentItems = newItems
            if isPlanBetter(problem, newPlan, bestPlan):
                bestPlan = newPlan
        else:
            acceptanceProb = math.exp(-deltaEnergy / max(currentTemp, 1e-9))
            if random.random() < acceptanceProb:
                currentPlan = newPlan
                if newItems is not None:
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
