## v1.6.0

### 新增内容
- 休整 / 出征准备界面对齐 Hypixel SkyBlock 原版 Minecraft GUI 风格：新增绘制模块 `src/ui/skyblock_ui.py`（浅灰容器、9 列凹陷槽位网格、物品只显示图标、悬停显示 Minecraft 暗色提示框——名称 / 稀有度 / 属性 / lore），装备、背包、商店、锻造、仓库等页面全部按该风格重绘
- 主菜单新增 `Storage`（仓库）入口（`src/ui/storage.py`）：可直接查看本地仓库存货，并对仓库中的装备使用重铸石锻造，无需先进入一局游戏
- 全局游戏速度：战斗中 `F8` 减速 / `F9` 加速 / `F10` 恢复 `1.0x`（`0.25x ~ 2.0x`），弹幕 / 敌机 / 玩家 / 关卡 / 特效时间轴整体缩放（音乐与音效保持原速）；设置界面新增调节条，数值保存到 `config.json` 的 `game_speed`
- 新版 Boss 立绘实装：立绘按套组存放 `assets/sprites/bosses/{new,another,legacy}`，统一为透明背景 PNG，`src/engine/boss_art.py` 只负责载入与缓存（同一张图每个进程解码一次，关卡载入时后台预热），Boss 战贴图 / 符卡立绘 / 对话立绘共用同一套处理（导出图外圈那层半透明白框由 `tools/_strip_boss_border.py` 交付前剥掉，运行时不再做抠图与裁剪）；设置界面新增「Boss 立绘」行，方向键或点击分段按钮即时切换，选择保存到 `config.json` 的 `boss_art`
- 五面 BOSS RUSH 终符演出：Necron 焚符「Nuclear Frenzy」与终符「Necron's Frenzy」（八臂螺旋 + 大玉环 + 烈焰上涌），Scarf 职业轮换（战士 / 弓手 / 法师两两激活），Dark Queen 扇与 Gagouji 旋风 / 锯齿环等符卡重做
- 物品系统扩展：装备可按部位分别记录重铸前缀（同名装备不同前缀互不混淆），仓库按堆叠存取；修正 Goldor's Leggings / Storm's Helmet / Maxor's Boots 的装备部位，Bonzo's Mask 改为「每关首次被弹时获得 3 秒无敌」并将价格调整为 20M / 4M
- 显示设置与 GPU 呈现（`src/engine/display.py`）：设置界面新增「输出分辨率」（1x/2x/3x/4x）与「缩放模式」（整数倍 / 填充），`F11` 切换无边框全屏，选择保存到 `config.json` 的 `resolution_index` / `scale_mode` / `fullscreen`；声明 DPI 感知并借 SCALED 窗口背后的 SDL renderer 由显卡完成最终缩放，消除高 DPI 下系统二次拉伸带来的模糊
- 渲染倍率与 GPU 原生地面：伪3D 洞穴地面 / 洞壁改为按渲染倍率（1x / 2x / 3x）直接由显卡绘制（`Pseudo3DFloor.draw_gpu`），几何与贴图采样改为分辨率无关——放大只增加细节，构图与贴图密度与 1x 完全一致；设置界面新增「渲染倍率」行（保存到 `config.json` 的 `render_scale_index`），无 GPU 呈现时自动退回 1x
- 伪3D 地面绘制优化：地面行 / 洞壁列条带左右镜像共用一次缩放、缩放目标面按尺寸复用，配合 GPU 原生绘制把 3x 下的地面开销从约 17.5ms/帧降到约 1ms/帧
- 关卡加载界面（`src/ui/loading.py`）：进入关卡时先显示加载进度面板（按真实时间推进，同时预建关卡与贴图资源），避免进场瞬间卡顿
- 文字 / 立绘高分辨率图层（`src/engine/hires.py`）：文字、立绘、半透明底板不再画在 960x720 上再整体放大，而是按渲染倍率原生绘制后叠加——画布给带倍率标记的表面单独开一张高分辨率图层（位置按逻辑坐标换算），字体按「逻辑字号 x 倍率」渲染并缓存，立绘抠图 / 投影 / 缩放也按倍率做，因此排版代码（居中、右对齐、按文字宽度做底板、自动换行）一行都不用改；立绘缓存设上限并在关卡加载界面预热
- 高分辨率 UI 的每帧开销优化：立绘淡入不再「复制整张立绘 + 逐像素乘法」（改用临时整体透明度，3x 立绘从约 8ms/张降到接近 0）；投影与立绘烘成一张合成图（每帧少贴一半像素）；HUD 半透明底板改为直接在高分辨率图层上填充（3.4ms -> 0.4ms）；整屏遮罩表面改为复用（不再每帧重建 24MB）；本帧没有高分辨率内容时连上传都跳过
- 帧时间（2880x2160 窗口）：第 1 面开场对话 1x 3.3ms / 3x 10.2ms；第 5 面开场对话 1x 6.2ms / 3x 16.1ms（优化前为 42ms）
- 界面统一走显卡原生绘制（`src/engine/painter.py`）：新增统一绘制入口 `Painter`——它本身就是高分辨率画布（既有 `blit` / `pygame.draw` 写法一行都不用改），另给 `fill_gpu` / `blit_gpu` 两个「显卡优先」方法：有 GPU 呈现时只登记本帧绘制指令、由 `present()` 在 1x 画布之前统一回放，没有 GPU 时自动落回画布，因此关掉开关（`TOUHOU_UI_GPU=0`）拿到的就是旧版画面，可以逐屏做「改前 / 改后」对比验收
- 界面底板与图标改为「预烤 + 贴图」（`src/engine/painter.py`）：显卡只会贴图、不会画圆 / 多边形 / 渐变，所以容器、按钮、槽位、选中框这些面板先按渲染倍率画成一张图并用 `SurfaceCache` 按 key 缓存（`blit_baked`），之后每帧只剩一次贴图——每帧现算的 CPU 绘制变成静态贴图，主菜单 / 设置的背景，以及休整（装备 / 背包 / 商店 / 锻造）、出征准备、仓库的底板与物品图标已由显卡按渲染倍率原生绘制（仓库 99 条 / 出征准备 124 条 / 商店 149 条绘制指令），清晰度与已经原生高分辨率的地面 / 文字 / 立绘拉齐；主菜单与设置里的菜单项 / 按钮仍走画布
- 顺带修正立绘与背景缩放的通道错位（`src/engine/hires.py`）：`pygame.transform.smoothscale(image, size, dest)` 的三参数写法会直接往目标缓冲区里写，源图与目标表面像素格式不一致时（例如 24 位 BGR 的 PNG 写进 32 位 RGBA 表面）整幅画面的通道错位、alpha 变成噪声；现在只有格式一致才走这条快路径，否则先缩放成新表面再整幅贴过去。对话立绘（`src/ui/dialogue.py`）与 Boss 贴图（`src/entities/boss.py`）走的是同一个函数，一并修正
- 新资源：`assets/gui/`（Minecraft 原版 GUI 贴图 `mc_inventory.png`、`mc_widgets.png`）、`assets/sounds/effects/`（擦弹 / 符卡展开 / 火力升级 / 残机炸弹 / 激光等效果音）与第 5 面后半 BGM `5_2_start.wav`

