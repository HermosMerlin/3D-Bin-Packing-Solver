# 当前框架问题与工作进度

## 当前状态
项目已经完成了第一阶段的框架加固，当前具备：
- 缓存与代码版本绑定
- 解合法性校验
- 默认可复现实验
- 重复试验统计
- CSV/JSON 基础汇总导出

截至 2026-04-20 当前轮实现，框架已经进一步具备：
- 新的测试用例 schema：`containerTypes / itemTypes / objective / analysis / scenarioMetadata`
- 多容器方案结构：`ProblemInstance / ContainerType / ContainerInstance / ShipmentPlan`
- 第一小问标签约束的正式字段化表达
- 约束感知单容器装箱内核
- 即时放置反馈：`isFeasible / reasonCode / supportAreaRatio / bearingPressure / topClearanceCm`
- 方案层目标评估：支持 `max totalFillRate` 和 `min totalCost`
- `run/group/container/placement` 四层分析表
- 每测试用例分析图 + 跨测试用例聚合分析图
- 面向非程序背景用户的使用手册：`USAGE_GUIDE.md`

如果目标只是“单容器、单目标、做基础装箱实验”，当前框架已经超过 baseline。

但现在目标已经变了。项目不再只是一个单容器装箱程序，而是要往“可扩展的建模实验框架”走。按这个目标看，当前最大的短板已经不只是算法强弱，而是数据模型、目标函数抽象、结果汇总结构和分析可视化能力都还停留在第一版。

## 已确认的设计原则
在最新讨论里，已经明确了两条重要原则：

1. 暂时不考虑兼容旧版本 schema
   这意味着可以直接重设计测试用例格式和核心对象，不必为了保留旧字段而牺牲结构清晰度。
2. 单集装箱满容问题和多集装箱成本问题要共用一套框架
   不能做成两套互相独立的求解器。更合理的做法是：
   - 同一套 `ProblemInstance`
   - 同一套结果结构
   - 同一套分析数据表
   - 用不同 `objective` 和不同求解策略覆盖不同研究问题

## 已验证进度
2026-04-20 已连续运行两轮 `python batchTest.py`：
- 每轮成功加载 2 个测试用例
- 每轮包含 12 个参数组、36 次实际运行
- 每轮成功生成 4 个可视化，失败 0 个
- 第二轮在固定 seed 配置下完整命中缓存
- 两轮参数组汇总结果一致
- 单次运行结果在忽略 `isCached` 状态位后完全一致

说明当前“缓存签名 + 合法性校验 + 可复现实验 + 汇总导出”这条链路已经稳定。

在本轮框架重构完成后，又完成了新的端到端验证：
- 新 schema 测试集可正常加载
- 多容器成本目标可正常求解并导出结果
- 第二轮运行可以在新结构下重新命中缓存
- 每个测试用例都会生成：
  - 文本报告
  - `run/group/container/placement` CSV/JSON
  - 最优方案文本
  - 装箱三维图
  - 分析散点图
- 顶层结果目录会生成跨测试用例总表和聚合分析图

最新一次验证结果目录为：
- `results/20260420_201620/`

当前输出目录已经按用途分层：
- `logs/`
- `cases/<testName>/reports`
- `cases/<testName>/tables/csv`
- `cases/<testName>/tables/json`
- `cases/<testName>/plans`
- `cases/<testName>/visuals/packing`
- `cases/<testName>/visuals/analysis`
- `aggregate/tables/csv`
- `aggregate/tables/json`
- `aggregate/visuals/analysis`

## 新增需求

### 1. 多规格集装箱 + 特殊货物标签 + 成本目标
新需求不是简单地“多加几个字段”，而是把问题定义本身改了：
- 集装箱不再只有一个固定规格，而是可以同时存在多个规格
- 每种集装箱有单趟成本
- 集装箱数量不限
- 目标不再只是单箱满容率，而是可以计算并优化总成本
- 货物不再只是长宽高重量，还要支持易碎品、定向品等特殊标签

这意味着当前“一个 `Container` + 一个 `PackingSolution`”的结构已经不够用。

更进一步地说，这个变化会直接改变算法模块的职责：
- 以前算法只需要在单个容器内调物品顺序
- 现在算法还要决定容器类型选择、容器数量、物品分配、单容器内装载、总体目标排序

所以这已经不是“换一个评分指标”，而是“问题状态空间发生了变化”。

