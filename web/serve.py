# -*- coding: utf-8 -*-
"""本站本地预览服务器：多线程 + 自动挑选空闲端口 + 自动打开浏览器。

用法：
    python web/serve.py            # 从 8000 起挑一个空闲端口
    python web/serve.py 8080       # 指定起始端口
启动后会自动在默认浏览器打开本站。
"""
import os
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"  # 仅本机访问；用 127.0.0.1 而非 localhost，规避 IPv6 解析问题
START_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


def make_server(host, start, tries=40):
    """在 [start, start+tries) 里找到可用端口并绑定。"""
    for port in range(start, start + tries):
        try:
            return ThreadingHTTPServer((host, port), SimpleHTTPRequestHandler), port
        except OSError:
            continue
    raise SystemExit("未找到可用端口。")


def open_browser(url):
    time.sleep(0.8)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    # 以脚本所在目录（web/）为站点根，脚本可能以相对或绝对路径启动
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server, port = make_server(HOST, START_PORT)
    url = "http://%s:%d" % (HOST, port)
    print("站点已启动： %s （关闭此窗口或 Ctrl+C 停止）" % url, flush=True)
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。", flush=True)
