from typing import Dict, List, Optional, Tuple
from dataStructures import (
    ContainerLoad,
    ContainerInstance,
    GlobalConstraints,
    Item,
    Placement,
    PlacementFeedback
)

TOLERANCE = 1e-9
MAX_CANDIDATE_POSITIONS = 192

def _rect_overlap(
    first: Tuple[float, float, float, float],
    second: Tuple[float, float, float, float]
) -> Optional[Tuple[float, float, float, float]]:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    if x2 - x1 <= TOLERANCE or y2 - y1 <= TOLERANCE:
        return None
    return (x1, y1, x2, y2)

def _rect_area(rect: Tuple[float, float, float, float]) -> float:
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])

def _union_area(rectangles: List[Tuple[float, float, float, float]]) -> float:
    if not rectangles:
        return 0.0

    xValues = sorted({rect[0] for rect in rectangles} | {rect[2] for rect in rectangles})
    totalArea = 0.0
    for left, right in zip(xValues, xValues[1:]):
        if right - left <= TOLERANCE:
            continue

        intervals: List[Tuple[float, float]] = []
        for rect in rectangles:
            if rect[0] < right - TOLERANCE and rect[2] > left + TOLERANCE:
                intervals.append((rect[1], rect[3]))
        if not intervals:
            continue

        intervals.sort()
        mergedLength = 0.0
        currentStart, currentEnd = intervals[0]
        for start, end in intervals[1:]:
            if start <= currentEnd + TOLERANCE:
                currentEnd = max(currentEnd, end)
            else:
                mergedLength += currentEnd - currentStart
                currentStart, currentEnd = start, end
        mergedLength += currentEnd - currentStart
        totalArea += mergedLength * (right - left)

    return totalArea

def _base_rect(x: float, y: float, dx: float, dy: float) -> Tuple[float, float, float, float]:
    return (x, y, x + dx, y + dy)

def _get_item_lookup(items: List[Item]) -> Dict[int, Item]:
    return {item.id: item for item in items}

def _get_placed_dims(item: Item, placement: Placement) -> Tuple[float, float, float]:
    placedDims = item.get_oriented_dims(placement.rotation)
    if placedDims is None:
        raise ValueError(f"Invalid rotation {placement.rotation} for item {item.id}")
    return placedDims

def _placements_overlap(
    first: Tuple[float, float, float, float, float, float],
    second: Tuple[float, float, float, float, float, float]
) -> bool:
    separated = (
        first[0] + first[3] <= second[0] + TOLERANCE or
        second[0] + second[3] <= first[0] + TOLERANCE or
        first[1] + first[4] <= second[1] + TOLERANCE or
        second[1] + second[4] <= first[1] + TOLERANCE or
        first[2] + first[5] <= second[2] + TOLERANCE or
        second[2] + second[5] <= first[2] + TOLERANCE
    )
    return not separated

def _support_source_allowed(item: Item, supportItem: Item) -> bool:
    if "floor" in item.constraints.allowedSupportSources:
        pass
    for tag in supportItem.tags:
        if tag in item.constraints.allowedSupportSources:
            return True
    return False

def _compute_candidate_positions(
    load: ContainerLoad,
    itemLookup: Dict[int, Item]
) -> List[Tuple[float, float, float]]:
    candidatePositions = {(0.0, 0.0, 0.0)}

    for placement in load.placements:
        placedItem = itemLookup.get(placement.itemId)
        if placedItem is None:
            continue
        placedL, placedW, placedH = _get_placed_dims(placedItem, placement)

        candidatePositions.add((placement.x + placedL, placement.y, placement.z))
        candidatePositions.add((placement.x, placement.y + placedW, placement.z))
        candidatePositions.add((placement.x, placement.y, placement.z + placedH))
        candidatePositions.add((placement.x + placedL, placement.y, placement.z + placedH))
        candidatePositions.add((placement.x, placement.y + placedW, placement.z + placedH))

    sortedPositions = sorted(candidatePositions, key=lambda row: (row[2], row[1], row[0]))
    return sortedPositions[:MAX_CANDIDATE_POSITIONS]

