# -*- coding: utf-8 -*-
"""本站本地开发服务器（多线程，避免 python -m http.server 并发卡顿）。

用法：
    python web/serve.py            # 默认 http://127.0.0.1:8000
    python web/serve.py 8080       # 指定端口
"""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

# 以 web/ 为站点根目录
ROOT = __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0] or "."
if ROOT:
    import os
    os.chdir(ROOT)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler)
    print("站点已启动： http://127.0.0.1:%d" % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
