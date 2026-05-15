# 🔍 RepoScout-AI

**轻量级AI驱动GitHub仓库智能发现与推荐引擎 | Lightweight AI-Driven GitHub Repository Intelligent Discovery & Recommendation Engine**

[English](#english) | [简体中文](#简体中文) | [繁體中文](#繁體中文)

---

## 简体中文

### 🎉 项目介绍

**RepoScout-AI** 是一款轻量级的AI驱动GitHub仓库智能发现与推荐引擎。它能帮助你从GitHub海量仓库中快速发现高质量、高价值的项目，基于多维评分系统和个性化推荐算法，为你精准推荐最值得关注的开源项目。

**灵感来源**：每天GitHub都有数以千计的新项目诞生，开发者很难从中筛选出真正有价值的项目。RepoScout-AI旨在解决这一痛点，通过智能化的方式帮助开发者高效发现优质开源项目。

**自研差异化亮点**：
- 🧠 **智能推荐引擎** — 基于TF-IDF的个性化推荐，越用越懂你
- 📊 **四维评分体系** — 活跃度/社区热度/代码健康度/流行度综合评分
- 🏷️ **智能标签系统** — 自动识别项目类型、技术栈、应用场景
- 📈 **趋势追踪** — 实时追踪Star增速、Fork趋势、活跃度变化
- 💾 **本地收藏管理** — SQLite持久化，支持自定义标签和备注
- 🖥️ **精美TUI界面** — ANSI彩色终端UI，交互式浏览体验
- 📤 **多格式导出** — JSON/CSV/Markdown/HTML四种格式报告
- ⚡ **零外部依赖** — 纯Python标准库实现，开箱即用

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔍 **智能搜索** | 基于GitHub API的多维度仓库搜索，支持语言、星标、更新时间过滤 |
| 📈 **Trending解析** | 自动解析GitHub Trending页面，获取每日/每周/每月热门项目 |
| 🎯 **个性化推荐** | 基于用户兴趣画像和浏览历史的TF-IDF推荐算法 |
| 📊 **多维评分** | 活跃度、社区热度、代码健康度、流行度四维综合评分（S/A/B/C/D/F等级） |
| 🏷️ **智能标签** | 自动识别项目类型（库/工具/框架/应用）、技术栈、应用场景 |
| 📉 **趋势追踪** | Star/Fork增速计算、异常检测、ASCII图表可视化 |
| 💾 **收藏管理** | SQLite本地持久化存储，支持收藏、备注、自定义标签 |
| 🖥️ **TUI界面** | 美观的彩色终端交互界面，支持键盘导航 |
| 📤 **报告导出** | JSON/CSV/Markdown/HTML多格式报告导出 |
| ⚡ **零依赖** | 纯Python标准库实现，无需安装任何第三方包 |

### 🚀 快速开始

#### 环境要求

- Python 3.8 或更高版本
- Git（可选，用于版本控制）
- GitHub Token（可选，提高API请求限额）

#### 安装

```bash
# 克隆仓库
git clone https://github.com/gitstq/RepoScout-AI.git
cd RepoScout-AI

# 无需安装依赖！直接使用
python main.py --help
```

#### 配置GitHub Token（推荐）

```bash
# 方式一：环境变量
export GITHUB_TOKEN="your_github_token"

# 方式二：命令行参数
python main.py search "web framework" --token "your_github_token"

# 方式三：配置文件
python main.py config set token "your_github_token"
```

#### 基础使用

```bash
# 搜索仓库
python main.py search "web framework" --lang python --limit 10

# 查看Trending
python main.py trending --lang javascript --since weekly

# 评分仓库
python main.py score python/cpython

# 获取推荐
python main.py recommend --limit 5

# 趋势追踪
python main.py track vuejs/vue --action record

# 收藏管理
python main.py fav add facebook/react
python main.py fav list

# 启动TUI界面
python main.py tui

# 导出报告
python main.py export --source favorites --format html --output report.html
```

### 📖 详细使用指南

#### 搜索命令

```bash
# 基础搜索
python main.py search "machine learning"

# 高级搜索（多条件过滤）
python main.py search "web framework" \
  --lang python \
  --sort stars \
  --order desc \
  --limit 20 \
  --min-stars 1000

# 搜索特定用户的仓库
python main.py search "topic:react language:typescript"
```

#### Trending命令

```bash
# 查看今日热门
python main.py trending

# 按语言过滤
python main.py trending --lang rust

# 查看每周热门
python main.py trending --since weekly

# 查看每月热门
python main.py trending --since monthly
```

#### 评分系统

```bash
# 对单个仓库评分
python main.py score facebook/react

# 查看评分详情（包含各维度分数）
python main.py score vuejs/vue --detail

# 批量评分
python main.py score python/cpython rust-lang/rust go-lang/go
```

#### 推荐引擎

```bash
# 获取个性化推荐
python main.py recommend --limit 10

# 基于特定仓库找相似项目
python main.py recommend --similar-to facebook/react --limit 5

# 按技术栈推荐
python main.py recommend --lang rust --limit 10
```

#### TUI界面

```bash
# 启动交互式TUI
python main.py tui

# TUI内操作：
# ↑/↓  上下移动选择
# Enter 查看详情
# f    收藏/取消收藏
# s    评分
# /    搜索
# q    返回/退出
```

#### 报告导出

```bash
# 导出收藏为JSON
python main.py export --source favorites --format json --output fav.json

# 导出搜索结果为CSV
python main.py export --source search:web --format csv --output results.csv

# 导出为Markdown
python main.py export --source trending --format markdown --output trending.md

# 导出为HTML报告
python main.py export --source favorites --format html --output report.html
```

### 💡 设计思路与迭代规划

#### 设计理念

RepoScout-AI遵循以下设计原则：

1. **零依赖哲学** — 仅使用Python标准库，消除环境配置障碍
2. **离线优先** — 本地SQLite存储，无需网络即可查看收藏和历史
3. **渐进式智能** — 推荐算法基于用户行为持续优化，越用越精准
4. **终端原生** — TUI界面深度适配终端环境，高效操作

#### 技术选型原因

| 选择 | 原因 |
|------|------|
| Python标准库 | 零依赖，跨平台兼容性最佳 |
| SQLite | 内置于Python，无需额外安装，轻量高效 |
| TF-IDF | 经典文本相似度算法，纯Python实现简单高效 |
| ANSI控制码 | 终端UI标准，兼容所有主流终端 |
| GitHub REST API | 官方API，稳定可靠，文档完善 |

#### 后续迭代计划

- [ ] 🔌 插件系统 — 支持自定义评分维度和推荐策略
- [ ] 🌐 Web界面 — 基于内置HTTP服务器的Web Dashboard
- [ ] 📱 通知系统 — 关注仓库更新通知
- [ ] 🔄 GitLab/Gitea支持 — 多平台仓库发现
- [ ] 🤖 LLM集成 — 接入大语言模型增强推荐能力
- [ ] 📊 高级可视化 — SVG图表导出

### 📦 打包与部署指南

#### 作为CLI工具安装

```bash
# 添加到PATH（Linux/macOS）
echo 'alias reposcout="python /path/to/RepoScout-AI/main.py"' >> ~/.bashrc
source ~/.bashrc

# 使用别名
reposcout search "AI agent"
```

#### 作为Python包使用

```python
from github_client import GitHubClient
from scorer import RepoScorer
from recommender import Recommender

# 创建客户端
client = GitHubClient(token="your_token")

# 搜索仓库
results = client.search_repos("web framework", language="python")

# 评分
scorer = RepoScorer(client)
score = scorer.score_repo("facebook/react")
print(f"评分: {score['overall']}/{score['grade']}")
```

#### Docker部署（可选）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
CMD ["python", "main.py", "tui"]
```

### 🤝 贡献指南

欢迎贡献！请遵循以下规范：

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m "feat: 添加某个特性"`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

**提交规范**：
- `feat:` 新增功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 繁體中文

### 🎉 專案介紹

**RepoScout-AI** 是一款輕量級的AI驅動GitHub倉庫智慧發現與推薦引擎。它能幫助你從GitHub海量倉庫中快速發現高品質、高價值的專案，基於多維評分系統和個人化推薦演算法，為你精準推薦最值得關注的開源專案。

**靈感來源**：每天GitHub都有數以千計的新專案誕生，開發者很難從中篩選出真正有價值的專案。RepoScout-AI旨在解決這一痛點，透過智慧化的方式幫助開發者高效發現優質開源專案。

**自研差異化亮點**：
- 🧠 **智慧推薦引擎** — 基於TF-IDF的個人化推薦，越用越懂你
- 📊 **四維評分體系** — 活躍度/社群熱度/程式碼健康度/流行度綜合評分
- 🏷️ **智慧標籤系統** — 自動識別專案類型、技術棧、應用場景
- 📈 **趨勢追蹤** — 即時追蹤Star增速、Fork趨勢、活躍度變化
- 💾 **本地收藏管理** — SQLite持久化，支援自訂標籤和備註
- 🖥️ **精美TUI介面** — ANSI彩色終端UI，互動式瀏覽體驗
- 📤 **多格式匯出** — JSON/CSV/Markdown/HTML四種格式報告
- ⚡ **零外部依賴** — 純Python標準函式庫實現，開箱即用

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔍 **智慧搜尋** | 基於GitHub API的多維度倉庫搜尋，支援語言、星標、更新時間過濾 |
| 📈 **Trending解析** | 自動解析GitHub Trending頁面，取得每日/每週/每月熱門專案 |
| 🎯 **個人化推薦** | 基於使用者興趣畫像和瀏覽歷史的TF-IDF推薦演算法 |
| 📊 **多維評分** | 活躍度、社群熱度、程式碼健康度、流行度四維綜合評分（S/A/B/C/D/F等級） |
| 🏷️ **智慧標籤** | 自動識別專案類型（庫/工具/框架/應用）、技術棧、應用場景 |
| 📉 **趨勢追蹤** | Star/Fork增速計算、異常檢測、ASCII圖表視覺化 |
| 💾 **收藏管理** | SQLite本地持久化儲存，支援收藏、備註、自訂標籤 |
| 🖥️ **TUI介面** | 美觀的彩色終端互動介面，支援鍵盤導航 |
| 📤 **報告匯出** | JSON/CSV/Markdown/HTML多格式報告匯出 |
| ⚡ **零依賴** | 純Python標準函式庫實現，無需安裝任何第三方套件 |

### 🚀 快速開始

#### 環境需求

- Python 3.8 或更高版本
- Git（可選，用於版本控制）
- GitHub Token（可選，提高API請求限額）

#### 安裝

```bash
# 克隆倉庫
git clone https://github.com/gitstq/RepoScout-AI.git
cd RepoScout-AI

# 無需安裝依賴！直接使用
python main.py --help
```

#### 設定GitHub Token（建議）

```bash
# 方式一：環境變數
export GITHUB_TOKEN="your_github_token"

# 方式二：命令列參數
python main.py search "web framework" --token "your_github_token"

# 方式三：設定檔
python main.py config set token "your_github_token"
```

#### 基礎使用

```bash
# 搜尋倉庫
python main.py search "web framework" --lang python --limit 10

# 查看Trending
python main.py trending --lang javascript --since weekly

# 評分倉庫
python main.py score python/cpython

# 取得推薦
python main.py recommend --limit 5

# 趨勢追蹤
python main.py track vuejs/vue --action record

# 收藏管理
python main.py fav add facebook/react
python main.py fav list

# 啟動TUI介面
python main.py tui

# 匯出報告
python main.py export --source favorites --format html --output report.html
```

### 📖 詳細使用指南

#### 搜尋命令

```bash
# 基礎搜尋
python main.py search "machine learning"

# 進階搜尋（多條件過濾）
python main.py search "web framework" \
  --lang python \
  --sort stars \
  --order desc \
  --limit 20 \
  --min-stars 1000
```

#### Trending命令

```bash
# 查看今日熱門
python main.py trending

# 按語言過濾
python main.py trending --lang rust

# 查看每週熱門
python main.py trending --since weekly
```

#### 評分系統

```bash
# 對單個倉庫評分
python main.py score facebook/react

# 查看評分詳情
python main.py score vuejs/vue --detail

# 批量評分
python main.py score python/cpython rust-lang/rust go-lang/go
```

#### 推薦引擎

```bash
# 取得個人化推薦
python main.py recommend --limit 10

# 基於特定倉庫找相似專案
python main.py recommend --similar-to facebook/react --limit 5
```

#### TUI介面

```bash
# 啟動互動式TUI
python main.py tui

# TUI內操作：
# ↑/↓  上下移動選擇
# Enter 查看詳情
# f    收藏/取消收藏
# s    評分
# /    搜尋
# q    返回/退出
```

#### 報告匯出

```bash
# 匯出收藏為JSON
python main.py export --source favorites --format json --output fav.json

# 匯出為HTML報告
python main.py export --source favorites --format html --output report.html
```

### 💡 設計思路與迭代規劃

#### 設計理念

1. **零依賴哲學** — 僅使用Python標準函式庫，消除環境配置障礙
2. **離線優先** — 本地SQLite儲存，無需網路即可查看收藏和歷史
3. **漸進式智慧** — 推薦演算法基於使用者行為持續優化，越用越精準
4. **終端原生** — TUI介面深度適配終端環境，高效操作

#### 後續迭代計畫

- [ ] 🔌 外掛系統 — 支援自訂評分維度和推薦策略
- [ ] 🌐 Web介面 — 基於內建HTTP伺服器的Web Dashboard
- [ ] 📱 通知系統 — 關注倉庫更新通知
- [ ] 🔄 GitLab/Gitea支援 — 多平台倉庫發現
- [ ] 🤖 LLM整合 — 接入大型語言模型增強推薦能力

### 📦 打包與部署指南

#### 作為CLI工具安裝

```bash
# 新增到PATH（Linux/macOS）
echo 'alias reposcout="python /path/to/RepoScout-AI/main.py"' >> ~/.bashrc
source ~/.bashrc
```

#### 作為Python套件使用

```python
from github_client import GitHubClient
from scorer import RepoScorer
from recommender import Recommender

client = GitHubClient(token="your_token")
results = client.search_repos("web framework", language="python")
scorer = RepoScorer(client)
score = scorer.score_repo("facebook/react")
print(f"評分: {score['overall']}/{score['grade']}")
```

### 🤝 貢獻指南

歡迎貢獻！請遵循以下規範：

1. Fork本倉庫
2. 建立特性分支：`git checkout -b feature/amazing-feature`
3. 提交變更：`git commit -m "feat: 新增某個特性"`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

### 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

## English

### 🎉 Introduction

**RepoScout-AI** is a lightweight AI-driven GitHub repository intelligent discovery and recommendation engine. It helps you quickly discover high-quality, high-value projects from the massive GitHub ecosystem, providing personalized recommendations based on a multi-dimensional scoring system and intelligent recommendation algorithms.

**Inspiration**: Thousands of new projects are born on GitHub every day, making it incredibly difficult for developers to filter out truly valuable ones. RepoScout-AI aims to solve this pain point by intelligently helping developers discover premium open-source projects efficiently.

**Differentiated Highlights**:
- 🧠 **Smart Recommendation Engine** — TF-IDF-based personalized recommendations that learn from your behavior
- 📊 **4-Dimensional Scoring** — Activity/Community/Health/Popularity comprehensive scoring system
- 🏷️ **Intelligent Tagging** — Auto-detect project type, tech stack, and application scenarios
- 📈 **Trend Tracking** — Real-time Star growth rate, Fork trends, and activity change monitoring
- 💾 **Local Favorites** — SQLite persistent storage with custom tags and notes
- 🖥️ **Beautiful TUI** — ANSI-colored terminal UI with interactive browsing experience
- 📤 **Multi-format Export** — JSON/CSV/Markdown/HTML report generation
- ⚡ **Zero Dependencies** — Pure Python standard library, ready to use out of the box

### ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Multi-dimensional repository search via GitHub API with language, stars, and update time filters |
| 📈 **Trending Parser** | Auto-parse GitHub Trending page for daily/weekly/monthly hot projects |
| 🎯 **Personalized Recommendations** | TF-IDF recommendation algorithm based on user interest profile and browsing history |
| 📊 **Multi-dimensional Scoring** | Activity/Community/Health/Popularity 4D scoring with S/A/B/C/D/F grades |
| 🏷️ **Smart Tags** | Auto-identify project types (lib/tool/framework/app), tech stacks, and scenarios |
| 📉 **Trend Tracking** | Star/Fork growth rate calculation, anomaly detection, ASCII chart visualization |
| 💾 **Favorites Management** | SQLite local persistent storage with favorites, notes, and custom tags |
| 🖥️ **TUI Interface** | Beautiful colored terminal interactive UI with keyboard navigation |
| 📤 **Report Export** | JSON/CSV/Markdown/HTML multi-format report export |
| ⚡ **Zero Dependencies** | Pure Python standard library implementation, no third-party packages needed |

### 🚀 Quick Start

#### Requirements

- Python 3.8+
- Git (optional, for version control)
- GitHub Token (optional, for higher API rate limits)

#### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/RepoScout-AI.git
cd RepoScout-AI

# No dependencies to install! Start using immediately
python main.py --help
```

#### Configure GitHub Token (Recommended)

```bash
# Method 1: Environment variable
export GITHUB_TOKEN="your_github_token"

# Method 2: Command-line argument
python main.py search "web framework" --token "your_github_token"

# Method 3: Config file
python main.py config set token "your_github_token"
```

#### Basic Usage

```bash
# Search repositories
python main.py search "web framework" --lang python --limit 10

# View Trending
python main.py trending --lang javascript --since weekly

# Score a repository
python main.py score python/cpython

# Get recommendations
python main.py recommend --limit 5

# Track trends
python main.py track vuejs/vue --action record

# Manage favorites
python main.py fav add facebook/react
python main.py fav list

# Launch TUI interface
python main.py tui

# Export report
python main.py export --source favorites --format html --output report.html
```

### 📖 Detailed Usage Guide

#### Search Command

```bash
# Basic search
python main.py search "machine learning"

# Advanced search (multi-condition filtering)
python main.py search "web framework" \
  --lang python \
  --sort stars \
  --order desc \
  --limit 20 \
  --min-stars 1000

# Search with GitHub query syntax
python main.py search "topic:react language:typescript"
```

#### Trending Command

```bash
# View today's trending
python main.py trending

# Filter by language
python main.py trending --lang rust

# View weekly trending
python main.py trending --since weekly

# View monthly trending
python main.py trending --since monthly
```

#### Scoring System

```bash
# Score a single repository
python main.py score facebook/react

# View detailed scores (all dimensions)
python main.py score vuejs/vue --detail

# Batch scoring
python main.py score python/cpython rust-lang/rust go-lang/go
```

#### Recommendation Engine

```bash
# Get personalized recommendations
python main.py recommend --limit 10

# Find similar repositories
python main.py recommend --similar-to facebook/react --limit 5

# Recommend by tech stack
python main.py recommend --lang rust --limit 10
```

#### TUI Interface

```bash
# Launch interactive TUI
python main.py tui

# TUI Controls:
# ↑/↓    Navigate up/down
# Enter  View details
# f      Favorite/unfavorite
# s      Score
# /      Search
# q      Back/Quit
```

#### Report Export

```bash
# Export favorites as JSON
python main.py export --source favorites --format json --output fav.json

# Export search results as CSV
python main.py export --source search:web --format csv --output results.csv

# Export as Markdown
python main.py export --source trending --format markdown --output trending.md

# Export as HTML report
python main.py export --source favorites --format html --output report.html
```

### 💡 Design Philosophy & Roadmap

#### Design Principles

1. **Zero-Dependency Philosophy** — Only Python standard library, eliminating environment setup barriers
2. **Offline-First** — Local SQLite storage, view favorites and history without network
3. **Progressive Intelligence** — Recommendation algorithm continuously improves based on user behavior
4. **Terminal-Native** — TUI deeply adapted to terminal environments for efficient operation

#### Tech Stack Choices

| Choice | Reason |
|--------|--------|
| Python Standard Library | Zero dependencies, best cross-platform compatibility |
| SQLite | Built into Python, no extra installation, lightweight and efficient |
| TF-IDF | Classic text similarity algorithm, simple and efficient in pure Python |
| ANSI Control Codes | Terminal UI standard, compatible with all major terminals |
| GitHub REST API | Official API, stable and reliable, well-documented |

#### Roadmap

- [ ] 🔌 Plugin System — Custom scoring dimensions and recommendation strategies
- [ ] 🌐 Web Dashboard — Built-in HTTP server-based web interface
- [ ] 📱 Notification System — Watched repository update notifications
- [ ] 🔄 GitLab/Gitea Support — Multi-platform repository discovery
- [ ] 🤖 LLM Integration — Enhanced recommendations with large language models
- [ ] 📊 Advanced Visualization — SVG chart export

### 📦 Packaging & Deployment

#### Install as CLI Tool

```bash
# Add to PATH (Linux/macOS)
echo 'alias reposcout="python /path/to/RepoScout-AI/main.py"' >> ~/.bashrc
source ~/.bashrc

# Use alias
reposcout search "AI agent"
```

#### Use as Python Package

```python
from github_client import GitHubClient
from scorer import RepoScorer
from recommender import Recommender

# Create client
client = GitHubClient(token="your_token")

# Search repositories
results = client.search_repos("web framework", language="python")

# Score
scorer = RepoScorer(client)
score = scorer.score_repo("facebook/react")
print(f"Score: {score['overall']}/{score['grade']}")
```

### 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m "feat: add some feature"`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Submit a Pull Request

**Commit Convention**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code refactoring
- `test:` Test related
- `chore:` Build/tooling related

### 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/gitstq">gitstq</a>
</p>
