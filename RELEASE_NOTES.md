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
- 界面底板与图标改为「预烤 + 贴图」（`src/engine/painter.py`）：显卡只会贴图、不会画圆 / 多边形 / 渐变，所以容器、按钮、槽位、选中框这些面板先按渲染倍率画成一张图并用 `SurfaceCache` 按 key 缓存（`blit_baked`），之后每帧只剩一次贴图——每帧现算的 CPU 绘制变成静态贴图，主菜单 / 设置 / 难度选择的背景，以及休整（装备 / 背包 / 商店 / 锻造）、出征准备、仓库的底板与物品图标已由显卡按渲染倍率原生绘制（主菜单 14 条 / 设置 17 条 / 难度选择 17 条 / 仓库 99 条 / 出征准备 124 条 / 商店 149 条绘制指令），清晰度与已经原生高分辨率的地面 / 文字 / 立绘拉齐
- 顺带修正立绘与背景缩放的通道错位（`src/engine/hires.py`）：`pygame.transform.smoothscale(image, size, dest)` 的三参数写法会直接往目标缓冲区里写，源图与目标表面像素格式不一致时（例如 24 位 BGR 的 PNG 写进 32 位 RGBA 表面）整幅画面的通道错位、alpha 变成噪声；现在只有格式一致才走这条快路径，否则先缩放成新表面再整幅贴过去。对话立绘（`src/ui/dialogue.py`）与 Boss 贴图（`src/entities/boss.py`）走的是同一个函数，一并修正
- 主菜单 / 设置 / 难度选择也接进显卡路径：菜单项与提示文字不再落在 1x 画布上；设置界面的音量 / 速度调节条与分段按钮、难度选择的难度行改为「预烤成图 + 显卡 1:1 贴出」——此前这些矩形画在 1x 画布上，被整体放大时边缘会被线性过滤糊掉（1px 的边框糊成 4~5px 的渐变），现在边框是硬的
- 难度选择界面的背景修正：此前它把背景图缩到 960x720 再整体放大（先丢细节再放大，所以这一屏从背景到按钮一直是糊的），改用与主菜单同一个「按渲染倍率准备」的背景助手，背景与按钮一并变清晰
- 「呼吸」高亮的相位量化（`hires.pulse_color`）：菜单 / 难度选择里选中项的呼吸高亮此前每帧都算出一个新颜色，等于每帧都要重新渲染一次文字（文字渲染缓存与显卡纹理缓存永远命中不了）；改为量化成 16 档后全部命中缓存
- 载入 / 符卡练习 / Boss 奖励三个界面也接进显卡路径：载入界面不再抓 1x 画布的快照当底图（界面都改走显卡路径后画布上已经什么都没有，抓到的快照全透明），改为拿「来源界面」的背景图压暗当底——`start_stage` 把当前界面的 `background` 传进来，主菜单 / 练习 / 休整都有一张；载入面板与进度条、练习界面两侧的列表面板与选中行、Boss 奖励的卡片与按钮都改成「按渲染倍率预烤 + 显卡 1:1 贴出」，边框不再被放大糊掉（载入 8 条 / 练习 30 条 / Boss 奖励 30 条绘制指令）
- 符卡练习界面的背景修正：沿用主菜单那套「按渲染倍率准备」的背景助手，此前它把背景图缩到 960x720 再整体放大，这一屏从背景到按钮一直是糊的
- 战斗区弹幕上显卡（`src/entities/bullet.py`、`src/entities/bullet_atlas.py`）：敌弹 / 自机弹贴图此前画在 1x 画布上、随整幅画面被线性放大，这正是战斗区弹幕发糊的根源；现在按渲染倍率放大成「原生像素」再作为纹理 1:1 贴出（像素画用最近邻放大，保持硬边），清晰度与地面 / 文字 / 立绘拉齐。同一帧的「显卡弹幕 / 1x 画布弹幕 / 差分 x4」三联图见 `tools/_bench_battle.py` 生成的 `previews/battle/_clarity_stage3.png`：弹幕位置逐像素一致，差别只在清晰度
- 弹幕的绘制层次（`src/engine/painter.py`、`src/engine/display.py`）：战斗区内容是交错的 —— 地面 / 敌机 / 自机 / 掉落物在弹幕之下，判定点 / C技能 / 符卡前景 / HUD 在弹幕之上，一张画布表达不了。`Painter` 因此多出第二个显卡层（`blit_gpu_over`），`PlayingState.draw` 在弹幕之前给画布切一刀（`game.split_canvas_layer()`）：前半上传成「弹幕之下」那一层，弹幕夹在前后半之间回放。没有显卡路径时切刀是空操作，绘制顺序与旧版完全一致
- 弹幕贴图缓存按倍率 + 旋转角度量化（`bullet_atlas.SurfaceCache`）：高分辨率贴图是显存对象，必须限量 —— 米弹 / 尖弹 / 刀弹的角度每帧都在变，若按原角度建图等于每帧每发都新建一张贴图（缓存永不命中，还会变成每帧一次纹理上传）；改为 3° 一档（最多 120 种）后全部命中，旋转贴图缓存换成有界 FIFO（512 条）。光束线（电网连接）也一并按倍率拉伸烘焙
- 新资源：`assets/gui/`（Minecraft 原版 GUI 贴图 `mc_inventory.png`、`mc_widgets.png`）、`assets/sounds/effects/`（擦弹 / 符卡展开 / 火力升级 / 残机炸弹 / 激光等效果音）与第 5 面后半 BGM `5_2_start.wav`
- Ex 面「裂隙 ~ The Rift」（`src/stages/stage_ex.py`）：主菜单新增 `Extra Stage` 入口，进去后只能选自机与难度、选完直接开打（不经仓库 / 携带界面）；本面是「无装备」的一局 —— 装备被动 / C 技能 / 掉落 / 金币一律不生效，开局固定满火力 400，通关后回主菜单、不写物品存档也不进休整与 4 选 1 奖励
  - 道中 Boss **Wizardman**：先入场站定对话（14 句）再开打，是本作第一个「道中Boss 也有对话」的面；关底 Boss **Barry**：战前 14 句 + 战后 9 句对话，暂不配符卡，整场由自定义非符弹幕撑起（Wizardman 三项试炼 / Barry 五级税率与竞选纲领）
  - 小怪五种（裂隙虫 / Globowl / Blobbercyst / 裂隙吸血鬼 / Scribe Crux）、裂隙地板 / 洞壁 / 标题卡由 `tools/_gen_stage_ex_assets.py` 生成；两位 Boss 立绘取自 Hypixel SkyBlock Wiki 的 NPC 全身像（已是透明底像素图，离线核对后直接入库 `assets/sprites/bosses/{new,another}`，两套立绘套组都能用）
  - 两位 Boss 的对话立绘纳入取景对齐：关底 Barry 换上与本作其他 Boss 同规格的高清全身立绘，道中 Wizardman 一并从「裂隙面像素立绘按原样显示」改为走常规头高补偿 —— `DIALOGUE_PORTRAIT_HEAD_RATIO` 两套都补登 `wizardman` 0.23 / `barry` 0.16（读数口径见 `tools/_portrait_head_ruler.py`），关卡基类新增开关 `dialogue_portrait_harmonize`（默认开），`src/ui/menu.py` / `src/ui/loading.py` 不再拿 `items_disabled` 当代理；顺带把 `BOSS_ART_FILES` 里 `barry` / `wizardman` 的文件名大小写对齐仓库里的实际文件（`Barry.png` → `barry.png`、`wizardman.png` → `Wizardman.png`），免得在大小写敏感的文件系统上找不到图
  - 新增两个冒烟工具：`tools/_smoke_stage_ex.py`（关卡全流程 + 关键节点渲染）与 `tools/_smoke_ex_entry.py`（入口全流程：主菜单 → Extra Stage → 自机 → 难度 → 载入 → 战斗，并断言不进仓库、无装备效果、通关回主菜单）
