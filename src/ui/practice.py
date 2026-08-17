# -*- coding: utf-8 -*-
# 符卡练习模式
# 主菜单 Practice 入口：可单独练习所有 Boss 的每一张符卡（含 Last Spell）。

import os

import pygame

from src.engine import settings as cfg
from src.engine.game import GameState
from src.stages.stage1 import Stage1_SkyblockHub, Stage


def _load_menu_bg():
    try:
        if os.path.exists(cfg.MENU_BACKGROUND):
            img = pygame.image.load(cfg.MENU_BACKGROUND)
            return pygame.transform.smoothscale(
                img, (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    except Exception as e:
        print(f"[Practice] Failed to load background: {e}")
    return None


def _panel(screen, x, y, w, h, alpha=120):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, alpha))
    screen.blit(s, (x, y))


def _elide(font, text, max_w):
    """文本超宽时用省略号截断。"""
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "…")[0] > max_w:
        text = text[:-1]
    return text + "…"


# ---------------------------------------------------------------------------
# 练习条目注册表：覆盖全部 Boss（道中 + 关底）与全部符卡
# ---------------------------------------------------------------------------

def _mid_boss_stage(stage_cls):
    """构建器：创建真实关卡并取出道中 Boss 作为练习 Boss。"""
    def build():
        stage = stage_cls()
        stage.setup_mid_boss()
        stage.boss = stage.mid_boss
        stage.mid_boss = None
        return stage
    return build


def _final_boss_stage(stage_cls):
    """构建器：创建真实关卡并取出关底 Boss 作为练习 Boss。"""
    def build():
        stage = stage_cls()
        stage.setup_boss()
        return stage
    return build


def _stage5_boss_stage(boss_id):
    """构建器：五面 BOSS RUSH 中单独取出指定 Boss。"""
    def build():
        from src.stages.stage5 import Stage5_WitherLords
        stage = Stage5_WitherLords()
        stage.boss = stage._build_boss(boss_id)
        stage.mid_boss = None
        return stage
    return build


_PRACTICE_ENTRIES = None


def build_practice_entries():
    """构建练习条目列表（全部 Boss + 全部符卡，首次调用后缓存）。"""
    global _PRACTICE_ENTRIES
    if _PRACTICE_ENTRIES is not None:
        return _PRACTICE_ENTRIES

    def _entry(stage_num, group, boss_name, build):
        stage = build()
        boss = stage.boss
        cards = [{"name": c.name, "index": i, "last": False}
                 for i, c in enumerate(boss.spell_cards)]
        if boss.last_spell is not None:
            cards.append({
                "name": boss.last_spell.name,
                "index": len(boss.spell_cards),
                "last": True,
            })
        return {
            "stage_num": stage_num,
            "group": group,
            "boss_name": boss_name,
            "build": build,
            "cards": cards,
        }

    from src.stages.stage2 import Stage2_DragonsNest
    from src.stages.stage3 import Stage3_CatacombsF1
    from src.stages.stage4 import Stage4_Catacombs
    from src.stages.stage6 import Stage6_FinalApproach

    _PRACTICE_ENTRIES = [
        _entry(1, "第一面", "Arachne（道中）", _mid_boss_stage(Stage1_SkyblockHub)),
        _entry(1, "第一面", "Arachne", _final_boss_stage(Stage1_SkyblockHub)),
        _entry(2, "第二面", "End Stone Protector（道中）",
               _mid_boss_stage(Stage2_DragonsNest)),
        _entry(2, "第二面", "Ender Dragon", _final_boss_stage(Stage2_DragonsNest)),
        _entry(3, "第三面", "The Watcher（道中）",
               _mid_boss_stage(Stage3_CatacombsF1)),
        _entry(3, "第三面", "Bonzo", _final_boss_stage(Stage3_CatacombsF1)),
        _entry(4, "第四面", "Scarf（道中）", _mid_boss_stage(Stage4_Catacombs)),
        _entry(4, "第四面", "Sadan", _final_boss_stage(Stage4_Catacombs)),
        _entry(5, "第五面", "The Watcher", _stage5_boss_stage("watcher")),
        _entry(5, "第五面", "The Professor", _stage5_boss_stage("professor")),
        _entry(5, "第五面", "Thorn", _stage5_boss_stage("thorn")),
        _entry(5, "第五面", "Livid", _stage5_boss_stage("livid")),
        _entry(5, "第五面", "Maxor", _stage5_boss_stage("maxor")),
        _entry(5, "第五面", "Storm", _stage5_boss_stage("storm")),
        _entry(5, "第五面", "Goldor", _stage5_boss_stage("goldor")),
        _entry(5, "第五面", "Necron", _stage5_boss_stage("necron")),
        _entry(6, "第六面", "Kaeman", _final_boss_stage(Stage6_FinalApproach)),
    ]
    return _PRACTICE_ENTRIES


