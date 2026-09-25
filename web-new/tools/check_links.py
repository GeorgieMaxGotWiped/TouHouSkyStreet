# -*- coding: utf-8 -*-
"""检查 web-new/ 里所有本地引用的资源是否真的存在。

用法（在项目根目录执行）：
    python web-new/tools/check_links.py

会检查：
  · 每个 HTML 里的 src= / href= / style 内的 url(...)
  · css 里的 url(...)
  · data/*.json 里的图片路径
跳过 http(s) / 协议相对 / mailto / 纯锚点 / data: 这类外部引用。
退出码为 0 表示全部通过，1 表示有缺失。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # = web-new/
HTML_ATTR = re.compile(r'(?:src|href)\s*=\s*"([^"]+)"')
CSS_URL = re.compile(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)')
JSON_IMG = re.compile(r'"([^"]*assets/[^"]+)"')


def is_external(ref):
    return (ref.startswith(("http://", "https://", "//", "mailto:", "data:", "javascript:"))
            or ref.startswith("#") or ref == "")


def check(ref, base_dir, origin):
    if is_external(ref):
        return None
    target = ref.split("#")[0].split("?")[0]
    if not target:
        return None
    if target.startswith("/"):
        # 站点根的绝对路径：当作相对 web-new/ 处理
        path = os.path.join(ROOT, target.lstrip("/"))
    else:
        path = os.path.normpath(os.path.join(base_dir, target))
    if os.path.exists(path):
        return None
    return (origin, ref, os.path.relpath(path, ROOT).replace("\\", "/"))


def main():
    problems = []
    checked = 0

    for name in sorted(os.listdir(ROOT)):
        if not name.endswith((".html", ".htm")):
            continue
        path = os.path.join(ROOT, name)
        text = open(path, encoding="utf-8").read()
        refs = set(HTML_ATTR.findall(text))
        refs |= set(m for m in CSS_URL.findall(text) if "assets" in m)
        for ref in refs:
            checked += 1
            bad = check(ref, ROOT, name)
            if bad:
                problems.append(bad)

    css_dir = os.path.join(ROOT, "css")
    if os.path.isdir(css_dir):
        for name in sorted(os.listdir(css_dir)):
            if not name.endswith(".css"):
                continue
            text = open(os.path.join(css_dir, name), encoding="utf-8").read()
            for ref in set(CSS_URL.findall(text)):
                checked += 1
                bad = check(ref, css_dir, "css/" + name)
                if bad:
                    problems.append(bad)

    data_dir = os.path.join(ROOT, "data")
    if os.path.isdir(data_dir):
        for name in sorted(os.listdir(data_dir)):
            if not name.endswith(".json"):
                continue
            text = open(os.path.join(data_dir, name), encoding="utf-8").read()
            try:
                json.loads(text)
            except Exception as exc:
                problems.append(("data/" + name, "<JSON 解析失败>", str(exc)))
                continue
            for ref in set(JSON_IMG.findall(text)):
                checked += 1
                bad = check(ref, ROOT, "data/" + name)
                if bad:
                    problems.append(bad)

    print("检查了 %d 条本地引用。" % checked)
    if not problems:
        print("全部通过：没有缺失的文件。")
        return 0

    print("\n发现 %d 处缺失：" % len(problems))
    for origin, ref, resolved in problems:
        print("  %-24s %-46s -> 找不到 %s" % (origin, ref, resolved))
    return 1


if __name__ == "__main__":
    sys.exit(main())