- 关卡基类抽出道中Boss 出场钩子（`src/stages/stage1.py`）：`intro → mid_boss` 那段抽成 `_begin_mid_boss()`，默认实现与改动前逐行为等价（1~6 面不受影响），Ex 面覆写它实现「先对话再开打」
- 新增自机 **Frozen Blaze**（冰焰，`assets/sprites/self/FB/FB.png`）：在 `PLAYER_CHARACTER_FILES`（`src/engine/settings.py`）登记一行即可，选择界面自动多出一位（当前 4 位），代表色取立绘的冰蓝（144, 184, 255）；她的自机弹换用 `assets/sprites/bullets/Icy_Arrow.png` —— 原图指向斜上方，绘制前逆时针转 45 度让弹道朝上。自机弹贴图不再写死一张：登记表新增可选字段 `bullet`（`assets/sprites/bullets/` 下的文件名，也接受绝对路径）与 `bullet_angle`，不写时仍是默认的寒霜镰刀飞刃、不旋转；`cfg.PLAYER_BULLET_SPRITE`（+ `PLAYER_BULLET_SPRITE_ANGLE`）随 `set_player_character` 一起刷新，贴图缓存键也带上「路径 + 角度 + 倍率」，换自机即时换弹、不必清缓存
- 四位自机的战场贴图补齐（`assets/sprites/self/{Mage,Archer,Tank,FB}/`）：每位自机都带「立绘 + 站立 + 移动」三张（`portrait` / `idle` / `move`），`PLAYER_CHARACTER_FILES` 里全部登记——此前 Frozen Blaze 只登记了立绘，战场上站立与移动都退回那张立绘用。八张贴图与四张立绘同为 1024x1536 的全身构图（内容高约 1500px），所以沿用同一档渲染高度（70px）与同一个判定点锚位（贴图高的 0.38，四人实测落在腰胯同一处），不必逐角色调
- 剧情对话里的自机名牌跟着所选自机走（`src/engine/settings.py` 的 `PLAYER_DIALOGUE_NAME` / `player_character_dialogue_name`）：此前各面剧情把说话人写死成「魔法使 Mage」，选弓手 / 重装 / 冰焰出征时立绘已经是本人、名牌却仍然叫 Mage；现在七面共 98 处（说话名 / 立绘表 / 左右站位表三种写法）统一改用该常量，随 `set_player_character` 与 `SELF_SPRITE` 一起刷新
- 界面切换黑场过渡（`src/engine/game.py` 的 `ScreenTransition`）：`switch_state` / `push_state` / `pop_state` 不再硬切，改成先把画面按 `SCREEN_FADE_OUT`（0.10s）压到全黑、在最黑那一帧才真正换状态，再按 `SCREEN_FADE_IN`（0.16s）揭开。这么做顺带把「新界面最贵的那一帧」（立绘贴图首次上传、面板预烤）藏在了全黑上 —— 自机选择屏首帧实测 148ms（软件渲染下），落在黑场里就看不见接缝，不必让每个界面自己去预热。遮罩复用 `hires.overlay_surface` 的缓存表面、由 `blit_gpu_top` 在显卡端调制整体不透明度，每帧只是一条贴图指令
  - 过渡用真实时间推进（不跟 `game_speed`，它是观感不是游戏逻辑）；压黑阶段冻结当前界面并吞掉这几帧的输入，否则「按下确认」的那次按键会连同新界面首帧一起被消费、在新界面上再触发一次操作
  - 过渡途中又请求一次切换（淡入还没走完就又按了一次确认）时只把待执行的动作换掉、从当前覆盖度继续压黑，不重新起一段，画面不会「黑一下又亮回来」；走完的过渡对象若没被主循环收走也不会吞掉下一次请求
  - 主循环之外的状态变更（初始化，以及不跑主循环、自己手动 tick 的冒烟 / 截图 / 基准工具）仍是立即生效，那批工具的行为与之前完全一致；`Game.settle_ui()` 供它们一次走完过渡与进场动效（`tools/_ui_gpu_smoke.py`、`_ui_gpu_compare.py`、`_ui_residue_check.py`、`_smoke_ex_entry.py` 已接入）
- 界面进场动效（`src/ui/anim.py` 的 `Entrance`）：主菜单、设置、自机选择、难度选择、符卡练习五个界面进场时，标题 / 面板 / 选项按 0.055s 的间隔错位淡入，并自上而下落位 12px（`UI_INTRO_*` 为时长 / 间隔 / 延迟 / 位移）。设置界面按行错开、练习界面按「标题 → 左列 → 右列 → 底部信息 → 按钮」分组错开。动画结束后 `Entrance.item()` 一律返回 `(255, 0)`，各界面照原坐标与不透明度绘制，稳态一分钱不花
  - 淡入期间整层不透明度由显卡调制：`painter.blit_gpu` / `blit_baked` 新增 `alpha` 参数（默认 255，与改动前逐像素一致），CPU 端不必为淡入抠半透明副本；设置界面那几行原本走 `screen.blit` 的写法落定后仍回到 `blit`（两条路径的取整时机不同，文字会挪不到一个逻辑像素），落定帧与改动前完全一致 —— `tools/_ui_residue_check.py` 采样该屏 `diff_px=0`
  - 验收：13 个界面 × 显卡路径开 / 关两种模式逐屏冒烟通过；残留检查全部返回路径平均像素差 0.001、峰值 ≤ 5（仍是呼吸高亮的相位差）；`tools/_smoke_ex_entry.py` 全流程（主菜单 → Ex 面 → 自机 → 难度 → 载入 → 战斗 → 回主菜单）ALL OK

- 第 6 面道中新增小怪 Skeleton Lord（`src/stages/stage6.py`）：从场地左右两侧偏上方**横向高速切入**（7px/帧，约 0.45s 从边框滑到停驻位），到位后每 12 帧铺开一圈 **5 发高速螺旋鳞弹**（弹速 4.2，是道中其它小怪的 1.6~2.8 倍；每轮偏转 0.55 弧度、左右两位镜像），血量 420 / 3000 分。为此新增弹种 `Bullet.TYPE_SCALE`（`src/entities/bullet.py`）：映射到 `etama.png` 第 2 行的「鳞弹」原图、按飞行方向旋转，判定半径沿用贴图换算（4px）
  - 道中第一波（4s「Wither Vanguard」的 3 只 Wither Husk）整波换成左右两位 Skeleton Lord 同时入场（`Skeleton Lords`），后续波次不变；实测同屏鳞弹峰值 111 发（第 10.0s），切入 0.45s、到位后 0.1s 起手
  - 立绘 `assets/sprites/enemies/stage6/skeleton_lord.png` 由 `skeletor.png` 染成凋零紫（`tools/_gen_skeleton_lord.py`），避免与后面登场的凋零骑士撞图
- 自机弹幕差分（`src/engine/settings.py`、`src/ui/menu.py`、`src/entities/bullet.py`）：四位自机不再共用同一套自机弹 —— 冰焰（默认）保持与旧版逐发一致（1/2/3 条、±2.25° 扇形、±10 落点、含追踪弹）；魔法使 1/3/5 条、扩散两倍（±4.5°/±9°）、固定弹**穿透**、没有追踪弹；弓手与魔法使同形但**不**穿透、扩散减半（高速 ±2.25°/±4.5°，低速再减半 ±1.125°/±2.25°）；重装 1/2/3 条**笔直向上**（不扩散，±10 落点）+ 与旧版一样的追踪弹。参数集中在 `PLAYER_CHARACTER_SHOTS`：条数 = 起始 + 每级火力 × 步长、按上限截断（旧版的「1 + 1 × 火力等级，上限 3」就是这一族里的一行），加一位自机只要多登记一行；自机选择界面底部原本写着「四位自机性能相同」，也改成「弹条数 / 扩散 / 穿透 / 追踪弹各不相同」
  - 穿透：新增 `Bullet.try_hit`（`src/entities/bullet.py`）—— 穿透弹命中后不消失、同一目标只结算一次（穿过同一个敌人时不会每帧重复扣血），战斗区（`ui/menu.py` 的 `_check_collisions`）、三面亡灵复活、四面兵马俑四处命中结算统一走它；Loving / Terminator 等装备效果照旧生效（散射夹角仍由 Terminator 直接覆盖，弹道数增减加在截断之前，与旧版同序）
  - 物品 / C 技能逐条核对（`tools/_verify_shots.py` 第 7 节：7 组效果 × 4 机体 × 3 档火力 × 低速）：Terminator 覆盖夹角（±4.5°/±0.5°，重装装上它也会被摊成扇形，与旧版覆盖口径一致）、Loving 的 -1 固定弹（加在截断之前：火力 200 时 冰焰 2 / 魔法使 4 / 弓手 4 / 重装 2 条，满火力同样被上限吃掉）与 +1 追踪弹（冰焰 / 重装生效，魔法使 / 弓手没有追踪弹可加）、Withered 的追踪伤害与 Fabled 的非追踪伤害各走各的分支（魔法使的固定弹算非追踪）、Spirit Bow 的「追踪领域」把四机体的固定弹全变成追踪弹且魔法使的穿透标记保持 —— 冰焰的弹道几何在上述全部组合下仍与改前逐发一致
  - 顺带发现：Necrotic 重铸石原写的「低速状态固定弹射速+3%」（`fixed_bullet_speed_pct`）自加入起就没有任何代码读它（`Player.can_shoot` 一直用固定的 4 帧冷却，4 帧 × 1.03 仍是 4 帧），效果为空
  - 顺带改动：Necrotic 换成真实生效的 `fixed_double_damage_chance` —— **低速状态下每颗固定弹有 3% 概率造成双倍伤害**（只作用于固定弹，追踪弹不参与；`_player_shoot` 定完伤害后按概率翻倍）。`item_effects.py` 的效果键、`item_system.py` 的 `_EFFECT_LORE` / `REFORGES["necrotic"]` / 亡灵使者胸针图鉴文案、网图鉴 `web/data/items.json` 同步更新
  - 自机弹贴图按**自己的飞行方向**转正（`src/entities/bullet.py` 的 `_draw_player_sprite`）：此前自机弹贴图一律朝上，弓手扇形散开的五条箭看起来全朝上、只有位置分开，追踪弹改向后贴图也不跟着转。现在贴图按这一发的 `angle` 转到飞行方向（发射时即发射角，追踪弹由 `_update_homing_bullets` 改向时同步刷新），旋转角与机体自己的「贴图转正角」叠加，缓存键带上它（`_get_player_bullet_sprite` 的 `heading`）；敌弹那条路一行未动（仍按原来的 `angle` 贴图集 / 图元，没有新增朝向字段），载入界面按 `cfg.player_shot_headings` 把本机体可能飞出的每个方向先烤好（`loading._warm_bullet_sprite`），第一发不会现转
  - 验收（`tools/_verify_shots.py` 第 8 节）：飞了 8 帧的弓手五条箭，贴图朝向 = 各自的 `atan2(vy, vx)`、五条方向各不相同、且各自一张按方向转好的贴图（中间那条是 Explosive_Arrow）；追踪弹改向后取到的贴图键与朝上那张不同；敌弹路径没有新增朝向字段（`facing` / `_last_x` 不存在）、螺旋弹仍按 angle 贴着转；载入界面的预热在 4 机体 × 3 倍率 × 每个可能方向下 0 缺口；四位自机的 10 秒伤害与改前一致（冰焰 2791 / 魔法使 790 / 弓手 1270 / 重装 1962）