def build_practice_boss(entry, card_index):
    """构建练习 Boss：保留完整符卡序列以获得正确血条区间，但结符即视为击破。

    返回 (stage, boss)：stage 为带 Boss 的真实关卡实例，供练习舞台绘制复用。
    """
    stage = entry["build"]()
    boss = stage.boss
    spec = entry["cards"][card_index]
    boss.arm_combat(0)
    boss.entering = False
    boss.entry_timer = 0
    # 二阶段符卡（如 Bonzo 复活后）使用复活后的 max_hp，保证血条区间一致
    if (boss.revive_max_hp is not None and boss.revive_after_spell_idx is not None
            and spec["index"] >= boss.revive_after_spell_idx):
        boss.max_hp = boss.revive_max_hp
    if spec["last"]:
        boss.current_spell_idx = len(boss.spell_cards)
        boss._start_spell(boss.last_spell)
    else:
        card = boss.spell_cards[spec["index"]]
        if card.hp_threshold is not None:
            boss.hp = int(round(card.hp_threshold * boss.max_hp))
        boss.current_spell_idx = spec["index"]
        boss._start_spell(card)
    # 拦截结符推进：练习模式下结符 = 击破（不再进入下一张符卡 / Last Spell）
    orig_end_spell = boss._end_spell

    def _practice_end_spell():
        orig_end_spell()
        boss._cancel_screen_bullets()
        boss._begin_spell_bg_fade()
        boss._clear_spell_effects()
        boss.spell_banner_active = False
        boss.spell_banner_timer = 0
        boss.spell_banner_name = ""
        boss.current_spell = None
        boss.current_spell_idx = 0
        boss.last_spell_active = False
        boss.phase = "defeated"
        boss.alive = False

    boss._end_spell = _practice_end_spell
    return stage, boss


# ---------------------------------------------------------------------------
# 练习舞台：复用真实关卡的背景与符卡演出绘制，接管为单符卡练习
# ---------------------------------------------------------------------------

