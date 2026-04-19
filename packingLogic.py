from typing import List
from dataStructures import Item, Container, Space, PackingSolution

def simplePacking(container: Container, items: List[Item]) -> PackingSolution:
    spaces: List[Space] = [Space(0, 0, 0, container.L, container.W, container.H)]
    solution: PackingSolution = PackingSolution()

    # 按体积降序排列货物
    itemsSorted = sorted(items, key=lambda x: x.volume, reverse=True)

    for item in itemsSorted:
        placed = False
        # 排序空间以便更好的利用（先考虑低处、后处、左侧的空间）
        spaces.sort(key=lambda s: (-s.z, s.y, s.x))

        for space in spaces:
            if space.canFit(item):
                # 检查载重限制
                if solution.totalWeight + item.weight <= container.maxWeight:
                    solution.addItem(item, space.x, space.y, space.z, item.rotation)

                    # 分解剩余空间
                    newSpaces = [
                        Space(space.x + item.l, space.y, space.z,
                              space.L - item.l, space.W, space.H),
                        Space(space.x, space.y + item.w, space.z,
                              item.l, space.W - item.w, space.H),
                        Space(space.x, space.y, space.z + item.h,
                              item.l, item.w, space.H - item.h)
                    ]

                    spaces.remove(space)
                    spaces.extend(newSpaces)
                    placed = True
                    break

        if not placed:
            pass

    solution.calculateRates(container)
    return solution
