# -*- coding: utf-8 -*-
# 物品系统验证：定义完整性 / 价格 / 掉落表 / C技能约束 / 效果聚合 / UI 渲染冒烟
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
import pygame
import tempfile
import shutil

sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg

tmpdir = tempfile.mkdtemp(prefix="items_test_")
cfg.WAREHOUSE_PATH = os.path.join(tmpdir, "warehouse.json")

from src.systems.item_system import (
    SKYBLOCK_ITEMS, C_SKILLS, REFORGE_STONES, REFORGES,
    BOSS_REWARD_POOLS, ItemInventory, ItemDropManager,
    init_default_drop_table, init_stage_drop_table, parse_price,
)
from src.systems.item_effects import aggregate_effects

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
os.makedirs("previews", exist_ok=True)

# --- 1. 表格 56 个物品全部存在且价格正确 ---
EXPECTED = {
    "aspect_of_the_jerry": ("COMMON", "weapon", "weapon", 300000, 60000),
    "undead_sword": ("COMMON", "weapon", "weapon", 800000, 200000),
    "sword_of_bad_health": ("UNCOMMON", "weapon", "weapon", 2000000, 500000),
    "bonzos_staff": ("RARE", "weapon", "weapon", 8000000, 2500000),
    "golem_sword": ("RARE", "weapon", "weapon", 5000000, 1500000),
    "aspect_of_the_end": ("RARE", "weapon", "weapon", 3000000, 900000),
    "arack": ("EPIC", "weapon", "weapon", 4000000, 1200000),
    "end_stone_sword": ("EPIC", "weapon", "weapon", 6000000, 2000000),
    "wither_cloak_sword": ("EPIC", "weapon", "weapon", 22000000, 7000000),
    "spirit_bow": ("EPIC", "weapon", "weapon", 10000000, 3500000),
    "aspect_of_the_dragons": ("LEGENDARY", "weapon", "weapon", 30000000, 12000000),
    "flower_of_truth": ("LEGENDARY", "weapon", "weapon", 25000000, 10000000),
    "giants_sword": ("LEGENDARY", "weapon", "weapon", 100000000, 40000000),
    "hyperion": ("LEGENDARY", "weapon", "weapon", 500000000, 200000000),
    "terminator": ("LEGENDARY", "weapon", "weapon", 650000000, 260000000),
    "dark_claymore": ("LEGENDARY", "weapon", "weapon", 150000000, 60000000),
    "lapis_armor_helmet": ("UNCOMMON", "armor", "helmet", 350000, 120000),
    "lapis_armor_chestplate": ("UNCOMMON", "armor", "chestplate", 1000000, 300000),
    "lapis_armor_leggings": ("UNCOMMON", "armor", "leggings", 2000000, 600000),
    "lapis_armor_boots": ("UNCOMMON", "armor", "boots", 300000, 100000),
    "heavy_armor_helmet": ("RARE", "armor", "helmet", 2000000, 700000),
    "heavy_armor_chestplate": ("RARE", "armor", "chestplate", 4000000, 1500000),
    "heavy_armor_leggings": ("RARE", "armor", "leggings", 3000000, 1100000),
    "heavy_armor_boots": ("RARE", "armor", "boots", 2500000, 900000),
    "wither_goggles": ("EPIC", "armor", "helmet", 18000000, 7000000),
    "shadow_assassin_boots": ("EPIC", "armor", "boots", 10000000, 4000000),
    "tarantula_helmet": ("EPIC", "armor", "helmet", 8000000, 3000000),
    "tarantula_boots": ("EPIC", "armor", "boots", 8000000, 3000000),
    "necromancer_lord_leggings": ("LEGENDARY", "armor", "leggings", 45000000, 18000000),
    "precursor_eye": ("LEGENDARY", "armor", "helmet", 35000000, 14000000),
    "superior_dragon_chestplate": ("LEGENDARY", "armor", "chestplate", 30000000, 12000000),
    "storms_leggings": ("LEGENDARY", "armor", "chestplate", 45000000, 18000000),
    "goldors_helmet": ("LEGENDARY", "armor", "chestplate", 50000000, 20000000),
    "necrons_chestplate": ("LEGENDARY", "armor", "chestplate", 75000000, 30000000),
    "maxors_boots": ("LEGENDARY", "armor", "chestplate", 40000000, 16000000),
    "balloon_snake": ("RARE", "accessory", "accessory", 5000000, 2000000),
    "maddox_batphone": ("RARE", "accessory", "accessory", 3000000, 1000000),
    "overflux_power_orb": ("RARE", "accessory", "accessory", 18000000, 7000000),
    "summoning_ring": ("RARE", "accessory", "accessory", 25000000, 10000000),
    "tarantula_pet": ("RARE", "accessory", "accessory", 3000000, 1000000),
    "enderman_pet_epic": ("EPIC", "accessory", "accessory", 10000000, 4000000),
    "spider_artifact": ("EPIC", "accessory", "accessory", 6000000, 2000000),
    "catacombs_expert_ring": ("EPIC", "accessory", "accessory", 30000000, 12000000),
    "scarfs_studies": ("LEGENDARY", "accessory", "accessory", 20000000, 8000000),
    "baby_yeti_pet": ("LEGENDARY", "accessory", "accessory", 50000000, 20000000),
    "ender_dragon_pet": ("LEGENDARY", "accessory", "accessory", 500000000, 200000000),
    "wither_relic": ("LEGENDARY", "accessory", "accessory", 300000000, 120000000),
    "necromancers_brooch": ("RARE", "reforge_stone", None, 1000000, 350000),
    "red_scarf": ("RARE", "reforge_stone", None, 3000000, 1000000),
    "dragons_claw": ("EPIC", "reforge_stone", None, 2000000, 700000),
    "wither_blood": ("EPIC", "reforge_stone", None, 3000000, 1000000),
    "precursor_gear": ("EPIC", "reforge_stone", None, 4000000, 1500000),
    "divans_alloy": ("LEGENDARY", "material", None, 500000000, 250000000),
    "necrons_handle": ("LEGENDARY", "material", None, 400000000, 200000000),
    "judgement_core": ("LEGENDARY", "material", None, 300000000, 150000000),
    "skyblock_coin": ("SPECIAL", "material", None, 0, 0),
}
for item_id, (rarity, itype, slot, buy, sell) in EXPECTED.items():
    item = SKYBLOCK_ITEMS.get(item_id)
    assert item is not None, f"missing item {item_id}"
    assert item.rarity == rarity, f"{item_id} rarity {item.rarity} != {rarity}"
    assert item.item_type == itype, f"{item_id} type {item.item_type} != {itype}"
    assert item.slot == slot, f"{item_id} slot {item.slot} != {slot}"
    assert item.buy_price == buy, f"{item_id} buy {item.buy_price} != {buy}"
    assert item.sell_price == sell, f"{item_id} sell {item.sell_price} != {sell}"
