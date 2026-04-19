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
    def _derive_face_colors(base_rgba: Tuple[float, float, float]) -> Tuple[str, str, str]:
        r, g, b = base_rgba
        def clamp(v: float) -> float: return min(1.0, max(0.0, v))
        def rgb_str(rf: float, gf: float, bf: float) -> str:
            return f"rgb({int(clamp(rf)*255)},{int(clamp(gf)*255)},{int(clamp(bf)*255)})"

        top = rgb_str(r*1.0 + 0.40*(1-r), g*1.0 + 0.40*(1-g), b*1.0 + 0.40*(1-b))
        mid = rgb_str(r, g, b)
        dark = rgb_str(r * 0.62, g * 0.62, b * 0.62)
        return top, mid, dark

    @staticmethod
    def _box_surfaces(x: float, y: float, z: float, dx: float, dy: float, dz: float, 
                      top_color: str, mid_color: str, dark_color: str) -> List[go.Surface]:
        # 使用 2x2 网格定义 6 个面
        face_defs = [
            # 顶面 z=z+dz
            (np.array([[x, x+dx],[x, x+dx]]), np.array([[y, y],[y+dy, y+dy]]), np.array([[z+dz, z+dz],[z+dz, z+dz]]), top_color),
            # 底面 z=z
            (np.array([[x, x+dx],[x, x+dx]]), np.array([[y, y],[y+dy, y+dy]]), np.array([[z, z],[z, z]]), dark_color),
            # 左面 x=x
            (np.array([[x, x],[x, x]]), np.array([[y, y+dy],[y, y+dy]]), np.array([[z, z],[z+dz, z+dz]]), mid_color),
            # 右面 x=x+dx
            (np.array([[x+dx, x+dx],[x+dx, x+dx]]), np.array([[y, y+dy],[y, y+dy]]), np.array([[z, z],[z+dz, z+dz]]), dark_color),
            # 前面 y=y
            (np.array([[x, x+dx],[x, x+dx]]), np.array([[y, y],[y, y]]), np.array([[z, z],[z+dz, z+dz]]), dark_color),
            # 后面 y=y+dy
            (np.array([[x, x+dx],[x, x+dx]]), np.array([[y+dy, y+dy],[y+dy, y+dy]]), np.array([[z, z],[z+dz, z+dz]]), mid_color),
        ]
        return [go.Surface(
            x=gx, y=gy, z=gz,
            surfacecolor=np.zeros((2, 2)),
            colorscale=[[0, color], [1, color]],
            showscale=False, opacity=1.0,
            contours=dict(
                x=dict(show=True, color='rgba(0,0,0,0.75)', width=3),
                y=dict(show=True, color='rgba(0,0,0,0.75)', width=3),
                z=dict(show=True, color='rgba(0,0,0,0.75)', width=3),
            ),
            lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0, roughness=1.0, fresnel=0.0),
            hoverinfo='skip', showlegend=False
        ) for gx, gy, gz, color in face_defs]

    @staticmethod
    def _container_wireframe(L: float, W: float, H: float) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        pts = [
            [(0,0,0),(L,0,0)],[(L,0,0),(L,W,0)],[(L,W,0),(0,W,0)],[(0,W,0),(0,0,0)],
            [(0,0,H),(L,0,H)],[(L,0,H),(L,W,H)],[(L,W,H),(0,W,H)],[(0,W,H),(0,0,H)],
            [(0,0,0),(0,0,H)],[(L,0,0),(L,0,H)],[(L,W,0),(L,W,H)],[(0,W,0),(0,W,H)],
        ]
        wx, wy, wz = [], [], []
        for (x0,y0,z0),(x1,y1,z1) in pts:
            wx += [float(x0),float(x1),None]
            wy += [float(y0),float(y1),None]
            wz += [float(z0),float(z1),None]
        return wx, wy, wz

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
            # 用于检测同规格尺寸是否一致
            spec_to_actual_dims: Dict[Tuple[float, float, float, float], Set[Tuple[float, float, float]]] = {}
            color_counter = 0

            def get_dims(item: Item, rotation: int) -> Tuple[float, float, float]:
                # 目前仅支持 3 种基础旋转，后续可扩展
                if rotation == 1: return (item.l, item.h, item.w)
                if rotation == 2: return (item.h, item.w, item.l)
                return (item.l, item.w, item.h)

            traces = []
            for itemId, x, y, z, rotation in placedItems:
                item = next((it for it in result['items'] if it.id == itemId), None)
                if item is None:
                    logger.warning(f"    警告: 未找到货物 ID={itemId}")
                    continue

                dx, dy, dz = get_dims(item, rotation)
                spec_key = (item.l, item.w, item.h, item.weight)

                # 记录并检查尺寸一致性
                if spec_key not in spec_to_actual_dims:
                    spec_to_actual_dims[spec_key] = set()
                spec_to_actual_dims[spec_key].add((dx, dy, dz))

                if spec_key not in spec_to_rgba:
                    rgba = PALETTE[color_counter % len(PALETTE)]
                    spec_to_rgba[spec_key] = rgba
                    r, g, b = [int(c*255) for c in rgba]
                    spec_to_legend_color[spec_key] = f"rgb({r},{g},{b})"
                    color_counter += 1

                base_rgba = spec_to_rgba[spec_key]
                top_c, mid_c, dark_c = self._derive_face_colors(base_rgba)
                traces.extend(self._box_surfaces(x, y, z, dx, dy, dz, top_c, mid_c, dark_c))

            # 检查并打印尺寸不一致的警告
            for spec, actual_dims in spec_to_actual_dims.items():
                if len(actual_dims) > 1:
                    logger.warning(f"  检测到规格 {spec} 存在多种渲染尺寸: {actual_dims}")
                else:
                    logger.debug(f"  规格 {spec} 渲染尺寸一致: {list(actual_dims)[0]}")

            # 集装箱外框
            cx, cy, cz = self._container_wireframe(L, W, H)
            traces.append(go.Scatter3d(x=cx, y=cy, z=cz, mode='lines', line=dict(color='rgba(0,0,0,0.85)', width=3), showlegend=False, hoverinfo='skip'))

            # 图例
            for (l, w, h, wt), color_str in spec_to_legend_color.items():
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

            # 根据配置决定是否保存静态图片
            if self.outputConfig.get("saveStaticImage", True):
                try:
                    png_file = os.path.abspath(os.path.join(testFolder, f"pic_{result['testIndex']}.png"))
                    fig.write_image(png_file, width=1200, height=900, scale=1.5)
                    logger.info(f"  PNG已保存: {png_file}")
                except Exception:
                    logger.warning("  提示: PNG需要 kaleido")

            return html_file
        except Exception as e:
            logger.error(f"  可视化生成失败: {e}")
            logger.debug(traceback.format_exc())
            return None
