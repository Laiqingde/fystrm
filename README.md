# fystrm

**fystrm** 是一个开源的网盘媒体管理中枢，定位 **CloudDrive2 + Emby + fystrm 中间层**，自动从挂载的网盘目录扫描视频、TMDB 刮削、生成 `.strm` 文件喂给 Emby/Jellyfin。

## 架构

三层全插件化：

```
扫描源 (CD2/本地)  ──► fystrm ──► strm/nfo/poster/subtitle ──► Emby
                       │
                       ├─ DrivePlugin    (扫源/转存)
                       ├─ MetaPlugin     (TMDB/豆瓣)
                       ├─ StrmPathPlugin (cd2_local | webdav)
                       └─ SourcePlugin   (资源订阅, v0.3+)
```

## v0.2 范围

- ✅ 扫描挂载目录 (`LocalDrivePlugin`)
- ✅ guessit + anitopy 文件名识别（电影 / 剧集 / 动漫）
- ✅ TMDB 中文刮削 + 多语言 fallback + 未匹配缓存
- ✅ **剧集完整支持**：Season XX/SxxExx.{strm,nfo,thumb} + tvshow.nfo + 季海报
- ✅ **字幕处理**：同目录字幕识别 + copy 到 strm 同目录跟随重命名（zh/en/ja...）
- ✅ **WebDAV strm 模式**：写 WebDAV URL（中文/空格 URL 编码）按 Library 切换
- ✅ Emby/Kodi 兼容 NFO 生成（movie/tvshow/episode）
- ✅ Emby `/Library/Refresh` 触发
- ✅ Web UI：媒体库 / 任务 / 媒体 / 设置
- ✅ WebSocket 实时进度推送
- ⏸ 网盘转存（接口预留，v0.3+ 实现）
- ⏸ 资源订阅 / 自动搜索（v0.3+）

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI + uvicorn + arq |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async |
| 缓存/队列 | Redis 7 |
| 前端 | Vue 3 + Vite + Naive UI |
| 容器 | Docker + Compose |

## 快速开始

```bash
git clone <repo> /opt/fystrm
cd /opt/fystrm
cp .env.example .env
vi .env  # 改 TMDB_API_KEY=

docker compose up -d
# 浏览器打开 http://<host>:8095/
```

第一次启动后：
1. 设置 → 确认 TMDB 已配置
2. 媒体库 → 新建：填扫描源、strm 输出、选 **strm 模式**（cd2_local 或 webdav）
3. 点"扫描" → 任务页看实时进度
4. 媒体页查看入库结果（含季/集 + 字幕数）
5. Emby 指向 strm 输出目录扫描

## 目录映射示例

### CD2 本地路径模式

```
扫描源: /scan-source/电影/复仇者联盟 (2012).mkv
strm 输出: /opt/fystrm/media/复仇者联盟 (2012)/复仇者联盟.strm
.strm 内容: /CloudNAS/115/电影/复仇者联盟 (2012).mkv  ← Emby 通过 CD2 挂载回源
```

### 剧集（v0.2）

```
扫描源:
  /scan-source/TV Shows/Breaking.Bad/Season 01/Breaking.Bad.S01E01.mkv
  /scan-source/TV Shows/Breaking.Bad/Season 01/Breaking.Bad.S01E01.zh.ass

strm 输出:
  /media/剧集/绝命毒师 (2008)/
    ├── tvshow.nfo
    ├── poster.jpg
    ├── fanart.jpg
    └── Season 01/
        ├── 绝命毒师 - S01E01.strm
        ├── 绝命毒师 - S01E01.nfo
        ├── 绝命毒师 - S01E01-thumb.jpg
        └── 绝命毒师 - S01E01.zh.ass    ← 字幕 copy 自源, 跟随中文剧名重命名
```

### WebDAV strm 模式

```
扫描源: /scan-source/TV Shows/Breaking.Bad/Season 01/Breaking.Bad.S01E01.mkv
.strm 内容: http://cd2:19798/dav/115/绝命毒师/Season%2001/Breaking.Bad.S01E01.mkv
                                ↑ webdav_path_prefix       ↑ URL 编码中文/空格
```

## License

AGPL-3.0