### 调整
- 无边框全屏：全屏改为 `NOFRAME` 并按屏幕居中定位窗口（`_position_window`），修复多显示器与系统缩放下的窗口错位
- 难度选择：当前开放 Easy（默认难度同步改为 EASY），其余难度显示为锁定
- 二面「电光」符卡新增 20 秒未击破自动结算；三面 The Watcher 本体螺旋弹改为 240 度扇形旋转臂（不追踪、不清弹）
- 旧版 Boss 立绘统一移入 `assets/sprites/bosses/legacy/` 作为缺图兜底，不再放在 `bosses/` 根目录（该套组分辨率较低、不作为可选套组出现；已核对两个可选套组各 15 张立绘齐备，正常游戏不会用到它，因此高分辨率化不需要为它做降级处理）
- 对话立绘淡出：投影与立绘合成后统一淡化，非说话者不再被自己的投影透过身体「糊」上一层灰
- 分代 GC 调优：只放宽 gen2 的触发间隔（`gc.set_threshold(700, 10, 100)`），这类扫描一次 4~8ms 且最容易落在「一帧里分配最多」的帧上（例如开符帧）
- 开符卡顿修复（背景部分）：符卡背景的静态部分（暗角 / 中心微光 / 整幅背景贴图 / 全景贴图）原本在「开符那一帧」现算——第 1 面约 13ms，五面的整幅贴图风格（storm / goldor / maxor）80~100ms（PNG 解码为主）；现在按参数缓存并在关卡载入界面预热
- 开符卡顿修复（横幅部分，真正的元凶）：符卡宣言横幅每帧都对整幅 Boss 立绘做 `copy()` + `fill(BLEND_RGBA_MULT)` 来调透明度，3x 下每帧约 14ms；横幅持续 100 帧，等于每次开符有 1.6 秒掉到 ~30fps。改用表面级 alpha（pygame 2 对带逐像素透明的表面同样生效，alpha=255 时逐位等价），横幅期间帧时间 33ms → 18ms（同场景无横幅基准 14ms），画面差异仅为轮廓边缘 ±1 的舍入
  - 说明：上一轮的性能探针有误（探针里 Boss 没进入关卡的 Boss 阶段，Boss 整体没被绘制），所以漏掉了横幅这一项；这次改用「真实满屏弹幕 + 正常 Boss 战阶段」重测
  - 自机符卡（Wither Impact / Hyperion）横幅同一处写法一并修掉
