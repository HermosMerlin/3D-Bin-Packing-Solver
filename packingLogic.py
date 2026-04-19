from typing import List
from dataStructures import Item, Container, Space, PackingSolution
import bisect

def mergeSpaces(spaces: List[Space]) -> List[Space]:
    """尝试合并相邻且可以合并的空间以减少碎片化"""
    if len(spaces) <= 1:
        return spaces
        
    merged = True
    while merged:
        merged = False
        i = 0
        while i < len(spaces):
            j = i + 1
            while j < len(spaces):
                s1 = spaces[i]
                s2 = spaces[j]
                newSpace = None
                
                # 检查在 X 轴方向是否可以合并
                if s1.y == s2.y and s1.z == s2.z and s1.W == s2.W and s1.H == s2.H:
                    if s1.x + s1.L == s2.x:
                        newSpace = Space(s1.x, s1.y, s1.z, s1.L + s2.L, s1.W, s1.H)
                    elif s2.x + s2.L == s1.x:
                        newSpace = Space(s2.x, s1.y, s1.z, s1.L + s2.L, s1.W, s1.H)
                
                # 检查在 Y 轴方向是否可以合并
                if not newSpace and s1.x == s2.x and s1.z == s2.z and s1.L == s2.L and s1.H == s2.H:
                    if s1.y + s1.W == s2.y:
                        newSpace = Space(s1.x, s1.y, s1.z, s1.L, s1.W + s2.W, s1.H)
                    elif s2.y + s2.W == s1.y:
                        newSpace = Space(s1.x, s2.y, s1.z, s1.L, s1.W + s2.W, s1.H)
                        
                # 检查在 Z 轴方向是否可以合并
                if not newSpace and s1.x == s2.x and s1.y == s2.y and s1.L == s2.L and s1.W == s2.W:
                    if s1.z + s1.H == s2.z:
                        newSpace = Space(s1.x, s1.y, s1.z, s1.L, s1.W, s1.H + s2.H)
                    elif s2.z + s2.H == s1.z:
                        newSpace = Space(s1.x, s1.y, s2.z, s1.L, s1.W, s1.H + s2.H)
                
                if newSpace:
                    spaces.pop(j)
                    spaces.pop(i)
                    spaces.append(newSpace)
                    merged = True
                    # 回到内层循环起始，因为列表已变
                    break
                j += 1
            if merged:
                break
            i += 1
    return spaces

def simplePacking(container: Container, items: List[Item]) -> PackingSolution:
    # 初始空间：整个容器
    spaces: List[Space] = [Space(0, 0, 0, container.L, container.W, container.H)]
    solution: PackingSolution = PackingSolution()

    # 直接使用传入的货物顺序
    itemsToPlace = items

    # 排序键：优先低处 (z), 其次后处 (y), 最后左侧 (x)
    def spaceSortKey(s: Space):
        return (s.z, s.y, s.x)

    for item in itemsToPlace:
        placed = False
        
        # 尝试 6 种旋转姿态 (L, W, H)
        # 0: (l, w, h), 1: (l, h, w), 2: (w, l, h), 3: (w, h, l), 4: (h, l, w), 5: (h, w, l)
        possible_rotations = [
            (item.l, item.w, item.h, 0),
            (item.l, item.h, item.w, 1),
            (item.w, item.l, item.h, 2),
            (item.w, item.h, item.l, 3),
            (item.h, item.l, item.w, 4),
            (item.h, item.w, item.l, 5)
        ]

        for i, space in enumerate(spaces):
            for orient_l, orient_w, orient_h, rot_id in possible_rotations:
                # 检查此姿态是否能放入空间
                if orient_l <= space.L and orient_w <= space.W and orient_h <= space.H:
                    # 检查载重限制
                    if solution.totalWeight + item.weight <= container.maxWeight:
                        # 确定放置！
                        solution.addItem(item, space.x, space.y, space.z, rot_id)

                        # 分解剩余空间 (Guillotine 切割，使用当前姿态的尺寸)
                        newSpaces = [
                            Space(space.x + orient_l, space.y, space.z,
                                  space.L - orient_l, space.W, space.H),
                            Space(space.x, space.y + orient_w, space.z,
                                  orient_l, space.W - orient_w, space.H),
                            Space(space.x, space.y, space.z + orient_h,
                                  orient_l, orient_w, space.H - orient_h)
                        ]

                        # 移除旧空间
                        spaces.pop(i)

                        # 添加新空间并过滤无效空间
                        for ns in newSpaces:
                            if ns.L > 0 and ns.W > 0 and ns.H > 0:
                                spaces.append(ns)

                        # 尝试合并空间以减少碎片化
                        if len(spaces) > 10:
                            spaces = mergeSpaces(spaces)

                        # 重新排序空间以保证 FFD 效果
                        spaces.sort(key=spaceSortKey)

                        placed = True
                        break # 跳出 rotation 循环

            if placed:
                break # 跳出 space 循环


    solution.calculateRates(container)
    return solution
