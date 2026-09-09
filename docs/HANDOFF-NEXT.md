# 交接文档：自设面板「添加」按钮问题（2026-09-09 夜）

> **给下一个会话的第一份读物。** 先读这份，再读 `AGENTS.md` 与 `docs/ROLE-PIPELINE.md`。
> 上一份影武者交接（含池 3/18 误判等根因分析）在 `docs/HANDOFF-SHADOW.md`，仍有效。

---

## 一、用户当前要求（原话）

> 「不行，我还是感觉你没找对地方，依旧请你 reset 到一个这个添加按钮还能用的地方，我准备重开会话了」
> 「这里面板不能绕开，因为面板是一个常用的基础逻辑」

**结论：用户认为「自设 → 选中角色 → 添加」这条基础路径必须能用；此前所有绕过方案（自动注入、测试构建特判）都不可接受。**
**已按用户要求 reset。**

---

## 二、当前仓库状态

| 项 | 值 |
|---|---|
| 当前 HEAD | `d80a6e7`（**影武者改动之前的最后一个提交**） |
| 该提交内容 | 烙印变体 + 变体菜单清理 + 原图面板**完全未改动** |
| 已部署地图 | `D:\StarCraft II\Maps\Test\boot2-clean-add.SC2Map`（= d80a6e7） |
| 对照地图 | `D:\StarCraft II\Maps\Test\boot2-pristine.SC2Map`（= `dcb0f59` 初始提交，**完全原始**） |
| 备份分支 | `backup/shw45-mess`（影武者全部工作 + 所有修复尝试）、`backup/shadow-mess-20260909`（更早的乱改动） |
| 基线地图 | `work/boot2-user.SC2Map`（用户的地图，**不要覆盖**） |

**下一步第一件事：让用户在游戏里打开 `boot2-pristine.SC2Map`，试「自设 → 选角色 → 添加」。**
- 如果**原始版也不能添加** → 问题在 Test Document 的大厅属性为空（不是任何代码改动造成的），应改为**用真实大厅开局**验证，或先解决大厅属性。
- 如果**原始版可以添加** → 用 `git bisect` 在 `dcb0f59..backup/shw45-mess` 之间二分，找出第一个让按钮失效的提交。

---

## 三、已排查但**未解决**的线索（避免重复劳动）

用户反馈的报错（截图为证）：

| 报错 | 位置 | 我的处理 | 是否解决 |
|---|---|---|---|
| `DialogControlSelectItem` 参数超出界限（值：-1） | `gt_OSMenus_Func` 86305 / `gt_OSVariantsMenuConfirm_Func` 84687–84689 | 删除全库 10 处「空列表上 SelectItem(...,0)」冗余调用 | ❌ 无效 |
| `DialogControlSetPropertyAsBool` 无法获取 `triggerControl`（值：0） | `gt_OSVariantsMenuConfirm_Func` 84669/84672 | 未处理（怀疑是控件未创建） | ❌ 无效 |
| `StringWord` 无法获取 `str`（值：0） | `gt_Init2_Func` 56167（读银行 `Blacklist`） | 给 21 处银行字符串加 null 保护 | ❌ 无效 |
| `不正确的类型（不允许进行隐式强制转换）` | `gf_SequenceKills` 12781 | `gv_name[...]` → `StringToText(gv_name[...])` | ✅ 已修（真 bug） |

**「添加」按钮的启用逻辑（关键）** —— `gf_OSActivateOptions`（约 54365 行）：

```galaxy
if ((gv_playerSelection != 0)) {
    DialogControlSetEnabled(gv_rolesMenusItem[4], PlayerGroupSingle(gv_host), true);   // 添加
```

- `gv_playerSelection` 只在 **86474 行**（`gt_OSMenus` 的玩家槽位列表选择事件）被写入；
- `gt_OSMenus_Func` 开头会 `TriggerEnable(gt_OSMenus, false)`（约 86217 行）→ 怀疑该值恒为 0；
- 我曾在 `gf_OSActivateOptions` 里加测试构建补丁 `gv_playerSelection = gv_host`，**用户反馈仍无效**。

**尚未验证的假设**：`gv_playerSelection` 的语义可能是「玩家列表的**索引**」而不是玩家号，直接赋 `gv_host` 反而指错槽位。

---

## 四、影武者工作在哪、怎么取回

全部在 `backup/shw45-mess` 分支（`0ebf346`）。当时状态：

- 面板五段列表/映射**数量全部对齐**（城镇 30/30、黑手D 28/28、三合会 25/25、中立 17/17、随机 19/19）；
- 影武者用**池 3 / 角色 13**（**不要**用 18，那是「小金执行者」）；
- 已实现：双目标行动按钮、夜晚行踪/击杀/去向播报、案底标记、探员结果（风衣）、角色卡正文分支、中立致命残局判定、`-solo` 虚拟玩家、`-prefer yingwuzhe`；
- 唯一确认的真 bug 已修（`gv_name` 需 `StringToText`）。

取回方式（**不要整体 merge**，只按需 cherry-pick 或参考）：

```bash
git show backup/shw45-mess:work/blackhand/CustomLogic.galaxy | grep -n "SHW\|gf_ESShadowKill\|gf_RAShadowActions"
git diff d80a6e7 backup/shw45-mess -- work/blackhand/CustomLogic.galaxy > /tmp/shadow.patch
```

---

## 五、下次继续的正确姿势（建议）

1. **先解决面板**（用户的硬要求），再谈影武者。
2. 用 `boot2-pristine.SC2Map` 建立「能添加」的基线事实。
3. 二分定位破坏点（`git bisect start backup/shw45-mess dcb0f59`）。
4. 定位后，**只把影武者的角色定义 + 面板条目 + 映射**按 `AGENTS.md` 铁律 3.1 追加，**每加一步就在游戏里验证一次「添加」仍可用**。
5. 每次改动都要看 `Documents\StarCraft II\GameLogs\*ScriptError.txt` 的**最近一次**日志，注意「触发器报错会中断该触发器后续所有代码」这一点。

---

## 六、环境速查

```bash
# 部署
scp -P 2222 work/boot2-<name>.SC2Map "administrator@100.94.140.84:/mnt/d/StarCraft II/Maps/Test/boot2-<name>.SC2Map"

# 看最近脚本错误
ssh -p 2222 administrator@100.94.140.84 \
  "f=\$(ls -t '/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs/'*ScriptError*.txt | head -1); tail -40 \"\$f\""

# 打包（替换脚本 + 合并字符串）
python3 - <<'EOF'
import sys; sys.path.insert(0, 'tools'); import sc2map
from pathlib import Path
src, out = Path('work/boot2-user.SC2Map'), Path('work/boot2-<name>.SC2Map')
out.write_bytes(src.read_bytes())
sc2map.write(out, 'CustomLogic.galaxy', Path('work/blackhand/CustomLogic.galaxy').read_text(encoding='utf-8').encode('utf-8'))
EOF
```

| 项 | 值 |
|---|---|
| 远程 | `ssh -p 2222 administrator@100.94.140.84`（WSL，`/mnt/d` = `D:`） |
| 游戏 | `D:\StarCraft II`，5.0.15.97579 |
| 编辑器 | 必须由用户在交互式桌面手动启动 |
| 测试地图目录 | `D:\StarCraft II\Maps\Test\` |