- 弓手弹道调整（`src/engine/settings.py`、`src/entities/bullet.py`、`src/ui/menu.py`）：弓箭起始点收束到同一点、扩散翻倍、贴图换成 `Iron_Arrow.png`（中间那条每 240 帧有一根是 `Explosive_Arrow.png`）、爆裂箭命中敌人时炸掉小范围敌弹
  - 起始点收束：差分表新增 `converge`，`player_shot_lines` 照它把横向落点全给 0，扇形只由倾角决定（此前是 ±20 / ±10 落点等距排开），低速同样收束
  - 扩散翻倍：`tilt_step` 从 1 倍基准提到 2 倍（与魔法使相同）、低速仍按 0.5 倍算 —— 高速 ±9° / ±4.5° / 0、低速 ±4.5° / ±2.25° / 0（此前分别是它的一半）
  - 贴图：弓手登记 `bullet: Iron_Arrow.png`（+ `bullet_angle: 45`，口径同冰焰的冰箭）；中间那条到点时由差分表的 `center` 换成 `Explosive_Arrow.png`，其余时候中间也是普通箭。自机弹贴图因此要能逐发区分：`_get_player_bullet_sprite` 接受「这一发自己的贴图 + 角度」，`Bullet` 新增 `player_sprite_path` / `player_sprite_angle`，载入界面把这张额外贴图一起预热（否则它第一次出现的那几帧要现读现缩）
  - 爆裂箭：`Bullet.try_hit` 结算成功后触发 `clear_radius_on_hit`（登记 34px，比击破小怪的清弹 42~90 小一圈），清弹直接复用击破小怪那一套 `burst_cancel_bullets`（半径内敌弹进消弹动画 + 一圈橙色扩散光效）；它在 `_player_shoot` 里由「倾角最接近 0 的那条」认领 —— 五条时是正中间，Loving 把弓手变成偶数条（2 / 4 条）时取靠左的那条
  - 发射节奏：`center` 新增 `interval`（弓手 240 帧 = 4 秒），到点那一轮中间才是爆裂箭。计时按真实帧走（`PlayingState._tick_shot_cadence`，战斗与练习两条 update 路径都调），不按开了几枪 —— 开火间隔随火力变，按枪数算的话节奏会跟着火力跑
  - 验收：`tools/_verify_shots.py` 新增 8 项 —— 扩散（高速 ±9 / ±4.5 / 0、低速减半）、收束后五条箭的横向落点全为 0（低速同）、贴图组合（到点那一轮 1 张 Explosive_Arrow + 4 张 Iron_Arrow）、爆裂箭恰好一条且是中间那条、Loving 偶数条时也恰好一条、其余机体没有、720 帧里只有第 4 / 244 / 484 帧那三根（间隔正好 240 帧）、其余 177 轮中间都是 Iron_Arrow；另走真实 `_check_collisions` 打一发：半径内敌弹进消弹 / 半径外不受影响 / 伤害照常结算一次；`tools/_smoke_self_shots.py` 四位自机照旧无异常 —— 同一随机种子下，弓手的 10 秒伤害 1610（改前）→ 2705（只做收束）→ 1270（再把扩散翻倍 + 爆裂箭改成 4 秒一根）：收束把五条箭压到同一点，扩散翻倍又把它摊开，单点命中率反而比改前更低，要调平衡就动 `converge` / `tilt_step`
  - 顺带：`tools/_smoke_self_shots.py` 固定随机种子（Boss 的弹幕与移动都吃随机数，不种种子时同一位自机每次跑出来的秒伤能差三成），秒伤数字从此可复现、可横向对比
  - 验收：`tools/_verify_shots.py`（不启动游戏）—— 冰焰与改前的 `_player_shoot` 在 8 档火力 × 低速 × Loving × Terminator 共 192 组下逐发一致（落点 / 速度 / 伤害 / 追踪 / 穿透标记全等），其余机体按条数 / 扩散 / 落点 / 穿透 / 追踪逐档核对，并接进真实 `_check_collisions` 验证「一发穿透弹打穿两个敌人各 10 点、同一敌人只结算一次」；Necrotic 单独核对：高速态即使 100% 也不翻倍、低速 100% 时固定弹全 20 / 追踪弹仍 6.7、四位自机都生效、3% 在 1000 发上实测 2.9%；`tools/_smoke_self_shots.py` 让四位自机各打 600 帧第一面 Boss 无异常，满火力 10 秒伤害依次为 冰焰 2791 / 重装 1962 / 弓手 1610（收束与扩散调整前的口径，见上一条）/ 魔法使 790 —— 扇面越宽、离得越远，单点命中率越低（魔法使换来的是穿透与覆盖面）

- 游戏图标（`assets/gui/icon.png`）：窗口 / 任务栏与打包后的 EXE 统一用这一张图 —— `src/engine/game.py` 在建窗口之前 `pygame.display.set_icon`（换分辨率重建窗口时 pygame 会自动重新套用），`build_exe.bat` 与 `TouHouSkyStreet.spec` 加 `--icon`；原图 1254x1254，运行时等比缩到 256 再交给系统。换图标只需替换这一个文件

### 调整
- 启动闪退修复（`src/engine/game.py`）：此前窗口一律先建成 960x720 的 SCALED 窗口、建完 presenter 之后才调到设置的输出分辨率 —— 而 `Renderer.from_window` 拿到的就是 pygame 为 SCALED 建的那一份 SDL renderer（`logical_size` 已经是 960x720，不是另开一份），挂着它改窗口尺寸会让 SDL 重建窗口后备缓冲、连带把这份 renderer 的显存状态一起带走，实测约四到六成概率在开局头几帧读到已释放的内存直接闪退（崩在 python312.dll 的小对象分配器里、读到被写坏的空闲池头，`%LOCALAPPDATA%\CrashDumps` 下多次 minidump 指向同一地址；`TOUHOU_UI_GPU=0` 不建 presenter 时不会复现）。现在窗口按设置的输出分辨率一次建成，尺寸只在建 renderer 之前修正一次（SCALED 还会按系统 DPI 缩放把窗口开大一圈：本机 200% 缩放下请求 960x720 得到的是 1920x1440 的窗口，「输出分辨率」就不等于窗口像素数了），建完不再动窗口，挂 renderer 期间改尺寸这条路径彻底不走
- 换输出分辨率改为整体重建（`src/engine/game.py`）：SCALED 下窗口缩不到比自身逻辑尺寸更小（`Window.size` 会被顶回逻辑尺寸），所以 `set_resolution` 不再走「改窗口尺寸」，改为走与 `F11` 全屏切换同一条「先释放 presenter、再重建窗口与渲染器」的路径（旧的 `_apply_window_size` 随之删除）；窗口尺寸严格等于「输出分辨率」（960×720 / 1920×1440 / 2880×2160 / 3840×2880，超过桌面时按桌面夹住），全屏取桌面尺寸
  - 验收：`main.py` 连跑 144 次 0 次提前退出（改前同样条件 5~6/8 崩，其中 1x 那 40 次每次都走「建完窗口再摁尺寸」这条路）；全屏 / 四种分辨率 / 三种渲染倍率 / 两种缩放模式逐条自检，presenter 全程可用且窗口尺寸逐条正确
