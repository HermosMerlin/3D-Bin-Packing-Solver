from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ROTATIONS: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
DEFAULT_SUPPORT_SOURCES: Tuple[str, ...] = ("floor", "standard", "oriented")

ROTATION_DIMENSIONS: Dict[int, Tuple[str, str, str]] = {
    0: ("l", "w", "h"),
    1: ("l", "h", "w"),
    2: ("w", "l", "h"),
    3: ("w", "h", "l"),
    4: ("h", "l", "w"),
    5: ("h", "w", "l")
}

def normalizeRotationList(rotations: Optional[List[int]]) -> List[int]:
    if not rotations:
        return list(DEFAULT_ROTATIONS)
    normalized = [
        int(rotation) for rotation in rotations
        if int(rotation) in ROTATION_DIMENSIONS
    ]
    return normalized if normalized else list(DEFAULT_ROTATIONS)

@dataclass
class ItemConstraints:
    allowedRotations: List[int] = field(default_factory=lambda: list(DEFAULT_ROTATIONS))
    canSupportOthers: bool = True
    allowedSupportSources: List[str] = field(
        default_factory=lambda: list(DEFAULT_SUPPORT_SOURCES)
    )
    requiredSupportAreaRatio: float = 0.0
    requiredSupportProjectionContainment: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowedRotations": list(self.allowedRotations),
            "canSupportOthers": self.canSupportOthers,
            "allowedSupportSources": list(self.allowedSupportSources),
            "requiredSupportAreaRatio": self.requiredSupportAreaRatio,
            "requiredSupportProjectionContainment": self.requiredSupportProjectionContainment
        }

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "ItemConstraints":
        data = data or {}
        return ItemConstraints(
            allowedRotations=normalizeRotationList(data.get("allowedRotations")),
            canSupportOthers=bool(data.get("canSupportOthers", True)),
            allowedSupportSources=list(
                data.get("allowedSupportSources", DEFAULT_SUPPORT_SOURCES)
            ),
            requiredSupportAreaRatio=float(data.get("requiredSupportAreaRatio", 0.0)),
            requiredSupportProjectionContainment=bool(
                data.get("requiredSupportProjectionContainment", False)
            )
        )

@dataclass
class ItemType:
    typeId: str
    l: float
    w: float
    h: float
    weight: float
    count: int
    tags: List[str] = field(default_factory=list)
    constraints: ItemConstraints = field(default_factory=ItemConstraints)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume(self) -> float:
        return self.l * self.w * self.h

    def to_dict(self) -> Dict[str, Any]:
        return {
            "typeId": self.typeId,
            "l": self.l,
            "w": self.w,
            "h": self.h,
            "weight": self.weight,
            "count": self.count,
            "tags": list(self.tags),
            "constraints": self.constraints.to_dict(),
            "metadata": dict(self.metadata)
        }

@dataclass
class Item:
    id: int
    typeId: str
    l: float
    w: float
    h: float
    weight: float
    tags: List[str] = field(default_factory=list)
    constraints: ItemConstraints = field(default_factory=ItemConstraints)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume(self) -> float:
        return self.l * self.w * self.h

    def get_oriented_dims(self, rotation: int) -> Optional[Tuple[float, float, float]]:
        axisOrder = ROTATION_DIMENSIONS.get(rotation)
        if axisOrder is None:
            return None
        return tuple(getattr(self, axis) for axis in axisOrder)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "typeId": self.typeId,
            "l": self.l,
            "w": self.w,
            "h": self.h,
            "weight": self.weight,
            "tags": list(self.tags),
            "constraints": self.constraints.to_dict(),
            "metadata": dict(self.metadata)
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Item":
        return Item(
            id=int(data["id"]),
            typeId=str(data["typeId"]),
            l=float(data["l"]),
            w=float(data["w"]),
            h=float(data["h"]),
            weight=float(data["weight"]),
            tags=list(data.get("tags", [])),
            constraints=ItemConstraints.from_dict(data.get("constraints")),
            metadata=dict(data.get("metadata", {}))
        )

@dataclass
class ContainerType:
    typeId: str
    L: float
    W: float
    H: float
    maxWeight: float
    tripCost: float
    maxInstances: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume(self) -> float:
        return self.L * self.W * self.H

    @property
    def aspectRatio(self) -> float:
        shortest = min(self.L, self.W, self.H)
        if shortest <= 0:
            return 0.0
        return max(self.L, self.W, self.H) / shortest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "typeId": self.typeId,
            "L": self.L,
            "W": self.W,
            "H": self.H,
            "maxWeight": self.maxWeight,
            "tripCost": self.tripCost,
            "maxInstances": self.maxInstances,
            "metadata": dict(self.metadata)
        }