### 2. 灵活的参数分析与散点图输出
新需求要求框架能方便做实验分析，而不是只能生成单次装箱三维图。

需要支持的能力包括：
- 指定任意横轴/纵轴字段生成散点图
- 对比单算法的 `iterations -> volumeRate`
- 对比 `货物规格种类数 -> 满容率`
- 对比 `集装箱尺寸比例 -> 满容率`
- 对比 `集装箱规格不变、货物规格变化 -> 装载效率`
- 对比 `集装箱规格变化、货物规格变化 -> 装载效率`
- 后续还能继续扩展到 `总成本 -> 满容率`、`容器类型数 -> 算法稳定性` 等分析

这意味着当前结果导出虽然已经有 CSV/JSON，但字段体系还不够通用，也没有“分析视图”的抽象层。

## 第一小问约束已确认
第一小问的货物与装载约束已经明确，可以作为新 schema 和新校验层的直接输入。

### 货物类型定义

#### 1. 标准件 `standard`
- 货物形状为刚性长方体
- 可任意方向摆放
- 可堆叠
- 无额外特殊约束

建议映射字段：
- `allowedRotations = [0, 1, 2, 3, 4, 5]`
- `canSupportOthers = true`
- `allowedSupportSources = ["floor", "standard", "oriented"]`

#### 2. 易碎件 `fragile`
- 货物形状为刚性长方体
- 可任意方向摆放
- 不可作为承重下层继续堆叠
- 摆放时底面必须完全贴合箱体底面或其他标准件顶面

已经确认的理解是：
- 易碎件可以放在地面
- 易碎件可以放在标准件顶面
- 易碎件上方不能再放其他货物
- 易碎件不允许部分悬空

建议映射字段：
- `allowedRotations = [0, 1, 2, 3, 4, 5]`
- `canSupportOthers = false`
- `allowedSupportSources = ["floor", "standard"]`
- `requiredSupportAreaRatio = 1.0`

#### 3. 定向件 `oriented`
- 货物形状为刚性长方体
- 有明确方向要求
- 仅允许一种摆放姿态
- 可堆叠
- 上层货物重心不得超出下层投影范围

建议映射字段：
- `allowedRotations = [0]`
- `canSupportOthers = true`
- `allowedSupportSources = ["floor", "standard", "oriented"]`
- `requiredSupportProjectionContainment = true`

### 全局几何与装载规则
- 所有货物均为刚性长方体
- 不可挤压
- 不可拆分
- 货物之间不得重叠
- 货物与箱体之间不得重叠
- 所有摆放必须保持正交，即货物棱边与箱体棱边平行

建议映射字段：
- `orthogonalOnly = true`
- `allowCompression = false`
- `allowSplit = false`

### 附加约束

#### 1. 承重约束
- 下层货物承重上限为 `500 kg/m^2`
- 超重则不允许堆叠

建议映射字段：
- `maxBearingPressureKgPerM2 = 500`

#### 2. 稳定性与顶部安全间隙
- 货物高度不得超过车厢高度
- 顶层货物距车厢顶部预留不小于 `3 cm` 安全间隙

建议映射字段：
- `minTopClearanceCm = 3`

## 受影响模块评估
在当前代码结构下，这次修改会直接影响的不是单个模块，而是整条主链路。按影响程度看，可以分成下面几层。

### 高影响模块

#### 1. [dataStructures.py](F:\code\MathematicalModeling\Packing\dataStructures.py)
这是受影响最大的模块之一。

当前问题：
- 只有 `Item`、`Container`、`PackingSolution`
- 结构默认就是“一个容器 + 一个解”
- `Item` 没有正式标签和约束字段

这次需要改成能够表达：
- `ItemType`
- `ItemConstraints`
- `ContainerType`
- `ContainerInstance`
- `Placement`
- `ShipmentPlan`
- `PlanMetrics`

如果这一层不先改，后面的算法、校验、结果导出都会被旧结构卡住。

#### 2. [testCaseManager.py](F:\code\MathematicalModeling\Packing\testCaseManager.py)
当前只会读取：
- 一个 `container`
- 一个 `itemTypes`

这次需要支持：
- `containerTypes`
- `itemTypes` 中的标签与约束字段
- `objective`
- `analysis`
- 派生的场景元数据

它不仅要做基础合法性检查，还要成为新 schema 的入口校验器。

#### 3. [optimization.py](F:\code\MathematicalModeling\Packing\optimization.py)
这是算法层的核心影响点。