print(f"[1] {len(EXPECTED)} items verified")

# --- 2. C 技能元数据与唯一装备约束 ---
EXPECTED_C = {
    "sword_of_bad_health": 1, "bonzos_staff": 1, "golem_sword": 4,
    "aspect_of_the_end": 1, "end_stone_sword": 3, "wither_cloak_sword": 1,
    "spirit_bow": 1, "aspect_of_the_dragons": 1, "flower_of_truth": 2,
    "giants_sword": 1, "precursor_eye": 1, "overflux_power_orb": 1,
    "summoning_ring": 1, "enderman_pet_epic": 1, "tarantula_boots": 1,
}
for item_id, per_stage in EXPECTED_C.items():
    assert item_id in C_SKILLS, f"missing C skill {item_id}"
    assert C_SKILLS[item_id]["per_stage"] == per_stage, f"{item_id} per_stage mismatch"
inv = ItemInventory()
for iid in ("sword_of_bad_health", "bonzos_staff", "golem_sword"):
    inv.add_item(iid, 1)
ok, _ = inv.equip("sword_of_bad_health")
assert ok
ok, err = inv.equip("bonzos_staff")
assert ok, f"C skill swap failed: {err}"
assert inv.get_c_skill_equipped_id() == "bonzos_staff"
print("[2] C skill metadata + swap OK")

# --- 3. 效果聚合 ---
inv2 = ItemInventory()
for iid in ("lapis_armor_helmet", "lapis_armor_chestplate", "lapis_armor_leggings", "lapis_armor_boots"):
    inv2.add_item(iid, 1)
    inv2.equip(iid)
eff = aggregate_effects(inv2, 1)
assert eff["epic_drop_rate_mult"] == 1.2, f"lapis set {eff['epic_drop_rate_mult']}"
assert eff["coin_drop_pct"] == 5.0
assert eff["kill_small_coins"] == 80000
assert eff["kill_boss_coins"] == 10000000
assert eff["kill_midboss_coins"] == 5000000
print("[3a] lapis set effects OK")

inv3 = ItemInventory()
for iid in ("heavy_armor_helmet", "heavy_armor_chestplate", "heavy_armor_leggings", "heavy_armor_boots"):
    inv3.add_item(iid, 1)
    inv3.equip(iid)
eff = aggregate_effects(inv3, 1)
assert abs(eff["speed_pct"] - (-43.0)) < 0.001
assert eff["hit_cancel_chance"] == 43.0
assert eff["high_speed_pct"] == 20.0
print("[3b] heavy set effects OK")

