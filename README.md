# 3D Bin Packing Solver

## 项目简介
本项目面向物流装载场景，建立了一个三维装箱实验框架，用于研究：

- 单容器装载率优化
- 多容器最低运输成本优化
- 不同货物约束和参数变化对装载率、成本与运行表现的影响

项目重点不只是求解器本身，还包括测试集组织、约束校验、结果导出、可视化与实验分析能力。

## 当前能力
当前版本已经支持：

- 多种容器规格同时存在
- 单趟成本建模
- 多容器装载方案输出
- 货物标签与约束表达
  - `standard`
  - `fragile`
  - `oriented`
- 合法性校验
  - 越界
  - 重叠
  - 非法旋转
  - 支撑面积不足
  - 承压超限
  - 顶部安全间隙不足
- 目标函数配置
  - 最大总体积利用率
  - 最小总运输成本
- 参数批量实验
- CSV / JSON 结果导出
- 装箱三维图与分析图输出
- 独立功能验证样例集

## 项目结构
- `test/`
  正式实验测试集
- `validation/cases/`
  最小功能验证样例
- `batchTest.py`
  批量运行入口
- `config.json`
  默认参数与输出配置
- `results/`
  运行结果目录

## 使用方式
直接运行：

```powershell
python batchTest.py
```

常用单独运行方式：

```powershell
python batchTest.py --case question1
python batchTest.py --case question1 --algorithm greedy_search --iterations 1 --repeat 1 --no-viz
python batchTest.py --validation-only
```

## 输出结果
每次运行会生成一个时间戳目录，主要包含：

- `logs/`
  运行日志
- `cases/<testName>/reports/`
  文本报告
- `cases/<testName>/tables/csv|json/`
  运行表、参数组表、容器表、放置表
- `cases/<testName>/plans/`
  最优方案文本
- `cases/<testName>/visuals/packing/`
  装箱三维图
- `cases/<testName>/visuals/analysis/`
  单测试集分析图
- `aggregate/`
  跨测试集总表与聚合图
- `manifest.json`
  本次运行索引