- 界面残留修复（显卡路径引入的副作用）：显卡层是叠在 1x 画布「下面」的，所以开了显卡路径以后画布不再是整幅画面、只是画在显卡层之上的一层，而画布此前每帧并不清空（旧写法里每个界面都会把整屏背景画满，等于顺手擦了）。于是从设置 / 难度选择 / 仓库 / 出征准备 / 休整按 Esc 返回主菜单时，上一个界面留在画布上的像素（调节条、分段按钮、难度行）会继续透在主菜单上。现在开了显卡路径时帧首把画布清成透明（实测 0.06ms/帧），`tools/_ui_residue_check.py` 对全部返回路径逐条比对，平均像素差 0.001、峰值 ≤ 10（呼吸高亮的相位差）
- 弹幕飞出战斗框修复（`src/engine/painter.py`、`src/engine/display.py`）：显卡指令是在画布之外回放的，画布上的 `set_clip` 管不到它们 —— 弹幕上了显卡以后，骑在战斗框边上的那一发会继续画到框外（上下黑边、右侧 HUD 都会沾到）。现在登记指令时顺手记下当时生效的裁剪框，回放时用 SDL 渲染视口复现同一块裁剪（视口同时是裁剪框与坐标原点，指令坐标相应减去视口原点）；`tools/_bench_battle.py` 顺带新增弹幕出框检查：框内新增像素与画布参考一路一致、框外一律为 0（stage1 / stage3 / stage4 各 22 发骑边弹实测），战斗区里的弹幕与图形不会再越界
- Boss 奖励卡片布局修复：物品带「部位」时，最后一行说明会与「按 Enter 确认领取」叠在一起（提示行的位置漏算了部位那一行，卡片高度也跟着少一行）；顺带把卡片几何收成一份 `_card_layouts`，绘制与鼠标点击区域共用，不再各算一遍
- 弹幕斜向轨迹的锯齿修复（`src/entities/bullet.py`、`src/engine/painter.py`）：弹幕贴图虽然已经由显卡原生绘制，但位置在贴图之前就被 `int()` 截成了整数逻辑像素，倍率换算又是「先取整、后乘倍率」—— 弹只能落在 1 逻辑像素 = 渲染倍率个物理像素的网格上，3x 下表现为「一帧停住、下一帧跳 3 个物理像素」，10 度浅角斜飞的弹最明显（实测 y 步进 0,3,0,3,…）。现在绘制保留浮点坐标，取整挪到图层空间（新增 `painter._dest_scaled`：先乘倍率、再取整），同一发弹的最大步进误差 2.86 -> 0.86 图层像素（3x：y 步进 0,3,0,3,… -> 2,1,2,1,… 理想值 1.56；x 步进 9,9,9,8,… 理想值 8.86），位置的最小步进由 1 逻辑像素降到 1 个物理像素；落回画布的路径（无 GPU 呈现 / 倍率对不齐）仍按整数贴，行为与旧版逐位一致
  - 残余抖动 <= 0.5 图层像素，这是 1 像素网格的极限、肉眼不可见；要完全消除需要浮点贴图（SDL `SDL_RenderCopyF` / `pygame.FRect`），收益已经很小
  - 新增 `tools/_bullet_subpixel_check.py` 自证：2x / 3x 下改前位置全部落在渲染倍率的整数倍上、改后不再是，且最大步进误差 <= 1 个图层像素
- 无边框全屏：全屏改为 `NOFRAME` 并按屏幕居中定位窗口（`_position_window`），修复多显示器与系统缩放下的窗口错位
- 难度选择：当前开放 Easy（默认难度同步改为 EASY），其余难度显示为锁定
- 二面「电光」符卡新增 20 秒未击破自动结算；三面 The Watcher 本体螺旋弹改为 240 度扇形旋转臂（不追踪、不清弹）
- 旧版 Boss 立绘统一移入 `assets/sprites/bosses/legacy/` 作为缺图兜底，不再放在 `bosses/` 根目录（该套组分辨率较低、不作为可选套组出现；已核对两个可选套组各 15 张立绘齐备，正常游戏不会用到它，因此高分辨率化不需要为它做降级处理）
- 对话立绘淡出：投影与立绘合成后统一淡化，非说话者不再被自己的投影透过身体「糊」上一层灰
- 对话立绘取景对齐（`src/ui/dialogue.py`、`src/engine/settings.py`）：对话框此前只按「内容高度」统一缩放立绘，而各张立绘的取景差得很远，同屏就一大一小 —— 换上取景更近的立绘（例如新的末影龙，头占内容高 0.24，自机只有 0.18）时最明显。现在 `DIALOGUE_PORTRAIT_HEAD_RATIO` 按套组登记每张立绘的「头高 ÷ 内容高」（自机另有一张 `DIALOGUE_PORTRAIT_SELF_HEAD_RATIO`，度量方式见 README），运行时按「目标头高 0.19 ÷ 该图头占比」换算补偿倍率（`_portrait_frame_scale`，结果随贴图缓存）；倍率限制在 0.70~1.45，放大方向另受宽度预算约束（380px，本轮随整体放大改为 418px），没登记的立绘维持原样。同屏头高（逻辑像素）实测：末影龙 98 → 78、The Watcher 89 → 77、Sadan 86 → 78，远景全身像 Necron 52 → 74 / Maxor 56 → 76，自机 73 → 77（其余 74~82 之间），Kaeman 相对自机的 2.16x 回到它自己配置的 1.5x
  - 接近正方形取景的半身立绘（三面 Bonzo、五面 Thorn 与 `new` 套组的 Watcher）原尺寸就已经顶到宽度预算，所以只会缩、不再放大：按头占比换算它们本该再放大 1.19x，但那样同屏两张会互相糊住，此时宽度预算优先
  - 裂隙面不参与对齐（`src/ui/menu.py`、`src/ui/loading.py`）：两张像素 NPC 立绘不登记头占比即自动跳过，对话框再按「本关是否 `items_disabled`」整体关掉补偿，载入界面的预热也按同一判据分档。验收：`tools/_dialogue_preview.py` 重渲染的 `_dialogue_ex_*.png` 与改动前逐字节相同
  - 整体再放大 10%（`DIALOGUE_PORTRAIT_SCALE`，取景对齐后统一乘在基准缩放上）：同屏头高 84~86（自机 76.7 → 84.4、末影龙 78.0 → 85.7、Watcher 76.8 → 84.3、Bonzo 64.2 → 70.6），把所有人一起做大一档、相对大小不变。宽度预算同步按同一倍率放大（380 → 418），否则取景最远的 Necron / Maxor 会被预算卡住、只有它们不跟着变大。裂隙面不参与放大
  - 靠边站的探出量限幅（`DIALOGUE_PORTRAIT_EDGE_BLEED`，按内容宽算上限 25%）：立绘是「靠边站」的构图，先前一律按内容外沿对齐，而各张立绘里脸落在内容的哪一列相差很大 —— 六面 Kaeman 的脸在内容正中、两侧披风却宽得多，第五面开始它又被手调右移 120px（`stage6.py`），结果整张脸被推出战斗框外（只有披风和星座环在画面里）。现在探出量按内容宽限幅，脸始终留在框内（Kaeman 的内容右沿 794 → 675），说话 / 不说话的进退动画（`DIALOGUE_PORTRAIT_RETREAT`）照旧叠在上面一分不少；`stage6.py` 里那个手调右移随之删掉。裂隙面同样不吃这层限幅
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
- 开符卡顿修复（全景符卡背景的逐帧重建）：伪3D 环形全景每帧都要重采样地面与洞壁，「地面按预计算行号取源贴图」这一步原先用 `np.take_along_axis` 在转置视图上取两次（0.31ms/帧），插值的中间数组还每帧现分配（0.94ms/帧）。现在把「组内第几行 x 通道」的下标一次性压平成一维花式索引（下标必须用 `np.intp`：换成 int32 反而更慢，numpy 会先做一次转换缓冲），插值改成预分配缓冲的就地乘加，列循环里的列高/列起点也预先拆成静态表不再逐列取 numpy 标量 —— 整块 `_build_frame` 最小 2.69ms -> 2.15ms、中位 3.07ms -> 2.40ms（2400 帧取最小），画面逐位一致（8 种配置 / 7400 万像素比对）
- 开符卡顿修复（五面焚符「Nuclear Frenzy」的白热太阳）：太阳底图是 1024x1024 程序化径向渐变，原本等到开符后第一次绘制才现算（网格运算 + 4 次 `np.interp`，实测 44ms），正好压在第 2 帧上；每帧还要把这张 1024 底图 `smoothscale` 到当前直径（3x 下 600~1500px，2ms/帧）。现在底图由新增的「符卡演出特效」预热步骤在载入界面建好（`Stage.warm_spell_effects`，各面自报），缩放结果按直径记住最近几个 —— 五面第一张符卡横幅期的最大帧 60.3ms -> 13.4ms，超 16.7ms 的帧 1 -> 0
- 开符卡顿修复（高分辨率图层上传）：文字 / 立绘 / 面板那一层此前每帧按「本帧标脏的包围盒」整块上传，而 HUD 的标脏点散在屏幕四角，包围盒等于整屏（2880x2160 每次 24MB）；改为逐块上传（最多 128 块），单帧上传少 5.2ms。逐块清屏顺带修掉了「上一帧没标脏的区域留在图层上」的残留（实测残留像素 232 万 -> 24 万）。像素与整幅上传逐位等价
- 开符卡顿修复（HUD 面板底板）：符卡横幅期间 HUD 面板那块恒定的大半透明底板画在高分辨率图层上，等于每帧重传一遍；改为交给显卡填矩形（`Painter.fill_gpu_ui`）。顺带修了渲染器 `draw_blend_mode` 默认 NONE 导致 `fill` 把 (r,g,b,a) 当不透明色丢掉 alpha 的问题（面板的 128 半透明会被糊成纯色），切换混合模式实测 0.1us
- 开符卡顿修复（符卡素材预热）：符卡演出才现读的贴图（第 4 / 6 面的巨人解码 12ms、石像兵 7ms，第 6 面凋零幽影 25~45ms）改为载入界面按面配置表提前解码（`boss_art.load_sprite` 改为共享解码缓存，敌机贴图与第 6 面共用）；符卡宣言的整幅立绘也提前缩放成成品并传成显卡纹理（1728x1728 首次上屏 3.5ms 挪到载入界面）；全景贴图 / 地砖 / 交界线检测等静态资源同属这一步
- 开符卡顿修复（闪光与横幅）：开符瞬间的整幅加色闪光此前用 `canvas.fill(color, BLEND_RGB_ADD)`（pygame 逐像素慢路径，576x670 实测 1.9ms/帧，共 14 帧），改为预烤一张加色表面后 blit（0.06ms/帧）；符卡宣言的立绘与符卡名改为贴到「所有图层之上」那一层显卡指令（带逐指令 alpha 调制），不再每帧把 1728x1728 立绘与两份 3x 文字贴进 2880x2160 的高分辨率图层（原先 5.3ms/帧 x 100 帧）
- 符卡背景（第 1 面）的压暗层：恒定的一整块半透明色不再每帧新建 Surface 再 fill，改为按压暗值缓存复用（与第 6 面的既有写法一致）
- 仓库内基准工具：新增 `tools/_bench_spellcard.py`（把关卡推到关底 Boss，逐张符卡报告普通帧 / 横幅期 / 符卡后期的帧时间与超 16.7ms 帧数；默认走真实显示驱动的显卡路径，`PROBE_DUMMY=1` 走软件回退）；`tools/_bench_battle.py` 的弹幕出框检查见上
  - 六面实测（3x，2880x2160，载入界面全量预热）：普通帧中位 7.3~8.2ms；第一张符卡横幅期中位 6.3~11.8ms、符卡后期 6.2~12.1ms；18 张符卡共 5400 帧里只剩 3~4 帧超 16.7ms（第 1 面符卡后期第 169 帧 17.6ms、第 4 面巨符第 34 帧 18.6ms 等个别单帧），开符第 1 帧已从 21.4ms 降到 17.9ms（本条数字是召唤物 / 符卡演出搬上显卡之前实测；搬完以后的开销见下文「战斗区特效与召唤物上显卡」两条）
