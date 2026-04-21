import os
import traceback
from typing import Any, Dict, List, Optional, Tuple
import plotly.graph_objects as go
from logger import get_logger

logger = get_logger("visualizer")

class Visualizer:
    def __init__(self, resultsDir: str = "results", outputConfig: Dict[str, Any] = None):
        self.resultsDir = resultsDir
        self.outputConfig = outputConfig or {}
        os.makedirs(self.resultsDir, exist_ok=True)

    def _getCasePackingDir(self, testName: str) -> str:
        return os.path.join(self.resultsDir, "cases", testName, "visuals", "packing")

    def _getCaseAnalysisDir(self, testName: str) -> str:
        return os.path.join(self.resultsDir, "cases", testName, "visuals", "analysis")

    def _getAggregateAnalysisDir(self) -> str:
        return os.path.join(self.resultsDir, "aggregate", "visuals", "analysis")

    @staticmethod
    def _apply_filters(
        rows: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not filters:
            return rows
        filteredRows = rows
        for key, expected in filters.items():
            if isinstance(expected, list):
                allowed = set(expected)
                filteredRows = [
                    row for row in filteredRows
                    if row.get(key) in allowed
                ]
            else:
                filteredRows = [
                    row for row in filteredRows
                    if row.get(key) == expected
                ]
        return filteredRows

    @staticmethod
    def _apply_sort_and_topn(
        rows: List[Dict[str, Any]],
        sortBy: Optional[str],
        sortOrder: str,
        topN: Optional[int]
    ) -> List[Dict[str, Any]]:
        processedRows = list(rows)
        if sortBy:
            processedRows.sort(
                key=lambda row: (row.get(sortBy) is None, row.get(sortBy)),
                reverse=(sortOrder.lower() == "desc")
            )
        if topN is not None and topN > 0:
            processedRows = processedRows[:topN]
        return processedRows

    @staticmethod
    def _box_mesh(
        x: float,
        y: float,
        z: float,
        dx: float,
        dy: float,
        dz: float,
        color: str,
        hovertext: str = ""
    ) -> go.Mesh3d:
        return go.Mesh3d(
            x=[x, x, x + dx, x + dx, x, x, x + dx, x + dx],
            y=[y, y + dy, y + dy, y, y, y + dy, y + dy, y],
            z=[z, z, z, z, z + dz, z + dz, z + dz, z + dz],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color,
            opacity=1.0,
            flatshading=True,
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.1, roughness=0.5),
            hoverinfo="text",
            text=hovertext,
            showlegend=False
        )

    @staticmethod
    def _box_wireframe(
        x: float,
        y: float,
        z: float,
        dx: float,
        dy: float,
        dz: float,
        color: str = "rgb(30,30,30)",
        width: int = 4
    ) -> go.Scatter3d:
        points = [
            (x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z), (x, y, z),
            (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz), (x, y, z + dz),
            (None, None, None),
            (x, y, z), (x, y, z + dz), (None, None, None),
            (x + dx, y, z), (x + dx, y, z + dz), (None, None, None),
            (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (None, None, None),
            (x, y + dy, z), (x, y + dy, z + dz)
        ]
        px, py, pz = zip(*points)
        return go.Scatter3d(
            x=px,
            y=py,
            z=pz,
            mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="skip",
            showlegend=False
        )

    @staticmethod
    def _container_wireframe(L: float, W: float, H: float) -> go.Scatter3d:
        return Visualizer._box_wireframe(0, 0, 0, L, W, H, color="black", width=5)

    def generatePackingVisualization(
        self,
        result: Dict[str, Any],
        testName: str
    ) -> List[str]:
        files: List[str] = []
        try:
            itemById = {item.id: item for item in result["items"]}
            packingDir = self._getCasePackingDir(testName)
            os.makedirs(packingDir, exist_ok=True)

            for containerLoad in result.get("containerLoads", []):
                if not containerLoad.placements:
                    continue

                traces = [self._container_wireframe(
                    containerLoad.container.L,
                    containerLoad.container.W,
                    containerLoad.container.H
                )]
                palette = [
                    "rgb(84, 168, 139)",
                    "rgb(216, 117, 63)",
                    "rgb(107, 128, 200)",
                    "rgb(213, 94, 108)",
                    "rgb(237, 201, 78)"
                ]
                colorByType: Dict[str, str] = {}

                for placement in containerLoad.placements:
                    item = itemById.get(placement.itemId)
                    if item is None:
                        continue
                    dims = item.get_oriented_dims(placement.rotation)
                    if dims is None:
                        continue
                    color = colorByType.setdefault(
                        item.typeId,
                        palette[len(colorByType) % len(palette)]
                    )
                    tagText = ",".join(item.tags)
                    hoverText = (
                        f"item={item.id}<br>type={item.typeId}<br>tags={tagText}<br>"
                        f"pos=({placement.x},{placement.y},{placement.z})<br>"
                        f"dims={dims[0]}x{dims[1]}x{dims[2]}"
                    )
                    traces.append(
                        self._box_mesh(
                            placement.x,
                            placement.y,
                            placement.z,
                            dims[0],
                            dims[1],
                            dims[2],
                            color,
                            hovertext=hoverText
                        )
                    )
                    traces.append(
                        self._box_wireframe(
                            placement.x,
                            placement.y,
                            placement.z,
                            dims[0],
                            dims[1],
                            dims[2]
                        )
                    )

                layout = go.Layout(
                    title=dict(
                        text=(
                            f"{testName} - {containerLoad.container.instanceId} "
                            f"(fill={containerLoad.fillRate:.2%}, cost={containerLoad.container.tripCost})"
                        ),
                        x=0.5
                    ),
                    scene=dict(
                        xaxis=dict(title="X", range=[0, containerLoad.container.L]),
                        yaxis=dict(title="Y", range=[0, containerLoad.container.W]),
                        zaxis=dict(title="Z", range=[0, containerLoad.container.H]),
                        aspectmode="data"
                    ),
                    width=1200,
                    height=900,
                    paper_bgcolor="white"
                )
                figure = go.Figure(data=traces, layout=layout)
                htmlPath = os.path.abspath(
                    os.path.join(
                        packingDir,
                        f"packing_g{result['combinationIndex']:02d}_"
                        f"r{result['repeatIndex']:02d}_"
                        f"{containerLoad.container.instanceId}.html"
                    )
                )
                figure.write_html(htmlPath, include_plotlyjs=True)
                files.append(htmlPath)
                logger.info(f"  装箱可视化已保存: {htmlPath}")

                if self.outputConfig.get("saveStaticImage", False):
                    pngPath = os.path.abspath(
                        os.path.join(
                            packingDir,
                            f"packing_g{result['combinationIndex']:02d}_"
                            f"r{result['repeatIndex']:02d}_"
                            f"{containerLoad.container.instanceId}.png"
                        )
                    )
                    try:
                        figure.write_image(pngPath)
                        files.append(pngPath)
                        logger.info(f"  装箱静态图已保存: {pngPath}")
                    except Exception as imageError:
                        logger.warning(f"  装箱静态图生成失败: {imageError}")

            return files
        except Exception as e:
            logger.error(f"  装箱可视化生成失败: {e}")
            logger.debug(traceback.format_exc())
            return files

    def generateAnalysisVisualizations(
        self,
        tables: Dict[str, List[Dict[str, Any]]],
        analysisConfig: Dict[str, Any],
        testName: str
    ) -> List[str]:
        files: List[str] = []
        scatterPlots = analysisConfig.get("scatterPlots", [])
        if not scatterPlots:
            return files

        if testName == "_combined":
            analysisDir = self._getAggregateAnalysisDir()
        else:
            analysisDir = self._getCaseAnalysisDir(testName)
        os.makedirs(analysisDir, exist_ok=True)

        for index, spec in enumerate(scatterPlots, start=1):
            level = spec.get("level", "group")
            xField = spec.get("x")
            yField = spec.get("y")
            colorField = spec.get("color")
            seriesField = spec.get("series")
            chartType = str(spec.get("chartType", "scatter")).lower()
            filters = spec.get("filter")
            sortBy = spec.get("sortBy")
            sortOrder = str(spec.get("sortOrder", "desc"))
            topN = spec.get("topN")
            title = spec.get("title", f"{level}: {xField} vs {yField}")
            rows = tables.get(level, [])
            if not rows or not xField or not yField:
                continue

            filteredRows = self._apply_filters(rows, filters)
            filteredRows = [
                row for row in filteredRows
                if row.get(xField) is not None and row.get(yField) is not None
            ]
            filteredRows = self._apply_sort_and_topn(
                filteredRows,
                sortBy=sortBy,
                sortOrder=sortOrder,
                topN=topN if isinstance(topN, int) else None
            )
            if not filteredRows:
                continue

            figure = go.Figure()
            if seriesField:
                groupedRows: Dict[str, List[Dict[str, Any]]] = {}
                for row in filteredRows:
                    groupKey = str(row.get(seriesField, "unknown"))
                    groupedRows.setdefault(groupKey, []).append(row)
            else:
                groupedRows = {"all": filteredRows}

            for seriesName, seriesRows in groupedRows.items():
                hoverText = [
                    f"test={row.get('testName')}<br>"
                    f"algorithm={row.get('algorithmType')}<br>"
                    f"group={row.get('combinationIndex')}"
                    for row in seriesRows
                ]
                if chartType == "box":
                    figure.add_trace(
                        go.Box(
                            x=[row.get(xField) for row in seriesRows],
                            y=[row.get(yField) for row in seriesRows],
                            name=seriesName,
                            boxpoints="all",
                            jitter=0.4,
                            pointpos=-1.8,
                            text=hoverText,
                            hoverinfo="text"
                        )
                    )
                else:
                    markerColors = (
                        [row.get(colorField) for row in seriesRows]
                        if colorField and not seriesField else "rgb(84, 168, 139)"
                    )
                    figure.add_trace(
                        go.Scatter(
                            x=[row.get(xField) for row in seriesRows],
                            y=[row.get(yField) for row in seriesRows],
                            mode="markers",
                            name=seriesName if seriesField else None,
                            marker=dict(
                                size=10,
                                color=markerColors,
                                showscale=False
                            ),
                            text=hoverText,
                            hoverinfo="text"
                        )
                    )
            figure.update_layout(
                title=title,
                xaxis_title=xField,
                yaxis_title=yField,
                width=1000,
                height=700,
                paper_bgcolor="white"
            )
            filePath = os.path.abspath(
                os.path.join(analysisDir, f"analysis_{level}_{index:02d}.html")
            )
            figure.write_html(filePath, include_plotlyjs=True)
            files.append(filePath)
            logger.info(f"  分析图已保存: {filePath}")

        return files
