# 东方天空街 ~ Touhou Sky Street

基于 Hypixel Skyblock 的东方 Project 同人弹幕射击游戏（STG），使用 Python + Pygame 开发。

## 环境要求

- Windows 10/11
- Python 3.8+（安装时勾选 “Add Python to PATH”）
- 首次运行会自动检测并安装依赖；也可手动执行：`pip install -r requirements.txt`
- 若自动检测仍找不到 Python，可在根目录新建 python_path.txt，第一行填写 Python 可执行文件的完整路径（如 C:\Python313\python.exe）

## 运行游戏

- 双击根目录 `启动游戏.bat`（自动检测本机 Python，缺少依赖时自动安装）
- 或命令行执行：`python main.py`
- 可选难度参数：`python main.py easy|normal|hard|lunatic`

## 打包 EXE

- 双击 `build_exe.bat`（自动检测本机 Python 并安装 PyInstaller），产物输出到 `dist\TouHouSkyStreet.exe`
- 等价命令：`pip install -r requirements-build.txt` 后执行 `python -m PyInstaller --onefile --name TouHouSkyStreet --add-data "assets;assets" --noconsole main.py`

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `main.py` | 游戏入口 |
| `src/` | 源码：`engine`（引擎/设置/字体/伪3D/符卡背景）、`entities`（玩家/敌人/Boss/子弹）、`stages`（关卡 1-3）、`systems`（道具/技能）、`ui`（菜单/HUD/对话） |
| `assets/` | 资源：`backgrounds`（背景）、`sprites`（精灵）、`fonts`（字体）、`sounds/musics`（音乐）、`titles`（标题图） |
| `tools/` | 开发辅助脚本；`archive/` 存放已使用完毕的一次性补丁脚本 |
| `backup/` | 旧版源码备份 |
| `dist/` | 打包产物 |
| `previews/` | 开发期预览截图（由工具脚本生成） |

## 开发脚本

- `tools/_smoke_stage2.py`、`tools/_smoke_stage3.py`：关卡冒烟回归测试，输出截图到 `previews/`
- `tools/_gen_stage2_assets.py`、`tools/_gen_stage3_assets.py`：程序化生成关卡资源
- 其余 `tools/_*.py` 为开发期调试/预览脚本

## 注意事项

- 部分音乐文件尚未就绪（如 `3_1.wav`、`3_2_start.wav`、`3_2_loop.wav`），代码会自动跳过缺失音乐，不影响运行
- `__pycache__/`、`build/`、`dist/`、`previews/`、`backup/` 已在 `.gitignore` 中忽略