# -*- coding: utf-8 -*-
"""新官网（web-new/）本地预览服务。

用法：
    python web-new/serve.py          # 默认 8100 端口
    python web-new/serve.py 8200     # 指定端口

特点：
  · 以 web-new/ 为站点根
  · 页面 / 样式 / 脚本 / 数据带 no-cache：每次都回服务器确认，内容变了立刻可见，
    没变就是 304，不重复传输（no-store 会让浏览器每次翻页都重下字体，见下）
  · 字体给一段真实缓存期：否则翻页时 5.2MB 的中文字体要重下一遍，
    字体到位前文字先用回退字形，会看到一次字形跳变
  · 多线程，图鉴 / 曲目页的 fetch 不会被单线程阻塞
"""
import http.server
import os
import socketserver
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8100


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # 字体：给一段真实缓存期。中文字体有 5MB 级，若每次翻页都重下，
    # 会出现「文字先用回退字形渲染、字体到位后再跳一次」的观感。
    FONT_EXT = (".ttf", ".otf", ".woff", ".woff2")
    FONT_MAX_AGE = 600

    def end_headers(self):
        path = self.path.split("?")[0].split("#")[0].lower()
        if path.endswith(self.FONT_EXT):
            self.send_header("Cache-Control", "public, max-age=%d" % self.FONT_MAX_AGE)
        else:
            # no-cache 而不是 no-store：允许存下来，但每次使用前回服务器确认。
            # 内容没变就是 304（无响应体），改了立刻生效，两头都占。
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("端口必须是数字，收到：%s" % sys.argv[1])
            return 1

    url = "http://127.0.0.1:%d/" % port
    print("东方天空街 · 新官网预览")
    print("站点根目录：%s" % ROOT)
    print("地址：%s" % url)
    print("提示：请用 127.0.0.1 而不是 localhost，避免 IPv6 解析问题。")
    print("按 Ctrl+C 停止。\n")

    with Server(("127.0.0.1", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())