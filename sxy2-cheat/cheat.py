#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
属性与生活2 (com.SmmGame.SXYSH2) 存档修改器 —— MIUI 本地备份方案

原理：
  1. 手机「备份与恢复」导出的 .zip 内含 MIUI 备份包 (.bak)
  2. .bak = MIUI 头 + "ANDROID BACKUP\n5\n0\nnone\n" + tar
  3. 存档就是 tar 里的 shared_prefs PlayerPrefs XML（明文）
  4. 原地改写 XML（保持字节长度不变），重新打包，推回手机，用系统「恢复」写回

不改 APK、不需要 root。

用法见 README.md
"""

import argparse
import datetime
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

PKG = "com.SmmGame.SXYSH2"
PREFS_PATH = f"apps/{PKG}/sp/{PKG}.v2.playerprefs.xml"
ANDROID_BACKUP_MARK = b"ANDROID BACKUP\n"
BACKUP_DIR = "/sdcard/MIUI/backup/AllBackup"
MIRROR = "https://mirrors.cloud.tencent.com/AndroidSDK/platform-tools-latest-windows.zip"

# 默认「全满」配置
DEFAULT_CHANGES = {
    "Money": "999999999",
    "MyBalance": "999999999",
    "Coding": "9999",
    "Art": "9999",
    "Music": "9999",
    "Action": "9999",
    "Cham": "9999",
    "BasicCham": "9999",
    "Healthy": "100",
    "Plan": "9999",
    "Fans": "9999",
    "MaxCoding": "9999",
    "MaxArt": "9999",
    "MaxMusic": "9999",
    "MaxAction": "9999",
    "MaxPlan": "9999",
}

ATTR_KEYS = ["Coding", "Art", "Music", "Action", "Cham", "BasicCham", "Healthy", "Plan", "Fans"]

HERE = os.path.dirname(os.path.abspath(__file__))

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg=""):
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((str(msg) + "\n").encode("utf-8", "replace"))


def die(msg, code=1):
    log("错误: " + str(msg))
    sys.exit(code)


# ---------- 读取备份 ----------

def read_backup(path):
    """返回 (bak_bytes, descript_xml 或 None, 原始 bak 文件名)"""
    if path.lower().endswith(".bak"):
        return open(path, "rb").read(), None, os.path.basename(path)
    if not zipfile.is_zipfile(path):
        die("不是有效的备份文件（.zip 或 .bak）: " + path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        baks = [n for n in names if n.lower().endswith(".bak")]
        if not baks:
            die("备份 zip 里没有 .bak 文件")
        if len(baks) > 1:
            log("警告: 备份含多个应用，默认处理第一个: " + baks[0])
        descript = z.read("descript.xml") if "descript.xml" in names else None
        return z.read(baks[0]), descript, baks[0]


def tar_offset(bak):
    pos = bak.find(ANDROID_BACKUP_MARK)
    if pos < 0:
        die("未找到 ANDROID BACKUP 头，可能不是 MIUI 备份或无数据")
    cur = pos + len(ANDROID_BACKUP_MARK)
    lines = []
    for _ in range(3):  # version, compressed, encryption
        end = bak.index(b"\n", cur)
        lines.append(bak[cur:end].decode("ascii", "replace"))
        cur = end + 1
    if lines[0] not in ("1", "2", "3", "4", "5"):
        die("未知的 Android backup 版本: " + lines[0])
    if lines[1] == "1":
        die("该备份是压缩格式，暂不支持")
    if lines[2] != "none":
        die("该备份已加密，无法处理")
    return cur


def find_entry(bak, tar_start, target):
    pos = tar_start
    while pos + 512 <= len(bak):
        block = bak[pos:pos + 512]
        if block == b"\0" * 512:
            break
        name = block[0:100].split(b"\0")[0]
        size = int((block[124:136].split(b"\0")[0].strip() or b"0"), 8)
        typ = block[156:157]
        if name == target and typ in (b"0", b"\0"):
            return pos + 512, size
        pos += 512 + ((size + 511) // 512) * 512
    die("备份里找不到游戏存档文件（可能备份不完整）")


def read_prefs(bak):
    start = tar_offset(bak)
    off, size = find_entry(bak, start, PREFS_PATH.encode())
    return bak[off:off + size], off, size


def parse_values(xml_bytes):
    text = xml_bytes.decode("utf-8", "replace")
    return dict(re.findall(r'name="([^"]+)" value="([^"]*)"', text))


# ---------- 改写 ----------

def build_xml(original, changes, slot_size):
    text = re.sub(r">\s+<", "><", original.decode("utf-8")).strip()
    report = []
    for key, val in changes.items():
        pat = re.compile(r'(name="%s" value=")(-?\d+)(")' % re.escape(key))
        m = pat.search(text)
        if not m:
            report.append((key, None, val))
            continue
        report.append((key, m.group(2), val))
        text = text[:m.start(2)] + str(val) + text[m.end(2):]
    new = text.encode("utf-8")
    if len(new) > slot_size:
        die(f"改写后 XML 超出原大小（{len(new)} > {slot_size}），请减少修改项")
    pad = slot_size - len(new)
    if pad:
        idx = new.rfind(b"</map>")
        if idx < 0:
            die("XML 结构异常，缺少 </map>")
        new = new[:idx] + b" " * pad + new[idx:]
    return new, report


def patch(bak_path, out_bak, changes):
    bak = bytearray(open(bak_path, "rb").read())
    original, off, size = read_prefs(bytes(bak))
    new, report = build_xml(original, changes, size)
    if len(new) != size:
        die("内部错误: 长度不一致")
    bak[off:off + size] = new
    with open(out_bak, "wb") as f:
        f.write(bak)
    return report


def make_zip(src_zip, patched_bak, out_zip):
    with zipfile.ZipFile(src_zip) as z:
        names = z.namelist()
        descript = z.read("descript.xml") if "descript.xml" in names else None
        bak_name = [n for n in names if n.lower().endswith(".bak")][0]
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        if descript is not None:
            z.writestr("descript.xml", descript)
        z.write(patched_bak, bak_name, zipfile.ZIP_DEFLATED)


# ---------- adb ----------

def find_adb(explicit=None):
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("ADB"):
        cands.append(os.environ["ADB"])
    cands.append(os.path.join(HERE, "tools", "platform-tools", "adb.exe"))
    cands.append(os.path.join(HERE, "tools", "platform-tools", "adb"))
    w = shutil.which("adb")
    if w:
        cands.append(w)
    for c in cands:
        if c and os.path.isfile(c):
            return c
    die("找不到 adb。先运行: py cheat.py setup-adb  或设置环境变量 ADB")


def adb_run(adb, *args, check=True):
    p = subprocess.run([adb] + [str(a) for a in args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    if check and p.returncode != 0 and "daemon" not in err:
        die("adb 失败: " + (err.strip() or out.strip()))
    return out, err, p.returncode


def ensure_device(adb):
    out, _, _ = adb_run(adb, "devices", check=False)
    lines = [l for l in out.splitlines()[1:] if l.strip()]
    ready = [l for l in lines if l.endswith("device")]
    if not ready:
        die("没有已授权的设备。请连接手机并允许 USB 调试。\n" + out)
    return ready[0].split()[0]


# ---------- 命令 ----------

def cmd_setup_adb(args):
    dest = os.path.join(HERE, "tools")
    os.makedirs(dest, exist_ok=True)
    zip_path = os.path.join(dest, "platform-tools.zip")
    log("下载 platform-tools（腾讯镜像）...")
    req = urllib.request.Request(MIRROR, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(zip_path, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    os.remove(zip_path)
    adb = os.path.join(dest, "platform-tools", "adb.exe")
    if not os.path.isfile(adb):
        die("解压后没有找到 adb.exe")
    log("完成: " + adb)


def cmd_inspect(args):
    bak, _, _ = read_backup(args.backup)
    xml, _, _ = read_prefs(bak)
    vals = parse_values(xml)
    keys = ["Money", "MyBalance", "Coding", "Art", "Music", "Action", "Cham",
            "BasicCham", "Healthy", "Plan", "Fans", "Year", "Month", "Day"]
    log("=== 当前存档 ===")
    for k in keys:
        if k in vals:
            log(f"  {k:12s} = {vals[k]}")
    log(f"PlayerPrefs 条目数: {len(vals)}")


def cmd_patch(args):
    bak, _, bak_name = read_backup(args.backup)
    changes = dict(DEFAULT_CHANGES) if not args.no_defaults else {}
    if args.money is not None:
        changes["Money"] = str(args.money)
        changes["MyBalance"] = str(args.money)
    if args.attrs is not None:
        for k in ATTR_KEYS:
            changes[k] = str(args.attrs)
    for kv in args.set or []:
        if "=" not in kv:
            die("--set 格式应为 KEY=VALUE: " + kv)
        k, v = kv.split("=", 1)
        changes[k.strip()] = v.strip()

    tmp_bak = os.path.join(os.path.dirname(os.path.abspath(args.output)), "_patched.bak")
    report = patch_content(bak, tmp_bak, changes)

    out = args.output
    if out.lower().endswith(".bak"):
        shutil.move(tmp_bak, out)
    else:
        if not args.backup.lower().endswith(".zip"):
            die("从 .bak 输入生成 .zip 需要原始备份 .zip 提供 descript.xml；请用 .zip 作为输入")
        make_zip(args.backup, tmp_bak, out)
        os.remove(tmp_bak)

    log("=== 修改结果 ===")
    for key, old, new in report:
        if old is None:
            log(f"  {key:12s} 未找到，跳过")
        else:
            log(f"  {key:12s} {old} -> {new}")
    log("输出: " + out)


def patch_content(bak, out_bak, changes):
    tmp = bytearray(bak)
    original, off, size = read_prefs(bytes(tmp))
    new, report = build_xml(original, changes, size)
    tmp[off:off + size] = new
    open(out_bak, "wb").write(bytes(tmp))
    return report


def cmd_push(args):
    adb = find_adb(args.adb)
    ensure_device(adb)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    remote = f"{BACKUP_DIR}/{ts}.zip"
    log("推送 -> " + remote)
    adb_run(adb, "push", args.zip, remote)
    log("已推送。请在手机「备份与恢复 → 恢复」中选择该备份并恢复。")
    if args.open:
        adb_run(adb, "shell", "am", "start", "-a", "miui.intent.backup.LOCAL_HOME_ACTIVITY", check=False)
        log("已在手机上打开备份页面。")


def cmd_apply(args):
    adb = find_adb(args.adb)
    ensure_device(adb)
    tmp = os.path.join(os.path.dirname(os.path.abspath(args.backup)), "_apply.zip")
    ns = argparse.Namespace(backup=args.backup, output=tmp, money=args.money,
                            attrs=args.attrs, set=args.set, no_defaults=args.no_defaults)
    cmd_patch(ns)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    remote = f"{BACKUP_DIR}/{ts}.zip"
    log("推送 -> " + remote)
    adb_run(adb, "push", tmp, remote)
    os.remove(tmp)
    adb_run(adb, "shell", "am", "start", "-a", "miui.intent.backup.LOCAL_HOME_ACTIVITY", check=False)
    log("完成。请在手机备份页面点「恢复」，选择最新备份并勾选游戏。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="属性与生活2 存档修改器（MIUI 备份方案）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup-adb", help="下载并解压 platform-tools 到 tools/")
    p.set_defaults(func=cmd_setup_adb)

    p = sub.add_parser("inspect", help="查看备份里的当前数值")
    p.add_argument("backup")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("patch", help="生成修改后的备份 zip")
    p.add_argument("backup")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--money", type=int)
    p.add_argument("--attrs", type=int)
    p.add_argument("--set", action="append")
    p.add_argument("--no-defaults", action="store_true", help="不套用默认全满配置")
    p.set_defaults(func=cmd_patch)

    p = sub.add_parser("push", help="把改好的 zip 推到手机")
    p.add_argument("zip")
    p.add_argument("--adb")
    p.add_argument("--open", action="store_true", help="推送后打开备份页面")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("apply", help="patch + push + 打开恢复页面 一条龙")
    p.add_argument("backup")
    p.add_argument("--money", type=int)
    p.add_argument("--attrs", type=int)
    p.add_argument("--set", action="append")
    p.add_argument("--no-defaults", action="store_true")
    p.add_argument("--adb")
    p.set_defaults(func=cmd_apply)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
