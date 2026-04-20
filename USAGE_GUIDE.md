# Usage Guide

## 这套框架是做什么的
这不是一个只会“把货物塞进一个箱子”的小程序，而是一套可以反复做实验的装箱研究框架。它适合做下面几类事情：

- 研究单集装箱尽量装满的问题
- 研究多种集装箱并存时，如何降低总运输成本
- 比较不同算法参数对结果的影响
- 做控制变量实验，比如：
  - 容器规格不变，货物规格变化
  - 货物规格不变，容器规格变化
  - 约束比例变化后，装载效率怎么变

你不需要直接修改算法代码，也可以通过修改测试集和配置文件完成大多数实验。

## 整体工作思路
可以把它理解成 5 个步骤：

1. 先写一个测试用例
   说明有哪些集装箱、有哪些货物、目标是什么、要不要生成分析图。
2. 程序读取测试用例
   把 JSON 内容变成内部的“问题实例”。
3. 算法开始尝试装箱
   算法会不断尝试把货物放进容器。
4. 装箱内核实时判断是否合法
   例如：
   - 这个姿态是否允许
   - 易碎件是不是完整贴合支撑面
   - 承压是否超过上限
   - 顶部安全间隙够不够
5. 输出结果和分析表
   程序会自动生成报告、CSV/JSON 表、装箱图、散点图。

一句话说，就是：

“你负责描述问题，框架负责跑实验、校验合法性、输出结果。”

## 目录说明

### 主要文件
- [config.json](F:\code\MathematicalModeling\Packing\config.json)
  全局配置，主要控制算法默认参数、缓存、输出和聚合分析图。
- `test/*.json`
  测试用例。你做实验时，最常修改的通常就是这里。
- [problem.md](F:\code\MathematicalModeling\Packing\problem.md)
  当前开发进度、设计思路和下一步计划。

### 主要代码模块
- [testCaseManager.py](F:\code\MathematicalModeling\Packing\testCaseManager.py)
  读取测试用例，检查格式是否合法。
- [dataStructures.py](F:\code\MathematicalModeling\Packing\dataStructures.py)
  定义货物、容器、装载方案等核心结构。
- [packingLogic.py](F:\code\MathematicalModeling\Packing\packingLogic.py)
  单容器装箱内核，负责判断“某个放置动作能不能放”。
- [optimization.py](F:\code\MathematicalModeling\Packing\optimization.py)
  算法层，负责搜索更好的方案。
- [solutionValidator.py](F:\code\MathematicalModeling\Packing\solutionValidator.py)
  最终校验器，确认整套方案是否合法。
- [resultSaver.py](F:\code\MathematicalModeling\Packing\resultSaver.py)
  输出报告、表格和方案文本。
- [visualizer.py](F:\code\MathematicalModeling\Packing\visualizer.py)
  生成装箱三维图和分析散点图。
- [batchTest.py](F:\code\MathematicalModeling\Packing\batchTest.py)
  批量运行入口。

## 最简单的使用方法

在项目目录下运行：

```powershell
python batchTest.py
```

程序会自动：
- 读取 `config.json`
- 读取 `test/` 目录下所有 JSON 测试集
- 对每个测试集跑所有参数组合
- 生成报告、表格和图

结果会保存在：

```text
results/<时间戳>/
```

例如：

```text
results/20260420_194612/
```

## 测试用例怎么写
每个测试用例都是一个 JSON 文件。建议把一个测试用例理解成“一组完整实验条件”。

### 基本结构

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

下面分别解释。

## 一、`containerTypes`：定义可用的集装箱类型
这里写“有哪些规格的集装箱可以用”。

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

### 字段说明
- `typeId`
  容器类型编号，自己取名字，建议英文或拼音，不能重复。
- `L`
  容器长度。
- `W`
  容器宽度。
- `H`
  容器高度。
- `maxWeight`
  最大载重。
- `tripCost`
  使用 1 个该类型容器的单趟成本。
- `maxInstances`
  可选。限制这种容器最多能用几个。
  如果不写，默认视为不限量。

### 中文理解
如果你研究“最低总成本”，这里通常要写 2 种或以上容器。
如果你研究“单集装箱满容率”，这里通常只写 1 种容器。

