# 官方网站（web/）

东方天空街 ~ Touhou Sky Street 官方资讯站点。纯静态 HTML / CSS / JavaScript，零构建依赖。

## 运行

```bash
python web/serve.py
# 打开 http://127.0.0.1:8000
```
也可用 `cd web` 后执行 `python -m http.server 8000`。

图鉴 / 画廊 / OST 页通过 `fetch` 读取 `data/*.json`，因此**必须经由 HTTP 服务访问**（直接双击 HTML 文件无法加载）。

## 页面

| 路径 | 说明 |
| --- | --- |
| `index.html` | 首页：Hero（头图 `bg_0`）、特色、截图、下载入口 |
| `gameplay.html` | 玩法、操作、难度与模式 |
| `characters.html` | 六大舞台与主要 Boss（图鉴整理中） |
| `items.html` | 物品图鉴（按罕见度/类型筛选） |
| `gallery.html` | 人物画廊：玩家与 Boss 图鉴（WebP 优化） |
| `ost.html` | 原声音乐页（曲目暂空） |
| `download.html` | 下载、系统要求、运行方式 |
| `about.html` | 项目简介、同人声明、素材许可 |

## 数据

| 文件 | 生成方式 |
| --- | --- |
| `data/items.json` | `python web/tools/export_items.py`（从游戏源码导出） |
| `data/gallery.json` | `python web/tools/build_assets.py`（人物图优化 + 元数据） |
| `data/music.json` | 手动维护，当前曲目为空 |

## 目录

```
web/
  index.html            # 各页面
  css/style.css         # 全局样式
  js/site.js            # 导航高亮 / 视口淡入
  js/items.js           # 物品图鉴渲染与筛选
  js/gallery.js         # 画廊渲染与灯箱
  js/ost.js             # OST 曲目渲染（暂空）
  data/items.json       # 物品数据（导出生成）
  data/gallery.json     # 画廊数据（导出生成）
  data/music.json       # 曲目数据（手动）
  assets/img/           # 站点位图素材（含 hero.webp 头图）
  assets/gallery/       # 人物图（WebP）
  serve.py              # 本地多线程服务
  tools/export_items.py # 物品数据导出脚本
  tools/build_assets.py # 头图/人物图优化 + 画廊数据
```