@dataclass
class ContainerInstance:
    instanceId: str
    containerTypeId: str
    L: float
    W: float
    H: float
    maxWeight: float
    tripCost: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume(self) -> float:
        return self.L * self.W * self.H

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instanceId": self.instanceId,
            "containerTypeId": self.containerTypeId,
            "L": self.L,
            "W": self.W,
            "H": self.H,
            "maxWeight": self.maxWeight,
            "tripCost": self.tripCost,
            "metadata": dict(self.metadata)
        }

@dataclass
class Placement:
    itemId: int
    x: float
    y: float
    z: float
    rotation: int
    supportSource: str = "floor"
    supportInstanceIds: List[int] = field(default_factory=list)
    supportAreaRatio: float = 0.0
    bearingPressure: float = 0.0
    topClearanceCm: float = 0.0
    projectionContained: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "itemId": self.itemId,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "rotation": self.rotation,
            "supportSource": self.supportSource,
            "supportInstanceIds": list(self.supportInstanceIds),
            "supportAreaRatio": self.supportAreaRatio,
            "bearingPressure": self.bearingPressure,
            "topClearanceCm": self.topClearanceCm,
            "projectionContained": self.projectionContained
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Placement":
        return Placement(
            itemId=int(data["itemId"]),
            x=float(data["x"]),
            y=float(data["y"]),
            z=float(data["z"]),
            rotation=int(data["rotation"]),
            supportSource=str(data.get("supportSource", "floor")),
            supportInstanceIds=[int(value) for value in data.get("supportInstanceIds", [])],
            supportAreaRatio=float(data.get("supportAreaRatio", 0.0)),
            bearingPressure=float(data.get("bearingPressure", 0.0)),
            topClearanceCm=float(data.get("topClearanceCm", 0.0)),
            projectionContained=bool(data.get("projectionContained", True))
        )

@dataclass
class PlacementFeedback:
    isFeasible: bool
    reasonCode: str = ""
    supportAreaRatio: float = 0.0
    bearingPressure: float = 0.0
    topClearanceCm: float = 0.0
    projectionContained: bool = True
    supportSource: str = "floor"
    supportPlacementIds: List[int] = field(default_factory=list)

@dataclass
class ContainerLoad:
    container: ContainerInstance
    placements: List[Placement] = field(default_factory=list)
    totalVolume: float = 0.0
    totalWeight: float = 0.0
    fillRate: float = 0.0
    weightRate: float = 0.0

    def add_placement(self, item: Item, placement: Placement) -> None:
        self.placements.append(placement)
        self.totalVolume += item.volume
        self.totalWeight += item.weight
        self.recalculate_rates()

    def recalculate_rates(self) -> None:
        self.fillRate = self.totalVolume / self.container.volume if self.container.volume > 0 else 0.0
        self.weightRate = (
            self.totalWeight / self.container.maxWeight
            if self.container.maxWeight > 0 else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container": self.container.to_dict(),
            "placements": [placement.to_dict() for placement in self.placements],
            "totalVolume": self.totalVolume,
            "totalWeight": self.totalWeight,
            "fillRate": self.fillRate,
            "weightRate": self.weightRate
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ContainerLoad":
        load = ContainerLoad(
            container=ContainerInstance(
                instanceId=str(data["container"]["instanceId"]),
                containerTypeId=str(data["container"]["containerTypeId"]),
                L=float(data["container"]["L"]),
                W=float(data["container"]["W"]),
                H=float(data["container"]["H"]),
                maxWeight=float(data["container"]["maxWeight"]),
                tripCost=float(data["container"]["tripCost"]),
                metadata=dict(data["container"].get("metadata", {}))
            ),
            placements=[Placement.from_dict(row) for row in data.get("placements", [])],
            totalVolume=float(data.get("totalVolume", 0.0)),
            totalWeight=float(data.get("totalWeight", 0.0)),
            fillRate=float(data.get("fillRate", 0.0)),
            weightRate=float(data.get("weightRate", 0.0))
        )
        return load

@dataclass
class ObjectiveRule:
    metric: str
    order: str = "max"

    def to_dict(self) -> Dict[str, Any]:
        return {"metric": self.metric, "order": self.order}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ObjectiveRule":
        return ObjectiveRule(
            metric=str(data["metric"]),
            order=str(data.get("order", "max")).lower()
        )

@dataclass
class ObjectiveSpec:
    primaryMetric: str
    primaryOrder: str = "max"
    tieBreakers: List[ObjectiveRule] = field(default_factory=list)
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "primaryMetric": self.primaryMetric,
            "primaryOrder": self.primaryOrder,
            "tieBreakers": [rule.to_dict() for rule in self.tieBreakers]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ObjectiveSpec":
        return ObjectiveSpec(
            primaryMetric=str(data.get("primaryMetric", "totalFillRate")),
            primaryOrder=str(data.get("primaryOrder", "max")).lower(),
            tieBreakers=[
                ObjectiveRule.from_dict(rule)
                for rule in data.get("tieBreakers", [])
            ],
            name=str(data.get("name", data.get("primaryMetric", "objective")))
        )

@dataclass
class GlobalConstraints:
    orthogonalOnly: bool = True
    allowCompression: bool = False
    allowSplit: bool = False
    minTopClearanceCm: float = 3.0
    maxBearingPressureKgPerM2: float = 500.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orthogonalOnly": self.orthogonalOnly,
            "allowCompression": self.allowCompression,
            "allowSplit": self.allowSplit,
            "minTopClearanceCm": self.minTopClearanceCm,
            "maxBearingPressureKgPerM2": self.maxBearingPressureKgPerM2
        }

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "GlobalConstraints":
        data = data or {}
        return GlobalConstraints(
            orthogonalOnly=bool(data.get("orthogonalOnly", True)),
            allowCompression=bool(data.get("allowCompression", False)),
            allowSplit=bool(data.get("allowSplit", False)),
            minTopClearanceCm=float(data.get("minTopClearanceCm", 3.0)),
            maxBearingPressureKgPerM2=float(data.get("maxBearingPressureKgPerM2", 500.0))
        )