inv4 = ItemInventory()
inv4.add_item("giants_sword", 1); inv4.equip("giants_sword")
inv4.add_item("precursor_gear", 1)
inv4.add_coins(10000)
ok, err = inv4.apply_reforge("giants_sword", "precursor_gear")
assert ok, f"reforge failed {err}"
eff = aggregate_effects(inv4, 3)
assert eff["damage_pct"] == 3.0, f"ancient {eff['damage_pct']}"
print("[3c] ancient reforge effects OK")

inv5 = ItemInventory()
inv5.add_item("maxors_boots", 1); inv5.equip("maxors_boots")
eff = aggregate_effects(inv5, 1)
assert eff["hitbox_scale"] == 0.5
assert eff["speed_pct"] == 25.0
inv5b = ItemInventory()
inv5b.add_item("superior_dragon_chestplate", 1); inv5b.equip("superior_dragon_chestplate")
eff = aggregate_effects(inv5b, 1)
assert eff["drop_rate_mult"] == 1.1
assert eff["damage_pct"] == 10.0
print("[3d] maxor/superior effects OK")

inv5c = ItemInventory()
inv5c.add_item("tarantula_helmet", 1); inv5c.equip("tarantula_helmet")
eff = aggregate_effects(inv5c, 1)
assert eff["end_lost_over1_bombs"] == 1
print("[3e] tarantula helmet effects OK")

# --- 4. 掉落表关键概率 ---
mgr = ItemDropManager()
init_default_drop_table(mgr)
for stage in range(1, 7):
    init_stage_drop_table(mgr, stage)
def chance_of(key, item_id):
    for e in mgr.drop_table.get(key, []):
        if e["item_id"] == item_id:
            return e["chance"]
    return None
assert chance_of("FairyEnemy", "aspect_of_the_jerry") == 0.05
assert chance_of("FairyEnemy", "skyblock_coin") == 0.20
assert chance_of("GuardEnemy", "baby_yeti_pet") == 0.04
assert chance_of("Boss", "divans_alloy") == 0.01
assert chance_of("MidBoss", "catacombs_expert_ring") == 0.05
assert chance_of("stage1_minion", "sword_of_bad_health") == 0.04
assert chance_of("stage1_final_boss", "arack") == 0.30
assert chance_of("stage1_midboss", "tarantula_boots") == 0.04
assert chance_of("stage1_midboss", "tarantula_helmet") == 0.04
assert chance_of("stage1_final_boss", "tarantula_boots") == 0.18
assert chance_of("stage1_final_boss", "tarantula_helmet") == 0.18
assert chance_of("stage2_any", "aspect_of_the_end") == 0.02
assert chance_of("stage2_any", "judgement_core") == 0.002
assert chance_of("stage2_midboss", "golem_sword") == 1.0
assert chance_of("stage2_final_boss", "aspect_of_the_dragons") == 0.30
assert chance_of("stage3_any", "wither_cloak_sword") == 0.01
assert chance_of("stage3_final_boss", "bonzos_staff") == 0.12
assert chance_of("stage4_midboss", "scarfs_studies") == 1.0
assert chance_of("stage4_midboss", "red_scarf") == 0.80
assert chance_of("stage4_terracotta", "flower_of_truth") == 0.03
assert chance_of("stage4_final_boss", "flower_of_truth") == 0.60
assert chance_of("stage5_midboss_livid", "shadow_assassin_boots") == 1.0
assert chance_of("stage5_midboss_thorn", "spirit_bow") == 0.10
assert chance_of("stage5_boss", "precursor_gear") == 0.15
assert chance_of("stage5_final_boss", "hyperion") == 0.05
assert chance_of("stage5_final_boss", "necrons_handle") == 0.05
assert chance_of("stage5_final_boss", "wither_blood") == 0.15
assert chance_of("stage6_minion", "wither_blood") == 0.05
assert chance_of("stage6_final_boss", "dark_claymore") == 0.50
assert chance_of("stage6_final_boss", "necrons_handle") == 0.10
assert BOSS_REWARD_POOLS == {
    1: ["arack", "spider_artifact", "tarantula_pet", "aspect_of_the_jerry"],
    2: ["aspect_of_the_dragons", "ender_dragon_pet", "superior_dragon_chestplate", "dragons_claw"],
    3: ["bonzos_staff", "balloon_snake", "necromancers_brooch", "wither_cloak_sword"],
    4: ["giants_sword", "summoning_ring", "necromancer_lord_leggings", "precursor_eye"],
    5: ["storms_leggings", "goldors_helmet", "necrons_chestplate", "maxors_boots"],
    6: ["hyperion", "terminator", "dark_claymore", "necrons_handle"],
}
# 奖励池物品必须都存在于物品表
for _pool in BOSS_REWARD_POOLS.values():
    for _pid in _pool:
        assert _pid in SKYBLOCK_ITEMS, f"reward pool has unknown item: {_pid}"
