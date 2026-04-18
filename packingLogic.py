from dataStructures import Space, PackingSolution

def simplePacking(container, items):
    spaces = [Space(0, 0, 0, container.L, container.W, container.H)]
    solution = PackingSolution()

    itemsSorted = sorted(items, key=lambda x: x.volume, reverse=True)

    for item in itemsSorted:
        placed = False
        spaces.sort(key=lambda s: (-s.z, s.y, s.x))

        for space in spaces:
            if space.canFit(item):
                if solution.totalWeight + item.weight <= container.maxWeight:
                    solution.addItem(item, space.x, space.y, space.z, item.rotation)

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