@dataclass
class PlanMetrics:
    totalCost: float = 0.0
    usedContainerCount: int = 0
    usedContainerTypeCount: int = 0
    packedItemCount: int = 0
    unpackedItemCount: int = 0
    packedVolume: float = 0.0
    packedWeight: float = 0.0
    totalContainerVolume: float = 0.0
    totalFillRate: float = 0.0
    avgContainerFillRate: float = 0.0
    maxContainerFillRate: float = 0.0
    avgContainerWeightRate: float = 0.0
    objectiveName: str = ""
    objectiveValue: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalCost": self.totalCost,
            "usedContainerCount": self.usedContainerCount,
            "usedContainerTypeCount": self.usedContainerTypeCount,
            "packedItemCount": self.packedItemCount,
            "unpackedItemCount": self.unpackedItemCount,
            "packedVolume": self.packedVolume,
            "packedWeight": self.packedWeight,
            "totalContainerVolume": self.totalContainerVolume,
            "totalFillRate": self.totalFillRate,
            "avgContainerFillRate": self.avgContainerFillRate,
            "maxContainerFillRate": self.maxContainerFillRate,
            "avgContainerWeightRate": self.avgContainerWeightRate,
            "objectiveName": self.objectiveName,
            "objectiveValue": self.objectiveValue
        }

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "PlanMetrics":
        data = data or {}
        return PlanMetrics(
            totalCost=float(data.get("totalCost", 0.0)),
            usedContainerCount=int(data.get("usedContainerCount", 0)),
            usedContainerTypeCount=int(data.get("usedContainerTypeCount", 0)),
            packedItemCount=int(data.get("packedItemCount", 0)),
            unpackedItemCount=int(data.get("unpackedItemCount", 0)),
            packedVolume=float(data.get("packedVolume", 0.0)),
            packedWeight=float(data.get("packedWeight", 0.0)),
            totalContainerVolume=float(data.get("totalContainerVolume", 0.0)),
            totalFillRate=float(data.get("totalFillRate", 0.0)),
            avgContainerFillRate=float(data.get("avgContainerFillRate", 0.0)),
            maxContainerFillRate=float(data.get("maxContainerFillRate", 0.0)),
            avgContainerWeightRate=float(data.get("avgContainerWeightRate", 0.0)),
            objectiveName=str(data.get("objectiveName", "")),
            objectiveValue=float(data.get("objectiveValue", 0.0))
        )

@dataclass
class ShipmentPlan:
    containerLoads: List[ContainerLoad] = field(default_factory=list)
    unpackedItemIds: List[int] = field(default_factory=list)
    metrics: PlanMetrics = field(default_factory=PlanMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "containerLoads": [load.to_dict() for load in self.containerLoads],
            "unpackedItemIds": list(self.unpackedItemIds),
            "metrics": self.metrics.to_dict()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ShipmentPlan":
        return ShipmentPlan(
            containerLoads=[
                ContainerLoad.from_dict(load)
                for load in data.get("containerLoads", [])
            ],
            unpackedItemIds=[int(itemId) for itemId in data.get("unpackedItemIds", [])],
            metrics=PlanMetrics.from_dict(data.get("metrics"))
        )

@dataclass
class ProblemInstance:
    name: str
    schemaVersion: int
    units: Dict[str, str]
    containerTypes: List[ContainerType]
    itemTypes: List[ItemType]
    items: List[Item]
    globalConstraints: GlobalConstraints
    objective: ObjectiveSpec
    analysis: Dict[str, Any] = field(default_factory=dict)
    scenarioMetadata: Dict[str, Any] = field(default_factory=dict)
    algorithmParams: Dict[str, Any] = field(default_factory=dict)