当前问题：
- 输入是单个容器
- 输出是单个 `PackingSolution`
- 评价逻辑默认绑定 `volumeRate`
- 邻域操作只围绕物品顺序

新需求下必须拆层：
- `PackingKernel`
- `PlanOptimizer`
- `ObjectiveEvaluator`

否则最低总成本问题会把算法模块直接压坏。

#### 4. [solutionValidator.py](F:\code\MathematicalModeling\Packing\solutionValidator.py)
这是第二个高影响点。

当前只能校验：
- 单容器越界
- 单容器重叠
- 单容器重量汇总

需要新增的校验至少包括：
- 标签约束是否合法
- 易碎件支撑面是否完整
- 易碎件上方是否仍有货物
- 定向件姿态是否合法
- 定向件承重时上层重心是否越界
- 承压是否超过 `500 kg/m^2`
- 顶部安全间隙是否 >= `3 cm`
- 多容器方案是否合法
- 总成本统计是否一致

### 中高影响模块

#### 5. [testRunner.py](F:\code\MathematicalModeling\Packing\testRunner.py)
当前执行链路默认：
- 从测试用例生成一组 `Item`
- 构造一个 `Container`
- 调一次 `optimizePacking`
- 返回单容器结果

后续需要改成：
- 构造完整 `ProblemInstance`
- 调 `PlanOptimizer`
- 返回 `ShipmentPlan`
- 在结果中包含容器实例级统计、成本、未装货数量、目标值等字段

缓存输入哈希也会被新 schema 和新目标函数影响。

#### 6. [resultSaver.py](F:\code\MathematicalModeling\Packing\resultSaver.py)
当前输出仍然高度偏向单容器：
- 主汇总围绕 `volumeRate`
- 解文本围绕一个容器的放置序列
- CSV/JSON 仍然缺少容器实例级和目标函数级字段

后续需要支持：
- `run-level`
- `group-level`
- `container-level`
- 必要时的 `item-level`
- `objectiveName`
- `objectiveValue`
- `totalCost`
- `usedContainerCount`
- `unpackedItemCount`
- 标签相关统计

#### 7. [visualizer.py](F:\code\MathematicalModeling\Packing\visualizer.py)
这是必须重构但可以稍后动手的模块。

当前只会做：
- 单容器三维装箱图

后续需要分成两类可视化：
- `packing visualization`
  用来看单个容器或多个容器实例的三维装载效果
- `analysis visualization`
  用来看散点图、对比图、控制变量实验结果

如果不拆分这两类职责，后面这个模块会越来越乱。

### 中影响模块

#### 8. [packingLogic.py](F:\code\MathematicalModeling\Packing\packingLogic.py)
虽然这轮没有单独打开，但它会被 `optimization.py` 连带影响。

建议未来定位成：
- 纯单容器装载内核
- 只关心给定容器和给定货物如何装
- 不负责总成本、多容器分配和目标排序

#### 9. [batchTest.py](F:\code\MathematicalModeling\Packing\batchTest.py)
影响中等。

原因不是逻辑最复杂，而是它会承接：
- 新的测试用例输出结构
- 新的结果导出类型
- 新的分析图生成开关
- 新的总表聚合流程

#### 10. [configManager.py](F:\code\MathematicalModeling\Packing\configManager.py) 和 [config.json](F:\code\MathematicalModeling\Packing\config.json)
影响中等。

后续需要逐步支持：
- 目标函数默认值
- 分析图默认配置
- 是否导出容器级明细
- 是否启用分析图
- 多种可视化模式

## 当前结论
从影响范围看，这次不是“给算法加几个约束”，而是一次完整的框架升级。

受影响最重的模块链路是：
1. `dataStructures.py`
2. `testCaseManager.py`
3. `optimization.py`
4. `solutionValidator.py`
5. `testRunner.py`
6. `resultSaver.py`
7. `visualizer.py`

## 当前核心问题

### 1. 缓存绑定代码版本 [已完成]
这个问题已经修复。

当前缓存会校验：
- `cacheVersion`
- `codeFingerprint`
- 缓存解在当前代码下是否仍合法

因此旧结果静默污染当前实验的问题已经被显著压住。

### 2. 解合法性校验 [基础版已完成]
这个问题已经完成基础修复。

当前已统一校验：
- 越界
- 重叠
- 重复放置
- 非法旋转
- 超载
- 汇总指标不一致

