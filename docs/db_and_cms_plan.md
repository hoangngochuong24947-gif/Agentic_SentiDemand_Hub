# SentiDemand 数据库扩展与 CMS 管理方案计划

本方案旨在为服务器上的 `SentiDemand` 项目引入结构化数据库，以替代目前基于 `run_registry.json` 和碎片化 CSV 文件的文件系统存储，实现对评论分析数据的高效管理、全局搜索与可视化过滤。同时评估了引入 CMS（内容管理系统）的可行性。

---

## 1. 服务器当前数据库状态审计
根据对服务器环境的深度排查：
- **无活动数据库服务**：目前服务器（2核 / 2GB 内存）上没有运行任何数据库服务守护进程（如 MySQL, PostgreSQL, Redis, MongoDB 均未安装或未启动）。
- **无数据库端口监听**：系统监听列表中不存在 3306 (MySQL)、5432 (Postgres)、6379 (Redis) 等常见数据库端口。
- **历史痕迹**：仅存在 `/var/log/mysql` 历史日志目录，但 MySQL 本身已被卸载或禁用。

---

## 2. 数据库选型评估：面向 2GB 内存服务器的方案

由于服务器总内存仅有 **2GB (实际可用 1.6GiB)**，且当前 Python 进程已占用约 567MB，数据库选型必须将 **内存占用** 放在第一优先级：

| 数据库 | 内存占用 | 优点 | 缺点 / 风险 | 结论 |
| :--- | :--- | :--- | :--- | :--- |
| **SQLite3** | **~0 MB** (无常驻守护进程) | **嵌入式设计**，读写时才消耗极微量内存；单文件存储，备份极其方便（直接复制 `.db` 文件）；Python 原生支持，零配置。 | 并发写入性能一般（但本项目为单人/低频使用，完全不受影响）。 | **首选推荐 ⭐⭐⭐⭐⭐** |
| **PocketBase** | **~15 - 30 MB** (常驻服务) | 基于 Go + SQLite，**极度轻量**；自带超高颜值的管理后台（开箱即用 CMS）；自动生成 REST API 和 SDK。 | 需要额外运行一个轻量级系统守护进程。 | **CMS 方案首选 ⭐⭐⭐⭐⭐** |
| **PostgreSQL** | **~50 - 100 MB** (常驻服务) | 关系型数据库标杆，功能强大，支持高并发和复杂查询。 | 闲置时也会常驻内存，对 2GB 内存的机器来说属于“杀鸡用牛刀”。 | **备选方案 ⭐⭐** |
| **MySQL** | **~150 - 400 MB** (常驻服务) | 使用最广泛的关系型数据库。 | **极其消耗内存**。在 2GB 内存服务器上运行极易导致 OOM 崩溃。 | **不推荐 ❌** |
| **MongoDB** | **~500 MB+** (常驻服务) | 文档型数据库，适合存储非结构化数据。 | 内存开销巨大（默认占用 50% 物理内存），会立即撑爆系统。 | **极不推荐 ❌** |

---

## 3. 数据库引入实施计划 (SQLite 方案)

我们可以通过两阶段改造，平滑地将数据迁移到 SQLite 数据库中：

### Phase 1: 引入本地 SQLite3（后端代码改造）
将原有的 `run_registry.json`（JSON 文件注册表）重构为本地 `sentidemand.db` 数据库。

1. **设计表结构**：
   - **`runs` 表**：记录每次上传分析的历史元数据。
     ```sql
     CREATE TABLE runs (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         run_id TEXT UNIQUE NOT NULL,
         source_file TEXT NOT NULL,
         status TEXT NOT NULL,
         created_at TEXT NOT NULL,
         user_message TEXT,
         summary_json TEXT
     );
     ```
   - **`comments` 表**：记录清洗后的每条评论明细及分析结果（实现跨 run 的全局查询）。
     ```sql
     CREATE TABLE comments (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         run_id TEXT NOT NULL,
         raw_content TEXT NOT NULL,
         cleaned_content TEXT,
         sentiment_label TEXT,  -- positive / neutral / negative
         sentiment_score REAL,
         keywords_json TEXT,    -- 该评论提取出的关键词
         FOREIGN KEY(run_id) REFERENCES runs(run_id)
     );
     ```
2. **重构数据存储层**：
   - 修改 `src/comment_analyzer/visualization/run_registry.py`，将 `record()` 和 `list_runs()` 方法改写为 SQL 操作。
   - 在 `gallery.py` 的 `/upload` 接口中，在 Pipeline 分析完成后，将 DataFrame 数据批量插入 `comments` 表中（使用 `pandas.DataFrame.to_sql` 可以在几行代码内搞定）。

---

## 4. 可视化 CMS 管理方案：引入 PocketBase

如果您希望有一个**可视化的后台界面**来直观地增删改查、搜索、导出评论，引入 **PocketBase** 是最优雅、开发成本最低的方案。

### 什么是 PocketBase？
PocketBase 是一个用 Go 编写的开源后端。它将 **SQLite 数据库、用户身份认证、文件存储、管理员后台、REST API** 打包在了一个只有十几兆的单一可执行文件中。

### 方案设计：
1. **轻量运行**：在服务器上启动 PocketBase 监听 `127.0.0.1:8090`，通过 Nginx 代理规则将其映射到 `https://louilu.cn/pb/`。
2. **数据同步**：
   - SentiDemand 运行完毕后，通过 HTTP 接口将 runs 和 comments 写入 PocketBase；
   - 或者 SentiDemand 直接读写 PocketBase 底层的 SQLite `.db` 文件。
3. **免开发后台 (CMS)**：
   - 您可以直接访问 `https://louilu.cn/pb/_/` 登录管理员后台。
   - 界面提供了类似 Airtable/Notion 的电子表格界面，您可以直接进行**关键词搜索、情感分类过滤、手动修改数据、一键导出 CSV/JSON**。

```
[用户浏览器] <---> [Nginx (443)] <---> [PocketBase Admin UI (8090)]
                                             |
                                     (读写同一个 SQLite.db)
                                             |
[SentiDemand Python (FastAPI)] <------------+
```

---

## 5. 后续行动路线

如果您赞同该规划，我们可以在继续开发时按以下路线实施：
1. **当前开发**：优先按照先前的 `Audit & Repair` 计划，清理线上 `https://louilu.cn/app/` 的开发文案残留、404 静态资源缺失和 runs 页面可见性。
2. **数据库重构**：编写一个 `sqlite` 适配器，将 `run_registry.json` 替换为本地 `sqlite3`。
3. **PocketBase 部署（可选）**：在服务器上下载部署 PocketBase，并接入 Nginx 路由。