- 开符卡顿修复（符卡背景旋转层的缓存治理）：背景里那些旋转层的 rotozoom 结果原本按「角度 4 度 / 缩放 0.04 分桶」缓存，但缓存一满就整锅 `clear()`，于是超容的那一帧里所有旋转层同时重新旋转（实测 4 层 x 约 1.5ms 合成 6~7ms 的掉帧，正好卡在符卡进行中）。现在改成三件事：逐出「最久没用过」的那一条（真 LRU，命中即刷新次序）、各层的分桶相位用黄金分割错开（避免两层转速成 2:1 时周期性同时换桶）、每帧最多重算一个大层（结果面积 ≥ 40000 像素算大层，额度用完的那一帧先用同层上一张图顶上，最多差不到一个分桶 = 4 度）。相位只影响「哪一帧重算」，重算那一帧仍按真实角度 rotozoom，因此画面逐位不变
- 开符卡顿修复（符卡换装立绘预热）：第 4 面王符「The Giant One」在符卡开始时会把 Boss 立绘换成巨人，横幅期第一次按横幅高度缩放要 5.7ms，正好压在第 1 帧上（原先 `stage_boss_art_paths` 表里没有它，`_warm_spell_banner` 够不到）。现在新增 `STAGE_BOSS_ART_SWAPS` 表把换装立绘也纳入预热（横幅成品 + 战斗用的小图两种尺寸）—— 该符卡横幅期超 16.7ms 的帧 1 -> 0、最大帧 20.5ms -> 11.4ms
- 开符卡顿修复（载入界面预热「开符第一帧」的旋转层）：旋转层缓存原本每个符卡背景各存一份，每开一张符卡第一帧都是冷的 —— 而大层的一次 rotozoom 实测 2.4ms，正好是「开符那一下」。现在缓存改为所有符卡背景共享（同一张图案在同一分桶下结果逐位相同），载入界面预热时顺带空跑开符第 1 帧把分桶结果填进去；顺带把「本帧大层额度用完」时的兜底从「退回未旋转原图」改成「取共享缓存里同一张图案最近的一次结果」（原图是 256px 未缩放的，会明显小一圈）。开符第 1 帧的符卡背景耗时 7.7ms -> 4.6ms
- 开符卡顿修复（符卡宣言文字）：宣言文字的「带色投影 + 白字」两份贴图（`_get_banner_text`）是在第一次开符那一帧才现 render + 抠副本（实测 1.4ms），载入界面原先只填了字形缓存。现在按 Boss 各自的宣言色把成品一并烤好。第 1 面第一张符卡开场那一帧 22.6ms -> 18.3ms（其中文字部分 1.4ms -> 0.04ms）
- 界面残留修复（高分辨率图层「清了却没上传」）：逐块上传的脏区列表在帧首清完屏之后被一起丢掉，于是「这一帧清掉、本帧却没再画」的像素永远不会上传——显卡纹理上那一块还停着上一帧的内容。表现就是对话立绘滑入 / 淡出后，在原地多出一块（或几块）立绘，关卡标题、HUD 文字同理（六面 Kaeman 战前对话第 9 句、同场景同帧 A/B：修复前 89.4 万像素与修复后不同，全落在立绘与标题上）。现在帧首清屏用的那份矩形列表会一并交给 `end_frame` 当成本帧要上传的区域（两份列表每帧互换，不会累积；实测每帧 36 块 / 0.57 Mpx，只有整幅上传 6.22 Mpx 的 9%）。像素回归（旧路径 vs 新路径）仍只剩第一轮已知的那 6230 像素 HUD 文字行差异；`tools/_ui_residue_check.py` 覆盖 10 条界面返回路径全部无残留（峰值 <= 8，其中「设置 -> 出征准备」这类在修复前峰值 255、平均差 4.17）
- 官网更新：画廊改用 /new 套组立绘重新出图，物品数据同步（Bonzo's Mask 效果与价格、护甲部位）
- 官网更新：画廊新增四位自机（Mage / Archer / Berserk / Tank）立绘，首页与角色页补上「选择自机」，「选择自机 / 选择难度 / 设置」实机截图与玩法页的显示设置、游戏速度说明一并同步
- 官网改版：上一版的 `web/` 下线，新官网（原 `web-new/`）改名 `web/` 顶上，GitHub Pages 的发布目录随之指到它 —— 旧站的画廊 / OST 两页与 `data/gallery.json`、`tools/export_items.py` 一并移除（人物图并进人物页、曲目并进音乐室，舞台扩到 01-EX 含 Ex 面两位 Boss）。Boss 立绘按当前 `another` 套组从游戏素材重新出图，Barry 同步为新的高清全身立绘（`web/assets/boss/barry.webp`）

