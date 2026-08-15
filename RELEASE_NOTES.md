## v1.1.0

### 新增内容
- 第 3 关（CatacombsF1）：Boss 召唤物、符卡战斗与完整演出重做
- 第 4 关（Catacombs）：Scarf / Professor / Sadan 三场 Boss 战
- 第 5 关（Wither Lords）：Thorn / Livid / Storm / Maxor / Goldor / Necron 六场 Boss 战（Necron尚未完成）

### 玩法与系统
- Skyblock 物品系统：掉落、背包、装备属性与图标（`src/systems/item_system.py`、`item_icons.py`）
- 自机符卡/Bomb 重做：Hyperion 立绘与多段斩击（`src/entities/player_spell.py`）
- 决死 Bomb：中弹后短暂窗口内可 Bomb 自救
- Boss 奖励结算界面（`src/ui/boss_reward.py`）与关卡间过场（`src/ui/intermission.py`）
- 战斗 HUD、主菜单与符卡背景大幅增强

### 资源
- 新增第 3–5 关背景、Boss/敌人/道具贴图与标题图
- 新增音乐 `3_2_start.wav`、`3_2_loop.wav`，并更新 `3_1_start.wav`

### 其他
- README 更新至 1–5 关；新增忽略 `config.json` 与工具启动日志
- 对话目前为AI生成占位用，后续更新中修复。
- Skyblock 物品系统暂时对战斗无影响。
- 部分关卡背景尚未制作完成，使用占位背景。
