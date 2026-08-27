# 官方网站（web/）

东方天空街 ~ Touhou Sky Street 官方资讯站点。纯静态 HTML / CSS / JavaScript，零构建依赖。

## 运行

```bash
python web/serve.py
# 打开 http://127.0.0.1:8000
```
也可用 `cd web` 后执行 `python -m http.server 8000`。

图鉴页通过 `fetch` 读取 `data/items.json`，因此**必须经由 HTTP 服务访问**（直接双击 HTML 文件无法加载图鉴）。

## 页面

| 路径 | 说明 |
| --- | --- |
| `index.html` | 首页：Hero、特色、截图、下载入口 |
| `gameplay.html` | 玩法、操作、难度与模式 |
| `characters.html` | 六大舞台与主要 Boss（图鉴整理中） |
| `items.html` | 物品图鉴（按罕见度/类型筛选） |
| `download.html` | 下载、系统要求、运行方式 |
| `about.html` | 项目简介、同人声明、素材许可 |

## 数据

- `data/items.json`：由脚本从游戏源码导出。
- 更新物品后重新生成：

```bash
python web/tools/export_items.py
```

## 目录

```
web/
  index.html            # 各页面
  css/style.css         # 全局样式
  js/site.js            # 导航高亮 / 视口淡入
  js/items.js           # 物品图鉴渲染与筛选
  data/items.json       # 物品数据（自动导出生成）
  assets/img/           # 站点位图素材
  tools/export_items.py # 物品数据导出脚本
```

