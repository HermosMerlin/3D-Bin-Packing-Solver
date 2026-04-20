from typing import List, Tuple, Optional

class Item:
    def __init__(
        self,
        id: int,
        l: float,
        w: float,
        h: float,
        weight: float,
        typeId: Optional[int] = None
    ):
        self.id: int = id
        self.l: float = l
        self.w: float = w
        self.h: float = h
        self.weight: float = weight
        self.typeId: Optional[int] = typeId
        self.volume: float = l * w * h
        self.rotation: int = 0

class Container:
    def __init__(self, L: float, W: float, H: float, maxWeight: float):
        self.L: float = L
        self.W: float = W
        self.H: float = H
        self.maxWeight: float = maxWeight
        self.volume: float = L * W * H

class PackingSolution:
    def __init__(self):
        # 存储格式: (itemId, x, y, z, rotation)
        self.placedItems: List[Tuple[int, float, float, float, int]] = []
        self.totalVolume: float = 0.0
        self.totalWeight: float = 0.0
        self.volumeRate: float = 0.0
        self.weightRate: float = 0.0

    def addItem(self, item: Item, x: float, y: float, z: float, rotation: int) -> None:
        self.placedItems.append((item.id, x, y, z, rotation))
        self.totalVolume += item.volume
        self.totalWeight += item.weight

    def calculateRates(self, container: Container) -> Tuple[float, float]:
        self.volumeRate = self.totalVolume / container.volume
        self.weightRate = self.totalWeight / container.maxWeight
        return self.volumeRate, self.weightRate

    def to_dict(self) -> dict:
        return {
            "placedItems": self.placedItems,
            "totalVolume": self.totalVolume,
            "totalWeight": self.totalWeight,
            "volumeRate": self.volumeRate,
            "weightRate": self.weightRate
        }

    @staticmethod
    def from_dict(data: dict) -> 'PackingSolution':
        sol = PackingSolution()
        sol.placedItems = [tuple(item) if isinstance(item, list) else item for item in data["placedItems"]]
        sol.totalVolume = data["totalVolume"]
        sol.totalWeight = data["totalWeight"]
        sol.volumeRate = data["volumeRate"]
        sol.weightRate = data["weightRate"]
        return sol

    def isFeasible(self, container: Container) -> bool:
        return self.totalWeight <= container.maxWeight

class Space:
    def __init__(self, x: float, y: float, z: float, L: float, W: float, H: float):
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.L: float = L
        self.W: float = W
        self.H: float = H

    def canFit(self, item: Item) -> bool:
        return item.l <= self.L and item.w <= self.W and item.h <= self.H
