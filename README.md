# macro-monitor-skill

每日宏观数据监控 WorkBuddy 技能 + GitHub Actions 自动化。自动采集全球宏观经济数据和政策信息，生成结构化报告并推送到企业微信。

## 功能

- 自动采集过去24小时全球宏观数据（PMI、CPI、GDP、央行利率决议等）
- 覆盖国内外主要数据源（Trading Economics、新浪财经、东方财富、财联社）
- 每个指标附带通俗易懂的科普解释
- 输出 Markdown 报告，结构清晰、重点突出
- 支持 cron 定时调度，每天自动运行
- 支持企业微信机器人 Webhook 推送

## 数据源

| 类别 | 来源 |
|------|------|
| 国际经济数据 | Trading Economics、新浪财经全球行情 |
| 国内经济数据 | 新浪财经宏观、东方财富数据中心 |
| 新闻资讯 | 财联社快讯 |
| 市场指数 | 新浪实时行情（上证/深证/恒生/道琼斯/纳斯达克等） |

## 一、WorkBuddy 技能安装

### 方法一：直接复制

将本仓库中的 `SKILL.md` 和 `references/` 复制到 WorkBuddy 用户级技能目录：

```bash
cp -r SKILL.md references/ ~/.workbuddy/skills/macro-monitor/
```

Windows PowerShell:
```powershell
Copy-Item -Recurse SKILL.md, references\ ~/.workbuddy\skills\macro-monitor\
```

### 方法二：Git 克隆

```bash
git clone https://github.com/<your-username>/macro-monitor-skill.git
cp -r macro-monitor-skill/SKILL.md macro-monitor-skill/references/ ~/.workbuddy/skills/macro-monitor/
```

### 配置 WorkBuddy 自动化

安装技能后，在 WorkBuddy 中创建自动化任务：

- **名称**: macro-monitor-daily
- **调度**: 每天 22:00 (Asia/Singapore, GMT+8)
- **提示词**: `执行宏观数据监控，浏览免费数据源，整理过去24小时发布的宏观数据和政策信息并推送`

## 二、GitHub Actions 自动化配置

### 步骤 1：Fork 或 Clone 本仓库

将本仓库 Fork 到你的 GitHub 账号，或直接 Clone 后推送到自己的仓库。

### 步骤 2：配置企业微信 Webhook Secret

1. 打开你的 GitHub 仓库页面
2. 进入 **Settings** > **Secrets and variables** > **Actions**
3. 点击 **New repository secret**
4. 添加以下 Secret：

| Name | Value |
|------|-------|
| `WECOM_WEBHOOK_URL` | 你的企业微信机器人 Webhook URL |

> 获取 Webhook URL：企业微信群 > 群设置 > 群机器人 > 添加机器人 > 复制 Webhook 地址

### 步骤 3：启用 GitHub Actions

1. 进入仓库的 **Actions** 页签
2. 如果看到提示，点击 **I understand my workflows, go ahead and enable them**
3. 确认 `每日宏观数据监控` 工作流已启用

### 步骤 4：手动测试（可选）

1. 进入 **Actions** 页签
2. 选择 `每日宏观数据监控` 工作流
3. 点击 **Run workflow** > **Run workflow**
4. 等待运行完成，检查企业微信群是否收到消息

### 调度时间

工作流默认在北京时间每天 **22:00** 自动运行（UTC 14:00）。

如需修改时间，编辑 `.github/workflows/macro-monitor.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 14 * * *'  # UTC 14:00 = 北京时间 22:00
```

常用时间对照：

| 北京时间 | UTC | cron 表达式 |
|----------|-----|-------------|
| 08:00 | 00:00 | `0 0 * * *` |
| 12:00 | 04:00 | `0 4 * * *` |
| 18:00 | 10:00 | `0 10 * * *` |
| 20:00 | 12:00 | `0 12 * * *` |
| 22:00 | 14:00 | `0 14 * * *` |

## 手动触发 (WorkBuddy)

在 WorkBuddy 中发送以下消息即可手动运行：

```
执行宏观数据监控，浏览免费数据源，整理过去24小时发布的宏观数据和政策信息并推送
```

## 文件结构

```
macro-monitor-skill/
├── .github/
│   └── workflows/
│       └── macro-monitor.yml   # GitHub Actions 工作流
├── references/
│   └── indicators.md           # 宏观指标科普知识库
├── SKILL.md                    # WorkBuddy 技能定义文件
├── macro_monitor.py            # Python 数据采集脚本
├── requirements.txt            # Python 依赖
├── README.md                   # 本文件
├── LICENSE                     # MIT 许可证
└── .gitignore
```

## 更新日志

### v1.2.0 (2026-04-30)
- 新增 GitHub Actions 自动化工作流
- 新增 Python 数据采集脚本（macro_monitor.py）
- 新增企业微信 Webhook 推送功能
- 新增全球市场实时指数采集
- 更新 README 增加 GitHub Actions 配置文档

### v1.1.0 (2026-04-30)
- 移除硬编码路径，改为相对路径引用
- 增加工具选择说明（WebFetch/WebSearch 优先）
- 增加 HTML 报告输出规范
- 增加安装方法和更新日志

### v1.0.2
- 初始版本

## 许可证

MIT License
