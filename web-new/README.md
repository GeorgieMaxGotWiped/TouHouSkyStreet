# 东方天空街 · 官网（web-new/）

東方天空街 Touhou Sky Street 的官方网站。纯静态 HTML / CSS / JavaScript，零框架、零构建依赖。

> 本目录与旧的 `web/` 并存、互不影响。新站成熟之后再决定是否替换。

## 设计概念：游戏自己的标题画面，就是官网

- **首页不是 landing page，而是一张活的 title screen**：底图直接用游戏的菜单背景原画（`bg_0.png`），
  菜单落在原画中段那条空白带上——和游戏里主菜单的位置（x560 / y380）是同一个意图。
- **操作也和游戏一样**：`↑ ↓` 移动光标、`Enter` / `Z` / 空格确认、`1-7` 直选，鼠标悬停即切换选中项。
- 选中的那一行前面会出现金色的 `>`，文字带 `+2,+3` 的硬阴影 —— 都照游戏主菜单的做法来。
- **往下滚动＝从天空街往下走**：页面越深颜色越暗，背景那层弹幕一路跟着你。
- 点站内链接会先闪一张「标题卡」再进目标页：卡面用游戏关卡标题卡的版式（小号拉丁标签 + 大字 + 副标题），内容则是目标页自己的身份，例如进舞台页是 `Stages / 七段上升的路 / 01 – EX`、进下载页是 `Start Game / 下载与运行 / Download & Run`。

这张卡是**跨页接力**的，不是两次跳变：

1. 本页把卡淡入，三行内容 260ms 落定（跳转时刻 280ms 略晚于它，避免动画被硬切）；
2. 卡面存进 `sessionStorage`，然后跳转；
3. 新页面 `<head>` 里的内联脚本更早一步给 `<html>` 加上 `warp-in`，遮罩从首帧就生效；
   紧跟 `#warp` 的 `js/warp-in.js` 在解析到卡片的那一刻把内容填好（终态、不重播入场）；
4. `js/site.js` 等字体就位（200ms 封顶）后把这张卡淡出，露出新页面。

于是「旧页消失 / 新页出现」这一刻是不存在的——屏幕上始终是一张连续的卡。卡片背景不透明，
就是为了让新页面在揭幕前被完整盖住，否则会看到亮度跳变。

配色与配色常量直接取自游戏源码 `src/engine/settings.py`：`COLOR_BLUE` → 青、`COLOR_YELLOW` → 金、
`COLOR_RED` / `COLOR_PURPLE` → 强调色、`COLOR_PANEL_BG` → 面板底色。全站方角、1px 线、四角括号，
不用圆角与胶囊按钮。

## 运行

- 双击 `启动预览.bat`：起本地服务并打开浏览器。
- 或手动：`python web-new/serve.py`（默认 8100 端口），浏览器访问 `http://127.0.0.1:8100`。

> 请用 `127.0.0.1` 而不是 `localhost`，避免 IPv6 解析问题。
> 图鉴 / 舞台 / 人物 / 曲目四页用 `fetch` 读取 `data/*.json`，**必须经由 HTTP 服务访问**；
> 直接双击 HTML 文件时首页与玩法 / 下载 / 关于仍能看，但这四页会提示需要起服务。
> 预览服务的缓存策略：页面 / 样式 / 脚本 / 数据带 `no-cache`，兼顾「改完刷新即可见」；
> 字体带 `public, max-age=600`。**别把字体也设成 `no-store`** —— 那会让浏览器每次翻页
> 都把 5.2MB 的中文字体重新下一遍，字体到位前文字先用回退字形，翻页时能看到一次字形跳变。

## 页面

| 路径 | 说明 |
| --- | --- |
| `index.html` | 首页：标题画面菜单 + 序、舞台、自机、系统、实机截图、下载入口 |
| `stages.html` | 七段舞台：关卡标题卡、道中 / 关底 Boss 立绘与逐个介绍、全部符卡、道中与关底曲名 |
| `characters.html` | 人物：四位自机（立绘、介绍、自机弹差异、战斗形象）+ 十七位 Boss（一位一行，按首次登场的面分组，立绘 + 介绍） |
| `items.html` | 物品图鉴：61 件物品，按稀有度 / 类型筛选 + 关键词搜索，悬停看属性与 Lore |
| `music.html` | 音乐室：七段舞台的 13 首曲目 |
| `gameplay.html` | 玩法：键位、自机与难度、一局流程、物品与重铸、画面设置、练习模式 |
| `download.html` | 下载与运行：打包版 / 源码、系统要求、首次启动、存档位置、排错 |
| `about.html` | 关于：项目简介、技术栈、同人声明与素材许可 |