- 顺手修：`hires.rescale` 保留表面级 alpha 调制（否则切换渲染倍率后横幅淡出会失效）
- 开符卡顿修复（Boss 战视角抬升期间的伪3D 几何）：每一关的 Boss 登场都会花 2.0~2.6s 把摄像机抬高（`ramp_view_height`），地平线一动就要重建地面/洞壁几何（约 6ms：按行逐列建表 + 重填两张压暗/雾面）。符卡背景不透明时会把地面完全遮住，关卡这段时间根本不画地面——那些重建纯属白烧，一次视角抬升里能白烧上百帧。现在地平线变化只置「待重建」标记，真正要画地面时才重建（`Pseudo3DFloor.ensure_geometry`）。六面 Kaeman 第一张符卡前后：整段帧时间中位数 24.8ms → 20.4ms，超过 24ms 的帧 102 个 → 38 个
  - 同一处顺手修：地面远端的下落量（drop）此前只在「地平线跨过整像素」时更新，视角抬升动画末尾地平线不再跳动的那几帧会停在上一次的值（差 1px）；现在跟着视角高度走
- 开符卡顿修复（符卡背景图案）：符卡背景图层里那几张 SkyBlock 物品图标是绘制时才懒加载的（PNG 解码 + 抠底 + 缩放约 10ms/张），正好压在第一张符卡的头几帧上；现在建符卡背景时就解析，载入界面预热即完成（六面第一张符卡第 2 帧 62.2ms → 43.5ms）
- 开符卡顿修复（每次开符 + 每个 Boss 的第一张卡）：伪3D 背景的「墙体/地面交界线」检测（`panorama3d._detect_junction_v`）每次开符都要重新解码贴图并逐行扫描亮度，而结果只取决于贴图本身——改为按贴图路径缓存，开符帧少 4.6ms；符卡宣言的整幅 Boss 立绘只在「某个 Boss 的第一张卡」才会首次缩放（3x 下约 13ms），符卡名用的字号首次使用还要解析字库（约 5ms），两者都提前到关卡载入界面做（`loading._warm_spell_banner`，同时按面配置的立绘表覆盖本关稍后才登场的 Boss）。六面 Kaeman 第一张符卡那一帧 44.7ms → 22.4ms（同场景普通帧 12.4ms、横幅期间 18ms）
- 符卡背景预热补漏（第 1 面）：`STAGE_SPELL_BG` 原先没有第 1 面，而这一面两个 Boss 的符卡都没写死背景风格（靠符卡名推断），用主菜单隐藏快捷键进入时（例如 `D+1` 直接进道中 Boss）关底 Boss 还没生成，等于一种风格都不预热，开符那帧只能现算（spool / thread / tornado / soul 合计约 24.5ms）；现在补上这 4 种风格并在加载界面预热，开符帧相对平时帧多出的耗时由 51.7ms 降到 39.3ms
  - 说明：隐藏快捷键本来就先过加载界面（实测停留 225~301ms / 102~155 帧），漏的只是第 1 面不在预热表里
- 官网更新：画廊改用 /new 套组立绘重新出图，物品数据同步（Bonzo's Mask 效果与价格、护甲部位）

