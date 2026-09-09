# 影武者接入交接文档（2026-09-09）

> **最新状态：已按方案 A 重置并完成重做（见下方「重做进度」）。**
> 第一～九节保留完整根因分析，供复盘与后续修改参考。

---

## 重做进度（2026-09-09 晚）

### 已执行

1. **备份**：乱改动全部保留在分支 `backup/shadow-mess-20260909`。
2. **重置**：`git reset --hard 3e3b300`（影武者定义 + 击杀助手，无面板污染）。
3. **文档恢复**：从备份取回本文件与 AGENTS.md 铁律（提交 `83e00f9`）。
4. **面板重做**（`27b93b9`）：拼音名 → `yingwuzhe`；中立列表**末尾**追加第 17 条；中立映射**末尾**追加 `== 17 → 13`。
5. **功能摘取**（`4593efa`…`1227618`）：按序 cherry-pick 了 `-solo`、虚拟玩家、`-prefer` 放开、双目标行动按钮与分发、夜晚行踪/击杀/播报、案底标记、探员结果、角色卡正文分支（含狱警分支限定池 1）、中立致命残局判定、测试构建强制 `gv_variantSelection = 1`。
   - **跳过**被污染的提交：`a17789e`（迁到池 3/18）、`23935fd`、`a9ee146`、`d7e61b3`。
6. **部署**：`D:\StarCraft II\Maps\Test\boot2-shw41.SC2Map`（14,537,362 bytes）。

### 校验结果

| 项 | 结果 |
|---|---|
| `[3][18]` 行数 | **5**（与原图一致 → 小金执行者未被污染 ✓） |
| 面板五段 列表/映射 | 30/30、28/28、25/25、**17/17**、19/19 ✓ |
| 大括号配平 | OK |
| 池 3/13 行为引用 | 全部带 `(gv_roles[...][1] == 3)` 池判断 ✓ |

### 已知遗留

- 约 12762 行的旧处刑逻辑仍在，已加 `(c_bhSoloBuild == false)` 守卫：**测试构建不触发，正式构建仍会触发**。发布前必须删除或补池判断。
- 角色卡文案分支已按池限定；若后续新增复用同一角色号的角色，必须重复同样处理。

---

## 一、当前状态

| 项 | 值 |
|---|---|
| 工作区 | `/home/mon3tr/dev/blackhand-rewrite` |
| 主脚本 | `work/blackhand/CustomLogic.galaxy` |
| 基线地图（**不要覆盖**） | `work/boot2-user.SC2Map` |
| 最近部署地图 | `D:\StarCraft II\Maps\Test\boot2-shw38.SC2Map` |
| 最近提交 | `d7e61b3` |
| 打包/部署 | `python3 tools/sc2pack.py` 风格脚本 + `scp -P 2222` |

### 可用

- 影武者角色定义、探员结果、案底文案、夜间演出文案
- `gf_ESShadowKill` 击杀助手（标准击杀 + 免疫/救治判定 + 紫色演出）
- 双目标行动函数 `gf_RAShadowActions`
- 夜晚结算（行踪记录 + 三条件击杀 + 去向播报）
- `-solo` 单人测试与 `-prefer` 优选（拼音名 `yingwuzhe`）
- 测试构建强制 `gv_variantSelection = 1`（否则 Test Document 大厅属性为空 → 自设列表全空）

### 不可用 / 已损坏

- **狱警位置显示成其他角色**（列表索引→角色号映射错位，见第五节）
- **池3/18「小金执行者」被覆盖**（影武者错误地迁到了 18 号，见第三节）
- 添加按钮不亮（根因：`gv_roleSelection` 因映射错位未被正确设置）
- `gt_OSMenus_Func` / `gt_OSVariantsMenuConfirm_Func` 的
  `DialogControlSelectItem(-1)`、`DialogControlSetPropertyAsBool(triggerControl=0)`
  报错（空列表/空控件，Test Document 环境下固有）

---

## 二、影武者当前的改动点（槽位 = 池 3 / 角色 **18**）

> 这个槽位是**错的**，见第三节。

| 类别 | 位置 |
|---|---|
| 名称/描述/探员/开关/案底 | `CustomLogic.galaxy` 4759–4777 |
| 拼音名 | 5380（`yingwuzhe`） |
| 开关默认值/权重 | 5919–5920、5953–5956 |
| 行踪记录 | 10646 |
| 夜晚结算 + 去向播报 | 12772–12785 |
| 行动分发 | 35272 |
| 卡片分支（`gf_RTNeutralRoleText`） | 42717 |
| 卡片分支（另一处） | 41161 |
| 阵营标记 | 43533 |
| 自设列表条目 | 86442（中立段末尾追加） |
| 选中映射 | 86027（`索引 18 → 角色 18`） |
| 行动函数 | 88382 `gf_RAShadowActions` |
| 击杀函数 | 88335 `gf_ESShadowKill` |

