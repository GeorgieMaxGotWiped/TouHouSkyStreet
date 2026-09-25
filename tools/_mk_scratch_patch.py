import io
old = "line1\n\nline3\n"
new = "ok\n"
for tag, blank in (("dash-only", ""), ("dash-space", " ")):
    body = []
    for ln in old.splitlines():
        body.append("-" + (ln if ln else blank) + "\n")
    for ln in new.splitlines():
        body.append("+" + ln + "\n")
    txt = "*** Begin Patch\n*** Update File: tools/_scratch_a.py\n@@\n" + "".join(body) + "*** End Patch\n"
    io.open("tools/_patch_scratch_%s.txt" % tag, "w", encoding="utf-8", newline="\n").write(txt)
print("ok")
