#!/usr/bin/env python3
"""2D 立牌 m3 的自动化崩溃探针（二分用）。

    python3 tools/sprite_probe.py --label ctrl-nailong --no-sprite     # 对照：真奶龙
    python3 tools/sprite_probe.py --label v1-safe --no-billboard       # 变体：不带 BBSC
    python3 tools/sprite_probe.py --label v2-bbsc --billboard 6

流程：重出 data/BHSprite.m3 →（--sprite-poc）打包 → sc2run 启动 → 轮询 GameLogs 有没有新的
Crash 目录。CustomLogic 里有一个临时探针（c_bhSoloBuild 时 t=0 就 CreateModelAtPoint("Nailong")），
所以模型数据有问题会**在开局几秒内**崩，不必等 gt_CreatePlayers_Func（实测要等 1.5–6 分钟）。

判据：出现新的 `*Crash` 目录 = 引擎拒收该模型数据（日志里会有 `Erroneous custom model data`）。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "administrator@100.94.140.84"
PORT = "2222"
SSH = ["ssh", "-p", PORT, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", HOST]
GAMELOGS = "/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs"


def run_ssh(cmd: str, timeout: int = 90) -> str:
    proc = subprocess.run([*SSH, cmd], capture_output=True, timeout=timeout)
    return (proc.stdout + proc.stderr).decode("utf-8", errors="replace")


def crash_dirs() -> list[str]:
    out = run_ssh(f"ls -1 '{GAMELOGS}' 2>/dev/null | grep -i crash || true")
    return [line.strip() for line in out.splitlines() if line.strip()]


def game_alive() -> bool:
    out = run_ssh('/mnt/c/Windows/System32/tasklist.exe /FO CSV /NH 2>/dev/null '
                  '| grep -i SC2_x64 || true')
    return "SC2_x64" in out


def report(labels: list[str]) -> int:
    """只读最新 Alerts.txt，按模型路径报告每个探针变体是否被引擎拒收。"""
    alerts = run_ssh(f'ls -1t {GAMELOGS}/*Alerts.txt 2>/dev/null | head -1 | '
                     'xargs -r cat || true')
    bad = set()
    for line in alerts.splitlines():
        if 'Unable to create this model' in line and 'Probe' in line:
            bad.add(line.split('Probe')[-1].split('\\')[0].split('.')[0].lower())

    print(f'最新 Alerts.txt 判读（{"、".join(labels)}）:')
    for label in labels:
        verdict = '✗ fallback' if label.lower() in bad else '✓ 建出模型'
        print(f'  {label:>3}  {verdict}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="probe")
    ap.add_argument("--no-sprite", action="store_true", help="对照：用真奶龙模型（不换 m3）")
    ap.add_argument("--wait", type=int, default=300, help="最多等多少秒（含地图加载）")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--pack", action="store_true", help="构建后用 --sprite-poc（默认开）")
    ap.add_argument("--report", default=None, help="只读日志报告这些标签（逗号分隔）")
    args, rest = ap.parse_known_args()

    if args.report:
        return report([x.strip() for x in args.report.split(',') if x.strip()])

    if not args.label:
        ap.error('--label 必填（--report 模式除外）')

    before = set(crash_dirs())
    m3 = ROOT / "data" / "BHSprite.m3"
    probe_map = ROOT / "work" / f"probe-{args.label}.SC2Map"

    if not args.no_sprite:
        cmd = [sys.executable, "tools/m3_sprite.py", "--out", str(m3),
               "--texture", "/BHSprite.dds", *rest]
        print("$", " ".join(cmd[1:]))
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            return 1

    if not args.skip_build:
        cmd = [sys.executable, "tools/boot2_build.py", "--out", str(probe_map), "--solo"]
        if not args.no_sprite:
            cmd.append("--sprite-poc")
        print("$", " ".join(cmd[1:]))
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            return 1

    name = f"probe{args.label}"
    cmd = [sys.executable, "tools/sc2run.py", str(probe_map), "--kill", "--name", name]
    print("$", " ".join(cmd[1:]))
    subprocess.run(cmd, cwd=ROOT)

    started = time.time()
    verdict = "timeout"
    while time.time() - started < args.wait:
        time.sleep(15)
        new = set(crash_dirs()) - before
        if new:
            verdict = "crash"
            print(f"\n✗ 崩溃（{int(time.time() - started)} 秒后）: {sorted(new)}")
            for d in sorted(new):
                ctx = run_ssh(f'grep -a "FunctionContext\\|Erroneous" "{GAMELOGS}/{d}/"*.txt '
                              '| head -8 || true')
                print(ctx.strip()[:600])
            break
        if not game_alive():
            verdict = "exited"
            print(f"\n? 进程已退出但没有 Crash 目录（{int(time.time() - started)} 秒）——"
                  "可能被人关掉，或崩溃上报被禁用")
            break

    # 「没有崩」不等于「模型建出来了」：引擎会用 fallback 模型替换并往 Alerts.txt 写一行
    # USER ... CActorModel[...] Model <路径>; Unable to create this model.
    alerts = run_ssh(f'ls -1t {GAMELOGS}/*Alerts.txt 2>/dev/null | head -1 | xargs -r cat '
                     '| grep -a "BHSprite2D" | tail -3 || true')
    fallback = "Unable to create this model" in alerts

    if verdict == "timeout" and not fallback:
        print(f"\n✓ 无崩溃、也没有 fallback：引擎接受并成功建出这份模型数据")

    if fallback:
        print("\n✗ 模型没建出来（引擎用 fallback 顶替）：")
        print(alerts.strip()[:400])

    print(f"[{args.label}] 判定 = {verdict}" + ("（fallback）" if fallback else ""))
    return 0 if (verdict == "timeout" and not fallback) else 1


if __name__ == "__main__":
    raise SystemExit(main())
