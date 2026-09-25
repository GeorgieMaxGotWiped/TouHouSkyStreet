# 东方天空街 ~ Touhou Sky Street

基于 Hypixel Skyblock 的东方 Project 同人弹幕射击游戏（STG），使用 Python + Pygame 开发。

## 环境要求

- Windows 10/11
- Python 3.8+（安装时勾选 “Add Python to PATH”）
- 首次运行会自动检测并安装依赖；也可手动执行：`pip install -r requirements.txt`
- 若自动检测仍找不到 Python，可在根目录新建 python_path.txt，第一行填写 Python 可执行文件的完整路径（如 C:\Python313\python.exe）

## 物品与掉落

- 游戏内含 54 件可掉落物品（武器/护甲/护符/重铸石/材料），掉落表见 `src/systems/item_system.py`；掉落概率遵循 items.md 表格，爆率加成按乘算，其余 +xx% 效果按加算
- 部分物品携带 C 技能（C 键释放，每面有使用次数限制，同时只能装备 1 件）；重铸石可为装备附加前缀
- 休整阶段可购买/出售物品，并在 B 键撤离时将本局物资存入本地仓库；Game Over 时本局装备与金币不会保留
- 物品贴图位于 `assets/items/<物品id>.png`，缺失时自动优雅回退

## 运行游戏

- 双击根目录 `启动游戏.bat`（自动检测本机 Python，缺少依赖时自动安装）
- 或命令行执行：`python main.py`
- 可选难度参数：`python main.py easy|normal|hard|lunatic`

## 鼠标操作

- 主菜单 / 设置 / 自机选择 / 出征准备 / 符卡练习 / Boss 奖励 / 休整界面均已支持鼠标点击：悬停可切换选中项，左键点击直接确认
- 自机选择界面：点右侧列表里的一行换人（悬停只亮边框，不会自动换），点右下角「确定」出征
- 休整界面底部「下一关（N）」「撤离/放弃（B）」「返回主菜单（Esc）」以及页签、装备槽、背包、商店（购买/出售）、锻造（重铸石/物品/确认）均可鼠标点击
- 较长的物品列表（仓库 / 背包 / 商店 / 锻造 / 装备选择）支持鼠标滚轮上下滚动，不再因鼠标悬停而自动滚动
- 对话推进也支持鼠标左键点击

## 界面风格与仓库

- 休整 / 出征准备等界面采用 Hypixel SkyBlock 原版 Minecraft GUI 风格（`src/ui/skyblock_ui.py`）：槽位网格 + 悬停提示框，物品只显示图标
- 主菜单 `Storage` 可打开本地仓库（`src/ui/storage.py`）：查看库存物品、对仓库中的装备使用重铸石锻造

## 难度选择

- 主菜单 Start Game 后先选自机、再进入难度选择界面，当前仅开放 Easy，其余难度显示为锁定
- 命令行参数 `python main.py easy|normal|hard|lunatic` 仍可直接指定难度

## 自机选择

- 主菜单 Start Game / Extra Stage 之后先选一位自机（`src/ui/character_select.py`），再往下走：立绘直接站在键艺图上（不套面板），右侧一列是全部自机，选中的那一位在列表里展开称号与介绍，左下角是当前选择的徽记与名牌，右下角「确定」
- 本屏只展示正常立绘（对话 / Bomb 卡用的那张），不再预览关卡里的站立 / 移动贴图
- 左右 / 上下 / 滚轮切换自机，Enter/Z 确定，Esc 返回主菜单；鼠标点列表换人、点「确定」出征
- 选中的自机一路带进关卡：战场上的站立 / 移动贴图取该角色目录（`assets/sprites/self/<角色>/stg1.png` / `stg2.png`），剧情对话里的立绘与**名牌**也跟着换（`cfg.PLAYER_DIALOGUE_NAME`，例如选弓手后 Boss 与旁白都称你为 Archer）
- 自机清单、名字与介绍文字都来自 `src/engine/settings.py` 的自机登记表：加一位角色只要在那里登记一行，这一屏会自动多出一行（列表里的「第几位 / 共几位」也随之刷新）
- 四位自机的**自机弹**各不相同（`cfg.PLAYER_CHARACTER_SHOTS`，参数登记在 `src/engine/settings.py`）：冰焰（默认）与旧版逐发一致 —— 1/2/3 条扇形 + 追踪弹；魔法使 1/3/5 条、扩散两倍、固定弹穿透、没有追踪弹；弓手与魔法使同形（扩散相同、低速减半）但不穿透，所有箭从**同一点**射出（起始点收束），中间那支每 240 帧有一根是命中敌人时炸掉小范围敌弹的爆裂箭（`Explosive_Arrow.png`），其余时候中间也是普通箭（`Iron_Arrow.png`）；重装 1/2/3 条笔直向上 + 追踪弹
- 自机弹的**贴图按自己的飞行方向转正**（`src/entities/bullet.py` 的 `_draw_player_sprite`）：扇形散开的五条箭各指各的弹道，追踪弹改向后贴图跟着转；方向在发射时就是发射角，之后由追踪逻辑改向时同步刷新。敌弹的贴图 / 图元一行未动，载入界面会把本机体用得上的每个方向先烤好（第一发不现转）。自检见 `tools/_verify_shots.py`