def evaluatePlacement(
    load: ContainerLoad,
    item: Item,
    x: float,
    y: float,
    z: float,
    rotation: int,
    itemLookup: Dict[int, Item],
    globalConstraints: GlobalConstraints
) -> PlacementFeedback:
    if rotation not in item.constraints.allowedRotations:
        return PlacementFeedback(isFeasible=False, reasonCode="rotation_not_allowed")

    orientedDims = item.get_oriented_dims(rotation)
    if orientedDims is None:
        return PlacementFeedback(isFeasible=False, reasonCode="invalid_rotation")

    dx, dy, dz = orientedDims
    container = load.container

    if x < -TOLERANCE or y < -TOLERANCE or z < -TOLERANCE:
        return PlacementFeedback(isFeasible=False, reasonCode="negative_origin")

    topLimit = container.H - globalConstraints.minTopClearanceCm
    if x + dx > container.L + TOLERANCE:
        return PlacementFeedback(isFeasible=False, reasonCode="exceeds_length")
    if y + dy > container.W + TOLERANCE:
        return PlacementFeedback(isFeasible=False, reasonCode="exceeds_width")
    if z + dz > topLimit + TOLERANCE:
        return PlacementFeedback(isFeasible=False, reasonCode="top_clearance_violation")

    if load.totalWeight + item.weight > container.maxWeight + TOLERANCE:
        return PlacementFeedback(isFeasible=False, reasonCode="container_overweight")

    candidateBox = (x, y, z, dx, dy, dz)
    for existingPlacement in load.placements:
        existingItem = itemLookup.get(existingPlacement.itemId)
        if existingItem is None:
            continue
        existingDims = _get_placed_dims(existingItem, existingPlacement)
        existingBox = (
            existingPlacement.x,
            existingPlacement.y,
            existingPlacement.z,
            existingDims[0],
            existingDims[1],
            existingDims[2]
        )
        if _placements_overlap(candidateBox, existingBox):
            return PlacementFeedback(isFeasible=False, reasonCode="overlap_detected")

    topClearanceCm = container.H - (z + dz)
    if abs(z) <= TOLERANCE:
        return PlacementFeedback(
            isFeasible=True,
            reasonCode="",
            supportAreaRatio=1.0,
            bearingPressure=0.0,
            topClearanceCm=topClearanceCm,
            projectionContained=True,
            supportSource="floor",
            supportPlacementIds=[]
        )

    candidateBase = _base_rect(x, y, dx, dy)
    supportRects: List[Tuple[float, float, float, float]] = []
    supportPlacementIds: List[int] = []
    projectionContained = True

    for placement in load.placements:
        supportItem = itemLookup.get(placement.itemId)
        if supportItem is None:
            continue
        supportL, supportW, supportH = _get_placed_dims(supportItem, placement)
        supportTop = placement.z + supportH
        if abs(supportTop - z) > TOLERANCE:
            continue

        overlapRect = _rect_overlap(
            candidateBase,
            _base_rect(placement.x, placement.y, supportL, supportW)
        )
        if overlapRect is None:
            continue

        if not supportItem.constraints.canSupportOthers:
            continue
        if not _support_source_allowed(item, supportItem):
            continue

        supportRects.append(overlapRect)
        supportPlacementIds.append(placement.itemId)

        if supportItem.constraints.requiredSupportProjectionContainment:
            centerX = x + dx / 2.0
            centerY = y + dy / 2.0
            if not (
                placement.x - TOLERANCE <= centerX <= placement.x + supportL + TOLERANCE and
                placement.y - TOLERANCE <= centerY <= placement.y + supportW + TOLERANCE
            ):
                projectionContained = False

    if not supportRects:
        return PlacementFeedback(isFeasible=False, reasonCode="unsupported")

    supportedArea = _union_area(supportRects)
    baseArea = dx * dy
    supportAreaRatio = supportedArea / baseArea if baseArea > 0 else 0.0
    if supportAreaRatio + TOLERANCE < item.constraints.requiredSupportAreaRatio:
        return PlacementFeedback(
            isFeasible=False,
            reasonCode="support_area_insufficient",
            supportAreaRatio=supportAreaRatio
        )

    if not projectionContained:
        return PlacementFeedback(
            isFeasible=False,
            reasonCode="projection_containment_failed",
            supportAreaRatio=supportAreaRatio,
            projectionContained=False
        )

    bearingPressure = 0.0
    if supportedArea > TOLERANCE:
        supportedAreaM2 = supportedArea / 10000.0
        if supportedAreaM2 <= TOLERANCE:
            return PlacementFeedback(isFeasible=False, reasonCode="support_area_too_small")
        bearingPressure = item.weight / supportedAreaM2
        if bearingPressure > globalConstraints.maxBearingPressureKgPerM2 + TOLERANCE:
            return PlacementFeedback(
                isFeasible=False,
                reasonCode="bearing_pressure_exceeded",
                supportAreaRatio=supportAreaRatio,
                bearingPressure=bearingPressure
            )

    return PlacementFeedback(
        isFeasible=True,
        reasonCode="",
        supportAreaRatio=supportAreaRatio,
        bearingPressure=bearingPressure,
        topClearanceCm=topClearanceCm,
        projectionContained=projectionContained,
        supportSource="item",
        supportPlacementIds=supportPlacementIds
    )

def findBestPlacement(
    load: ContainerLoad,
    item: Item,
    allItems: List[Item],
    globalConstraints: GlobalConstraints
) -> Tuple[Optional[Placement], Optional[PlacementFeedback]]:
    itemLookup = _get_item_lookup(allItems)
    bestPlacement: Optional[Placement] = None
    bestFeedback: Optional[PlacementFeedback] = None

    for x, y, z in _compute_candidate_positions(load, itemLookup):
        for rotation in item.constraints.allowedRotations:
            feedback = evaluatePlacement(
                load=load,
                item=item,
                x=x,
                y=y,
                z=z,
                rotation=rotation,
                itemLookup=itemLookup,
                globalConstraints=globalConstraints
            )
            if not feedback.isFeasible:
                continue

            placement = Placement(
                itemId=item.id,
                x=x,
                y=y,
                z=z,
                rotation=rotation,
                supportSource=feedback.supportSource,
                supportInstanceIds=list(feedback.supportPlacementIds),
                supportAreaRatio=feedback.supportAreaRatio,
                bearingPressure=feedback.bearingPressure,
                topClearanceCm=feedback.topClearanceCm,
                projectionContained=feedback.projectionContained
            )
            if bestPlacement is None:
                bestPlacement = placement
                bestFeedback = feedback
                continue

            currentKey = (
                placement.z,
                placement.y,
                placement.x,
                -placement.supportAreaRatio,
                placement.bearingPressure
            )
            bestKey = (
                bestPlacement.z,
                bestPlacement.y,
                bestPlacement.x,
                -bestPlacement.supportAreaRatio,
                bestPlacement.bearingPressure
            )
            if currentKey < bestKey:
                bestPlacement = placement
                bestFeedback = feedback

    return bestPlacement, bestFeedback

def createEmptyLoad(container: ContainerInstance) -> ContainerLoad:
    return ContainerLoad(container=container)
