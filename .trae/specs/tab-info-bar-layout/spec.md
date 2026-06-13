# 吉他谱信息栏布局优化 Spec

## Why
当前六线谱渲染器的信息栏布局存在以下问题：
1. TAB标识在每行系统左侧竖排显示，占用空间且视觉上不够简洁
2. 调号和拍号信息分散在每行开头，未与标题区域整合
3. 行间距偏紧凑，阅读体验可优化

## What Changes
- **TAB标识位置调整**: 将"T A B"竖排文字从每行系统(`_draw_info_bar`)移至每行第一行系统的信息小节中显示（仅首行显示）
- **行间距增加**: 增大系统间垂直间距，提升可读性
- **调号拍号整合到标题区**: 在页面头部标题右侧显示调号(1=X)和拍号(分数形式 A/B)，格式为 `1=X (A/B)`
- **精简每行信息栏**: 移除每行的TAB竖排文字和调号拍号堆叠显示，保留简洁的分隔线

## Impact
- Affected specs: 无
- Affected code:
  - `ApolloTab/renderer/tab_renderer.py`: 修改 `_draw_header()`, `_draw_info_bar()`, `_draw_system()`
  - `ApolloTab/utils/constants.py`: 调整 `LINE_SPACING`, `SYSTEM_SPACING` 参数

## ADDED Requirements

### Requirement: TAB标识移入首行信息小节
系统 SHALL 在每行第一个系统的信息栏中以横排方式显示"TAB"标识，而非当前的全行竖排"T/A/B"。

#### Scenario: 首行显示TAB
- **WHEN** 渲染任意一页的六线谱时
- **THEN** 每行系统的第一行信息栏内显示横排"TAB"文字，后续行不再重复显示TAB

### Requirement: 行间距增大
系统 SHALL 增大行与行之间的垂直间距，使六线谱更易阅读。

#### Scenario: 系统间距增加
- **WHEN** 计算两个相邻系统的Y坐标间距时
- **THEN** 使用增大的间距值（从当前的20px增加到合适值）

### Requirement: 标题右侧显示调号拍号
系统 SHALL 在页面标题右侧显示该谱子的调号和拍号信息。

#### Scenario: 标题区调号拍号展示
- **WHEN** 渲染第1页头部信息时
- **THEN** 在标题同行右侧显示格式为 `1=C (4/4)` 的文本，其中C为调性名，4/4为分数形式的拍号

## MODIFIED Requirements

### Requirement: 每行信息栏简化
原有的 `_draw_info_bar()` 方法 SHALL 精简为仅绘制分隔线，不再绘制TAB竖排文字和调号拍号堆叠。调号拍号的显示职责转移到标题区。
