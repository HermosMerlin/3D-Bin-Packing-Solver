# 使用手册

## 1. 先看整体
这套框架现在主要做两类问题：

- 单容器满容率优化
- 多容器最低总成本优化

主流程：

1. 在 `test/` 写测试集
2. 在 `config.json` 改默认参数
3. 运行 `python batchTest.py`
4. 去 `results/<时间戳>/` 看报告、表格和图

输出已经按 `logs / cases / aggregate / validation` 分层，不会再把所有文件堆在一起。

## 2. 主要改哪几个文件

- `test/*.json`
  正式实验集。最常改这里。
- `config.json`
  算法默认参数、缓存、可视化、验证套件开关。
- `validation/cases/*.json`
  最小功能验证样例。平时可以不跑，调试框架时用。
- `problem.md`
  当前进度、设计思路和下一步计划。

## 3. 测试集 schema
正式测试集最少包含这些字段：

```json
{
  "schemaVersion": 2,
  "units": {
    "lengthUnit": "cm",
    "weightUnit": "kg",
    "bearingPressureUnit": "kg/m^2",
    "clearanceUnit": "cm"
  },
  "containerTypes": [],
  "itemTypes": [],
  "globalConstraints": {},
  "objective": {},
  "analysis": {},
  "scenarioMetadata": {}
}
```

### 3.1 `schemaVersion`
当前固定写：

```json
"schemaVersion": 2
```

### 3.2 `units`
当前单位约定固定写：

```json
"units": {
  "lengthUnit": "cm",
  "weightUnit": "kg",
  "bearingPressureUnit": "kg/m^2",
  "clearanceUnit": "cm"
}
```

这套框架当前就是按这组单位实现的，不建议改。

### 3.3 `containerTypes`
写可用容器类型。

示例：

```json
"containerTypes": [
  {
    "typeId": "small_box",
    "L": 100,
    "W": 80,
    "H": 90,
    "maxWeight": 3000,
    "tripCost": 260
  },
  {
    "typeId": "large_box",
    "L": 140,
    "W": 100,
    "H": 110,
    "maxWeight": 6500,
    "tripCost": 430
  }
]
```

字段：

- `typeId`
- `L / W / H`
- `maxWeight`
- `tripCost`
- `maxInstances` 可选

怎么用：

- 单箱满容：通常只写 1 种容器
- 成本优化：通常写 2 种或以上容器，并给不同 `tripCost`

### 3.4 `itemTypes`
写货物种类。

示例：

```json
"itemTypes": [
  {
    "typeId": "std_block",
    "l": 50,
    "w": 40,
    "h": 20,
    "weight": 85,
    "count": 5,
    "tags": ["standard"]
  },
  {
    "typeId": "fragile_case",
    "l": 35,
    "w": 35,
    "h": 18,
    "weight": 28,
    "count": 4,
    "tags": ["fragile"]
  }
]
```

字段：

- `typeId`
- `l / w / h`
- `weight`
- `count`
- `tags`

当前常用标签：

- `standard`
  标准件，可任意方向摆放，可堆叠。
- `fragile`
  易碎件，不能作为下层承重件，底面必须完整贴合地面或标准件顶面。
- `oriented`
  定向件，只允许一种姿态，可堆叠，但上层重心不能超出其投影。

### 3.5 `globalConstraints`
写全局约束。

示例：

```json
"globalConstraints": {
  "orthogonalOnly": true,
  "allowCompression": false,
  "allowSplit": false,
  "minTopClearanceCm": 3,
  "maxBearingPressureKgPerM2": 500
}
```

最常用字段：

- `orthogonalOnly`
- `allowCompression`
- `allowSplit`
- `minTopClearanceCm`
- `maxBearingPressureKgPerM2`

### 3.6 `objective`
写优化目标。

满容率优先：

```json
"objective": {
  "name": "max_fill_rate",
  "primaryMetric": "totalFillRate",
  "primaryOrder": "max",
  "tieBreakers": [
    { "metric": "packedItemCount", "order": "max" },
    { "metric": "totalCost", "order": "min" }
  ]
}
```

总成本优先：

```json
"objective": {
  "name": "min_total_cost",
  "primaryMetric": "totalCost",
  "primaryOrder": "min",
  "tieBreakers": [
    { "metric": "packedItemCount", "order": "max" },
    { "metric": "totalFillRate", "order": "max" }
  ]
}
```

常用指标：

- `totalFillRate`
- `totalCost`
- `packedItemCount`
- `unpackedItemCount`
- `usedContainerCount`
- `avgContainerFillRate`

### 3.7 `analysis`
写单个测试集自己的分析图。

示例：

```json
"analysis": {
  "scatterPlots": [
    {
      "level": "group",
      "x": "iterations",
      "y": "avgFillRate",
      "title": "Iterations vs Avg Fill Rate"
    }
  ]
}
```

当前支持的常用配置：

- `level`
  `run / group / container / placement`
- `x`
- `y`
- `title`
- `color`
- `series`
- `chartType`
  目前常用 `scatter`、`box`
- `filter`
- `sortBy`
- `sortOrder`
- `topN`

### 3.8 `scenarioMetadata`
写场景标签，方便后续筛选。

示例：

```json
"scenarioMetadata": {
  "scenarioTag": "containerVaried_itemFixed",
  "studyGroup": "cost_balanced"
}
```

建议常写：

- `scenarioTag`
- `studyGroup`

## 4. `config.json` 常改项

## 4.1 算法默认参数
在 `algorithmDefaults` 里改。

示例：

```json
"greedy_search": {
  "iterations": {
    "min": 20,
    "max": 40,
    "step": 20
  },
  "useTimeSeed": false,
  "baseSeed": 42,
  "repeatCount": 1
}
```

