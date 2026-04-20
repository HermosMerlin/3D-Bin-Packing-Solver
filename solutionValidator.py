from typing import Dict, Any, List, Optional, Tuple
from dataStructures import Item, Container, PackingSolution

ROTATION_DIMENSIONS: Dict[int, Tuple[str, str, str]] = {
    0: ("l", "w", "h"),
    1: ("l", "h", "w"),
    2: ("w", "l", "h"),
    3: ("w", "h", "l"),
    4: ("h", "l", "w"),
    5: ("h", "w", "l")
}

VALIDATION_TOLERANCE = 1e-9
MAX_OVERLAP_ERRORS = 20

def getRotationDimensions(item: Item, rotation: int) -> Optional[Tuple[float, float, float]]:
    """Return oriented dimensions for a rotation id, or None if invalid."""
    axisOrder = ROTATION_DIMENSIONS.get(rotation)
    if axisOrder is None:
        return None
    return tuple(getattr(item, axis) for axis in axisOrder)

def buildPlacementRecords(
    items: List[Item],
    solution: PackingSolution
) -> List[Dict[str, Any]]:
    """Expand placements into records that are easier to validate and export."""
    itemById = {item.id: item for item in items}
    records: List[Dict[str, Any]] = []

    for placementOrder, (itemId, x, y, z, rotation) in enumerate(solution.placedItems, start=1):
        item = itemById.get(itemId)
        placedDims = getRotationDimensions(item, rotation) if item is not None else None
        records.append({
            "placementOrder": placementOrder,
            "itemId": itemId,
            "item": item,
            "typeId": getattr(item, "typeId", None) if item is not None else None,
            "x": x,
            "y": y,
            "z": z,
            "rotation": rotation,
            "placedDims": placedDims
        })

    return records

def _boxesOverlap(
    first: Dict[str, Any],
    second: Dict[str, Any],
    tolerance: float
) -> bool:
    firstL, firstW, firstH = first["placedDims"]
    secondL, secondW, secondH = second["placedDims"]

    separated = (
        first["x"] + firstL <= second["x"] + tolerance or
        second["x"] + secondL <= first["x"] + tolerance or
        first["y"] + firstW <= second["y"] + tolerance or
        second["y"] + secondW <= first["y"] + tolerance or
        first["z"] + firstH <= second["z"] + tolerance or
        second["z"] + secondH <= first["z"] + tolerance
    )
    return not separated

def validatePackingSolution(
    container: Container,
    items: List[Item],
    solution: PackingSolution,
    tolerance: float = VALIDATION_TOLERANCE
) -> Dict[str, Any]:
    """Validate boundary, uniqueness, overlap, and aggregate metrics."""
    errors: List[str] = []
    records = buildPlacementRecords(items, solution)
    seenItemIds = set()
    accumulatedWeight = 0.0
    accumulatedVolume = 0.0

    for record in records:
        item = record["item"]
        itemId = record["itemId"]

        if item is None:
            errors.append(f"Unknown item id: {itemId}")
            continue

        if itemId in seenItemIds:
            errors.append(f"Duplicate placement detected for item {itemId}")
        seenItemIds.add(itemId)

        if record["placedDims"] is None:
            errors.append(f"Invalid rotation {record['rotation']} for item {itemId}")
            continue

        placedL, placedW, placedH = record["placedDims"]
        x, y, z = record["x"], record["y"], record["z"]

        if x < -tolerance or y < -tolerance or z < -tolerance:
            errors.append(
                f"Negative origin for item {itemId}: ({x}, {y}, {z})"
            )

        if x + placedL > container.L + tolerance:
            errors.append(f"Item {itemId} exceeds container length bound")
        if y + placedW > container.W + tolerance:
            errors.append(f"Item {itemId} exceeds container width bound")
        if z + placedH > container.H + tolerance:
            errors.append(f"Item {itemId} exceeds container height bound")

        accumulatedWeight += item.weight
        accumulatedVolume += item.volume

    overlapErrors = 0
    for i, first in enumerate(records):
        if first["item"] is None or first["placedDims"] is None:
            continue
        for second in records[i + 1:]:
            if second["item"] is None or second["placedDims"] is None:
                continue
            if _boxesOverlap(first, second, tolerance):
                overlapErrors += 1
                errors.append(
                    f"Overlap detected between item {first['itemId']} and item {second['itemId']}"
                )
                if overlapErrors >= MAX_OVERLAP_ERRORS:
                    errors.append("Too many overlap errors; remaining overlaps omitted")
                    break
        if overlapErrors >= MAX_OVERLAP_ERRORS:
            break

    if accumulatedWeight > container.maxWeight + tolerance:
        errors.append(
            f"Total weight {accumulatedWeight} exceeds container limit {container.maxWeight}"
        )

    if abs(solution.totalWeight - accumulatedWeight) > tolerance:
        errors.append(
            f"Stored totalWeight {solution.totalWeight} does not match placement sum {accumulatedWeight}"
        )

    if abs(solution.totalVolume - accumulatedVolume) > tolerance:
        errors.append(
            f"Stored totalVolume {solution.totalVolume} does not match placement sum {accumulatedVolume}"
        )

    expectedVolumeRate = accumulatedVolume / container.volume if container.volume > 0 else 0.0
    expectedWeightRate = accumulatedWeight / container.maxWeight if container.maxWeight > 0 else 0.0

    if abs(solution.volumeRate - expectedVolumeRate) > 1e-6:
        errors.append(
            f"Stored volumeRate {solution.volumeRate} does not match computed value {expectedVolumeRate}"
        )

    if abs(solution.weightRate - expectedWeightRate) > 1e-6:
        errors.append(
            f"Stored weightRate {solution.weightRate} does not match computed value {expectedWeightRate}"
        )

    return {
        "isValid": len(errors) == 0,
        "errors": errors,
        "placementRecords": records,
        "computedTotalWeight": accumulatedWeight,
        "computedTotalVolume": accumulatedVolume
    }
