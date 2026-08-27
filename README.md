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

- 主菜单 / 设置 / 出征准备 / 符卡练习 / Boss 奖励 / 休整界面均已支持鼠标点击：悬停可切换选中项，左键点击直接确认
- 休整界面底部「下一关（N）」「撤离/放弃（B）」「返回主菜单（Esc）」以及页签、装备槽、背包、商店（购买/出售）、锻造（重铸石/物品/确认）均可鼠标点击
- 较长的物品列表（仓库 / 背包 / 商店 / 锻造 / 装备选择）支持鼠标滚轮上下滚动，不再因鼠标悬停而自动滚动
- 对话推进也支持鼠标左键点击

## 练习模式

- 主菜单选择 `Practice` 进入符卡练习：左侧选择 Boss（含道中 Boss 与 BOSS RUSH 各 Boss），右侧选择符卡（含 Last Spell），Enter 开始
- 练习模式固定满火力（400）、3 残机、3 雷；击破符卡后可按 R 重试、N 下一张、Esc 返回选择
- 练习模式不写入主线存档（分数/残机/物品等均不影响正式流程）

## 打包 EXE

- 双击 `build_exe.bat`（自动检测本机 Python 并安装 PyInstaller），产物输出到 `dist\TouHouSkyStreet.exe`
- 等价命令：`pip install -r requirements-build.txt` 后执行 `python -m PyInstaller --onefile --name TouHouSkyStreet --add-data "assets;assets" --noconsole main.py`

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `main.py` | 游戏入口 |
| `src/` | 源码：`engine`（引擎/设置/字体/伪3D/符卡背景）、`entities`（玩家/敌人/Boss/子弹）、`stages`（关卡 1-6）、`systems`（物品/掉落/效果/仓库/C技能）、`ui`（菜单/HUD/对话/过场/Boss奖励） |
| `assets/` | 资源：`backgrounds`（背景）、`sprites`（精灵）、`fonts`（字体）、`sounds/musics`（音乐）、`titles`（标题图） |
| `tools/` | 开发辅助脚本；`archive/` 存放已使用完毕的一次性补丁脚本 |
| `backup/` | 旧版源码备份 |
| `dist/` | 打包产物 |
| `previews/` | 开发期预览截图（由工具脚本生成） |

## 开发脚本

- `tools/_verify_items.py`、`tools/_verify_warehouse.py`：物品掉落/效果与本地仓库回归测试
- `tools/_smoke_stage2.py`、`tools/_smoke_stage3.py`、`tools/_smoke_stage5.py`、`tools/_smoke_stage6.py`、`tools/_smoke_goldor_terminal.py`：关卡冒烟回归测试，输出截图到 `previews/`
- `tools/_gen_stage2_assets.py`、`tools/_gen_stage3_assets.py`、`tools/_gen_stage5_assets.py`、`tools/_gen_stage6_assets.py`：程序化生成关卡资源
- 其余 `tools/_*.py` 为开发期调试/预览脚本

## 注意事项

- 部分音乐文件仍在打磨中，代码会自动跳过缺失/播放失败的音乐，不影响运行
- `__pycache__/`、`build/`、`dist/`、`previews/`、`backup/` 已在 `.gitignore` 中忽略
