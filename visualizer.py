import os
import traceback
from typing import List, Tuple, Dict, Any, Optional, Set
import numpy as np
import plotly.graph_objects as go
from logger import get_logger
from dataStructures import Item, PackingSolution

logger = get_logger("visualizer")

class Visualizer:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir: str = resultsDir
        self.outputConfig: Dict[str, Any] = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

    @staticmethod
    def _box_mesh(x: float, y: float, z: float, dx: float, dy: float, dz: float, 
                  color: str, opacity: float = 1.0, hovertext: str = "") -> go.Mesh3d:
        """使用 Mesh3d 创建立方体，保持不透明材质"""
        return go.Mesh3d(
            x=[x, x, x+dx, x+dx, x, x, x+dx, x+dx],
            y=[y, y+dy, y+dy, y, y, y+dy, y+dy, y],
            z=[z, z, z, z, z+dz, z+dz, z+dz, z+dz],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color,
            opacity=opacity,
            flatshading=True,
            # 均衡的光照设置，确保立体感的同时面与面有区分
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.1, roughness=0.5, fresnel=0.2),
            lightposition=dict(x=100, y=200, z=150),
            hoverinfo='text',
            text=hovertext,
            showlegend=False
        )

    @staticmethod
    def _box_wireframe(x: float, y: float, z: float, dx: float, dy: float, dz: float, 
                       color: str = 'rgb(30,30,30)', width: int = 5) -> go.Scatter3d:
        """适中厚度的轮廓线 (width=5) 并使用深灰色，平衡可见度与美观"""
        pts = [
            (x,y,z),(x+dx,y,z),(x+dx,y+dy,z),(x,y+dy,z),(x,y,z),
            (x,y,z+dz),(x+dx,y,z+dz),(x+dx,y+dy,z+dz),(x,y+dy,z+dz),(x,y,z+dz),
            (None,None,None),
            (x,y,z),(x,y,z+dz),(None,None,None),
            (x+dx,y,z),(x+dx,y,z+dz),(None,None,None),
            (x+dx,y+dy,z),(x+dx,y+dy,z+dz),(None,None,None),
            (x,y+dy,z),(x,y+dy,z+dz)
        ]
        wx, wy, wz = zip(*pts)
        return go.Scatter3d(
            x=wx, y=wy, z=wz,
            mode='lines',
            line=dict(color=color, width=width),
            hoverinfo='skip',
            showlegend=False
        )

    @staticmethod
    def _container_wireframe(L: float, W: float, H: float) -> go.Scatter3d:
        pts = [
            (0,0,0),(L,0,0),(L,W,0),(0,W,0),(0,0,0),
            (0,0,H),(L,0,H),(L,W,H),(0,W,H),(0,0,H),
            (None,None,None),
            (L,0,0),(L,0,H),(None,None,None),
            (L,W,0),(L,W,H),(None,None,None),
            (0,W,0),(0,W,H)
        ]
        wx, wy, wz = zip(*pts)
        return go.Scatter3d(
            x=wx, y=wy, z=wz,
            mode='lines',
            line=dict(color='black', width=4),
            hoverinfo='skip',
            showlegend=False
        )

    def generateVisualization(self, result: Dict[str, Any], testName: str) -> Optional[str]:
        try:
            solution: PackingSolution = result.get('solution')
            if solution is None or not hasattr(solution, 'placedItems'):
                logger.error("  错误: 缺少有效的 solution.placedItems")
                return None

            placedItems = solution.placedItems
            if not placedItems:
                logger.warning("  警告: 没有放置任何货物，跳过可视化")
                return None

            container = result['container']
            L, W, H = container.L, container.W, container.H
            logger.info(f"  货物数量: {len(placedItems)}")

            PALETTE: List[Tuple[float, float, float]] = [
                (0.329, 0.659, 0.545), (0.847, 0.459, 0.247), (0.420, 0.502, 0.784),
                (0.835, 0.369, 0.424), (0.929, 0.788, 0.306), (0.545, 0.753, 0.812),
                (0.667, 0.467, 0.784), (0.478, 0.647, 0.306), (0.902, 0.608, 0.392),
                (0.384, 0.620, 0.718), (0.776, 0.502, 0.655), (0.647, 0.722, 0.420),
            ]

            spec_to_rgba: Dict[Tuple[float, float, float, float], Tuple[float, float, float]] = {}
            spec_to_legend_color: Dict[Tuple[float, float, float, float], str] = {}
            spec_to_actual_dims: Dict[Tuple[float, float, float, float], Set[Tuple[float, float, float]]] = {}
            color_counter = 0

            def get_dims(item: Item, rotation: int) -> Tuple[float, float, float]:
                # 0: (l, w, h), 1: (l, h, w), 2: (w, l, h), 3: (w, h, l), 4: (h, l, w), 5: (h, w, l)
                if rotation == 0: return (item.l, item.w, item.h)
                if rotation == 1: return (item.l, item.h, item.w)
                if rotation == 2: return (item.w, item.l, item.h)
                if rotation == 3: return (item.w, item.h, item.l)
                if rotation == 4: return (item.h, item.l, item.w)
                if rotation == 5: return (item.h, item.w, item.l)
                return (item.l, item.w, item.h)

            traces = []
            seen_ids = set()
            for itemId, x, y, z, rotation in placedItems:
                if itemId in seen_ids:
                    logger.warning(f"    严重警告: 发现重复放置的货物 ID={itemId}")
                seen_ids.add(itemId)

                item = next((it for it in result['items'] if it.id == itemId), None)
                if item is None:
                    continue

                dx, dy, dz = get_dims(item, rotation)
                sorted_dims = tuple(sorted([item.l, item.w, item.h]))
                spec_key = (*sorted_dims, item.weight)

                if spec_key not in spec_to_actual_dims:
                    spec_to_actual_dims[spec_key] = set()
                spec_to_actual_dims[spec_key].add((dx, dy, dz))

                if spec_key not in spec_to_rgba:
                    rgba = PALETTE[color_counter % len(PALETTE)]
                    spec_to_rgba[spec_key] = rgba
                    r, g, b = [int(c*255) for c in rgba]
                    spec_to_legend_color[spec_key] = f"rgb({r},{g},{b})"
                    color_counter += 1

                color_str = spec_to_legend_color[spec_key]
                hover_text = f"ID: {item.id}<br>规格: {item.l}x{item.w}x{item.h}<br>当前姿态: {dx}x{dy}x{dz}<br>坐标: ({x},{y},{z})"
                
                # 添加 3D 网格体
                traces.append(self._box_mesh(x, y, z, dx, dy, dz, color_str, hovertext=hover_text))
                # 添加 3D 边缘线
                traces.append(self._box_wireframe(x, y, z, dx, dy, dz))

            for spec, actual_dims in spec_to_actual_dims.items():
                if len(actual_dims) > 1:
                    logger.info(f"  规格 {spec} 使用了 {len(actual_dims)} 种旋转姿态: {actual_dims}")

            # 集装箱外框
            traces.append(self._container_wireframe(L, W, H))

            # 图例
            for dims_and_wt, color_str in spec_to_legend_color.items():
                l, w, h, wt = dims_and_wt
                traces.append(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers', marker=dict(size=10, color=color_str, symbol='square'), name=f"{l}×{w}×{h}, {wt}kg", showlegend=True))

            layout = go.Layout(
                title=dict(text=f"{testName} - {result['testIndex']}", x=0.5),
                scene=dict(
                    xaxis=dict(title='X', range=[0, L], showbackground=True),
                    yaxis=dict(title='Y', range=[0, W], showbackground=True),
                    zaxis=dict(title='Z', range=[0, H], showbackground=True),
                    aspectmode='data',
                    camera=dict(eye=dict(x=1.8, y=1.8, z=1.4)),
                ),
                width=1200, height=900,
                paper_bgcolor='white',
            )

            fig = go.Figure(data=traces, layout=layout)
            testFolder = os.path.join(self.resultsDir, testName)
            os.makedirs(testFolder, exist_ok=True)
            html_file = os.path.abspath(os.path.join(testFolder, f"pic_{result['testIndex']}.html"))
            fig.write_html(html_file, include_plotlyjs=True)
            logger.info(f"  HTML已保存: {html_file}")

            if self.outputConfig.get("saveStaticImage", True):
                try:
                    png_file = os.path.abspath(os.path.join(testFolder, f"pic_{result['testIndex']}.png"))
                    fig.write_image(png_file, width=1200, height=900, scale=1.5)
                    logger.info(f"  PNG已保存: {png_file}")
                except Exception:
                    pass

            return html_file
        except Exception as e:
            logger.error(f"  可视化生成失败: {e}")
            logger.debug(traceback.format_exc())
            return None