## 游戏速度

- 战斗中按 `F8` 减速、`F9` 加速、`F10` 恢复 `1.0x`，可选范围 `0.25x ~ 2.0x`
- 主菜单「设置 → 游戏速度」也可用方向键/鼠标条调节，数值保存到 `config.json` 的 `game_speed`
- 流速会同步缩放弹幕、敌机、玩家、关卡与特效时间轴；音乐与音效保持原速

## Boss 立绘

- Boss 立绘按套组存放在 `assets/sprites/bosses/<套组>/`：`new`（默认，新版立绘）、`another`（另一版立绘），`legacy` 为缺图时的兜底
- 主菜单「设置 → Boss 立绘」可在两套之间切换（方向键 / 点击分段按钮），选择保存到 `config.json` 的 `boss_art`
- 立绘统一为透明背景 PNG：`src/engine/boss_art.py` 只做载入与缓存（同一张图每个进程解码一次，关卡载入时后台预热）；白底或边缘带白框的图请先用离线脚本处理成透明 PNG 再放入
- 对话立绘另按「头高 ÷ 内容高」做取景对齐（`src/engine/settings.py` 的 `DIALOGUE_PORTRAIT_HEAD_RATIO` / `DIALOGUE_PORTRAIT_SELF_HEAD_RATIO`）：换图或加图后用 `tools/_portrait_head_ruler.py` 生成标尺图重新量一遍填表，`tools/_dialogue_preview.py` 可把各段对白渲染成图片核对同屏人物的相对大小；表里没有的立绘不做补偿
- 取景补偿的开关是关卡的 `dialogue_portrait_harmonize`（`src/stages/stage1.py`，默认开）：Ex 面两位 Boss 换成与本作其他 Boss 同规格的高清立绘后一并纳入对齐，先前「裂隙面像素立绘按原样显示」那条不再适用
- 立绘整体大小由 `DIALOGUE_PORTRAIT_SCALE` 统一缩放，靠边站位允许探出战斗框的上限是内容宽的 `DIALOGUE_PORTRAIT_EDGE_BLEED`（`src/ui/dialogue.py`）：换上一张「脸不在内容正中」的立绘后如果脸被推出框，先看这个上限够不够

## 练习模式

- 主菜单选择 `Practice` 进入符卡练习：左侧选择 Boss（含道中 Boss 与 BOSS RUSH 各 Boss），右侧选择符卡（含 Last Spell），Enter 开始
- 练习模式固定满火力（400）、3 残机、3 雷；击破符卡后可按 R 重试、N 下一张、Esc 返回选择
- 练习模式不写入主线存档（分数/残机/物品等均不影响正式流程）

## Ex 面：裂隙 ~ The Rift

- 主菜单 `Extra Stage` 进入（关卡实现见 `src/stages/stage_ex.py`）：进去后只能选自机与难度，选完难度直接开打，不进仓库 / 携带界面
- 本面不结算装备：装备被动、C 技能、掉落与金币一律不生效，开局固定满火力（400）；通关后回主菜单，不写物品存档、也不进休整 / Boss 奖励界面
- 道中 Boss **Wizardman**（先对话再开打，暂不配符卡）、关底 Boss **Barry**（暂不配符卡，整场由自定义非符弹幕撑起）；道中残兵清空后进入 Barry 的战前对话，战后对话结束即通关
- 素材：`tools/_gen_stage_ex_assets.py` 生成裂隙地板 / 洞壁 / 关卡标题卡与五种裂隙小怪；两位 Boss 立绘取自 Hypixel SkyBlock Wiki 的 NPC 全身像，离线处理成透明 PNG 后放进 `assets/sprites/bosses/{new,another}`

## 打包