class PracticeStage(Stage):
    """练习舞台：单 Boss 单符卡，支持机械符/裂符等需要舞台配合的符卡。"""

    def __init__(self, base_stage, boss):
        super().__init__(base_stage.stage_num, base_stage.name,
                         bg_color=getattr(base_stage, "bg_color", (8, 8, 24)))
        self.base = base_stage
        self.boss = boss
        # 让真实关卡的绘制逻辑直接使用练习 Boss
        self.base.boss = boss
        self.base.mid_boss = None
        self.base.phase = "boss"
        self.phase = "boss"
        self.practice_cleared = False
        self.player_teleport_target = None

        # 透传音乐 / 标题 / 背景
        self.title_path = getattr(base_stage, "title_path", "")
        self.music_name = getattr(base_stage, "music_name", "")
        self.music_loop_path = getattr(base_stage, "music_loop_path", None)
        self.boss_music_name = getattr(base_stage, "boss_music_name", "")
        self.boss_music_start_path = getattr(base_stage, "boss_music_start_path", "")
        self.boss_music_loop_path = getattr(base_stage, "boss_music_loop_path", "")
        self.background = getattr(base_stage, "background", None)
        self.background_darkness = getattr(base_stage, "background_darkness", 0)
        # 六面 Kaeman：使用凋零要塞背景（与真实关底战一致）
        fortress = getattr(base_stage, "background_fortress", None)
        if fortress is not None:
            self.background = fortress
            base_stage.background = fortress

    @property
    def player_input_locked(self):
        boss = self.boss
        if boss is None:
            return False
        state = getattr(boss, "goldor_terminal", None)
        if state is None:
            return False
        return bool(state.get("input_locked"))

    def constrain_player(self, x, y):
        boss = self.boss
        if boss is None:
            return x, y
        state = getattr(boss, "goldor_terminal", None)
        if state is None or state.get("spell_done"):
            return x, y
        from src.stages.goldor_terminal import _gt_clamp_player
        return _gt_clamp_player(x, y, state)

    def update(self, dt, bullet_manager, player_x, player_y):
        if self.background:
            self.background.update(dt)
        self.timer += 1
        boss = self.boss
        if boss is None:
            return
        # 机械符「Terminal Pursuit」：转发鼠标/按键（与五面真实流程一致）
        gt_state = getattr(boss, "goldor_terminal", None)
        if gt_state is not None:
            mbj = getattr(self, "mouse_buttons_just_pressed", None) or {}
            mp = getattr(self, "mouse_pos", None) or (0, 0)
            if mbj.get(1):
                gt_state["mouse_clicked"] = (
                    mp[0] - cfg.BATTLE_OFFSET_X, mp[1] - cfg.BATTLE_OFFSET_Y)
            else:
                gt_state["mouse_clicked"] = None
            gt_state["mouse_battle"] = (
                mp[0] - cfg.BATTLE_OFFSET_X, mp[1] - cfg.BATTLE_OFFSET_Y)
            gt_state["keys_just_pressed"] = (
                getattr(self, "keys_just_pressed", None) or {})
        # Boss 死亡后仍更新一帧，让符卡背景淡出播完
        boss.update(dt, bullet_manager, player_x, player_y)
        livid_active = getattr(boss, "livid_active", False)
        if livid_active and (not boss.alive or boss.phase != "spell"):
            from src.stages.stage5 import _livid_cleanup
            _livid_cleanup(boss)
            bullet_manager.enemy_pause_frames = 0
        # 裂符「Dimensional Slash」：触手拉拽请求 -> 下一帧应用到自机
        sl = getattr(boss, "kaeman_slash", None)
        if sl is not None and sl.get("tentacle") is not None:
            tt = sl["tentacle"].get("teleport_target")
            if tt is not None:
                self.player_teleport_target = tt
                sl["tentacle"]["teleport_target"] = None
        # 机械符传送请求
        if gt_state is not None and gt_state.get("teleport_to") is not None:
            self.player_teleport_target = gt_state["teleport_to"]
            gt_state["teleport_to"] = None
        if not boss.alive and not self.practice_cleared:
            self.practice_cleared = True

    def get_active_enemies(self):
        boss = self.boss
        if boss is None or not boss.alive or not boss.combat_enabled:
            return []
        # Sadan 巨符「Precursors' Return」：只允许攻击当前巨人（与真实关卡一致）
        if (boss.phase == "spell" and boss.current_spell is not None
                and boss.current_spell.name == "巨符「Precursors' Return」"):
            state = getattr(boss, "sadan_giant_state", None)
            if state:
                giant = state.get("giant")
                if (giant is not None and giant.get("alive")
                        and giant.get("phase") in ("entering", "attack")):
                    return [giant["proxy"]]
            return []
        enemies = [boss]
        enemies.extend(g for g in getattr(boss, "professor_guardians", [])
                       if g.alive)
        for clone in getattr(boss, "livid_clones", []):
            if clone.alive:
                enemies.append(clone)
        return enemies

    def draw(self, screen, offset_x=0, offset_y=0):
        self.base.draw(screen, offset_x, offset_y)

    def draw_foreground(self, screen, offset_x=0, offset_y=0):
        self.base.draw_foreground(screen, offset_x, offset_y)

    def is_cleared(self):
        return False


# ---------------------------------------------------------------------------
# 选择界面
# ---------------------------------------------------------------------------