- 战斗区实体上显卡（`src/engine/painter.py`、`src/engine/display.py`、`src/entities/boss.py`、`src/entities/enemy.py`、`src/entities/player.py`、`src/entities/pickup.py`）：敌机 / Boss / 自机 / 掉落物此前画在 1x 画布上、随整幅画面被线性放大（第 1 面 Arachne 的战斗贴图只有 65x96 逻辑像素，2x 输出下那 130x192 个物理像素全是从这张小图上采样的）。现在多出第三个显卡层（`blit_gpu_entity` / `gpu_entity_ops`），在「1x 画布前半」与弹幕之间回放，层级顺序与旧版逐条对应（同一层内按绘制顺序排）：敌机 → Boss → 掉落物 → 自机，仍在弹幕与 HUD 之下、压在关卡特效之上。贴图按渲染倍率重采样（`hires.blit_entity` + 按倍率分开的贴图缓存），碰撞 Mask、小怪的白色呼吸描边、六边形兜底绘制仍取 1x 版本，判定范围不随画面设置改变；无 GPU 呈现时倍率本来就是 1x，落回画布后与旧版逐像素相同
- 顺手修（`TOUHOU_HIRES=0` 对比模式下的图层错位）：显卡指令的坐标写的是「逻辑坐标 x 渲染倍率」，而回放用的 layer_size 取自高分辨率图层 —— 关掉高分辨率图层时两者不再一致（坐标按 2x 记、图层却是 1x），HUD 底板、背景带与弹幕会整体错位到画面外（战斗实体一并受影响）。现在指令倍率一律以画布的高分辨率倍率为准

- 战斗区特效与召唤物上显卡（`src/engine/painter.py`、`src/engine/display.py`、`src/engine/hires.py`、`src/entities/boss.py`、`src/stages/stage4.py`、`src/stages/stage5.py`、`src/stages/stage6.py`、`src/stages/goldor_terminal.py`、`src/stages/goldor_rage.py`）：符卡演出与 Boss 召唤物（Livid 分身 / Professor 的巨人与 guardian / Storm 的蓄力压暗与贯穿激光 / Necron 日核弹 / Goldor 终端、剑雨与走廊 / Kaeman 的权能环、圣物、枯龙、裂空斩、湮灭射线、终眠 / 第 4 面终符的黑暗吞噬）此前画在 1x 画布上、随整幅画面一起被线性放大，与已经原生高分辨率的弹幕 / 战场实体 / 文字 / 立绘之间有清晰度落差。现在多出第四个显卡层「战斗区前景」（`blit_gpu_fg` / `gpu_fg_ops`，回放位置在 1x 画布下半之后、HUD 之前，与它们原先画在画布后半的顺序逐条对应），图元按渲染倍率原生绘制（`hires.entity_effect(..., fg=True)` 与 `hi_*` 系列），贴图按倍率重采样（`hires.blit_entity` / `blit_fg`）；逐帧改「表面级 alpha」的写法改成让显卡按指令调透明度（`alpha=` 参数），逐帧旋转 / 翻转改走 `hires.rotate` / `hires.flip`。关掉显卡路径（`TOUHOU_UI_GPU=0`）时倍率回到 1x，逐像素与旧版相同
  - 第 6 面每张符卡都要整场尺寸的面板：3x 下每帧新建 1~2 块 1728x2010（13MB）的表面，还要各上传一次，实测吃掉 4.6~8.7ms/帧（权能符 26.7ms、湮灭符 18.9ms）。新增「本帧专用」的面板复用池（`hires.scratch_panel` / `reset_scratch`，帧内发不同槽位、帧首归还）与复用面板的重传（`TextureCache` 见到 `hi_dynamic` 标记就 `update()`）：面板分配 2~3.8ms -> 0.1~0.4ms，帧时间 26.7 -> 20.8ms、18.9 -> 14.0ms（3x，2880x2160）。复测（3x，2880x2160）：第 6 面权能符横幅期中位 17.2~19.0ms（超 16.7ms 的帧 99/99），同一段关掉高分辨率图层（`TOUHOU_HIRES=0`）中位 7.8ms —— 这 ~11ms 是弹幕 / 战场实体 / 战斗区特效三层合起来、按原生分辨率绘制多出的开销（清晰度换帧率的明账，不是哪一块面板能回去的）；这几张面板重的符卡在 3x 下仍在 16.7ms 预算之上（同一段在 2x 下是横幅期中位 12.0ms、0/99 帧超预算）
  - 验收：复用池与「每帧新建面板」在同一状态、冻结时钟下逐像素一致（关掉符卡背景后最大通道差 0）；第 4 面终符黑暗遮罩改横带后，逐行亮度剖面与旧版逐行画法最大差 1/255，渐变无台阶
- 冒烟工具修复：`tools/_smoke_goldor_terminal.py`（符卡宣言横幅的计时只在绘制里推进、开符后「站稳」最多还要等 240 帧，无头用例要先跳过这两步）、`tools/_smoke_stage2.py` / `tools/_smoke_stage3.py`（`PlayingState.draw` 走的是画布的显卡接口，传普通 Surface 会 `AttributeError: blit_gpu_bg`，改用 `Painter.create`）
- 六面道中背景改为「一套贴图 + 逐段压暗」（`src/stages/stage6.py`、`src/stages/stage1.py`、`src/engine/settings.py`）：道中不再在 66s 切进 `fortress_floor` / `fortress_wall` 那套凋零要塞贴图，整段沿用原来的 `floor.png` / `wall.png`（四面墓穴风格），阶段之间的区别交给压暗值 —— `BG_DARKNESS_KEYS` 给出「开场 66 → 进军结束 92 → 进入要塞 122 → 最后防线 152」的线性曲线，最后防线之后继续按每秒 7 加深到 178 封顶，于是背景亮度随三段推进持续下降，且开场就比原先的 40 暗一档；`_enter_fortress` 只保留镜头抬高与滚动加速（要塞进场的感觉不变），`background_fortress` 与 `settings.STAGE6_FORTRESS_*` 一并删除，练习模式的 Kaeman 战跟着吃关底那套背景（不再单独切要塞背景，`src/ui/practice.py`）
  - 压暗层由「按值缓存半透明表面」改为「一份常驻黑色表面 + 整层 alpha」（`Stage.draw_battle_backdrop`）：原先 `_dark_cache` 按压暗值缓存，值逐帧渐变会攒出上百张 576x670 的表面（约 170MB），现在改成一整块 `(0,0,0,255)` 表面按帧 `set_alpha(darkness)` —— 逐像素 alpha 与表面 alpha 相乘，像素与旧版逐位一致，其余各面（压暗值固定）画面完全不变

- 六面道中四位凋零残影登场时换上各自的背景（`src/stages/stage6.py`、`src/engine/spell_bg.py`、`src/engine/settings.py`）：残影在 70 / 78 / 86 / 94s 出场的那 3.2s 里，战斗区不再是走廊，而是这位门徒在五面 BOSS RUSH 的那张竞技场背景 —— Maxor / Storm / Goldor 直接复用五面同名风格的整幅贴图，仅 Necron 用六面自己的 `assets/backgrounds/stage6/NecronP.png`（2874x1736 的整幅图，与五面那张 3328x480 的环形全景条不是一路，因此在 `spell_bg` 里单独登记 `necron_p` 风格，dim 取 0.70 与其余三张的观感拉平）；背景随残影一起淡入（20 帧）、残影退场后 36 帧淡出并回收，两位残影之间自动回到走廊。残影背景与符卡背景走同一条绘制路径：完全不透明时同样跳过伪3D 地面绘制
  - 四张源图合计约 20MB，现解一次要 70~100ms（实测四条一起 528ms），已在 `STAGE_SPELL_BG[6]` 登记、由关卡载入界面预热，残影登场那一帧只剩建实例的约 1ms；单帧绘制 1.4~1.8ms（整幅贴图风格，无旋转层）

- 六面道中四位凋零残影改用「Boss 立绘套组」的立绘（`src/stages/stage6.py`、`src/engine/settings.py`、`src/ui/loading.py`）：残影不再读 `assets/sprites/enemies/stage6/*_ghost.png`，而是取这位门徒在五面的那张立绘（`assets/sprites/bosses/<套组>/`，new 是 2040x3072 的大图、another 是 1024x1536），于是在设置里切换 new / another 套组时残影立绘跟着换。路径在残影登场那一刻用 `cfg.boss_art_path()` 现取、记在残影自己身上（`_load_sprite` 按路径缓存，同时打两个套组也不会串图）；`settings.STAGE6_*_GHOST_SPRITE` 四个常量与 `STAGE_SPELL_SPRITES[6]` 里对应那四条一并删除，改由 `STAGE_GHOST_ART` + `stage_ghost_art_paths()` 按当前套组解析、经 `stage_spell_sprites()` 交给载入界面预热
  - 换成大图之后第一次绘制要现缩一次（`_load_sprite` 的 `smoothscale`，实测 new 100~120ms/张、another 36~49ms/张），而载入界面的「符卡贴图」一步原先只解码、不解缩，正好落在残影淡入的头几帧上。现在由新的 `Stage6_FinalApproach.warm_spell_effects` 把四张按 `GHOST_HEIGHT` 缩好的那一份（含显卡层要的倍率档）也提前建好：载入界面多花 0.42s（new）/ 0.16s（another），残影登场那一帧回到 8~9ms 的普通帧
  - 立绘长宽比与原 `*_ghost.png` 一致（约 0.664），`GHOST_HEIGHT = 190` 与四位的位置不用动；两套立绘是同一角色的两套画（`another` 那四张里 storm 与原 `storm_ghost.png` 是同一份文件），同一位置的画面差异实测平均通道差 22~56
