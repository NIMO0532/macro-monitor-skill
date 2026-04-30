---
name: macro-monitor
description: 每日宏观数据监控和推送。自动浏览免费数据源（Trading Economics、FRED、国家统计局、央行官网、财联社等），整理整合过去24小时发布的宏观数据和政策信息，并推送给用户。通过 cron 每天晚上10点自动触发。
description_zh: "每日自动采集宏观经济数据和政策信息并推送"
description_en: "Daily macro economic data monitoring and push notifications"
version: 1.2.0
---

# 宏观数据监控技能

## 工作流程

当此技能被触发时（通常通过 cron 每天晚上10点），执行以下步骤：

### 1. 读取科普知识库

**必须先读取**本技能目录下的 references/indicators.md 文件，获取常见指标的科普解释：
```
read path=<技能目录>/references/indicators.md
```

### 2. 采集数据

使用 WebFetch、WebSearch 或浏览器工具，按优先级访问以下数据源，收集过去24小时发布的宏观数据和政策信息：

**国际数据：**
- Trading Economics (https://tradingeconomics.com/calendar) - 查看经济日历
- FRED (https://fred.stlouisfed.org/releases) - 美联储经济数据发布

**国内数据：**
- 国家统计局 (http://www.stats.gov.cn/) - 查看最新数据发布
- 央行官网 (http://www.pbc.gov.cn/) - 货币政策、利率、流动性数据
- 证监会官网 (http://www.csrc.gov.cn/) - 监管政策

**新闻资讯：**
- 财联社 (https://www.cls.cn/) - 实时金融新闻
- 华尔街见闻 (https://wallstreetcn.com/) - 市场资讯

> **工具选择**：优先使用 WebFetch 和 WebSearch 进行数据采集（轻量、快速）；若页面需要 JavaScript 渲染或有反爬机制，使用浏览器工具（agent-browser / browser-use）。

### 3. 整理整合

将采集到的数据按以下结构整理：

```
【过去24小时宏观数据】

国际数据
- [数据名称] [发布值] [预期值] [前值] [影响说明]
  [小白向科普解释说明 - 每个指标都必须添加]

国内数据
- [数据名称] [发布值] [预期值] [前值] [影响说明]
  [小白向科普解释说明 - 每个指标都必须添加]

政策动态
- [政策标题] - [简要说明]

重要资讯
- [新闻标题] - [简要说明]
```

**科普解释规则（强制执行）：**

1. **每个指标都必须添加科普解释**，没有例外

2. **科普解释来源优先级：**
   - 优先：从 references/indicators.md 中查找现成解释
   - 其次：如果找不到，执行"未知指标处理"流程

3. **科普解释格式要求：**
   ```
   [指标名]：[一句话定义]
      - 为什么重要：[简短说明]
      - 怎么看：[正常范围/关键阈值]
   ```

4. **对于重要数据变化，添加额外解读：**
   - 超预期：为什么超预期？对市场有什么影响？
   - 低于预期：反映了什么问题？政策可能如何应对？

### 未知指标处理流程

当遇到 references/indicators.md 中没有的指标时：

1. **多源搜索验证**
   使用 WebSearch 搜索该指标，访问多个来源：
   - 搜索1："[指标名] 是什么 意思"
   - 搜索2："[指标名] 经济指标 解释"
   - 搜索3："[指标名] investing.com" 或 "[指标名] trading economics"

2. **交叉验证**
   - 对比多个来源的解释，确保准确性
   - 优先选择权威来源（央行官网、统计局、知名财经媒体）
   - 避免单一来源的片面解释

3. **整理科普内容**
   将搜索结果整理成通俗易懂的格式：
   ```
   [指标名]：[一句话定义]
      - 为什么重要：[简短说明]
      - 怎么看：[正常范围/关键阈值]
   ```

4. **可选：更新知识库**
   如果该指标是常见指标，考虑将解释添加到 references/indicators.md 中，避免重复搜索

### 4. 输出报告

将整理好的报告以 HTML 文件形式输出到工作目录，文件名格式：`macro-report-YYYY-MM-DD.html`。

报告应包含：
- 核心数据一瞥（关键数字卡片）
- 国际宏观数据（表格 + 科普解释）
- 国内宏观数据（表格 + 科普解释）
- 政策动态与重要资讯
- 今晚/近期关注事件日历

### 5. 推送消息

如果配置了消息推送渠道（企业微信、邮件等），将报告摘要推送给用户。

## 数据源快速访问

### Trading Economics 经济日历
- URL: https://tradingeconomics.com/calendar
- 关注：高重要性事件（红色标记）
- 字段：时间、国家、事件、实际值、预期值、前值

### 国家统计局
- URL: http://www.stats.gov.cn/
- 关注：最新数据发布栏目
- 重点指标：GDP、CPI、PPI、PMI、工业增加值、社会消费品零售

### 央行官网
- URL: http://www.pbc.gov.cn/
- 关注：新闻发布、政策解读
- 重点：LPR利率、MLF操作、公开市场操作、货币政策报告

## 注意事项

1. **时间过滤**：采集过去24小时（GMT+8）发布的数据和新闻
2. **科普解释强制**：每个指标都必须添加科普解释，没有例外
3. **重要性排序**：高重要性数据优先展示
4. **简洁明了**：每个条目不超过2行，重点突出数值变化
5. **数据验证**：对比实际值与预期值，标注超预期/不及预期
6. **异常处理**：如果某个数据源无法访问，跳过并记录，不影响其他数据源

## Cron 配置

此技能通过以下 cron job 调度（WorkBuddy 自动化）：

```json
{
  "name": "macro-monitor-daily",
  "schedule": {
    "kind": "cron",
    "expr": "0 22 * * *",
    "tz": "Asia/Singapore"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "执行宏观数据监控，浏览免费数据源，整理过去24小时发布的宏观数据和政策信息并推送"
  },
  "sessionTarget": "isolated",
  "enabled": true
}
```

## 手动触发

如需手动触发数据采集，发送消息：
```
执行宏观数据监控，浏览免费数据源，整理过去24小时发布的宏观数据和政策信息并推送
```

## 安装方法

### WorkBuddy 用户级安装

将本仓库内容复制到 `~/.workbuddy/skills/macro-monitor/` 目录：

```bash
# 克隆仓库
git clone https://github.com/<your-username>/macro-monitor-skill.git

# 复制到 WorkBuddy 技能目录
cp -r macro-monitor-skill/* ~/.workbuddy/skills/macro-monitor/
```

### 自动化配置

安装后，在 WorkBuddy 中创建自动化任务：
- 名称：`macro-monitor-daily`
- 调度：每天 22:00 (GMT+8)
- 提示词：`执行宏观数据监控，浏览免费数据源，整理过去24小时发布的宏观数据和政策信息并推送`

## 更新日志

### v1.2.0 (2026-04-30)
- 新增 GitHub Actions 自动化工作流
- 新增 Python 数据采集脚本（macro_monitor.py）
- 新增企业微信 Webhook 推送功能
- 新增全球市场实时指数采集

### v1.1.0 (2026-04-30)
- 移除硬编码路径，改为相对路径引用
- 增加工具选择说明（WebFetch/WebSearch 优先，浏览器工具兜底）
- 增加报告输出规范（HTML 格式，命名规则）
- 增加安装方法和更新日志

### v1.0.2
- 初始版本
