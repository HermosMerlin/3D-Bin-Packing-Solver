# 使用手册

## 1. 先看整体
这套框架现在做两类问题：

- 单容器满容率优化
- 多容器最低总成本优化

主流程很简单：

1. 在 `test/` 里写测试集
2. 在 `config.json` 里改算法参数和输出设置
3. 运行：

```powershell
python batchTest.py
```

4. 去 `results/<时间戳>/` 看报告、表格和图

## 2. 主要改哪几个文件

- `test/*.json`
  每个文件是一组实验条件。大多数情况下，先改这里。
- `config.json`
  改算法默认参数、重复次数、缓存、分析图。
- `problem.md`
  看当前框架状态、已完成内容和下一步计划。

如果只是跑实验，通常不需要先改代码。

## 3. 测试集结构
一个测试集最常用的字段是：

```json
{
  "containerTypes": [],
  "itemTypes": [],
  "globalConstraints": {},
  "objective": {},
  "analysis": {},
  "scenarioMetadata": {}
}
```

### 3.1 `containerTypes`
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

字段含义：

- `typeId`
  容器类型名，自己取，别重复。
- `L/W/H`
  长宽高。
- `maxWeight`
  最大载重。
- `tripCost`
  单个容器单趟成本。
- `maxInstances`
  可选。限制这种容器最多能用几个。

怎么用：

- 研究单箱装满：通常只写 1 种容器
- 研究最低成本：通常写 2 种或以上容器，并给不同 `tripCost`

### 3.2 `itemTypes`
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

字段含义：

- `typeId`
  货物类型名，别重复。
- `l/w/h`
  长宽高。
- `weight`
  单件重量。
- `count`
  件数。
- `tags`
  货物标签。

当前常用标签：

- `standard`
  标准件，可任意方向摆放，可堆叠。
- `fragile`
  易碎件，不能作为下层承重件，底面必须完整贴合地面或标准件顶面。
- `oriented`
  定向件，只允许一种姿态，可堆叠，但上层重心不能超出其投影。

### 3.3 `globalConstraints`
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

常用字段：

- `orthogonalOnly`
  是否只允许正交摆放。通常保持 `true`。
- `allowCompression`
  是否允许挤压。通常 `false`。
- `allowSplit`
  是否允许拆分。通常 `false`。
- `minTopClearanceCm`
  顶部安全间隙。
- `maxBearingPressureKgPerM2`
  承压上限。

### 3.4 `objective`
写优化目标。

#### 目标一：满容率优先

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

#### 目标二：总成本优先

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

### 3.5 `analysis`
写单个测试集的分析图。

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

最常改的是：

- `level`
  画哪一层表。常用：
  - `run`
  - `group`
  - `container`
- `x`
  横轴字段。
- `y`
  纵轴字段。
- `title`
  图标题。
- `color`
  可选，上色字段。

常用例子：

- `iterations -> avgFillRate`
- `itemTypeCount -> avgFillRate`
- `containerAspectRatio -> avgFillRate`
- `avgTotalCost -> avgFillRate`

### 3.6 `scenarioMetadata`
写场景标签，方便后续筛选和画图。

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

## 4. `config.json` 怎么改

## 4.1 算法默认参数
最常改的是 `algorithmDefaults`。

示例：

```json
"algorithmDefaults": {
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
}
```

### 常用参数

#### `iterations`
算法迭代次数。

如果写成范围：

```json
"iterations": {
  "min": 20,
  "max": 100,
  "step": 20
}
```

就会自动跑：
- 20
- 40
- 60
- 80
- 100

适合做“迭代数影响结果”的实验。

#### `repeatCount`
每组参数重复跑几次。

```json
"repeatCount": 3
```

适合做均值和波动统计。

#### `baseSeed`
固定随机种子起点。

```json
"baseSeed": 42
```

#### `useTimeSeed`
是否用时间随机种子。

- `false`
  结果可复现
- `true`
  每次更随机

正式实验一般优先 `false`。

## 4.2 当前可选算法