- 六面道中四位残影改成「接力」出场（`src/stages/stage6.py`）：前一位撑到后一位登场那一帧才退场，两人之间不再留间隔（原先每位登场后有一段空窗），最后一位（Necron）仍按 `GHOST_MAX_AGE` 收场，于是残影段的起止与总时长不变（70.00s 登场、97.15s 收尾，合计 27.15s，任何一帧都至少有一位在场）；每位登场那一帧（age 0）就开始放自己那 80 帧「告别弹」，不再是登场后等一段再起手。背景交接同样无缝：新一张贴图要在 20 帧里淡入，直接换会在这段淡入里露出走廊，所以上一张先留着铺底（`ghost_bg_prev`，两人交替时最多同时存在两张），等新图铺满或淡出后再无声丢掉

- 六面道中四位凋零残影的技能改成「各自符卡的削弱片段」（`src/stages/stage6.py`）：原来的「告别弹」是一组现编的扇形弹（大玉 / 贯道光束 / 整圈 / 刀弹），现在改成每位门徒从自己那张符卡里借一小段弹幕 —— 只留形状、一律削弱，并且不带任何符卡机制（没有无敌与破防、没有结晶 / 终端 / 避雷柱、没有判定窗口与全屏雷击、没有 TNT 与地狱火）。残影登场那一帧就起手、连续 80 帧（`GHOST_SPELL_FRAMES`），窗口之外什么都不做；整段与五面符卡同一种写法（逐帧推进的小状态机），残影原本那个「只开一次火」的 `fired` 标记因此删掉，残影本身依旧打不到
  - Maxor：Phase1「Maxor's Frenzy」的穿梭骷髅排 —— 三排各 3 发 Wither Skull（用原始骷髅贴图，弹速 3.0，原版 5.6 且飞出一段后减速），左右方向交替，末尾补一对原版破防螺旋里的自机狙大玉，共 11 发；TNT / 冲击波 / 结晶 / 红激光解除无敌全去掉
  - Storm：雷符「Giga Lightning」狂暴状态的四层弹幕 —— 八向圆弹环每 20 帧一圈 6 发（原每 8 帧 8 发）、自机狙双刀每 40 帧（原每 20 帧）、旋转箭环 8 发（原 14 发）、随机大玉 3 发（原 6 发），共 39 发，弹速同步下调；避雷柱安全区、蓄力破坏、全屏毁灭雷击的判定窗口，以及狂暴状态自带的「解封可被打 / 受伤 ×4」与换位都不带
  - Goldor：Phase3「Infinite Rage」的金环与米弹螺旋 —— 金环 8 发（原 10 发 / 每 15 帧）、反向白环 6 发（原 14 发 / 每 40 帧）、米弹三臂螺旋 4 圈（原四臂 / 每 13 帧），共 26 发；剑盾本体与「剑隙散射」那套几何机制去掉，只留弹幕形状
  - Necron：终符「Necron's Frenzy」的八臂螺旋与大玉环 —— 六臂螺旋 4 圈（每 15 帧一圈、弹速固定 1.5；原版每 5 帧一圈、弹速由 1.55 递增到 7.0），末尾一圈 10 发大玉环（原 12 发），共 34 发；屏幕底部不断上涌的地狱火与加速机制去掉

- 六面行军小怪的正弦横摆一律改为竖直下落（`src/stages/stage6.py`）：`WitherHuskEnemy` / `WitherMinerEnemy` / `WitherKnightEnemy` 的 `move_pattern` 由 `strafe`（下落 + 横向 `sin` 摆动，振幅 2.2/2.2/2.4、周期 2.62s）改成 `descend`，净下落速度不变（1.5 / 0.8 / 0.9 px/帧，即 90 / 48 / 54 px/s），改后横向位移严格 0；顺带删掉三者的 `move_amplitude` 与 Husk 那个没人用的 `move_pattern` 参数。按你的要求 `WitherWispEnemy` 不动（仍是 `sin` 飘移，只是它净竖直速度为 0、原本靠 ±0.9 横漂 6.3s 侧向离场），停驻型的 Golem / Colossus 也保留到位后的微摆
  - 影响：同行波次的敌人不再左右错开，压迫感从「蛇形逼近」变成「整列压下来」；实测在场时间不变（Husk 8.3s / Miner 15.5s / Knight 13.8s，均由下缘离场）

- 六面道中的凋零守卫 / 凋零矿工改为直接在画面内上部出现，凋零游魂变快变多（`src/stages/stage6.py`）：守卫与矿工原先从战斗区外（y=-24~-90）落下，先在框外走一段才进画面；现在按 `_top_spawn()` 把原来的区外高度换算成画面内落点（最低一档 y=180，原高度每高 1px 落点高 2.4px，先后关系与原版一致），入场即已站在战斗区上部（落点 64~180）；凋零游魂仍从区域外落下
  - 凋零游魂（Wither Husk）下落速度 1.5 → 3.0 px/帧（全道中最快的一档），自然离场用时由 8.3s 缩到 5.1~5.7s；每波数量翻倍：Undead Line 2→4、Miner Phalanx 2→4、Fortress Gate 1→3、Guard Wall 3→6、Last March 5→10（六面道中游魂总数 13 → 27），多出来的那一只按原落点的旁侧 / 再上一层错开，不排成一条竖线
  - 实测在场（空场、敌机不被击破）：29s Guard Wall 20 只（Guard 6 / Husk 6 / Miner 6 / Lord 2）、34s Last March 28 只、100s Final Defense 12 只，三处同屏敌弹分别 289 / 322 / 246 发

- 六面道中 Skeleton Lord 的螺旋鳞弹改为黄 / 绿交替，发射频率与每轮转角都翻倍（`src/stages/stage6.py`）：弹色按轮次交替 —— 偶数轮黄、奇数轮绿，两个色值经弹幕图集的配色槽位分别落到鳞弹行的 `g01_13` / `g01_10`（左右两位各按自己的轮次计数，同一轮同色）；每轮间隔 12 → 6 帧、每轮偏转角 0.55 → 1.10 弧度，弹数与弹速不变（每轮仍是 5 发、4.2 px/帧）
  - 密度实测（同一面无自机输出、空场扫满 105s）：首波 5~15s 的鳞弹稳态由 82 发涨到 163 发（新增条目里记的「同屏鳞弹峰值 111 发」是改动前的数字），整面同屏敌弹峰值由 321 涨到 395 发（@104.6s）；多出来的约 74 发正是两位 Lord 一直没被击破的螺旋，实战中打完（HP 420）这部分立即停止