---

## 三、致命错误：池 3 / 18 不是空闲槽位

原图脚本 `work/bh-src/MapScript.galaxy` 中：

```
5351: gv_roleNameInput[3][18] = "xiaojinzhixingzhe";   ← 小金执行者
5917: gv_roleOptionAllowed[3][18][0] = true;
5918: gv_roleOptions[3][18][0] = false;
5919: gv_bankSaveWeights[0][3][18] = 0.25;
5920: gv_roleWeights[3][18] = 0.75;
```

而池 3 / 13（`duoluoshenpanzhe` = 旧堕落审判者）在原图中**只有**：

```
5346: gv_roleNameInput[3][13] = "duoluoshenpanzhe";
5881: gv_roleOptionAllowed[3][13][0] = true;
5882: gv_roleOptionAllowed[3][13][1] = true;
5883: gv_roleOptions[3][13][0] = true;
5884: gv_roleOptions[3][13][1] = true;
5885: gv_bankSaveWeights[0][3][13] = 0.25;
```

**没有任何 `gv_roleNameArray[3][13]` / `gv_roleDescriptionArray[3][13]`** —— 也就是说
池 3 / 13 是原图里一个**没有名称与描述的遗留槽位**，它的行为代码（面板/按钮/处决）
仍然散落在脚本里，但角色本身已经不可见。

**结论：影武者应该用 池 3 / 13，不是 18。**

---

## 四、自设面板的双硬编码机制（本次最大的坑）

自设面板的角色列表由**两处彼此独立、且顺序敏感**的硬编码决定：

### 位置 A —— 列表构建 `gt_OSMenus_Func`

```
86309: if ((gv_roleCategory == 1)) {     // 城镇
86348: if ((gv_roleCategory == 2)) {     // 黑手 D
86391: if ((gv_roleCategory == 5)) {
86425: if ((gv_roleCategory == 3)) {     // 中立
86448: if ((gv_roleCategory == 4)) {     // 随机
```

每个段内部再按 `gv_variantSelection` 分档，然后**逐行** `DialogControlAddItem`：

```galaxy
DialogControlAddItem(gv_rolesMenusItem[1], PlayerGroupAll(),
    (StringExternal("Param/Value/前缀键") + gv_roleNameArray[gv_roleCategory][角色号]
     + StringExternal("Param/Value/258B2E40")));
```

**这些 AddItem 的行序 = 列表索引（1-based）。**

### 位置 B —— 选中映射 `gt_OSRoleSelect_Func`

```
85592: if ((gv_roleCategory == 1)) {
85722: if ((gv_roleCategory == 2)) {
85849: if ((gv_roleCategory == 5)) {
85958: if ((gv_roleCategory == 3)) {     // 中立
86036: if ((gv_roleCategory == 4)) {
```

段内同样是 `variantSelection` 分档 + 逐行：

```galaxy
if ((DialogControlGetSelectedItem(EventDialogControl(), gv_host) == N)) {
    gv_roleSelection = 角色号;
}
```

### 铁律

1. **两处必须一一对应**：A 的第 N 行 ↔ B 的 `== N`。
2. **只能追加到末尾**：插到中间会让该段之后所有角色的映射整体后移。
3. **必须按 category 段定位**：不能用全局 grep 的第一个匹配（我因此把映射插到了城镇段）。
4. **改完必须校验**：该段 AddItem 条数 == 该段映射条数。
5. 追加的文本前缀用 `StringExternal("Param/Value/...")`，常见值为
   `<s val="ModLeftSize20">`，尾部键为 `</s>` 形式（如 `258B2E40`）。

---

## 五、我这几轮的具体错误（供复盘）

| # | 错误 | 后果 |
|---|---|---|
| 1 | 把影武者条目**插进城镇段中间** | 狱警之后全部角色映射后移一位 → 狱警位置显示树妖 |
| 2 | 中立段改了映射，但**条目没加** | 中立第 17 项指向角色 18，名字却仍是角色 17 |
| 3 | 修补时映射**又插进城镇段**（全局第一个 `== 17 → 17` 匹配） | 城镇段出现重复 `== 18`，与原有 `18 → 12` 冲突 |
| 4 | 误判 **池 3 / 18 空闲** | 覆盖了「小金执行者」的名称/描述/开关 |
| 5 | 把影武者从 13 迁到 18 以"摆脱遗留代码" | 遗留代码问题没解决，反而多破坏一个角色 |

---

## 六、重置方案

