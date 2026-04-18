import os
import traceback
import numpy as np
import plotly.graph_objects as go
import matplotlib

class Visualizer:
    def __init__(self, resultsDir="results"):
        self.resultsDir = resultsDir
        os.makedirs(self.resultsDir, exist_ok=True)

    @staticmethod
    def _derive_face_colors(base_rgba):
        """
        从基础色派生三个面的颜色：
          顶面：最亮 (+40%)
          左面（Y方向）：基础色
          右面（X方向）：最暗 (-30%)
        完全不透明，立体感靠明暗体现。
        """
        r, g, b = base_rgba[0], base_rgba[1], base_rgba[2]

        def clamp(v): return min(1.0, max(0.0, v))

        def rgb_str(rf, gf, bf):
            return f"rgb({int(clamp(rf)*255)},{int(clamp(gf)*255)},{int(clamp(bf)*255)})"

        top   = rgb_str(r*1.0 + 0.40*(1-r), g*1.0 + 0.40*(1-g), b*1.0 + 0.40*(1-b))  # 提亮
        mid   = rgb_str(r, g, b)                                                          # 原色
        dark  = rgb_str(r * 0.62, g * 0.62, b * 0.62)                                   # 压暗

        return top, mid, dark   # 顶面, 左/后面, 右/前面

    @staticmethod
    def _box_surfaces(x, y, z, dx, dy, dz, top_color, mid_color, dark_color):
        """
        6个 Surface 面片，每面独立颜色，完全不透明。
        光影分配：
          顶面              → top_color  (最亮)
          左面(-X) / 后面(+Y) → mid_color  (中间)
          右面(+X) / 前面(-Y) → dark_color (最暗)
          底面              → dark_color (通常不可见，随意)
        轮廓线通过 contours 实现，与面片共享深度缓冲。
        """
        face_defs = [
            # (gx, gy, gz, color)
            # 顶面 z=z+dz
            (np.array([[x, x+dx],[x, x+dx]]),
             np.array([[y, y],   [y+dy, y+dy]]),
             np.array([[z+dz, z+dz],[z+dz, z+dz]]),
             top_color),
            # 底面 z=z
            (np.array([[x, x+dx],[x, x+dx]]),
             np.array([[y, y],   [y+dy, y+dy]]),
             np.array([[z, z],   [z, z]]),
             dark_color),
            # 左面 x=x (mid)
            (np.array([[x, x],[x, x]]),
             np.array([[y, y+dy],[y, y+dy]]),
             np.array([[z, z],  [z+dz, z+dz]]),
             mid_color),
            # 右面 x=x+dx (dark)
            (np.array([[x+dx, x+dx],[x+dx, x+dx]]),
             np.array([[y, y+dy],[y, y+dy]]),
             np.array([[z, z],  [z+dz, z+dz]]),
             dark_color),
            # 前面 y=y (dark)
            (np.array([[x, x+dx],[x, x+dx]]),
             np.array([[y, y],  [y, y]]),
             np.array([[z, z],  [z+dz, z+dz]]),
             dark_color),
            # 后面 y=y+dy (mid)
            (np.array([[x, x+dx],[x, x+dx]]),
             np.array([[y+dy, y+dy],[y+dy, y+dy]]),
             np.array([[z, z],     [z+dz, z+dz]]),
             mid_color),
        ]

        surfaces = []
        for gx, gy, gz, color in face_defs:
            surfaces.append(go.Surface(
                x=gx, y=gy, z=gz,
                surfacecolor=np.zeros((2, 2)),
                colorscale=[[0, color], [1, color]],
                showscale=False,
                opacity=1.0,                          # ✅ 完全不透明
                contours=dict(
                    x=dict(show=True, color='rgba(0,0,0,0.75)', width=3,
                        highlight=False, usecolormap=False),
                    y=dict(show=True, color='rgba(0,0,0,0.75)', width=3,
                        highlight=False, usecolormap=False),
                    z=dict(show=True, color='rgba(0,0,0,0.75)', width=3,
                        highlight=False, usecolormap=False),
                ),
                # 关闭 Plotly 自带光照，完全由面色控制明暗
                lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0,
                              roughness=1.0, fresnel=0.0),
                hoverinfo='skip',
                showlegend=False,
            ))
        return surfaces

    @staticmethod
    def _container_wireframe(L, W, H):
        pts = [
            [(0,0,0),(L,0,0)],[(L,0,0),(L,W,0)],[(L,W,0),(0,W,0)],[(0,W,0),(0,0,0)],
            [(0,0,H),(L,0,H)],[(L,0,H),(L,W,H)],[(L,W,H),(0,W,H)],[(0,W,H),(0,0,H)],
            [(0,0,0),(0,0,H)],[(L,0,0),(L,0,H)],
            [(L,W,0),(L,W,H)],[(0,W,0),(0,W,H)],
        ]
        wx, wy, wz = [], [], []
        for (x0,y0,z0),(x1,y1,z1) in pts:
            wx += [x0,x1,None]
            wy += [y0,y1,None]
            wz += [z0,z1,None]
        return wx, wy, wz

    def generateVisualization(self, result, testName):
        try:
            solution = result.get('solution')
            if solution is None or not hasattr(solution, 'placedItems'):
                print("  错误: 缺少有效的 solution.placedItems")
                return None

            placedItems = solution.placedItems
            if not placedItems:
                print("  警告: 没有放置任何货物，跳过可视化")
                return None

            container = result['container']
            L, W, H = container.L, container.W, container.H
            print(f"  货物数量: {len(placedItems)}")

            # 用视觉上更易区分的颜色集，替换 tab20
            # 选取饱和度适中、相互区分度高的颜色
            PALETTE = [
                (0.329, 0.659, 0.545),  # 绿
                (0.847, 0.459, 0.247),  # 橙
                (0.420, 0.502, 0.784),  # 蓝紫
                (0.835, 0.369, 0.424),  # 红
                (0.929, 0.788, 0.306),  # 黄
                (0.545, 0.753, 0.812),  # 青
                (0.667, 0.467, 0.784),  # 紫
                (0.478, 0.647, 0.306),  # 草绿
                (0.902, 0.608, 0.392),  # 杏
                (0.384, 0.620, 0.718),  # 钢蓝
                (0.776, 0.502, 0.655),  # 玫瑰
                (0.647, 0.722, 0.420),  # 黄绿
            ]

            spec_to_rgba = {}
            spec_to_legend_color = {}
            color_counter = 0

            def get_dims(item, rotation):
                return {
                    0: (item.l, item.w, item.h),
                    1: (item.l, item.h, item.w),
                    2: (item.h, item.w, item.l),
                }.get(rotation, (item.l, item.w, item.h))

            traces = []

            for itemId, x, y, z, rotation in placedItems:
                item = next((it for it in result['items'] if it.id == itemId), None)
                if item is None:
                    print(f"    警告: 未找到货物 ID={itemId}")
                    continue

                dx, dy, dz = get_dims(item, rotation)
                spec_key = (item.l, item.w, item.h, item.weight)

                if spec_key not in spec_to_rgba:
                    rgba = PALETTE[color_counter % len(PALETTE)]
                    spec_to_rgba[spec_key] = rgba
                    r, g, b = [int(c*255) for c in rgba]
                    spec_to_legend_color[spec_key] = f"rgb({r},{g},{b})"
                    color_counter += 1

                base_rgba = spec_to_rgba[spec_key]
                top_c, mid_c, dark_c = self._derive_face_colors(base_rgba)
                traces.extend(
                    self._box_surfaces(x, y, z, dx, dy, dz, top_c, mid_c, dark_c)
                )

            # 集装箱外框
            cx, cy, cz = self._container_wireframe(L, W, H)
            traces.append(go.Scatter3d(
                x=cx, y=cy, z=cz,
                mode='lines',
                line=dict(color='rgba(0,0,0,0.85)', width=3),
                showlegend=False,
                hoverinfo='skip',
            ))

            # 图例
            for (l, w, h, wt), color_str in spec_to_legend_color.items():
                traces.append(go.Scatter3d(
                    x=[None], y=[None], z=[None],
                    mode='markers',
                    marker=dict(size=10, color=color_str, symbol='square'),
                    name=f"{l}×{w}×{h}, {wt}kg",
                    showlegend=True,
                ))

            layout = go.Layout(
                title=dict(text=f"{testName} - {result['testIndex']}", x=0.5),
                scene=dict(
                    xaxis=dict(title='X', range=[0, L], showbackground=True,
                               backgroundcolor='rgba(240,240,240,0.5)'),
                    yaxis=dict(title='Y', range=[0, W], showbackground=True,
                               backgroundcolor='rgba(220,220,240,0.5)'),
                    zaxis=dict(title='Z', range=[0, H], showbackground=True,
                               backgroundcolor='rgba(220,240,220,0.5)'),
                    aspectmode='data',
                    camera=dict(
                        eye=dict(x=1.8, y=1.8, z=1.4),   # ← 从(+X,+Y)对角俯视，两面都能看到
                        up=dict(x=0, y=0, z=1),
                    ),
                ),
                width=1200, height=900,
                margin=dict(l=0, r=0, t=50, b=0),
                legend=dict(
                    title=dict(text='货物规格'),
                    x=0.02, y=0.98,
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='gray', borderwidth=1,
                ),
                paper_bgcolor='white',
            )

            fig = go.Figure(data=traces, layout=layout)

            testFolder = os.path.join(self.resultsDir, testName)
            os.makedirs(testFolder, exist_ok=True)

            html_file = os.path.abspath(
                os.path.join(testFolder, f"pic_{result['testIndex']}.html"))

            fig.write_html(html_file, include_plotlyjs=True)
            print(f"  HTML已保存（可离线查看）: {html_file}")

            try:
                png_file = os.path.abspath(
                    os.path.join(testFolder, f"pic_{result['testIndex']}.png"))
                fig.write_image(png_file, width=1200, height=900, scale=1.5)
                print(f"  PNG已保存: {png_file}")
            except Exception:
                print("  提示: PNG需要 kaleido，执行 pip install kaleido 后可用")

            return html_file

        except Exception as e:
            print(f"  可视化生成失败: {e}")
            traceback.print_exc()
            return None