### 后续计划
- 战斗区实体 GPU 化：弹幕 / 敌机 / 玩家 / 特效目前仍画在 960x720 画布上整体放大，与已经原生高分辨率的地面、文字、立绘之间有清晰度落差；后续把这部分绘制也搬到显卡，按渲染倍率原生绘制
  - 做法：沿用本次的 `Painter`——把弹幕里「现画」的图元（圆弹 / 米弹 / 刀弹 / 尖弹 / 光束线）改为按渲染倍率预烤成小图后贴图，`SurfaceCache` 与 `GpuLayer` 已经就位

### 文件
- 新增 `src/ui/skyblock_ui.py`、`src/ui/storage.py`、`src/engine/boss_art.py`
- 新增 `assets/gui/`、`assets/sounds/effects/`、`assets/sprites/bosses/{new,another,legacy}/`
- 新增 `src/engine/hires.py`（文字 / 立绘 / 面板高分辨率图层，含呈现层高分辨率纹理）
- 新增 `src/engine/painter.py`（统一绘制入口：显卡指令登记 + 预烤面板缓存 + 显卡纹理缓存）
- 新增 `src/engine/display.py`、`src/ui/loading.py`
- 更新 `src/engine/game.py`、`src/engine/settings.py`、`src/engine/pseudo3d.py`、`src/stages/stage1.py`、`src/stages/stage6.py`、`src/engine/spell_bg.py`、`src/entities/boss.py`、`src/entities/bullet.py`、`src/stages/stage2.py`、`src/stages/stage3.py`、`src/stages/stage4.py`、`src/stages/stage5.py`、`src/stages/stage6.py`、`src/systems/item_effects.py`、`src/systems/item_icons.py`、`src/systems/item_system.py`、`src/ui/dialogue.py`、`src/ui/difficulty.py`、`src/ui/hud.py`、`src/ui/intermission.py`、`src/ui/loadout.py`、`src/ui/menu.py`、`src/engine/fallback_font.py`、`src/engine/panorama3d.py`、`src/engine/spell_bg.py`、`src/entities/boss.py`、`src/entities/player_spell.py`、`src/stages/goldor_terminal.py`
## v1.5.0

### 新增内容
- 难度选择界面：主菜单 Start Game 后先进入「选择难度」（`src/ui/difficulty.py`），当前仅开放 Normal，其余难度显示「未开放」；命令行参数 `easy|normal|hard|lunatic` 仍可直接指定
- 全界面鼠标操作：主菜单 / 设置 / 出征准备 / 符卡练习 / Boss 奖励 / 休整界面 / 对话 均支持悬停切换、左键点击确认、滚轮滚动；休整界面底部页签、装备槽、背包、商店、锻造等全部可鼠标点击
- 音效系统：新增 SE 音效（`assets/sounds/se/`，系统音、擦弹、符卡展开、击中、Bomb 等），音量由 `config.json` 的 `sfx_volume` 控制并支持运行时调整；新增第 4 面后半与第 5 面 BGM（`4_1_*`、`4_2`、`5_1_*`）
- C 技能视觉特效：召唤物/龙怒等技能增加透明冲击波、龙焰柱等演出（`src/systems/c_skill_entities.py`）

### 调整
- 五面道中 Boss 开战不再切换/重放 BGM（`keep_stage_music_on_boss`）
- 五面各 Boss 立绘配色校正；六面 Kaeman 对话立绘对齐
- 第 1 面标题图与多处关卡背景更新

### 文件
- 新增 `src/ui/difficulty.py`（难度选择界面）
- 新增 `assets/sounds/se/`、`assets/sounds/effects/` 与 `assets/sounds/musics/4_1_*.wav`、`4_2.wav`、`5_1_*.wav`
- 更新 `src/engine/game.py`、`src/engine/settings.py`、`src/engine/spell_bg.py`、`src/entities/boss.py`、`src/stages/stage3.py`、`src/stages/stage5.py`、`src/stages/stage6.py`、`src/systems/c_skill_entities.py`、`src/systems/item_effects.py`、`src/systems/item_system.py`、`src/ui/menu.py`、`src/ui/dialogue.py`、`src/ui/intermission.py`、`src/ui/loadout.py`、`src/ui/practice.py`、`src/ui/boss_reward.py`

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