### `greedy_search`
特点：
- 快
- 适合基础对比
- 适合先试

主要参数：
- `iterations`

### `simulated_annealing`
特点：
- 搜索更灵活
- 运行更慢一些
- 更适合后续深入比较

主要参数：
- `iterations`
- `initialTemp`
- `coolingRate`
- `minTemp`

参数直观理解：

- `initialTemp`
  一开始搜索有多“敢跳”。
- `coolingRate`
  降温速度。越接近 1，降温越慢。
- `minTemp`
  降到多低就停。

## 4.3 输出配置
最常改的是这些：

- `enableCache`
  是否启用缓存。通常保持 `true`。
- `exportSummaryData`
  是否导出 CSV/JSON。通常保持 `true`。
- `saveSolutionText`
  是否导出最优方案文本。推荐 `"only-best"`。
- `enableVisualization`
  是否生成图。通常保持 `true`。
- `analysisCharts`
  跨测试用例聚合图配置。

示例：

```json
"analysisCharts": [
  {
    "level": "group",
    "x": "containerAspectRatio",
    "y": "avgFillRate",
    "title": "Container Aspect Ratio vs Avg Fill Rate"
  }
]
```

注意：

- 测试集里的 `analysis`
  只画该测试集自己的图
- `config.json` 里的 `analysisCharts`
  画所有测试集合并后的总图

## 5. 输出结果怎么看
每次运行会生成一个时间戳目录：

```text
results/<时间戳>/
```

### 每个测试集目录里

- `results_*.txt`
  文本报告。先看这个。
- `run_*.csv/json`
  每次运行一行。
- `group_*.csv/json`
  每组参数一行，最适合看调参结果。
- `container_*.csv/json`
  每个容器实例一行，适合看用了多少箱、每箱装得怎么样。
- `placement_*.csv/json`
  每个放置动作一行，适合查支撑、承压、姿态。
- `solutions/plan_best_*.txt`
  最优方案文本。
- `packing_*.html`
  装箱三维图。
- `analysis_*.html`
  该测试集自己的分析图。

### 顶层目录里

- `all_run.csv/json`
- `all_group.csv/json`
- `all_container.csv/json`
- `all_placement.csv/json`

这些是所有测试集合并后的总表，适合后续自己做筛选、画图、写论文。

## 6. 常见实验怎么配

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

如果是成本目标，把 `y` 改成 `avgTotalCost`。

### 做“容器不变、货物变化”

- 多个测试集共用同一组 `containerTypes`
- 只改 `itemTypes`
- `scenarioTag` 建议写成：

```json
"scenarioTag": "containerFixed_itemVaried"
```

### 做“容器变化、货物不变”

- 保持 `itemTypes` 基本不变
- 改 `containerTypes`
- `scenarioTag` 建议写成：

```json
"scenarioTag": "containerVaried_itemFixed"
```

## 7. 实际使用建议

- 先从小规模测试开始，再扩大。
- 正式实验先用 `useTimeSeed = false`。
- 想快一点就先减：
  - `iterations`
  - `repeatCount`
  - 测试集数量
- 如果结果不理想，先区分：
  - 是约束太严，根本装不进去
  - 还是求解器还不够强

优先看这些字段：
- `unpackedCount`
- `totalCost`
- `avgFillRate`
- `container_*.csv`
- `placement_*.csv`

## 8. 当前局限
当前框架已经能跑：
- 多容器
- 成本目标
- 第一小问约束
- 散点图分析

但还没完全做好的部分有：
- 多容器成本求解质量还只是基础版
- 图表类型还不够丰富
- 标签体系还可以继续扩展
- 更复杂业务约束还没完全接进来

## 9. 最实用的用法
如果只是想尽快开跑实验，建议直接按这个顺序来：

1. 复制一个 `test/*.json`
2. 改容器、货物、目标、分析图
3. 跑 `python batchTest.py`
4. 先看 `results_*.txt`
5. 再看 `group_*.csv` 和图

这样基本够用，不需要先看全部代码。
