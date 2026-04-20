from typing import Any, Dict, List
from dataStructures import ContainerLoad, PlanMetrics, ProblemInstance, ShipmentPlan
from packingLogic import createEmptyLoad, evaluatePlacement

VALIDATION_TOLERANCE = 1e-9

def buildPlacementRecords(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> List[Dict[str, Any]]:
    itemById = {item.id: item for item in problem.items}
    records: List[Dict[str, Any]] = []

    for containerIndex, load in enumerate(plan.containerLoads, start=1):
        for placementOrder, placement in enumerate(load.placements, start=1):
            item = itemById.get(placement.itemId)
            placedDims = (
                item.get_oriented_dims(placement.rotation)
                if item is not None else None
            )
            records.append({
                "containerIndex": containerIndex,
                "containerInstanceId": load.container.instanceId,
                "containerTypeId": load.container.containerTypeId,
                "placementOrder": placementOrder,
                "itemId": placement.itemId,
                "item": item,
                "itemTypeId": item.typeId if item is not None else None,
                "tags": list(item.tags) if item is not None else [],
                "x": placement.x,
                "y": placement.y,
                "z": placement.z,
                "rotation": placement.rotation,
                "placedDims": placedDims,
                "supportSource": placement.supportSource,
                "supportInstanceIds": list(placement.supportInstanceIds),
                "supportAreaRatio": placement.supportAreaRatio,
                "bearingPressure": placement.bearingPressure,
                "topClearanceCm": placement.topClearanceCm,
                "projectionContained": placement.projectionContained
            })

    return records

def computePlanMetrics(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> PlanMetrics:
    totalCost = sum(load.container.tripCost for load in plan.containerLoads if load.placements)
    packedVolume = sum(load.totalVolume for load in plan.containerLoads)
    packedWeight = sum(load.totalWeight for load in plan.containerLoads)
    totalContainerVolume = sum(load.container.volume for load in plan.containerLoads if load.placements)
    fillRates = [load.fillRate for load in plan.containerLoads if load.placements]
    weightRates = [load.weightRate for load in plan.containerLoads if load.placements]
    packedItemCount = sum(len(load.placements) for load in plan.containerLoads)
    usedTypeIds = {
        load.container.containerTypeId
        for load in plan.containerLoads
        if load.placements
    }

    metrics = PlanMetrics(
        totalCost=totalCost,
        usedContainerCount=sum(1 for load in plan.containerLoads if load.placements),
        usedContainerTypeCount=len(usedTypeIds),
        packedItemCount=packedItemCount,
        unpackedItemCount=len(plan.unpackedItemIds),
        packedVolume=packedVolume,
        packedWeight=packedWeight,
        totalContainerVolume=totalContainerVolume,
        totalFillRate=(
            packedVolume / totalContainerVolume if totalContainerVolume > 0 else 0.0
        ),
        avgContainerFillRate=(
            sum(fillRates) / len(fillRates) if fillRates else 0.0
        ),
        maxContainerFillRate=max(fillRates) if fillRates else 0.0,
        avgContainerWeightRate=(
            sum(weightRates) / len(weightRates) if weightRates else 0.0
        ),
        objectiveName=problem.objective.name or problem.objective.primaryMetric,
        objectiveValue=0.0
    )
    objectiveValue = getattr(metrics, problem.objective.primaryMetric, 0.0)
    metrics.objectiveValue = float(objectiveValue)
    return metrics

def validateShipmentPlan(
    problem: ProblemInstance,
    plan: ShipmentPlan
) -> Dict[str, Any]:
    errors: List[str] = []
    itemById = {item.id: item for item in problem.items}
    placedItemIds = set()
    expectedItemIds = set(itemById.keys())
    containerRows: List[Dict[str, Any]] = []

    for containerIndex, load in enumerate(plan.containerLoads, start=1):
        validationLoad: ContainerLoad = createEmptyLoad(load.container)

        for placementOrder, placement in enumerate(load.placements, start=1):
            item = itemById.get(placement.itemId)
            if item is None:
                errors.append(
                    f"Container {containerIndex}: unknown item id {placement.itemId}"
                )
                continue
            if placement.itemId in placedItemIds:
                errors.append(f"Duplicate placement detected for item {placement.itemId}")
                continue

            feedback = evaluatePlacement(
                load=validationLoad,
                item=item,
                x=placement.x,
                y=placement.y,
                z=placement.z,
                rotation=placement.rotation,
                itemLookup=itemById,
                globalConstraints=problem.globalConstraints
            )
            if not feedback.isFeasible:
                errors.append(
                    f"Container {containerIndex}, placement {placementOrder}, item {placement.itemId}: "
                    f"{feedback.reasonCode}"
                )
                continue

            validationLoad.add_placement(item, placement)
            placedItemIds.add(placement.itemId)

        containerRows.append({
            "containerIndex": containerIndex,
            "containerInstanceId": load.container.instanceId,
            "containerTypeId": load.container.containerTypeId,
            "tripCost": load.container.tripCost,
            "placedCount": len(load.placements),
            "fillRate": validationLoad.fillRate,
            "weightRate": validationLoad.weightRate,
            "totalWeight": validationLoad.totalWeight,
            "totalVolume": validationLoad.totalVolume
        })

        if abs(validationLoad.totalWeight - load.totalWeight) > VALIDATION_TOLERANCE:
            errors.append(
                f"Container {containerIndex}: stored totalWeight mismatch "
                f"{load.totalWeight} vs {validationLoad.totalWeight}"
            )
        if abs(validationLoad.totalVolume - load.totalVolume) > VALIDATION_TOLERANCE:
            errors.append(
                f"Container {containerIndex}: stored totalVolume mismatch "
                f"{load.totalVolume} vs {validationLoad.totalVolume}"
            )

    declaredUnpacked = set(plan.unpackedItemIds)
    if placedItemIds & declaredUnpacked:
        errors.append("Some items are both placed and marked unpacked")
    if placedItemIds | declaredUnpacked != expectedItemIds:
        missingIds = sorted(expectedItemIds - (placedItemIds | declaredUnpacked))
        if missingIds:
            errors.append(f"Items missing from plan accounting: {missingIds}")

    metrics = computePlanMetrics(problem, plan)
    return {
        "isValid": len(errors) == 0,
        "errors": errors,
        "containerRows": containerRows,
        "placementRecords": buildPlacementRecords(problem, plan),
        "metrics": metrics
    }