## 数据与素材

数据由脚本从游戏源码导出，**不要手改生成的文件**：

| 文件 | 来源 |
| --- | --- |
| `data/items.json` | `python web-new/tools/build_assets.py data`（读 `src/systems/item_system.py`） |
| `assets/**` | `python web-new/tools/build_assets.py`（读 `assets/` 与 `previews/` 下的原始素材） |
| `data/stages.json` | 手工维护（关卡顺序、Boss 归属、符卡与曲名，核对自 `src/stages/*.py` 与 `src/engine/settings.py`） |
| `data/bosses.json` | 手工维护（Boss 介绍文字，按 id 合并；同一位在多面出现时人物页只列一次，另一次登场写成条目里的脚注。核对自 `src/stages/*.py` 的台词与 `src/entities/boss.py` 的符卡注释） |
| `data/chara.json` | 手工维护（自机名单、介绍、代表色，核对自 `src/engine/settings.py`） |
| `data/tracks.json` | 手工维护（曲名，核对自 `src/engine/settings.py` 的 `*_MUSIC_NAME`） |

素材构建脚本可以只跑某一步：

```
python web-new/tools/build_assets.py            # 全量
python web-new/tools/build_assets.py title      # 只重做首页底图
python web-new/tools/build_assets.py shots      # 只重做实机截图
python web-new/tools/build_assets.py data       # 只重新导出物品数据
```

步骤名：`title` / `stage` / `chara` / `boss` / `item` / `shots` / `icon` / `data`。

Boss 立绘有两个套组（游戏设置里可切换，见 `src/engine/settings.py` 的 `BOSS_ART_SETS`）。
本站统一用「另一版」：由 `web-new/tools/build_assets.py` 顶部的 `BOSS_ART_SET` 决定，
舞台页与人物页共用同一批图。想换回「新版」就改这一个常量，再跑 `python web-new/tools/build_assets.py boss`。

改完页面后可以跑一次引用检查，确认没有引用到不存在的文件：

```
python web-new/tools/check_links.py
```

## 目录

```
web-new/
  index.html            首页（标题画面）
  stages.html           舞台
  characters.html       人物（自机 + Boss）
  items.html            物品图鉴
  music.html            音乐室
  gameplay.html         玩法
  download.html         下载
  about.html            关于
  css/site.css          全站样式（设计令牌 / 菜单语言 / 各页区块）
  js/danmaku.js         背景弹幕引擎（环形 / 螺旋 / 自机狙，尊重 prefers-reduced-motion）
  js/title.js           首页标题画面菜单（键盘 + 鼠标）
  js/site.js            滚动进场 / 标题卡转场（发起与接力淡出）/ 导航高亮
  js/warp-in.js         跨页接力：在新页面首帧把上一页的标题卡原样立起来
  js/render.js          舞台 / 人物 / 曲目三页的数据渲染（人物页由 chara + stages + bosses 三份数据拼成）
  js/items.js           物品图鉴渲染与筛选
  data/items.json       物品数据（脚本生成）
  data/stages.json      关卡数据
  data/chara.json       自机数据
  data/tracks.json      曲目数据
  data/bosses.json      Boss 介绍（按 id 合并进舞台页与人物页）
  assets/fonts/         与游戏同源的两套字体（font1 拉丁 / font2 中文）
  assets/img/           首页底图、关卡标题卡、实机截图、站点图标
  assets/chara/         自机立绘与战斗形象（WebP）
  assets/boss/          Boss 立绘（WebP，游戏里的「另一版」套组）
  assets/item/          物品图标（WebP，无损）
  tools/build_assets.py 素材与数据构建
  tools/check_links.py  本地引用检查
  serve.py              本地预览服务
  启动预览.bat          一键预览
```

## 无障碍与降级

- 全部动效都尊重 `prefers-reduced-motion`：开启后弹幕画布不启动、菜单不等入场动画、转场直接跳转（不写 `sessionStorage`，所以新页面也不会立起遮罩）。
- 转场有兜底：卡面接不上时立刻撤掉遮罩，绝不会把页面盖住；`<head>` 里还有一个 3s 的保险，超时自动撤销 `warp-in`。
- 标签页切到后台时弹幕自动停帧；窗口改变尺寸时重建发射器并清空场上弹幕。
- 首页在宽高比小于 4:3（竖屏 / 平板）时会改用 HTML 标题 + 底部菜单，因为原画右侧的竖排标题会被裁掉。