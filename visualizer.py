import os
import sys
import traceback
import matplotlib
# 设置非交互式后端，避免显示问题
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

class Visualizer:
    def __init__(self, resultsDir="results"):
        self.resultsDir = resultsDir
        # 确保结果目录存在
        os.makedirs(self.resultsDir, exist_ok=True)

    def generateVisualization(self, result, testName):
        """
        生成可视化图形
        :param result: 测试结果
        :param testName: 测试用例名称
        :return: 可视化文件路径
        """
        try:
            # print(f"  开始生成可视化: {testName} - 组合{result['testIndex']}")

            # 检查必要数据
            if 'solution' not in result:
                print("  错误: result中缺少'solution'字段")
                return None

            # 修复：检查PackingSolution对象的属性
            solution = result['solution']
            if not hasattr(solution, 'placedItems'):
                print("  错误: solution对象没有'placedItems'属性")
                return None

            placedItems = solution.placedItems

            if len(placedItems) == 0:
                print("  警告: 没有放置任何货物，跳过可视化")
                return None

            # 创建可视化图形
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')

            # 设置集装箱边界
            container = result['container']
            ax.set_xlim([0, container.L])
            ax.set_ylim([0, container.W])
            ax.set_zlim([0, container.H])
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Z')

            # 设置标题
            title = f"{testName} - {result['testIndex']}"
            ax.set_title(title)

            # 绘制集装箱线框 - 使用NumPy数组
            vertices = np.array([
                [0, 0, 0],
                [container.L, 0, 0],
                [container.L, container.W, 0],
                [0, container.W, 0],
                [0, 0, container.H],
                [container.L, 0, container.H],
                [container.L, container.W, container.H],
                [0, container.W, container.H]
            ])

            edges = [
                [0, 1], [1, 2], [2, 3], [3, 0],  # 底面
                [4, 5], [5, 6], [6, 7], [7, 4],  # 顶面
                [0, 4], [1, 5], [2, 6], [3, 7]   # 侧面
            ]

            for edge in edges:
                ax.plot(vertices[edge, 0], vertices[edge, 1], vertices[edge, 2],
                       color='black', alpha=0.3, linewidth=0.5)

            # 创建规格到颜色的映射字典
            spec_to_color = {}
            color_counter = 0

            # 使用tab20颜色映射，有20种颜色，足够应对多种规格
            colors = plt.cm.tab20(np.linspace(0, 1, 20))

            print(f"  货物数量: {len(placedItems)}")

            # 首先，收集所有货物的信息，包括它们的中心点坐标
            item_info_list = []
            for i, (itemId, x, y, z, rotation) in enumerate(placedItems):
                # 根据货物ID获取货物尺寸
                item = next((item for item in result['items'] if item.id == itemId), None)
                if item:
                    # 根据旋转调整尺寸（简化处理）
                    if rotation == 0:  # 原始方向
                        dx, dy, dz = item.l, item.w, item.h
                    elif rotation == 1:  # 绕X轴旋转90度
                        dx, dy, dz = item.l, item.h, item.w
                    elif rotation == 2:  # 绕Y轴旋转90度
                        dx, dy, dz = item.h, item.w, item.l
                    else:  # 其他旋转，使用原始尺寸
                        dx, dy, dz = item.l, item.w, item.h

                    # 创建规格标识符（尺寸+重量）
                    spec_key = (item.l, item.w, item.h, item.weight)

                    # 为规格分配颜色（相同规格使用相同颜色）
                    if spec_key not in spec_to_color:
                        spec_to_color[spec_key] = colors[color_counter % len(colors)]
                        color_counter += 1

                    # 获取该规格的颜色
                    color = spec_to_color[spec_key]

                    # 计算中心点坐标（用于深度排序）
                    center_x = x + dx / 2
                    center_y = y + dy / 2
                    center_z = z + dz / 2

                    # 存储货物信息
                    item_info_list.append({
                        'itemId': itemId,
                        'x': x, 'y': y, 'z': z,
                        'dx': dx, 'dy': dy, 'dz': dz,
                        'color': color,
                        'center_x': center_x,
                        'center_y': center_y,
                        'center_z': center_z,
                        'spec_key': spec_key
                    })
                else:
                    print(f"    警告: 未找到货物ID={itemId}")

            # 方法1：按中心点Z坐标排序（从低到高）
            # 这是基础排序，解决大部分高度相关的问题
            item_info_list.sort(key=lambda info: info['center_z'])

            # 方法2：进一步优化排序 - 按照视角方向排序
            # 获取当前视角参数
            elev = 30  # 仰角
            azim = 45  # 方位角

            # 计算每个货物在视线方向上的投影距离
            # 视线方向向量
            view_dir_x = np.cos(np.radians(elev)) * np.cos(np.radians(azim))
            view_dir_y = np.cos(np.radians(elev)) * np.sin(np.radians(azim))
            view_dir_z = np.sin(np.radians(elev))

            # 计算每个货物中心点在视线方向上的投影距离
            for info in item_info_list:
                # 投影距离 = 点积(中心点坐标, 视线方向)
                # 注意：这里我们使用负值，因为我们要从远到近排序
                projection = -(info['center_x'] * view_dir_x +
                              info['center_y'] * view_dir_y +
                              info['center_z'] * view_dir_z)
                info['projection_distance'] = projection

            # 按投影距离从远到近排序（距离大的先绘制）
            item_info_list.sort(key=lambda info: info['projection_distance'])

            # 方法3：对于重叠的货物，使用更精细的排序
            # 这里我们可以添加更复杂的排序逻辑，但考虑到性能，我们使用简单的排序

            # 按排序后的顺序绘制货物
            for info in item_info_list:
                x, y, z = info['x'], info['y'], info['z']
                dx, dy, dz = info['dx'], info['dy'], info['dz']
                color = info['color']

                # 定义长方体的8个顶点
                vertices = [
                    [x, y, z],
                    [x+dx, y, z],
                    [x+dx, y+dy, z],
                    [x, y+dy, z],
                    [x, y, z+dz],
                    [x+dx, y, z+dz],
                    [x+dx, y+dy, z+dz],
                    [x, y+dy, z+dz]
                ]

                # 定义长方体的6个面（每个面由4个顶点组成）
                faces = [
                    [vertices[0], vertices[1], vertices[2], vertices[3]],  # 底面
                    [vertices[4], vertices[5], vertices[6], vertices[7]],  # 顶面
                    [vertices[0], vertices[1], vertices[5], vertices[4]],  # 前面
                    [vertices[2], vertices[3], vertices[7], vertices[6]],  # 后面
                    [vertices[0], vertices[3], vertices[7], vertices[4]],  # 左面
                    [vertices[1], vertices[2], vertices[6], vertices[5]]   # 右面
                ]

                # 创建长方体的面集合，使用规格对应的颜色
                # 调整alpha值，使重叠部分更自然
                collection = Poly3DCollection(faces, alpha=0.7, linewidths=1, edgecolors='black')
                collection.set_facecolor(color)
                ax.add_collection3d(collection)

            # 设置视角
            ax.view_init(elev=30, azim=45)

            # 创建图例显示规格到颜色的映射
            if spec_to_color:
                legend_elements = []
                for spec_key, color in spec_to_color.items():
                    l, w, h, weight = spec_key
                    label = f"{l}x{w}x{h}, {weight}kg"
                    legend_elements.append(plt.Line2D([0], [0], marker='s', color='w',
                                                     markerfacecolor=color, markersize=10, label=label))

                ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

            # 创建测试用例文件夹 - 在本次运行的顶级目录下
            testFolder = os.path.join(self.resultsDir, testName)
            os.makedirs(testFolder, exist_ok=True)

            # 保存图形
            vizFile = os.path.join(testFolder, f"visualization_combo{result['testIndex']}.png")
            absVizFile = os.path.abspath(vizFile)

            print(f"  保存可视化到: {absVizFile}")

            plt.savefig(absVizFile, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"  可视化生成成功: {os.path.basename(absVizFile)}")
            return absVizFile

        except Exception as e:
            print(f"  可视化生成失败: {e}")
            print(f"  详细错误信息:")
            traceback.print_exc()
            return None