class PracticeSelectState(GameState):
    """符卡练习选择界面：左列 Boss，右列符卡。"""

    ROW_H = 30
    HEADER_H = 26
    PANE_Y = 150
    PANE_H = 440

    def __init__(self, game):
        super().__init__(game)
        self.background = _load_menu_bg()
        self.entries = build_practice_entries()
        self.boss_rows = self._build_boss_rows()
        self.boss_row_pos = {
            row[2]: row_idx for row_idx, row in enumerate(self.boss_rows)
            if row[0] == "boss"
        }
        self.boss_index = 0
        self.card_index = 0
        self.pane = 0          # 0=左侧 Boss 列表，1=右侧符卡列表
        self.boss_scroll = 0
        self.card_scroll = 0

    def _build_boss_rows(self):
        rows = []
        for i, e in enumerate(self.entries):
            if i == 0 or e["group"] != self.entries[i - 1]["group"]:
                rows.append(("group", e["group"]))
            rows.append(("boss", e["boss_name"], i))
        return rows

    def enter(self, game):
        pass

    def _clamp_scroll(self, scroll, index, visible):
        if index < scroll:
            return index
        if index >= scroll + visible:
            return index - visible + 1
        return scroll

    def update(self, dt):
        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False)
                or keys.get(pygame.K_BACKSPACE, False)):
            self.game.pop_state()
            return

        entry = self.entries[self.boss_index]
        n_cards = len(entry["cards"])

        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self.pane = 0
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self.pane = 1

        if self.pane == 0:
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.boss_index = (self.boss_index - 1) % len(self.entries)
                self.card_index = min(
                    self.card_index,
                    len(self.entries[self.boss_index]["cards"]) - 1)
            elif keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.boss_index = (self.boss_index + 1) % len(self.entries)
                self.card_index = min(
                    self.card_index,
                    len(self.entries[self.boss_index]["cards"]) - 1)
        else:
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.card_index = (self.card_index - 1) % n_cards
            elif keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.card_index = (self.card_index + 1) % n_cards

        # 滚动保持选中项可见
        visible = self.PANE_H // self.ROW_H
        self.boss_scroll = self._clamp_scroll(
            self.boss_scroll, self.boss_row_pos[self.boss_index], visible)
        self.card_scroll = self._clamp_scroll(self.card_scroll, self.card_index,
                                              visible)

        if (keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False)):
            launch_practice(self.game, self.entries[self.boss_index],
                            self.card_index)

    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((4, 4, 16))

        title = self.game.font_large.render(
            "符卡练习 Spell Practice", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 52))

        entry = self.entries[self.boss_index]
        visible = self.PANE_H // self.ROW_H

        # ---- 左侧：Boss 列表 ----
        bx, bw = 96, 420
        _panel(screen, bx - 10, self.PANE_Y - 40, bw + 20, self.PANE_H + 56)
        head = self.game.font_medium.render("选择 Boss", True, cfg.COLOR_WHITE)
        screen.blit(head, (bx, self.PANE_Y - 34))
        row_y = self.PANE_Y
        for row in self.boss_rows[self.boss_scroll:self.boss_scroll + visible + 1]:
            if row_y > self.PANE_Y + self.PANE_H - self.ROW_H:
                break
            if row[0] == "group":
                g = self.game.font_small.render("—— " + row[1] + " ——",
                                                True, cfg.COLOR_GRAY)
                screen.blit(g, (bx + 6, row_y))
                row_y += self.HEADER_H
                continue
            is_sel = row[2] == self.boss_index
            color = cfg.COLOR_YELLOW if is_sel else cfg.COLOR_WHITE
            text = self.game.font_medium.render(row[1], True, color)
            screen.blit(text, (bx + 26, row_y))
            if is_sel:
                ind = self.game.font_medium.render("> ", True, cfg.COLOR_YELLOW)
                screen.blit(ind, (bx + 2, row_y))
            row_y += self.ROW_H

        # ---- 右侧：符卡列表 ----
        cx, cw = 540, 390
        _panel(screen, cx - 10, self.PANE_Y - 40, cw + 20, self.PANE_H + 56)
        head = self.game.font_medium.render("选择符卡", True, cfg.COLOR_WHITE)
        screen.blit(head, (cx, self.PANE_Y - 34))
        row_y = self.PANE_Y
        cards = entry["cards"]
        max_text_w = cw - 26
        for ci in range(self.card_scroll, min(len(cards), self.card_scroll + visible + 1)):
            if row_y > self.PANE_Y + self.PANE_H - self.ROW_H:
                break
            spec = cards[ci]
            is_sel = ci == self.card_index
            color = cfg.COLOR_YELLOW if is_sel else cfg.COLOR_WHITE
            label = spec["name"]
            if spec["last"]:
                label += "（Last）"
            text = self.game.font_small.render(
                _elide(self.game.font_small, label, max_text_w), True, color)
            screen.blit(text, (cx + 20, row_y + 6))
            if is_sel:
                ind = self.game.font_small.render("> ", True, cfg.COLOR_YELLOW)
                screen.blit(ind, (cx + 2, row_y + 6))
            row_y += self.ROW_H

        # ---- 底部信息 ----
        sel_card = entry["cards"][self.card_index]
        label = sel_card["name"] + ("（Last Spell）" if sel_card["last"] else "")
        summary_text = _elide(
            self.game.font_medium,
            f"第{entry['stage_num']}面 · {entry['boss_name']} · {label}",
            cfg.SCREEN_WIDTH - 120)
        summary = self.game.font_medium.render(summary_text, True, cfg.COLOR_GREEN)
        screen.blit(summary, ((cfg.SCREEN_WIDTH - summary.get_width()) // 2, 616))

        hint = self.game.font_small.render(
            "↑↓ 选择    ←→ 切换列表    Enter/Z 开始练习    Esc 返回",
            True, cfg.COLOR_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, 652))


# ---------------------------------------------------------------------------
# 启动练习
# ---------------------------------------------------------------------------

def launch_practice(game, entry, card_index):
    """从练习选择进入单符卡练习。"""
    from src.ui.menu import PlayingState
    stage, boss = build_practice_boss(entry, card_index)
    practice_stage = PracticeStage(stage, boss)
    info = {
        "entry": entry,
        "card_index": card_index,
        "card_name": entry["cards"][card_index]["name"],
        "last": entry["cards"][card_index]["last"],
    }
    game.switch_state(PlayingState(game, practice_stage, skip_title=True,
                                   practice_info=info))