但这仍然只是“单容器几何合法性”层面的校验，不包含：
- 易碎品受压限制
- 定向品姿态限制
- 稳定性与支撑关系
- 多容器分配合法性
- 成本统计一致性

### 3. 默认可复现实验 [基础版已完成]
这个问题已经完成基础修复。

当前已支持：
- `baseSeed`
- `repeatCount`
- 固定 seed 序列
- 重复试验统计
- 二次运行复现并命中缓存

但目前还没有更高阶的统计分析，例如显著性比较、置信区间等。

### 4. 数据模型仍然是“单容器 + 单目标” [基础版已完成]
这个问题已经完成基础重构。

当前已经支持：
- `containerTypes`
- 容器单趟成本
- 多容器实例结果
- `item tags / constraints`
- `ShipmentPlan`
- 总成本、容器数、总满容率、平均满容率等派生指标

仍然不足的部分主要是：
- 标签体系还不够丰富
- 还没有更复杂的业务约束对象模型
- 结果结构虽然完整，但仍偏向第一小问约束集

### 5. 目标函数表达能力不足 [基础版已完成]
当前已经完成基础抽象。

但新需求已经要求支持：
- 最低总成本
- 成本与满容率联合分析
- 多目标或主次目标排序

当前已支持：
- 主目标字段
- 主目标方向 `min/max`
- 次目标排序
- `max totalFillRate`
- `min totalCost`

后续还需要继续补：
- 更多目标字段
- 更复杂的多目标组合策略
- 更灵活的显式目标配置校验

### 5.1 算法模块还没有做“装箱内核 / 方案优化 / 目标评估”分层 [基础版已完成]
这一层已经完成基础拆分。

当前已经落地为：
- `packingLogic.py` 负责单容器放置判断与候选放置搜索
- `optimization.py` 负责方案构建、算法扰动与目标排序
- 目标函数通过 `ObjectiveSpec` 进入方案评估

当前不足：
- `PlanOptimizer` 仍然是基础版顺序构建器
- 搜索邻域还主要围绕物品顺序
- 多容器成本求解质量还远不是最终形态

### 5.2 算法当前拿不到“这一步为什么不合法”的反馈 [基础版已完成]
这个问题已经完成基础修复。

当前已经具备：
- 即时反馈接口 `evaluatePlacement(...)`
- 结构化反馈字段：
  - `isFeasible`
  - `reasonCode`
  - `supportAreaRatio`
  - `bearingPressure`
  - `topClearanceCm`
  - `projectionContained`
- 最终兜底校验仍由 `solutionValidator.py` 负责

### 5.3 不需要让每个算法自己理解全部约束，但必须改算法调用路径 [基础版已完成]
这部分已经完成基础改造。

不需要做的事情：
- 不需要把 `fragile`、`oriented`、承压、顶部间隙这些规则分别硬编码进每个算法

当前已经做到：
- 算法通过新内核拿放置反馈
- 算法输出 `ShipmentPlan`
- 目标排序围绕 `objective` 工作

但并不意味着高层搜索已经完成，只是说明“不是每加一个新约束就要重写所有算法”这件事现在已经有了框架基础。

### 6. 结果导出已有基础，但分析视图层不存在 [基础版已完成]
这一项已经完成基础实现。

已经完成：
- `run/group/container/placement` 四层表
- 每测试用例 CSV/JSON
- 跨测试用例聚合总表
- 根据配置生成散点图
- 支持控制变量实验所需的场景元数据字段

仍然不足：
- 图表类型还比较少，当前主要是散点图
- 还没有自动分面、回归线、统计检验等更高级分析能力

### 7. 约束建模能力不足 [第一小问基础版已完成，高优先级]
第一小问范围内的标签约束已经正式进入框架。

当前已支持：
- `standard`
- `fragile`
- `oriented`
- `allowedRotations`
- `canSupportOthers`
- `allowedSupportSources`
- `requiredSupportAreaRatio`
- `requiredSupportProjectionContainment`
- `maxBearingPressureKgPerM2`
- `minTopClearanceCm`

后续仍然需要继续扩展：
- 更多标签
- 更复杂的支撑与堆叠规则
- 运输顺序等业务约束

### 8. 搜索能力偏弱 [未开始，暂时后置]
这一项依然成立，但当前阶段不应该先做。

在新需求下，先做更强算法意义不大，因为：
- 底层数据模型还不支持多容器多目标
- 输出结构还不支持成本分析和通用散点图
- 约束表达能力还不够

因此，搜索能力增强应该后置到框架稳定之后。

