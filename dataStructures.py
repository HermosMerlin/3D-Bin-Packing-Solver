class Item:
    def __init__(self, id, l, w, h, weight):
        self.id = id
        self.l = l
        self.w = w
        self.h = h
        self.weight = weight
        self.volume = l * w * h
        self.rotation = 0

class Container:
    def __init__(self, L, W, H, maxWeight):
        self.L = L
        self.W = W
        self.H = H
        self.maxWeight = maxWeight
        self.volume = L * W * H

class PackingSolution:
    def __init__(self):
        self.placedItems = []
        self.totalVolume = 0
        self.totalWeight = 0
        self.volumeRate = 0.0
        self.weightRate = 0.0

    def addItem(self, item, x, y, z, rotation):
        self.placedItems.append((item.id, x, y, z, rotation))
        self.totalVolume += item.volume
        self.totalWeight += item.weight

    def calculateRates(self, container):
        self.volumeRate = self.totalVolume / container.volume
        self.weightRate = self.totalWeight / container.maxWeight
        return self.volumeRate, self.weightRate

    def isFeasible(self, container):
        return self.totalWeight <= container.maxWeight

class Space:
    def __init__(self, x, y, z, L, W, H):
        self.x = x
        self.y = y
        self.z = z
        self.L = L
        self.W = W
        self.H = H

    def canFit(self, item):
        return item.l <= self.L and item.w <= self.W and item.h <= self.H
