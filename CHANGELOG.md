# Changelog

本项目所有版本变更记录。版本号遵循语义化版本，详细 release notes 见 [GitHub Releases](https://github.com/Laiqingde/fystrm/releases)。

## [v0.3.0] - 2026-05

认证 / CD2 集成 / 配置 Web 化 / UI 大改（22 个 commit）

### 新功能
- 账号密码认证：JWT (HS256) + bcrypt，全 API 保护，首启自动创建 admin，Web 改密
- CD2 Webhook 完整集成：接收 file/mount 事件 + 路径映射 + Bearer 鉴权，create/delete/rename 三动作
- 配置 Web 化：`app_settings` 表持久化，设置页 5 分组表单，secret 打码，不再依赖 .env
- 实时日志页：Redis pub/sub + WebSocket，按模块自动归类，类别+级别过滤
- UI 大改：仪表盘 (ECharts) + 深色/亮色主题 + 三页卡片化 + 复制配置 + 编辑按钮

### Library 配置增强
- 自定义 strm 后缀 / 元数据后缀
- 刮削开关 scrape_enabled（关闭只生成 strm + 镜像源元数据）
- 「跟扫描源相同」复选框，复制现有配置 select，移除无用「类型」字段

### 优化
- strm 文件名跟源 stem（保留 release tag）
- 中文电影 anime 误判修复
- /mnt 改 rw + CD2 路径前缀映射
- metadata 后置 + 跳过已存在（防 CD2 size 延迟误判）
- scan task 加 stage 阶段进度

### 修复
- WebSocket HTTP 403（WS 抽独立 router）
- scan task NameError total（僵尸 task 根因）
- 前端 WS URL 加 token query

## [v0.2.0] - 2026-05

剧集 / 字幕 / WebDAV

- 剧集完整支持：Season XX/SXXEXX 布局 + tvshow.nfo + 单集刮削
- 字幕处理：同目录识别 + 语言识别 + copy 重命名
- WebDAV strm 模式（按 Library 切换，URL 编码）
- TMDB 多语言 fallback + 未匹配缓存

## [v0.1.0] - 2026-05

MVP 首版

- 扫描挂载目录 + guessit/anitopy 识别 + TMDB 中文刮削
- 生成 strm + movie.nfo + poster + fanart
- Emby Library Refresh 触发
- Vue3 + Naive UI Web 界面 + WebSocket 进度
- Docker Compose 一键启动
- 四类 Plugin 抽象（Drive/Meta/StrmPath/Source）
