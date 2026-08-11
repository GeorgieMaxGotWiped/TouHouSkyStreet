# -*- coding: ascii -*-
import io

path = r'D:\pyz\my thingses\TouHou\src\ui\menu.py'
with io.open(path, 'r', encoding='utf-8') as f:
    src = f.read()

def rep(old, new):
    global src
    assert old in src, 'NOT FOUND: ' + repr(old[:80])
    src = src.replace(old, new, 1)

# 1) remove unused random import
rep('import os\nimport math\nimport random\nimport pygame\n',
    'import os\nimport math\nimport pygame\n')

# 2) __init__: drop title_alpha + star particles
old = '''        self.options = ["Start Game", "Practice", "Settings", "Quit"]
        self.selected = 0
        self.title_alpha = 0
        self.bg_stars = []
        for _ in range(40):
            self.bg_stars.append({
                "x": random.randint(0, cfg.SCREEN_WIDTH),
                "y": random.randint(0, cfg.SCREEN_HEIGHT),
                "speed": random.uniform(0.5, 2.0),
                "size": random.randint(1, 3),
            })
        # \u80cc\u666f\u56fe'''
new = '''        self.options = ["Start Game", "Practice", "Settings", "Quit"]
        self.selected = 0
        # \u80cc\u666f\u56fe'''
rep(old, new)

# 3) enter: drop title_alpha
rep('''    def enter(self, game):
        self.title_alpha = 0
        self.selected = 0''',
    '''    def enter(self, game):
        self.selected = 0''')

# 4) update: drop title_alpha + star movement
rep('''    def update(self, dt):
        self.title_alpha = min(255, self.title_alpha + 3)

        for star in self.bg_stars:
            star["y"] += star["speed"]
            if star["y"] > cfg.SCREEN_HEIGHT:
                star["y"] = 0
                star["x"] = random.randint(0, cfg.SCREEN_WIDTH)

        keys = self.game.keys_just_pressed''',
    '''    def update(self, dt):
        keys = self.game.keys_just_pressed''')

# 5) draw: normal brightness bg, no stars, no title lines, menu shifted +200
old = '''    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
            # \u6697\u8272\u906e\u7f69\u4fdd\u8bc1\u6587\u5b57\u53ef\u8bfb
            overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 20, 120))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill((4, 4, 16))

        for star in self.bg_stars:
            c = random.randint(80, 160)
            pygame.draw.circle(screen, (c, c, c + 40),
                               (int(star["x"]), int(star["y"])), star["size"])

        # \u6807\u9898
        title_font = self.game.font_huge
        title1 = title_font.render("\u4e1c\u65b9\u5929\u7a7a\u8857", True, cfg.COLOR_WHITE)
        title2 = self.game.font_medium.render("~ Touhou Sky Street ~", True, cfg.COLOR_GRAY)

        title1.set_alpha(self.title_alpha)
        title2.set_alpha(self.title_alpha)

        screen.blit(title1, (cfg.SCREEN_WIDTH // 2 - title1.get_width() // 2, 140))
        screen.blit(title2, (cfg.SCREEN_WIDTH // 2 - title2.get_width() // 2, 195))

        # \u526f\u6807\u9898
        sub = self.game.font_small.render("Based on Hypixel SkyBlock", True, cfg.COLOR_YELLOW)
        sub.set_alpha(self.title_alpha)
        screen.blit(sub, (cfg.SCREEN_WIDTH // 2 - sub.get_width() // 2, 230))

        # \u83dc\u5355\u9009\u9879
        start_y = 330
        for i, option in enumerate(self.options):
            color = cfg.COLOR_YELLOW if i == self.selected else cfg.COLOR_WHITE
            text = self.game.font_medium.render(option, True, color)

            x = cfg.SCREEN_WIDTH // 2 - text.get_width() // 2
            y = start_y + i * 44'''
new = '''    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((4, 4, 16))

        # \u83dc\u5355\u9009\u9879
        start_y = 330
        for i, option in enumerate(self.options):
            color = cfg.COLOR_YELLOW if i == self.selected else cfg.COLOR_WHITE
            text = self.game.font_medium.render(option, True, color)

            x = cfg.SCREEN_WIDTH // 2 - text.get_width() // 2 + 200
            y = start_y + i * 44'''
rep(old, new)

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(src)
print('PATCHED OK')