print("[4] drop tables verified")

# --- 5. PlayingState 冒烟：装备 + C 技能释放 ---
from src.engine.game import Game
from src.stages.stage1 import Stage1_SkyblockHub
from src.ui.menu import PlayingState

g = Game()
run = ItemInventory()
for iid, count in (("sword_of_bad_health", 1), ("hyperion", 1), ("terminator", 1)):
    run.add_item(iid, count)
run.equip("sword_of_bad_health")
run.coins = 12345
run.save_to_global_data(g.global_data)

stage = Stage1_SkyblockHub()
stage.setup_waves()
ps = PlayingState(g, stage)
assert ps.c_skill_id == "sword_of_bad_health"
assert ps.lives == cfg.PLAYER_START_LIVES
# 触发 C 技能（Sword of Bad Health：消耗1残机）
ps._use_c_skill()
assert ps.lives == cfg.PLAYER_START_LIVES - 1, f"lives {ps.lives}"
assert ps.bad_health_timer > 0
assert ps.c_uses.get("sword_of_bad_health") == 1
# 本面已用完
ps._use_c_skill()
assert ps.c_uses.get("sword_of_bad_health") == 1
# 更换装备后 C 技能变更
run.add_item("golem_sword", 1)
run.unequip_item("sword_of_bad_health")
run.equip("golem_sword")
ps.c_skill_id = "golem_sword"
ps.c_uses = {"golem_sword": 0}
ps._c_golem_sword()
assert ps.c_uses.get("golem_sword", 0) == 0  # 直接调用 handler 不计数
ps._use_c_skill()
assert ps.c_uses.get("golem_sword") == 1
# 其它 C 技能冒烟
for handler_name in (
    "_c_bonzos_staff", "_c_wither_cloak_sword", "_c_spirit_bow",
    "_c_precursor_eye", "_c_summoning_ring", "_c_flower_of_truth",
    "_c_overflux_power_orb", "_c_aspect_of_the_end",
):
    ps.c_skill_id = "golem_sword"
    ok = getattr(ps, handler_name)()
    if handler_name == "_c_overflux_power_orb":
        assert ok is False, "overflux orb should require boss fight"
    else:
        assert ok is not False, f"{handler_name} returned False"

# Tarantula Boots：清除移动方向最近的1个弹幕并瞬移至其位置
from src.entities.bullet import Bullet
ps.bullet_manager.enemy_bullets.clear()
run.add_item("tarantula_boots", 1)
run.unequip_item("golem_sword")
run.equip("tarantula_boots")
ps.c_skill_id = "tarantula_boots"
ps.c_uses = {"tarantula_boots": 0}
ps.player.vx = 0.0
ps.player.vy = 0.0
assert ps._c_tarantula_boots() is False, "no bullet ahead should fail"
assert ps.c_uses.get("tarantula_boots") == 0
tb = Bullet(ps.player.x, ps.player.y - 100, 0, 0)
ps.bullet_manager.enemy_bullets.append(tb)
tx = max(cfg.PLAY_AREA_LEFT, min(cfg.PLAY_AREA_RIGHT, tb.x))
ty = max(cfg.PLAY_AREA_TOP, min(cfg.PLAY_AREA_BOTTOM, tb.y))
ps._use_c_skill()
assert tb.cancel_timer > 0
assert ps.player.x == tx
assert ps.player.y == ty
assert ps.c_uses.get("tarantula_boots") == 1

ps.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_playing_cskill_preview.png"))
print("[5] PlayingState + C skill smoke OK")

# --- 6. UI 渲染冒烟：休整商店分类 / 三选一价格 ---
from src.ui.intermission import IntermissionState
from src.ui.boss_reward import BossRewardState

it = IntermissionState(g, 1)
it.page_idx = 2  # 商店
entries = it._current_shop_entries()
assert any(e.get("header") for e in entries), "shop has no category headers"
assert entries[0].get("header") == "武器"
it.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_intermission_shop_preview.png"))

br = BossRewardState(g, 2, BOSS_REWARD_POOLS[2])
br.offer = [SKYBLOCK_ITEMS[i] for i in BOSS_REWARD_POOLS[2][:3]]
br.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_boss_reward_price_preview.png"))

# 五面/六面奖励池渲染冒烟
for _sn in (5, 6):
    _br = BossRewardState(g, _sn, BOSS_REWARD_POOLS[_sn])
    assert len(_br.offer) == 3, f"stage {_sn} reward offers 3 items"
    _br.draw(screen)
    pygame.image.save(screen, os.path.join("previews", f"_boss_reward_stage{_sn}_preview.png"))
print("[6] UI render smoke OK")

pygame.quit()
shutil.rmtree(tmpdir, ignore_errors=True)
print("ALL ITEM TESTS PASSED")
