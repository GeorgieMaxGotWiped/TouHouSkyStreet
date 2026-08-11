import sys; sys.path.insert(0, r'D:\pyz\my thingses\TouHou')
from src.engine.game import Game
from src.engine import settings as cfg
import os
g = Game()
print(f'Window: {cfg.SCREEN_WIDTH}x{cfg.SCREEN_HEIGHT}')
print(f'Battle: {cfg.BATTLE_AREA_WIDTH}x{cfg.BATTLE_AREA_HEIGHT}')
print(f'Offset: ({cfg.BATTLE_OFFSET_X},{cfg.BATTLE_OFFSET_Y})')
print(f'Panel: x={cfg.PANEL_LEFT} w={cfg.PANEL_WIDTH}')
print(f'BG exists: {os.path.exists(cfg.MENU_BACKGROUND)}')
print(f'Surface: {g.screen.get_width()}x{g.screen.get_height()}')
pygame.quit()