- 六面道中的守卫 / 矿工落点再上移，同一批凋零游魂改成成队形下落（`src/stages/stage6.py`）：`_top_spawn()` 的基准由 220 抬到 180（原高度每高 1px 落点仍高 2.4px），另加一条上限 `TOP_SPAWN_HIGHEST_Y = 64` —— 原来最高的 -80 / -90 两档换算后已经贴到画面顶边，守卫（92px 高）/ 矿工（84px 高）的贴图会被切掉一截，现在压在这一行；落点带由 220~354 变成 64~180，各波之间的高低先后关系与原版一致
  - 凋零游魂不再逐个手写高度，改由 `_husk_line()` 按「这一批的 x 顺序」自动排：`shape="v"` 是 V 字（中间最低、两翼依次抬高，两臂档高一致）、`"\"` 左端最高向右逐档降低、`"/"` 右端最高向左逐档降低；整队都摆在战斗区上缘之外（默认最高一档 y=-112，每往里一档低 40px），因游魂下落速度相同，下压时队形保持不变
  - 各波队形：Undead Line / Miner Phalanx 各是左右两个斜臂（左 `\` + 右 `/`，合起来是一个 V）、Fortress Gate 3 只排 V（档高 44）、Guard Wall 6 只排 V（档高 34）、Last March 10 只是上下两层 V（各 5 只，档高 40，第二层整体再高 48px）

- 六面残影段不再生成小怪，四位门徒的弹幕加强（`src/stages/stage6.py`）：原来要塞段还排着四波小怪（68s Fortress Wall / 75s Siege Detail / 82s Knight Order / 90s Golem Ward），它们与 70s 起登场的门徒残影挤在同一段里；现在这四波全部取消，70~97s 只剩残影接力（每位登场那一帧即起手的一段弹幕），段内小怪为零，残影收场后照旧进入 100s 的王座前最后防线（`setup_waves` 里这一段只剩注释）
  - 四位残影的「告别弹」在原来的削弱版基础上整体加强到约 2.3 倍弹量，片段长度由 80 帧延长到 110 帧（`GHOST_SPELL_FRAMES`）：Maxor 骷髅排三排各 3 发 → 四排各 5 发、末尾自机狙大玉一对 → 两轮各 3 发（片段发弹 11 → 26）；Storm 八向环每 20 帧 6 发 → 每 18 帧 8 发、自机狙双刀每 40 → 36 帧、旋转箭环 8 发一圈 → 12 发两圈、随机大玉 3 → 4 发（39 → 92）；Goldor 金环 8 → 10 发并来两圈、反向白环 6 → 8 发并来两圈、米弹三臂每 12 帧 4 圈 → 四臂每 10 帧 5 圈（26 → 56）；Necron 螺旋六臂每 15 帧 4 圈 → 八臂每 10 帧 7 圈、末尾大玉环 10 发一圈 → 12 发两圈（34 → 80）
  - 仍然一个机制都不带（没有无敌与破防、没有结晶 / 终端 / 避雷柱、没有判定窗口与全屏雷击、没有 TNT 与地狱火），弹速也仍低于原版；实测（首波两位 Lord 已在真实战斗中被击破）71 / 79 / 87 / 95s 四帧的同屏敌弹是 47 / 70 / 57 / 80 发

 - 六面小怪被击破 / 门徒残影离场时会炸掉周围一圈敌弹（`src/entities/bullet.py`、`src/stages/stage1.py`、`src/stages/stage6.py`、`src/ui/menu.py`）：新增 `burst_cancel_bullets()` —— 把半径内的敌弹推进游戏里原有的「变白自爆」动画（不是瞬间消失），另补两圈无害白光展现爆炸范围（光效是 `harmless` 弹，不参与碰撞与擦弹，也不吃难度下的密度缩减）；清弹半径按体型给（`CLEAR_RADIUS_PER_SIZE = 3.0`，即判定半径 × 3）：凋零游魂 42 / 矿工 48 / 骑士 57 / 守卫与兵马俑 60 / Skeleton Lord 66 / 巨像 90，四位残影固定 180（立绘 190 高，约炸掉大半个战斗区，白光取各自残影的主色）
   - 挂点：`Stage` 新增钩子 `enemy_death_clear_radius(enemy)`（基类返回 0 = 不清弹，其余各面画面不变），六面覆写它；击破奖励这一条走 `PlayingState._death_clear_bullets()`（在 `_reward_enemy_kill` 开头调用，符卡练习与 Ex 面同样生效），残影离场则在 `_update_ghosts` 里直接调用
   - Kaeman 不走这条：击破 Boss 的那一下不清屏（`enemy_death_clear_radius` 见到 `Boss` 返回 0）

 - 六面王座前的最后防线（100s）换编成（`src/stages/stage6.py`）：原来这一波是 12 只小怪的混编，现在只有 5 只 —— 左右两位 Skeleton Lord（从画面左右外侧 x=±622 横向切入、停在 x=150 / 426）＋上方一位 Wither Colossus（x=288，从 y=-70 下降到 y=94 悬停）＋两位 Wither Guard（直接出现在画面内 y=118，x=196 / 380，随后照旧缓缓下落）
   - 上面「实测在场」那条里的 100s Final Defense 数字随之更新：12 只 → 7 只（含开场未被击破的两位 Lord，实战打完是 5 只）、同屏敌弹 246 → 192 发；29s Guard Wall 20 只 / 34s Last March 28 只 的敌机数不变，同屏敌弹因 Skeleton Lord 加密而由 289 / 322 涨到 312 / 358 发

- 切换渲染倍率后物件隐身修复（`src/engine/painter.py`、`src/ui/menu.py`、`src/ui/difficulty.py`、`src/ui/practice.py`、`src/ui/character_select.py`）：界面与各类贴图缓存都是「按倍率出图」的（界面把整幅背景存在自己身上、子弹把旋转贴图存在实例上、Boss 立绘按倍率进缓存），改倍率时不会从头重来，于是绘制时手里拿的是旧倍率的那一张；而倍率对不齐时的旧写法是退回 1x 画布 —— 画布恰恰画在显卡指令层「之上」，退回画布等于把整个指令层盖掉，所以切完倍率以后界面上的文字 / 立绘 / 面板（主菜单、设置、难度、自机选择、符卡练习最明显）与战斗区的敌机 / 弹幕成片隐身。现在 `Painter._at_render_factor` 把旧倍率的图换算到当前倍率一次并缓存（仍旧贴回它自己那一层，层级与倍率都不会错），整幅背景另在绘制前按当前倍率重出（`menu.refresh_background`，只多一次缓存查表，避免拿旧倍率的图放大后发虚）
  - 验收：12 个界面与 battle1 各跑一遍「原生该倍率」与「从另一个倍率切过来」的逐像素比对（`tools/_ui_gpu_smoke.py` 同一套场景），1x↔3x 两个方向都 0 差；`tools/_ui_gpu_smoke.py` 13 个界面 before / after 全通过，`tools/_ui_residue_check.py` 11 条返回路径全通过，二 / 三面与 Goldor Terminal 冒烟、`tools/_bullet_subpixel_check.py` 均 ALL OK

- 影符「八重存在」被击破的分身继续射击修复（`src/stages/stage5.py`）：分身的攻击与移动由 `boss.livid_states` 统一驱动，而击破一个分身只把 `_LividClone.alive` 置否（退出绘制与索敌），状态本身仍留在表里 —— 于是那个位置上只剩一段空位，弹幕却照常按它的道具节奏往外走（`dark_orb` 的紫玉环 / `livid_dagger` 的三连刀扇 / `warped_stone` 的瞬移落石都在其中）。现在分身被击破时同步把所属状态标为 `alive=False`，符卡循环跳过它：既不再发弹，也不再自行移动（黑幕换位仍会把它算进位置重排，与改前一致；分身实体本就不绘制、不可被击中、不重复给真身回血）
  - 验收：新增 `tools/_smoke_livid_clones.py`（不启动游戏）——逐帧记录「哪个状态发了弹」，8 个状态全员存活时 8 个都在发弹，击破其中 3 个后只剩存活的 5 个发弹、被击破的三个 0 发；同一工具带一条复刻修复前写法的自证：旧循环（不看 `state["alive"]`）下被击破的分身照常发弹，因此该检查确实能抓住此 bug。`tools/_smoke_stage5.py`（五面 BOSS RUSH 全流程）仍 ALL OK

### 后续计划
- 符卡背景（`src/engine/spell_bg.py`，全部 `bg_style`）仍画在 960x720 画布上整体放大：这是战斗区里最后一块没有原生高分辨率的图层（弹幕 / 敌机 / Boss / 自机 / 掉落物 / 召唤物 / 符卡演出都已搬上显卡，见上），它与其余图层之间还有清晰度落差。其中裂纹 / 旋转层这类图案逐帧变化，搬过去要按倍率重画并重做烘焙缓存
- 还没上显卡的弹幕图元（消弹动画 / 未配图集的光束线）目前画在切刀之后的画布上、等于叠在弹幕层之上，搬过去时一并规整
- 位置同样要按浮点坐标登记（本次弹幕的做法，见 `painter._dest_scaled`），否则搬上显卡后仍会落在 1 逻辑像素的网格上，斜向移动照样是台阶（弹幕 / 实体 / 前景三层已按此处理）
- 第 6 面面板重的几张符卡在 3x 下仍超 16.7ms（横幅期中位 17~19ms）：开销来自按整场尺寸原生重绘面板，可继续压的方向是静态部分烘焙复用、变化区域分块重绘

### 文件
- 新增 `src/ui/skyblock_ui.py`、`src/ui/storage.py`、`src/engine/boss_art.py`
- 新增 `assets/gui/`、`assets/sounds/effects/`、`assets/sprites/bosses/{new,another,legacy}/`
- 新增 `src/engine/hires.py`（文字 / 立绘 / 面板高分辨率图层，含呈现层高分辨率纹理）
- 新增 `src/engine/painter.py`（统一绘制入口：显卡指令登记 + 预烤面板缓存 + 显卡纹理缓存）
- 新增 `src/engine/display.py`、`src/ui/loading.py`
- 新增 `src/stages/stage_ex.py`（Ex 面：裂隙 ~ The Rift）与 `tools/_gen_stage_ex_assets.py`、`tools/_smoke_stage_ex.py`、`tools/_smoke_ex_entry.py`
- 新增 `assets/backgrounds/stage_ex/`、`assets/sprites/enemies/stage_ex/`、`assets/titles/stage_ex.png`、`assets/sprites/bosses/{new,another}/Wizardman|Barry.png`
- 新增 `tools/_ui_residue_check.py`（界面残留检查：可退出界面返回后逐条比对像素，带「复刻修复前写法」开关自证检查有效）
- 新增 `tools/_scratch_panel_check.py`（符卡面板复用检查：冻结时钟后逐像素对比「复用面板池」与「每帧新建面板」两条路径）
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
- 新增六面标题图 `assets/titles/stage6.png` 与六面道中曲 `6_1_start.wav`（六面 Boss 战曲目仍暂复用五面）

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
