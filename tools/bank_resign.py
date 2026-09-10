#!/usr/bin/env python3
"""SC2 bank 重签工具（shw134 期沉淀）。

背景：bank 签名 = SHA1(authorID + playerID + bankName
    + Σ(按名排序的 section.name + Σ(按名排序的 key.name + "Value" + 类型名 + 值)))
algorithm 已破解并实测可复现引擎签名。bank 从一个作者目录复制到另一个作者目录后
必须用「目标目录的作者 toon」重签，否则引擎 BankVerify 失败、地图清档。

用法：
    python3 tools/bank_resign.py <bank.SC2Bank> <authorToon> <playerToon> [-o OUT] [--name BANKNAME]
示例（把原图存档迁到自己目录）：
    python3 tools/bank_resign.py MBank13.SC2Bank 5-S2-1-12307342 5-S2-1-12307342
不指定 -o 时原地覆盖；--name 缺省取文件名去扩展名——**工作副本文件名与真实 bank 名不一致时必须显式传 --name**（签名含 bankName，算错 = 白签）。签名算法对 'text' 类型不拼值、'nodes' 键不支持（本图用不到）。
"""
import hashlib
import sys
import xml.etree.ElementTree as ET


def calc_signature(root, bank_name, author, player):
    t = author + player + bank_name
    sections = sorted(root.iter("Section"), key=lambda s: s.get("name"))
    for sec in sections:
        t += sec.get("name")
        for key in sorted(sec.iter("Key"), key=lambda k: k.get("name")):
            val = key.find("Value")
            vtype = val.get("string") is not None and "string" or next(iter(val.attrib))
            t += key.get("name") + "Value" + vtype
            if vtype != "text":
                t += val.get(vtype) or ""
    return hashlib.sha1(t.encode("utf-8")).hexdigest().upper()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    path, author, player = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else path
    tree = ET.parse(path)
    root = tree.getroot()
    bank_name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if bank_name.endswith(".SC2Bank"):
        bank_name = bank_name[: -len(".SC2Bank")]
    sig = root.find("Signature")
    sig.set("value", calc_signature(root, bank_name, author, player))
    ET.indent(tree, space="    ")
    xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode")
    open(out, "w", encoding="utf-8").write(xml)
    # 回读自检
    back = ET.parse(out).getroot()
    assert back.find("Signature").get("value") == calc_signature(back, bank_name, author, player)
    print(f"OK {out}: {bank_name} signed as author={author} player={player}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