- 双击 `build_exe.bat`（自动检测本机 Python 并安装 PyInstaller），产物输出到 `dist\TouHouSkyStreet\`：`TouHouSkyStreet.exe` + `_internal\`，双击其中的 exe 即可运行
- 等价命令：`pip install -r requirements-build.txt` 后执行 `python -m PyInstaller --onedir --noupx --name TouHouSkyStreet --add-data "assets;assets" --icon "assets\gui\icon.png" --noconsole main.py`
- 用 `--onedir` 而不是 `--onefile`：单文件版每次启动都要把整包解压到 `%TEMP%`（本作资源约 470 MB，启动要等十几秒，退出即删、下次重来），文件夹版就地读资源，启动快、资源还能随时替换
- `--noupx`：UPX 只压 PE 二进制，对本作的 WAV / PNG 没有收益，却会明显提高杀软误报率
- 分发：把整个 `dist\TouHouSkyStreet\` 文件夹压缩发给别人即可，对方无需安装 Python；产物是 64 位，需要 64 位 Windows 10 / 11
- 图标：窗口 / 任务栏 / EXE 图标统一取 `assets/gui/icon.png`（换图标只需替换这个文件，打包时由 Pillow 转成 ico）
- 用户设置 `config.json` 与仓库存档 `warehouse.json` 都存在 exe 同级目录；重新打包时 `build_exe.bat` 会自动把它们搬到新产物目录
- 确实需要单文件版时，把上面的 `--onedir` 换成 `--onefile` 即可（代价是每次启动都要解包）

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `main.py` | 游戏入口 |
| `src/` | 源码：`engine`（引擎/设置/字体/绘制与呈现/伪3D/符卡背景）、`entities`（玩家/敌人/Boss/子弹）、`stages`（关卡 1-6 与 Ex 面）、`systems`（物品/掉落/效果/仓库/C技能）、`ui`（菜单/HUD/对话/过场/Boss奖励/难度/自机选择/SkyBlock风格UI/仓库） |
| `assets/` | 资源：`backgrounds`（背景）、`sprites`（精灵/立绘套组）、`fonts`（字体）、`sounds`（音乐/音效/SE）、`gui`（Minecraft 风格 GUI 贴图）、`titles`（标题图） |
| `tools/` | 开发辅助脚本；`archive/` 存放已使用完毕的一次性补丁脚本 |
| `backup/` | 旧版源码备份 |
| `dist/` | 打包产物（`TouHouSkyStreet/` 文件夹） |
| `previews/` | 开发期预览截图（由工具脚本生成） |

## 开发脚本

- `tools/_verify_items.py`、`tools/_verify_warehouse.py`：物品掉落/效果与本地仓库回归测试
- `tools/_smoke_stage2.py`、`tools/_smoke_stage3.py`、`tools/_smoke_stage5.py`、`tools/_smoke_stage6.py`、`tools/_smoke_goldor_terminal.py`：关卡冒烟回归测试，输出截图到 `previews/`
- `tools/_smoke_stage_ex.py`：Ex 面冒烟（45s 道中 → Wizardman 对话 → 道中Boss 战 → Barry 对话 → 关底战 → 通关，并把关键节点渲染成图）；`tools/_smoke_ex_entry.py`：Ex 面入口冒烟（主菜单 → Extra Stage → 自机 → 难度 → 载入 → 战斗，顺带验证「不进仓库 / 无装备效果 / 通关回主菜单」三条规矩）
- `tools/_gen_stage2_assets.py`、`tools/_gen_stage3_assets.py`、`tools/_gen_stage5_assets.py`、`tools/_gen_stage6_assets.py`、`tools/_gen_stage_ex_assets.py`：程序化生成关卡资源
- `tools/_ui_gpu_smoke.py`：界面绘制冒烟（每个界面各画一帧，报告显卡绘制指令数）；`tools/_ui_gpu_compare.py`：界面「显卡路径 关 / 开」对比截图；`tools/_ui_residue_check.py`：界面残留检查（从可退出界面返回后不该留下上一个界面的像素）
- `tools/_bench_battle.py`：战斗场景基准与弹幕验收（`python tools\_bench_battle.py stage3 40 3 900 previews/battle/out.png`：把关卡直接推到关底 Boss，报告帧时间 / 弹幕条数 / 贴图种类，并输出「显卡弹幕 / 1x 画布弹幕 / 差分」三联对比图，并检查弹幕有没有越过战斗框边界）
- `tools/_bench_spellcard.py`：开符基准（`python tools\_bench_spellcard.py stage6 3 200 1`：把关卡推到关底 Boss，先走一遍载入界面那套符卡预热，再逐张符卡报告普通帧 / 横幅期 / 符卡后期的帧时间与超 16.7ms 的帧数；默认走真实显示驱动的显卡路径，`PROBE_DUMMY=1` 走软件回退）
- `tools/_bullet_subpixel_check.py`：弹幕子像素位置检查（`python tools\_bullet_subpixel_check.py 3`：取一发斜飞弹每帧登记给显卡的贴图坐标，报告每帧步进与误差，确认位置不再被吸在 1 逻辑像素的网格上）
- `tools/_scratch_panel_check.py`：符卡面板复用检查（冻结时钟后，对比「贴图重用面板池」与「每帧新建面板」两条路径的渲染结果，确认复用不会留下上一帧的残影）
- 其余 `tools/_*.py` 为开发期调试/预览脚本

## 注意事项

- 部分音乐文件仍在打磨中，代码会自动跳过缺失/播放失败的音乐，不影响运行
- `__pycache__/`、`build/`、`dist/`、`previews/`、`backup/` 已在 `.gitignore` 中忽略
- 战斗区里只剩符卡背景（`src/engine/spell_bg.py`）还是 1x 绘制后整体放大：地面 / 弹幕 / 敌机 / Boss / 自机 / 掉落物 / 召唤物 / 符卡演出 / 文字 / 立绘都已按渲染倍率原生绘制，这一层与它们之间还有清晰度落差，后续再补