## 当前优先级重排
既然基础框架已经落地，下一阶段优先级应当调整为：

1. 增强多容器成本求解质量
2. 扩充标签体系和更复杂业务约束
3. 增加更多分析图和统计分析能力
4. 做更系统的控制变量测试集
5. 最后再进入更强算法与论文级实验整理

## 本轮已完成的实现顺序
本轮已经按下列顺序完成了一轮框架重构：

1. 重新定义测试用例 schema
2. 重构 `ProblemInstance / ShipmentPlan` 等核心对象
3. 将第一小问约束语义落到数据结构和校验层
4. 重构单容器装箱内核，增加即时反馈
5. 重构算法入口，使其围绕 `ShipmentPlan` 和 `objective` 工作
6. 重构结果导出与分析表
7. 重构装箱可视化与散点图生成
8. 重写测试集并完成端到端验证
9. 新增中文使用手册，补充非程序背景用户说明

## 当前总体判断
当前项目已经不是“能不能继续写算法”的问题，而是“底层框架是否足够支撑新问题定义”的问题。

如果按你的新需求推进，最先该做的是：
- 在现有框架上继续增强多容器成本求解质量
- 继续扩展标签与约束体系
- 完善分析与统计能力
- 补更系统的研究型测试集

这条路的好处是，后面无论你换什么算法，或者再加什么业务约束，都不会推翻前面的框架层工作。

## 下一步可能计划
根据当前实现状态，下一阶段更合理的计划建议是：

1. 先增强多容器成本求解质量
   当前 `optimization.py` 里的方案构建器已经能工作，但还偏基础。下一步应优先增加更适合多容器成本问题的邻域操作，例如：
   - 物品跨容器移动
   - 容器类型替换
   - 合并容器 / 关闭容器
   - 针对某个容器局部重装
2. 再扩充标签和约束体系
   在第一小问约束稳定后，再加入：
   - 更多可组合标签
   - 更复杂的支撑规则
   - 装载顺序、禁压、禁混装等业务约束
3. 然后增强分析能力
   当前已经支持散点图。下一步可以补：
   - 分面图
   - 箱线图
   - 回归线
   - 组间统计比较
4. 最后完善研究型测试集
   按“容器固定 / 货物变化 / 标签比例变化 / 成本变化”系统扩样，形成更完整的实验矩阵。

## 本轮最后一次框架提升已完成
本轮又完成了一次偏“框架层”而非“算法层”的提升，新增内容如下：

1. 独立功能验证套件
   当前已经有：
   - `validation/cases/`
   - `validation/runner.py`
   - `validationExpect`
   - `validation/summary.json`
   - `validation/summary.txt`

2. CLI 运行控制
   当前已经支持：
   - `--case`
   - `--case-pattern`
   - `--algorithm`
   - `--iterations`
   - `--repeat`
   - `--no-viz`
   - `--no-cache`
   - `--output-tag`
   - `--run-validation`
   - `--validation-only`

3. schema 合同层
   当前测试集已经正式要求：
   - `schemaVersion`
   - `units`

   并且当前实现固定要求：
   - `lengthUnit = cm`
   - `weightUnit = kg`
   - `bearingPressureUnit = kg/m^2`
   - `clearanceUnit = cm`

4. 结果入口文件
   当前每次运行根目录都会生成：
   - `manifest.json`
   - `summary.md`

5. 分析图配置增强
   当前分析图除了基础散点图以外，还支持更多配置字段：
   - `filter`
   - `series`
   - `chartType`
   - `sortBy`
   - `sortOrder`
   - `topN`

## 最新补充验证
这轮补充验证已经完成：

- `python batchTest.py --validation-only --output-tag validation_only`
  验证套件 6 个用例全部通过
- `python batchTest.py --case single_fill_standard --algorithm greedy_search --iterations 1 --repeat 1 --no-viz --output-tag cli_smoke`
  CLI 覆盖、schema 校验、manifest、结果导出全部正常

对应结果目录为：
- `results/20260420_220041_validation_only/`
- `results/20260420_220042_cli_smoke/`

## 剩余框架缺口
如果继续只看框架、不看算法强弱，剩余缺口主要还有：

1. 验证样例集数量还不够多
2. 图表类型还不够丰富，缺少分面图、回归线、统计图
3. 标签体系还没有彻底外部化成独立配置资源
4. 运行级 manifest 还可以继续补充 git 信息和更详细的结果索引