最常改：

- `iterations`
  迭代次数。可写固定值，也可写范围。
- `repeatCount`
  每组参数重复次数。
- `baseSeed`
  固定随机种子起点。
- `useTimeSeed`
  是否用时间种子。正式实验建议 `false`。

当前算法：

- `greedy_search`
- `simulated_annealing`

退火额外参数：

- `initialTemp`
- `coolingRate`
- `minTemp`

## 4.2 验证套件开关
在 `validation` 段里改。

示例：

```json
"validation": {
  "enableValidationSuite": false,
  "runBeforeBatch": false,
  "stopOnValidationFailure": true,
  "casesDir": "validation/cases",
  "exportValidationSummary": true
}
```

含义：

- `enableValidationSuite`
  是否启用验证功能。
- `runBeforeBatch`
  正式实验前是否先跑验证。
- `stopOnValidationFailure`
  验证失败时是否中止正式运行。
- `casesDir`
  验证样例目录。
- `exportValidationSummary`
  是否导出验证汇总。

## 4.3 输出配置
常用：

- `enableCache`
- `exportSummaryData`
- `saveSolutionText`
- `enableVisualization`
- `analysisCharts`

`analysisCharts` 是跨测试用例聚合图配置，不是单个测试集自己的图。

## 5. CLI 单独运行
现在很多调试动作不需要改 `config.json`，可以直接命令行覆盖。

### 只跑一个测试集

```powershell
python batchTest.py --case question1
```

### 按通配符跑一批测试集

```powershell
python batchTest.py --case-pattern "*hard*"
```

### 只跑一个算法

```powershell
python batchTest.py --case question1 --algorithm greedy_search
```

### 临时改迭代次数和重复次数

```powershell
python batchTest.py --case question1 --algorithm greedy_search --iterations 1 --repeat 1
```

### 调试时关可视化

```powershell
python batchTest.py --case question1 --no-viz
```

### 调试时关缓存

```powershell
python batchTest.py --case question1 --no-cache
```

### 给结果目录打标签

```powershell
python batchTest.py --case question1 --output-tag debug_question1
```

### 只跑功能验证套件

```powershell
python batchTest.py --validation-only --output-tag validation_only
```

### 先跑验证，再跑正式实验

```powershell
python batchTest.py --run-validation
```

## 6. 验证套件怎么用
验证样例单独放在：

```text
validation/cases/
```

它的目标不是做正式实验，而是验证：

- schema 能否加载
- 约束是否按预期生效
- 非法方案是否能被拦住
- 输出链路是否正常

验证结果会输出到：

```text
results/<时间戳>/validation/
  summary.json
  summary.txt
```

## 7. 输出结果怎么看
每次运行会生成一个时间戳目录：

```text
results/<时间戳>/
  logs/
  cases/
  aggregate/
  validation/
  manifest.json
  summary.md
```

### `cases/<testName>/reports/`
- `results_*.txt`
  先看这个。

### `cases/<testName>/tables/csv|json/`
- `run_*`
- `group_*`
- `container_*`
- `placement_*`

最常看的是 `group_*`。

### `cases/<testName>/plans/`
- `plan_best_*.txt`

### `cases/<testName>/visuals/packing/`
- 装箱三维图。

### `cases/<testName>/visuals/analysis/`
- 该测试集自己的图。

### `aggregate/tables/csv|json/`
- `all_run.*`
- `all_group.*`
- `all_container.*`
- `all_placement.*`

### `aggregate/visuals/analysis/`
- 跨测试用例聚合图。

### 根目录文件
- `manifest.json`
  本次运行的结构化索引。
- `summary.md`
  简版运行摘要。

## 8. 常用实验配置

### 只研究单集装箱满容率

- `containerTypes` 只写 1 种
- `objective.primaryMetric = "totalFillRate"`
- `objective.primaryOrder = "max"`

### 研究最低总成本

- `containerTypes` 写 2 种或以上
- 给不同 `tripCost`
- `objective.primaryMetric = "totalCost"`
- `objective.primaryOrder = "min"`

### 看迭代数是否有效

- 在 `config.json` 里把 `iterations` 写成范围
- 在 `analysis.scatterPlots` 里加：

```json
{
  "level": "group",
  "x": "iterations",
  "y": "avgFillRate",
  "title": "Iterations vs Avg Fill Rate"
}
```

如果研究成本目标，就把 `y` 改成 `avgTotalCost`。

## 9. 实际使用建议

- 先从小规模 case 开始，再扩大。
- 正式实验优先 `useTimeSeed = false`。
- 想快一点就先减：
  - `iterations`
  - `repeatCount`
  - 测试集数量
- 如果先想确认框架没坏，先跑：

```powershell
python batchTest.py --validation-only
```

- 如果结果不理想，先看：
  - `unpackedCount`
  - `totalCost`
  - `avgFillRate`
  - `container_*.csv`
  - `placement_*.csv`

## 10. 当前局限

- 多容器成本求解质量还只是基础版
- 图表类型还不够丰富
- 标签体系还可以继续扩展
- 更复杂业务约束还没完全接进来
- 验证样例集目前还不大

## 11. 最实用的用法
平时最推荐的顺序：

1. 复制一个 `test/*.json`
2. 改容器、货物、目标、分析图
3. 必要时用 CLI 覆盖单次参数
4. 跑 `python batchTest.py`
5. 先看 `cases/<testName>/reports/results_*.txt`
6. 再看 `cases/<testName>/tables/csv/group_*.csv`

这样已经足够覆盖大多数实验和调试场景。
