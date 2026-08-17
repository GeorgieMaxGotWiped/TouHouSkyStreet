## v1.4.2

### 新增内容
- 主菜单 Practice 符卡练习模式实装：可单独练习全部 Boss（1~6 面道中/关底 + 五面 BOSS RUSH 全部 Boss）的每一张符卡，共 36 张（含各 Boss 的 Last Spell）
  - 练习界面左侧选择 Boss、右侧选择符卡，Enter 开始；击破后 R 重试、N 下一张、Esc 返回选择
  - 练习固定满火力 400、3 残机 3 雷；Miss 自动重试，不消耗残机
  - 练习全程不写回主线存档（分数/残机/Bomb/物品/技能均不受影响）
  - 复用真实关卡 Boss 配置与符卡血条区间，机械符/裂符等需要舞台配合的符卡也完整可用

### 文件
- 新增 `src/ui/practice.py`（练习条目注册表 / 练习舞台 / 选择界面）
- 更新 `src/ui/menu.py`（Practice 菜单入口、PlayingState 练习模式流程与结算）

## v1.4.1

### UI 改进
- 休整界面「退出（Esc）」「撤离（B）」「下一关（N）」均新增确认弹窗：默认选中「取消」，↑↓ 切换、Enter 确认、Esc 取消，避免误触导致结束本局

### 文件
- 更新 `src/ui/intermission.py`

## v1.4.0

### 新增内容
- 物品掉落系统全面实装（依据 items.md 掉落表）：
  - 1~6 面全部敌人的掉落表：妖精系/卫兵系/Boss 通用表、每面任意敌人表、Boss 专属表（Bonzo/Scarf/Sadan/Arachne/End Stone Protector/Ender Dragon 等）、5 面四凋零领主分组、6 面 Kaeman
  - Boss 掉落奖励池（1~6 面关底三选一）：五面=Necron 掉落 4 件凋零护甲（Storm's Leggings / Goldor's Helmet / Necron's Chestplate / Maxor's Boots）；六面=Kaeman 掉落 Hyperion / Terminator / Dark Claymore / Necron's Handle；五面 Boss Rush 仅 Necron 计入奖励
- 54 件物品全部实装（另保留 8 件旧版物品兼容旧存档）：
  - 14 件带 C 技能物品（Wither Shield / Bonzo Balloon / Flower Rose / Overflux Orb / Summoned Minion 等），每面使用次数限制，同时只能装备 1 件 C 技能物品
  - 5 种重铸石与对应前缀：Necrotic / Loving / Fabled / Withered / Ancient
  - 效果聚合：装备 + 重铸 + 套装（Lapis 4 件、Heavy 4 件），+xx% 按加算、爆率加成按乘算
- 关卡接入：C 键释放 C 技能、被动效果（伤害/追踪/低速擦弹/金币/残机 Bomb 等）、SkyBlock Coin 拾取 +1M 金币、击杀/通关奖励补发
- UI 改进：休整商店按物品类型分类；Boss 三选一卡片显示买入/售出价格；C 技能指示器与实体渲染
- 补齐 27 个物品贴图（assets/items/），来源为官方 Hypixel 资源 / Fandom / FurfSky Reborn

### 文件
- 新增 `src/systems/item_effects.py`（效果聚合）、`src/systems/c_skill_entities.py`（C 技能实体）
- 重写 `src/systems/item_system.py`（物品定义/掉落表/C 技能元数据/重铸）
- 更新 `src/ui/menu.py`、`src/ui/intermission.py`、`src/ui/boss_reward.py`、`src/ui/hud.py` 及各关卡文件

## v1.3.0


### 新增内容
- 本地仓库与撤离系统：
  - 休整界面按 `B` 撤离：本局全部物品、金币与重铸前缀存入本地仓库存档（`warehouse.json`，位于游戏目录）
  - 主菜单 Start Game 改为先进「仓库 · 出征准备」：从仓库选择携带物品与金币后开始远征，未携带的物资保留在仓库
  - 失去全部残机（Game Over）时本局装备与金币不会保留；只有主动撤离才会入库
- 游戏结束画面新增提示「本轮获得的装备与金币不会保留」

### 文件
- 新增 `src/systems/warehouse.py`（仓库存档读写）与 `src/ui/loadout.py`（出征准备界面）
- `warehouse.json` 已加入 `.gitignore`

## v1.2.0

### 新增内容
- 第 6 关「最终进军 ~ Final Approach」：取消传统道中 Boss，整体为通往 The Wither King 王座的三段式最终进军
- 前半段：Wither Miner / Wither Guard / Wither Husk 亡灵军队防线逐渐加强
- 中段：Kaeman 远程干涉——巨大 Wither Skull 注视并锁定玩家区域后攻击，黑色 Wither 能量持续侵入战场
- 后半段：进入凋零要塞，敌人减少而弹幕更宏大，Maxor / Storm / Goldor / Necron 残影短暂出现作为王之门徒象征
- 突破王座前的最后防线后直接进入 The Wither King 战（符卡暂空，仅非符占位，后续补充）
- The Wither King 战全部六张符卡已实装；Last Spell 终仪「The Wither King's Final Slumber」：紫色大玉与普通弹自场外被 Kaeman 吸引吸收，随后狂暴放出，循环直至击破

### 资源
- 新增 `assets/backgrounds/stage6/`（要塞地板/墙壁为程序生成，余为六面专属拷贝）
- 新增 `assets/sprites/enemies/stage6/`（亡灵军队、Wither Lords 残影拷贝）与程序生成的 The Wither King 立绘
- 新增六面标题图 `assets/titles/stage6.png`；音乐暂复用五面/四面 Boss 战曲目

### 其他
- 关卡注册表与菜单调试入口（S + K + 6）接入六面

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