## 二、`itemTypes`：定义货物种类
这里写“有哪些货物，每种有多少件”。

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
  },
  {
    "typeId": "oriented_column",
    "l": 30,
    "w": 25,
    "h": 45,
    "weight": 55,
    "count": 3,
    "tags": ["oriented"]
  }
]
```

### 字段说明
- `typeId`
  货物类型编号，不能重复。
- `l` `w` `h`
  货物长、宽、高。
- `weight`
  单件重量。
- `count`
  这种货物有多少件。
- `tags`
  货物标签，决定它属于哪类约束。

### 当前支持的标签

#### `standard`
标准件。

含义：
- 可任意方向摆放
- 可堆叠
- 无特殊约束

#### `fragile`
易碎件。

含义：
- 可任意方向摆放
- 不能作为承重下层继续堆叠
- 底面必须完整贴合地面或标准件顶面
- 不能部分悬空

#### `oriented`
定向件。

含义：
- 只能用一种姿态摆放
- 可堆叠
- 上层货物重心不能超出其投影范围

## 三、`globalConstraints`：全局约束
这里写整个场景都要遵守的规则。

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

### 字段说明
- `orthogonalOnly`
  是否只允许正交摆放。
  `true` 表示货物边必须和箱体边平行。
- `allowCompression`
  是否允许挤压。
  当前一般设成 `false`。
- `allowSplit`
  是否允许拆分货物。
  当前一般设成 `false`。
- `minTopClearanceCm`
  货物顶部和车厢顶部至少保留多少厘米安全间隙。
- `maxBearingPressureKgPerM2`
  支撑承压上限，单位是 `kg/m²`。

## 四、`objective`：目标函数
这决定程序“什么样的方案算更好”。

### 情况 A：研究单箱尽量装满

```json
"objective": {
  "name": "max_fill_rate",
  "primaryMetric": "totalFillRate",
  "primaryOrder": "max",
  "tieBreakers": [
    {
      "metric": "packedItemCount",
      "order": "max"
    },
    {
      "metric": "totalCost",
      "order": "min"
    }
  ]
}
```

中文意思：
- 先看总满容率，越大越好
- 如果差不多，再看装进去的件数，越多越好
- 再一样，就看总成本，越低越好

### 情况 B：研究最低总成本

```json
"objective": {
  "name": "min_total_cost",
  "primaryMetric": "totalCost",
  "primaryOrder": "min",
  "tieBreakers": [
    {
      "metric": "packedItemCount",
      "order": "max"
    },
    {
      "metric": "totalFillRate",
      "order": "max"
    }
  ]
}
```

中文意思：
- 先让总成本最低
- 如果成本一样，优先装进去更多货物
- 再一样，优先满容率更高

### 常见可用指标
当前框架里比较常用的指标有：
- `totalFillRate`
  所有已使用容器总体积利用率
- `totalCost`
  总运输成本
- `packedItemCount`
  已装货件数
- `unpackedItemCount`
  未装货件数
- `usedContainerCount`
  实际用了多少个容器
- `avgContainerFillRate`
  平均每个容器的满容率

## 五、`analysis`：分析图配置
这里写“希望自动生成什么散点图”。

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

### 字段说明
- `level`
  用哪一层数据作图。
  当前常用：
  - `run`
  - `group`
  - `container`
  - `placement`
- `x`
  横轴字段名。
- `y`
  纵轴字段名。
- `title`
  图标题。
- `color`
  可选。按某个字段上色。

### 实用示例

#### 1. 看算法迭代数和满容率关系

```json
{
  "level": "group",
  "x": "iterations",
  "y": "avgFillRate",
  "title": "Iterations vs Avg Fill Rate"
}
```

#### 2. 看货物规格种类数和效率关系

```json
{
  "level": "group",
  "x": "itemTypeCount",
  "y": "avgFillRate",
  "title": "Item Type Count vs Avg Fill Rate"
}
```

#### 3. 看容器尺寸比例和效率关系

```json
{
  "level": "group",
  "x": "containerAspectRatio",
  "y": "avgFillRate",
  "title": "Container Aspect Ratio vs Avg Fill Rate"
}
```

#### 4. 看总成本和满容率关系

```json
{
  "level": "group",
  "x": "avgTotalCost",
  "y": "avgFillRate",
  "title": "Cost vs Fill Rate"
}
```

## 六、`scenarioMetadata`：场景说明字段
这个部分不会直接改变装箱结果，但会进入 CSV/JSON 表，方便后续分析。

示例：

```json
"scenarioMetadata": {
  "scenarioTag": "containerVaried_itemFixed",
  "studyGroup": "cost_balanced"
}
```

### 建议常写的字段
- `scenarioTag`
  场景标签，例如：
  - `containerFixed_itemVaried`
  - `containerVaried_itemFixed`
  - `containerVaried_itemVaried`
- `studyGroup`
  实验分组名
- 也可以自行补充：
  - `difficultyLevel`
  - `caseFamily`
  - `containerShapeClass`

## 全局配置怎么改
全局配置放在 [config.json](F:\code\MathematicalModeling\Packing\config.json)。

## 一、算法默认参数
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

### 参数说明

#### `iterations`
算法迭代次数。

如果写成：

```json
"iterations": {
  "min": 20,
  "max": 60,
  "step": 20
}
```

表示会自动跑：
- 20
- 40
- 60

这适合做“迭代数影响结果”的实验。

#### `useTimeSeed`
是否使用时间随机种子。

- `false`
  每次运行结果更容易复现
- `true`
  每次都会更随机

一般做正式实验建议先用 `false`。

#### `baseSeed`
固定随机种子的起点。

例如：

```json
"baseSeed": 42
```

#### `repeatCount`
每组参数重复跑几次。

例如：

```json
"repeatCount": 3
```

表示同一组参数会跑 3 次，方便统计平均值和波动。

## 二、当前可选算法

### 1. `greedy_search`
中文理解：
先按某种顺序装，再不断打乱顺序重试。

适合：
- 跑得快
- 做基础对比
- 快速试验

主要参数：
- `iterations`

示例：

```json
"greedy_search": {
  "iterations": {
    "min": 20,
    "max": 100,
    "step": 20
  },
  "baseSeed": 42,
  "repeatCount": 3
}
```

### 2. `simulated_annealing`
中文理解：
模拟退火。允许在搜索过程中暂时接受较差方案，试图跳出局部最优。

适合：
- 想让搜索更灵活一些
- 允许多花一点时间换更好的结果

主要参数：
- `iterations`
- `initialTemp`
  初始温度。越高越“敢乱跳”。
- `coolingRate`
  降温速度。越接近 1，降温越慢。
- `minTemp`
  降到这个温度附近就停止。

示例：

```json
"simulated_annealing": {
  "iterations": {
    "min": 20,
    "max": 100,
    "step": 20
  },
  "initialTemp": 50.0,
  "coolingRate": 0.95,
  "minTemp": 0.1,
  "baseSeed": 42,
  "repeatCount": 3
}
```

### 参数怎么理解得更直白

#### `iterations`
“试多少次不同方案”。
一般越大越慢，但可能更好。

#### `initialTemp`
“一开始敢不敢尝试差一点的方案”。
越大，搜索越不保守。

#### `coolingRate`
“后来降温有多快”。
- `0.90`
  降得快
- `0.98`
  降得慢

#### `minTemp`
“降到多冷就停止”。

## 三、输出和可视化配置

### `enableCache`
是否启用缓存。

- `true`
  第二次同配置运行会更快
- `false`
  每次都重新计算

### `exportSummaryData`
是否导出 CSV/JSON 表。

建议保持 `true`。

### `saveSolutionText`
是否导出最优方案文本。

可选值：
- `"false"`
- `"true"`
- `"only-best"`

推荐：

```json
"saveSolutionText": "only-best"
```

### `enableVisualization`
是否生成图。

推荐：

```json
"enableVisualization": true
```

### `analysisCharts`
这是跨测试用例聚合图配置。

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

它和每个测试用例里的 `analysis.scatterPlots` 不同：
- 测试用例里的 `analysis`
  只画该测试用例自己的图
- `config.json` 里的 `analysisCharts`
  会画所有测试用例汇总后的总图

## 结果文件怎么看

假设输出目录是：

```text
results/20260420_194612/
```

### 一、每个测试用例目录里的文件

#### `results_*.txt`
文本报告。

适合先快速看：
- 哪组参数最好
- 成本多少
- 满容率多少
- 是否有非法方案

#### `run_*.csv / json`
每次运行一行。

适合看：
- 同一组参数不同重复结果
- 每次运行的时间、成本、满容率

#### `group_*.csv / json`
每组参数一行。

适合看：
- 平均结果
- 标准差
- 参数对结果的影响

#### `container_*.csv / json`
每个容器实例一行。

适合看：
- 实际用了几个容器
- 每个容器的装载率
- 每个容器的类型和成本

#### `placement_*.csv / json`
每个放置动作一行。

适合看：
- 某个货物放在哪个容器
- 旋转姿态是什么
- 支撑面积比
- 承压值
- 顶部间隙

#### `solutions/plan_best_*.txt`
最优方案文本。

适合人工检查方案细节。

#### `packing_*.html`
装箱三维图。

适合直观看每个容器内部怎么摆。

#### `analysis_*.html`
分析图。

适合看参数变化和结果变化的关系。

### 二、顶层目录里的总表

#### `all_run.csv / json`
所有测试用例的所有运行合并表。

#### `all_group.csv / json`
所有测试用例的参数组统计总表。

#### `all_container.csv / json`
所有测试用例的容器实例总表。

#### `all_placement.csv / json`
所有测试用例的放置明细总表。

这几张表最适合后续自己拿去做：
- Excel 分析
- 画图
- 写论文图表
- 进一步筛选对比

## 常见实验怎么配

## 1. 我只想研究“单个集装箱尽量装满”
建议：
- `containerTypes` 只写 1 种
- `objective.primaryMetric = "totalFillRate"`
- `objective.primaryOrder = "max"`

## 2. 我想研究“最低总成本”
建议：
- `containerTypes` 写 2 种或以上
- 每种写不同 `tripCost`
- `objective.primaryMetric = "totalCost"`
- `objective.primaryOrder = "min"`

## 3. 我想看“迭代次数是否真的有用”
建议：
- 在 `algorithmDefaults` 里把 `iterations` 写成范围
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

## 4. 我想做“容器不变、货物变化”的实验
建议：
- 多个测试用例共用同一组 `containerTypes`
- 只改 `itemTypes`
- 在 `scenarioMetadata` 里打上：

```json
"scenarioTag": "containerFixed_itemVaried"
```

## 5. 我想做“容器变化、货物不变”的实验
建议：
- 保持 `itemTypes` 基本不动
- 改 `containerTypes`
- 在 `scenarioMetadata` 里打上：

```json
"scenarioTag": "containerVaried_itemFixed"
```

## 常见注意事项

### 1. 单位要统一
这套框架目前默认你自己保持单位一致。

尤其注意：
- 尺寸单位
- 重量单位
- 承压上限 `kg/m²`
- 顶部间隙 `cm`

当前代码里，尺寸按“厘米”使用会最自然。

### 2. `typeId` 不要重复
不管是容器还是货物，`typeId` 都建议保持唯一。

### 3. 先用小规模测试调通，再上大规模
建议先从：
- 货物种类少
- 货物数量少
- 参数组少

开始，确认逻辑没问题，再扩大实验。

### 4. 如果运行慢
优先减少：
- `iterations`
- `repeatCount`
- 测试用例数量

### 5. 如果结果“不好”
先不要立刻怀疑程序错了，先区分：
- 是约束太严，根本装不进去
- 还是求解器还不够强

可以先看：
- `unpackedCount`
- `totalCost`
- `container_*.csv`
- `placement_*.csv`

## 当前局限
虽然框架已经能跑多容器、成本目标和第一小问约束，但目前仍然有这些局限：

- 多容器成本求解器还是基础版
- 当前图表类型主要是散点图
- 标签体系还不够丰富
- 更复杂的业务约束还没完全扩展

如果你后面继续做更深入实验，建议优先关注：
- 成本目标下的求解质量
- 更多标签与约束
- 更系统的控制变量测试集
- 更丰富的分析图和统计方法

## 一句最实用的建议
如果你不熟悉编程，最安全的使用方式就是：

1. 复制一个现有 `test/*.json`
2. 改容器、货物、目标和分析图配置
3. 运行 `python batchTest.py`
4. 先看 `results_*.txt`
5. 再看 `group_*.csv` 和生成的图

这样基本可以完成大多数实验，不需要先读懂全部代码。