### 方案 A（推荐）—— 回到影武者核心逻辑完整、尚未触碰面板的状态

```bash
git reset --hard 3e3b300
```

`3e3b300` 的内容：
- ✅ 影武者角色定义（`818465f`）
- ✅ `gf_ESShadowKill` 击杀助手（`1597718`）
- ✅ `docs/ROLE-PIPELINE.md`
- ❌ 无自设面板条目（因此**无索引错位**）
- ❌ 无双目标行动按钮 / 夜晚结算 / 案底 / `-solo`

然后按第七节清单**重新、按序**接入。

### 方案 B —— 保留当前树，定点修复

1. `[3][18]` 全部改回 `[3][13]`（恢复小金执行者的 18 号定义）
2. 删除中立段末尾追加的第 18 条 AddItem 与 `== 18 → 18` 映射
3. 校验城镇/中立两段的条目数 == 映射数
4. 再按第七节 5–9 步处理遗留代码与后续功能

> 无论哪种方案，**不要**再复用池 3 / 18。

---

## 七、重做清单（按顺序执行）

1. **角色定义** → `gv_roleNameArray[3][13]`、`gv_roleDescriptionArray[3][13]`、
   `gv_roleInvestigatorArray[3][13][*]`、`gv_roleOptionExists/Important/Text/Options[3][13][*]`、
   `gv_e78AAFE7BDAAE58FAFE883BD[3][13]`、`gv_roleNameInput[3][13] = "yingwuzhe"`。
2. **面板列表** → 中立段（`86425` 附近）的 `variantSelection` 分档末尾追加一条 AddItem。
3. **选中映射** → 中立段（`85958` 附近）**同一分档**末尾追加 `== N → 13`。
4. **校验** → 该分档 AddItem 条数 == 映射条数（用脚本数，不要目测）。
5. **清理旧堕落审判者遗留**（池 3 / 13 共 8 处）：
   `10314`（资格位）、`10646`（行踪记录）、`12762`+`12772`（处决/结算）、
   `13860`、`15760`、`42703`（`gf_RTNeutralRoleText` 卡片）、
   `35272`（行动分发）。**逐处加 `(gv_roles[lv_a][1] == 3)` 池判断**，不要靠换槽位规避。
6. **卡片字段**（用户规格）：
   - 阵营：`无（致命）`（沿用原图 `CE62498E + lv_t[2]` 形式，**不塞介绍**）
   - 能力：`SHWBOX1`（每晚选择两名玩家…）
   - 特性：`SHWF1`（你拥有夜间无敌）+ `SHWF2`（你会获知目标一的真实去向）
     + 开关开启时追加 `SHWF3`（你的攻击无视无敌和救治）
   - 取胜：`SHWBOX4`
7. **行动按钮**：`gf_RAShadowActions` 中 `gv_actionDialogItem[lv_a][5]/[6]` 的
   tooltip 用 `SHWTGT1` / `SHWTGT2`（**不要**沿用女巫的 `A1A1A229` =「控制」）。
8. **夜晚结算**：行踪记录 + 三条件击杀 + `SHWDEST1/2/3` 去向播报。
9. **测试链路**：`-solo`、`-prefer yingwuzhe`、测试构建强制 `gv_variantSelection = 1`。

---

## 八、验证清单

- [ ] 中立列表条数 == 中立映射条数
- [ ] 城镇列表条数 == 城镇映射条数（狱警位置正确）
- [ ] 自设 → 中立 → 末尾出现「影武者」，选中后右侧详情正确、添加按钮变亮
- [ ] 游戏内角色卡：阵营 = 无（致命）；特性两行（+ 开关第三行）
- [ ] 右下角按钮为「目标一」「目标二」，无「投票处死」
- [ ] 无新增 Galaxy 编译错误（`Documents/StarCraft II/GameLogs/*ScriptError.txt`）

---

## 九、常用命令

```bash
# 打包并部署（示例）
python3 - <<'PY'
# 见本文档附录脚本：读 work/boot2-user.SC2Map → 写 CustomLogic.galaxy + GameStrings → work/boot2-shwNN.SC2Map
PY
scp -P 2222 work/boot2-shwNN.SC2Map \
  "administrator@100.94.140.84:/mnt/d/StarCraft II/Maps/Test/boot2-shwNN.SC2Map"

# 读取最新脚本错误
ssh -p 2222 administrator@100.94.140.84 \
  "f=\$(ls -t '/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs/'*ScriptError*.txt | head -1); tail -40 \"\$f\""

# 校验面板与映射数量
python3 - <<'PY'
# 见第六/七节：按 category 段统计 AddItem 与 gv_roleSelection 行数
PY
```
