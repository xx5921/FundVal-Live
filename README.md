# FundVal Live

![GitHub stars](https://img.shields.io/github/stars/xx5921/FundVal-Live?style=social)
![GitHub views](https://komarev.com/ghpvc/?username=xx5921&repo=FundVal-Live&color=blue&style=flat-square&label=views)

**盘中基金实时估值与逻辑审计系统**

本仓库基于原项目 [Ye-Yu-Mo/FundVal-Live](https://github.com/Ye-Yu-Mo/FundVal-Live) fork 后二次开发。
当前仓库地址为 [xx5921/FundVal-Live](https://github.com/xx5921/FundVal-Live)，用于持续维护、自托管部署和后续功能迭代。

原项目中的公开演示和外部入口不再作为本仓库的维护内容，请直接以本仓库代码和文档为准。

## 二次开发说明

- 保留原项目核心能力：实时估值、AI 分析、持仓管理、通知和多数据源接入
- 新增生产环境部署文件 `docker-compose.prod.yml`
- 新增持仓操作记录相关能力，支持 AI 分析时引用操作历史上下文
- 新增定时 AI 规则与执行日志
- 对部署配置和前端相关页面做了同步调整

## 功能特性

- **实时估值**：基于持仓穿透 + 实时行情加权计算，支持东方财富、养基宝、小倍养基三类数据源
- **AI 分析**：接入 OpenAI 协议兼容模型，支持基金和持仓两个维度分析
- **定时 AI 规则**：可按交易日定时触发分析，并把结果发送到通知渠道
- **持仓管理**：多账户、父子账户结构，支持买入/卖出流水，自动重算持仓，支持切换默认账户
- **持仓操作记录**：记录操作历史，供基金详情和持仓分析使用
- **养基宝集成**：扫码登录、一键导入持仓、实时估值同步
- **小倍养基集成**：手机号 + 短信验证码登录，按账户分组一键导入全部持仓
- **多渠道通知**：支持 Webhook、邮件等通知方式
- **指数基金成分股**：基金详情页展示 Top 10 成分股实时行情，支持场内溢价监控
- **历史净值**：支持 1W / 1M / 3M / 6M / 1Y / ALL 时间范围
- **估值准确率**：记录每日估值误差，统计各数据源准确率
- **自选列表**：支持自定义基金分组
- **数据源偏好**：支持用户级别数据源切换和偏好持久化

## 快速开始

### 1. 准备配置

复制环境变量模板并修改为自己的配置：

```bash
cp .env.example .env
```

重点检查以下内容：

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ALLOWED_HOSTS`
- `ALLOW_REGISTER`
- `FRONTEND_PORT`

### 2. 选择部署方式

本仓库提供两套 Compose 文件：

- `docker-compose.yml`：本地开发 / 联调
- `docker-compose.prod.yml`：生产部署，使用镜像和独立配置卷

本地启动：

```bash
docker compose up -d
```

生产启动：

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 3. 初始化管理员

首次启动后，查看后端日志中的 `Bootstrap Key`，然后访问：

```text
http://localhost:21345/initialize
```

按页面提示初始化管理员账号和基础配置。

### 4. 常用操作

```bash
# 查看后端日志
docker compose logs -f backend

# 手动同步基金数据
docker compose exec backend python manage.py sync_funds
```

如需宿主机直接访问数据库，可按 `docker-compose.yml` 中的注释开启数据库端口映射。

## 手动部署

如果不使用 Docker，可以直接参考仓库中的 `build.sh`、`start.sh` 和 `stop.sh` 进行构建与启动。

## 技术栈

- **Frontend**: React 19 + Vite + Ant Design + ECharts
- **Backend**: Django 6 + DRF + Celery
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Platform**: Web + Desktop (Tauri) + Android (Capacitor)

## 常见问题

遇到注册、部署、数据源或持仓计算问题，请先查看 [问题排查文档](docs/问题排查.md)。

## 开源协议

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源协议。

这意味着：

- 你可以自由使用、修改、分发本软件
- 个人使用无需开源你的修改
- 如果你用本项目代码提供网络服务（SaaS），必须开源你的修改

详见 [LICENSE](LICENSE) 文件。

## 免责声明

本项目提供的数据与分析仅供技术研究使用，不构成任何投资建议。市场有风险，代码无绝对，交易需谨慎。
