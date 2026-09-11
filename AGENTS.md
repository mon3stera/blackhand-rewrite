# AGENTS.md — 黑手：升温 脚本二改工程

> 本文件是**长期维护**的工程约定，任何改动前先读它。
> 详细操作手册见 `docs/ROLE-PIPELINE.md`；设计见 `docs/BLACKHAND-REWRITE.md`。

## 工程定位

- **改版定位**：玩家自维护二改（原作者长期停更）；无原作者授权，**永不收费**（不收赞助/打赏/任何费用，不设付费门槛）；原管理员的权限与署名一律完整保留。
- 以**原图**（黑手：升温）为基底，通过**外挂 Galaxy 脚本**替换/扩展核心逻辑；
- 保留原图地形、美术、UI、角色卡、行动面板与演出；
- 主脚本：`work/blackhand/CustomLogic.galaxy`（唯一维护目标）；
- 基线地图：`work/boot2-user.SC2Map`（含用户的变体修改，**不要覆盖**）；
- 仓库：https://github.com/mon3stera/blackhand-rewrite（私有）。

## 铁律

1. **大括号配平定位函数体**，不要用文本锚点。同一段代码在多个函数里出现，`replace(..., 1)` 会命中错的。
2. **插入后必须验证落点**：①全文 `{}` 配平 = 0；②**打印目标分支/函数的行号范围和条目数**，确认代码在正确的位置。只看配平不够——曾连续三次把代码插进错误的分支。
   - **Galaxy 声明必须先于语句（shw137 事故）**：函数/块内**所有局部变量声明（含 `int autoXXX;`、`const int autoXXX_ae = N;`）必须在任何语句之前**。插桩点只能选在 `// Actions` 或已有语句之后；插进声明块中间 → 编译器在下一条声明处报 `解析函数行出错，可能有无效的变量名/函数调用，或是函数结尾缺失`（dbg9 报 `int init_i;`）。`gt_Init2_Func` 的声明块很长（auto 变量 + `// Variable Declarations` + `// Automatic Variable Declarations` 一直排到 `// Variable Initialization`），**不要在函数开头插任何东西**。
   - **自动变量必须有声明（shw139 事故）**：生成的循环写法 `for ( ; ( (autoXXXX_ai >= 0 && lv_a <= autoXXXX_ae) || …) ; lv_a += autoXXXX_ai )` **依赖声明区的 `const int autoXXXX_ae = N; const int autoXXXX_ai = 1;`**（动态上界写 `int autoXXXX_ae;` 再在体里赋值）。漏掉 → 游戏内 `解析for时出错，可能缺少分号`、**整个脚本读取失败**。自加函数（尤其 preset_gen 生成的 V 函数）必须克隆参考函数 `gf_VBFCZOptions` 的声明块；**改完必跑 `python3 tools/galaxy_lint.py`**（配平 + 962 函数 auto 声明检查，非 0 禁止打包）。
   - **改 `if (...)` 条件必须打印整行人工核对**：`()` 配平检查发现不了"括号位置错"——曾把 `!= 4)) {` 改成 `!= 4)) && (X) {`，配平过但 `&&` 跑到 `if` 外面，游戏报"需要一个左大括号"。正确写法是把新条件并入 `if` 内：`... && (X)) {`。
2a. **python 批量补丁：插入偏移必须在所有前置 replace 之后重新测量**（shw67 事故）。用旧偏移做插入会把新函数插进行中间 → 脚本读取失败 → 游戏取名后卡死。顺序：①提取函数体（`\n}\n` 定位）②对**提取文本**做替换 ③做完其它 rep 后**重新 index 测插入点** ④断言插入点前是 `}`/行首结构，插入后断言新函数位于行首且结构完整。
2b. **用切片拼 `if` 条件时逐行验证 `()` 配平**（shw69 事故）：`w[:-3]` 会把 `...16))) {` 削成 `...16))`，再拼 `|| (X))) {` 多一个 `)`——全文配平仍是 0 但该行解析失败。修完必须对**每个被改的 if 行**做 `line.count('(')==line.count(')')`。
3. **两套角色面板别搞混**（踩坑高发区）：
   - 自设界面（玩家可见）：`gv_rolesMenusItem[1]`，`gf_OSE...` 内按 `gv_roleCategory` 分支，约 86150–86300 行，**逐角色硬编码**；
   - 审查页：`gv_e8A792E889B2E68EA7E4BBB6`，`gf_ASE5AEA1E69FA5E98089E9A1B92`，约 38802 行。
   - 选中项 → 角色号 的映射在 `gt_OSRoleSelect_Func`（约 85413 行），同样是**按列表索引**逐条硬编码。
3.1 **自设列表是「行序 = 索引」的双硬编码，顺序敏感**（曾因此把狱警显示成树妖）：
   - **位置 A**（列表构建，`gt_OSMenus_Func`）：按 `gv_roleCategory` 分段，段内再按 `gv_variantSelection` 分档，逐行 `DialogControlAddItem(gv_rolesMenusItem[1], ...)`。**这些行的行序就是列表索引（1-based）**。
   - **位置 B**（选中映射，`gt_OSRoleSelect_Func`）：同样分段分档，逐行 `if (SelectedItem == N) gv_roleSelection = 角色号;`。
   - 当前段边界：A → 城镇 86309 / 黑手D 86348 / 86391 段 / 中立 86425 / 随机 86448；B → 城镇 85592 / 黑手D 85722 / 85849 段 / 中立 85958 / 随机 86036。
   - **铁律**：① 两处一一对应；② **只能追加到末尾**，插到中间会让该段之后所有角色的映射整体后移；③ **必须按 category 段定位**，不能用全局 grep 的第一个匹配（曾把映射插进城镇段，与原有的 `== 18` 冲突）；④ 改完用脚本校验「该段 AddItem 条数 == 该段映射条数」，不要目测。
   - 追加条目的文本前缀用 `StringExternal("Param/Value/...")`，常见值 `<s val="ModLeftSize20">`，尾部键形如 `258B2E40`（内容是 `</s>`）。
3.2 **不要靠「换槽位」规避遗留代码**：旧角色散落在十几个硬编码分支里，换槽位只会多破坏一个角色。正确做法是**逐处加池判断** `(gv_roles[lv_a][1] == 池)`。
3.3 **判定槽位空闲必须查原图 `work/bh-src/MapScript.galaxy`**，不能凭「没有名称数组」下结论：
   - 池 3 / 18 = **小金执行者**（`gv_roleNameInput[3][18] = "xiaojinzhixingzhe"` + options + 权重），**已被误覆盖过一次**，不要再用；
   - 池 3 / 13 = `duoluoshenpanzhe`（旧堕落审判者），原图**只有拼音名和开关、没有名称/描述**，是真正可复用的遗留空槽；其行为代码仍在（见 3.2）。
3.4 **Test Document 的大厅属性为空**：当前基线**已不需要**强制 `gv_variantSelection = 1`——那是 shw45 时期的死路补丁（变体 1=随机系会命中 `gt_OSRoleSelect_Func` 的禁用子句，添加按钮永远不亮）。当前基线在 Test Document 下自设路径直接可用，**不要再加变体强制补丁**。
4. **改角色要同时改多处**：完整清单见下方「新增角色端到端流程」。漏一处就"看起来加了但没生效"。
5. **回退文件前先列出已完成的所有改动**，`git checkout` 会把未提交的清理一起还原。
6. **部署用新文件名**（编辑器打开中的地图被锁定），部署后确认 `scp` 无 `failed to upload`。
7. **每次改完立刻提交**，提交信息写清"第几步 / 改了什么"。
8. **测试地图统一放 `D:\StarCraft II\Maps\Test\`**，不要放桌面。
9. **角色号上限红线**：`gv_bankRoleAchievements` 维度是 `int[16][9][21]`——角色卡分支里 `[xx][1][角色号]` 用 21 以上的角色号会数组越界（ScriptError 41358）；31 号角色**不得**做银行成就检查。`gf_VLoadSaveSlot` 的槽位加载校验曾用 `> gv_townMax(30)` 把 31 号槽清零（预设列表空行+实际阵容缺人），已放宽为 `> 31`；再加大于 31 的角色号需同步放宽。

## 预设（变体）系统

- 链路：变体菜单 `gv_variantsMenuItem[0]` 第 N 项 → `gt_OSVariantsMenuChange_Func`（显示描述，**每个菜单项都要有分支，否则无说明且右下标签残留上一个变体名**）→ `gt_OSVariantsMenuConfirm_Func`（SelectedItem → `gv_variantSelection` 映射 + 末尾分发调 `gf_V*Options()`）→ V 函数（=OSActivateOptions 的预设变体：重建面板 + 填 `lv_category`/`lv_role` 槽位串 + `gf_VLoadSaveSlot(0,...)`）。
- **槽位串语义**：`lv_category`/`lv_role` 按槽位空格分隔；槽位=「池 角色号」。**随机组槽 = category 4 + 随机池角色号**：4[2]=城镇随机、4[3]=黑手随机、4[4]=政府(zf)、4[5]=城镇调查、4[6]=保护、4[14]=中立温和、4[12]/4[13]=致命类。预设按人数逐档（15/14/13/12 人），≤11 人走拒绝提示分支。
- **现有自加预设**：第 31 项「烙印」（`BHYIN01`，原为悬挂键）→ variant 30 → `gf_VE78399E58DB0`；第 32 项「捕风捉影」（`GCZBNAME`）→ variant 31 → `gf_VBFCZOptions`（15 人=侦探/观察者/4城镇随机/城镇调查/政府/保护/教父(2,2)/陪侍(2,3)/黑手随机/影武者(3,31)/女巫(3,4)/中立温和；14/13/12 人递减城镇随机）；第 33 项「大审判」（`GCZJNAME`）→ variant 32 → `gf_VDSPOptions`；第 34 项「随机：天谴」（`GCZTNAME`，渐变 FFFFFF99-FFFF8800）→ variant 33 → `gf_VTQOptions`（shw133）：锁定型四子变体 A-D，固定天选者(3,32)，D 档固定 医生+瘟疫散布者×2；开局白字广播条件追加 `gv_variant == "tq"`。女巫=3/4、教父=2/2、陪侍=2/3、瘟疫散布者=3/14。
- **预设白名单（允许增删改角色）**：①目录浏览 `gt_OSMenus_Func`（6 处 `== 16)))` 结尾的变体串）②选中映射 `gt_OSRoleSelect_Func`（5 处 `== 12)))`）——两者都要含新 variantSelection；③**动作执行层**：`gt_OSRoleManipulate` 排除集 {1,4,8,9,10,11,12,14}（item[3]添加/item[4]移除/上下移）+ 预览选中处理（~86811）的 `!= 1`。**锁定型预设（???类）必须同时改③与添加按钮禁用集**，只摘①②会像 shw85 那样仍可移除。
- **注意**：预设再点「采纳设定」会重跑 fill 覆盖手动修改（原图语义）。

### 预设生成器（tools/preset_gen.py，shw95 后加入）

新增/调整随机系列锁定预设**不要手写函数体**，用生成器：

```bash
python3 tools/preset_gen.py work/presets/<名字>.json              # 校验规格 → 生成 <名字>.galaxy.txt + 打印接线清单
python3 tools/preset_gen.py work/presets/<名字>.json --selfcheck  # 与源码中同名函数回归比对（已上线预设必跑）
```

- **规格**：`work/presets/*.json`，字段见 `work/presets/dashenpan.json`（大审判，生成器回归样板）。`fixed`=固定角色、`randoms`=[随机槽别名,数量]、`enable_overrides`=按子变体覆盖随机槽选项、`decrement`=人数递减时优先删的随机槽。
- **角色名解析**：生成器每次运行时从 `CustomLogic.galaxy` + 基线 GameStrings 抽取 `gv_roleNameArray` 全表（含随机槽名），别名表 `ALIAS`/`SLOT_ALIAS` 在文件头部维护（影武者/观察者等非 hex 名称键的角色必须登记）。
- **函数体尾部**（VLoadSaveSlot 填充 + ??? 锁定覆写 + 选项禁用）从 `gf_VBFCZOptions` 原样克隆；克隆尾已含收尾 `}`，生成器**不再**追加（shw133 因多一个 `}` 导致配平 -1；插入前必须 `count('{')==count('}')`）。按钮文本键默认 `GCZJBTN`，规格加 `"btn_key": "GCZTBTN"` 可换。

### 随机槽使能串语义（lv_str[4]，实测解码）

- **结构**：19 个空格分词 = 随机槽 4/1..4/19（词序=槽号）。`gf_VLoadSaveSlot` 按 `roleOptionExists[4][槽][位]` 逐位解析：第 b 位字符 '1'/'0' 设 `gv_roleOptions[4][槽][b]`，**字符串不够长时该位回落到 `gv_defaultRoleOptions`**——所以 "0"（单字符）= 只显式关掉第 0 位、其余默认。
- **位串按位对齐**：必须从第 0 位写起；尾随 0 可省略（省略=默认，各"不包括X"选项默认值几乎都是 false/不过滤）。
- **随机槽选项目录**（生成器运行时自动抽取，写规格时照抄大厅原文标签）：4/1 全体随机=[不包括致命/黑手D/城镇/中立/三合会]；4/2 城镇随机=[致命/zf/调查/保护/权力]；4/3 黑手D随机=[不包括 致命角色]；4/4 城镇zf=[市民/共济会成员/市长执法长/共济会长老/g告员]；4/5 城镇调查=[法医/警长/探员联邦探员/侦探/监视者]；4/6 保护=[巴士司机/保镖/医生/舞娘]；4/12 中立致命=[连环爱手/纵火者/爱人狂/瘟疫散布者]；4/13 中立协恶=[致命/协教徒/法官/女巫/审ji官]；4/14 中立温和=[生存者/小丑/处刑者/失忆者/赌鬼]；4/15 三合会随机=[致命]；4/19 中立随机=[致命/协恶/温和]。
- **只有出现在阵容里的槽位其使能位才有意义**；未用槽位写 "0" 即可（捕风捉影/大审判串里残留的其它配置是历史包袱，无 gameplay 影响）。

### 预设座席排序约定（用户规定，生成器内建）

理论上游玩不受顺序影响，但面板展示顺序约定如下，生成器 `seat_sort_key` 已内建：

1. **阵营序**：城镇 → 黑手党 → 三合会 → 中立致命 → 中立邪恶 → 中立温和
2. **城镇内**：固定位（按规格列出顺序）→ 城镇随机 → 城镇保护 → 城镇调查 → **城镇政府（最后）**
3. **黑手党/三合会内**：固定位 → 随机 → 致命/支援/欺诈等其他随机槽
4. **中立内**：致命固定位（堕落审判者/瘟疫等）→ 中立致命槽 → 中立邪恶槽 → 温和固定位（小丑/处刑者等，集合见生成器 `NEUTRAL_MILD_ROLES`）→ 中立温和槽

新增池 3 固定角色时，若它属于温和层需同步 `NEUTRAL_MILD_ROLES`，属于协恶层同步 `NEUTRAL_EVIL_ROLES`，否则会被排进致命层。

## 标准循环

```bash
# 1) 改脚本 + 自检（配平 + 落点）+ 打包
python3 - <<'EOF'
...修改 work/blackhand/CustomLogic.galaxy...
...sc2map.write 写入 CustomLogic.galaxy 与 GameStrings...
EOF

# 2) 部署到新文件名
scp -P 2222 work/boot2-<name>.SC2Map "administrator@100.94.140.84:/mnt/d/StarCraft II/Maps/Test/boot2-<name>.SC2Map"

# 3) 提交
git add -A && git -c user.name="mon3stera" -c user.email="mon3stera@users.noreply.github.com" commit -q -m "<说明>"
```

验证：游戏内 `File → Test Document` → 看 `Documents\StarCraft II\GameLogs\*ScriptError.txt`（只看最近一次）；`Script compile error` 必修，运行期参数错误先对照原版同类角色判断是否为原图自带。

## 角色文案与设计规范

### 文案格式（对齐原图）

| 部分 | 格式 | 示例 |
|---|---|---|
| 名称 | `<c val="颜色">名字</c>`，不带字号标签（面板会套用大字） | `<c val="DE8421">系命人</c>` |
| 背景介绍 | **白色正文**，一段 | `影武者是一名隐于市井的杀手……` |
| 能力介绍 | 空两行后接 **天蓝色** `<c val="BBDDFF">…</c>` | `<n/><n/><c val="BBDDFF">每晚选择两名玩家……</c>` |

角色名颜色按阵营：城镇青绿 / 黑手党红 / 三合会黄 / 中立按主题（影武者 = 银灰 `C0C0C0`）/ 随机组灰。

**渐变色名称（shw131/132，用户要求）**：`<c val="上色-下色">` 支持上下渐变，但**每段必须是 8 位 ARGB**（如天选者 `FFFFFF99-FFFF8800`）——**6 位色值（`FFFF99-FF8800`）是非法标签，会让整张地图「无法运行游戏」**（shw131 事故：GameStrings 里一条非法文本标签 = 地图加载失败，且无 ScriptError）。名称色等用户验收；若 8 位仍不渲染渐变再回退单色。

### 国服和谐用词（shw147 沉淀，公开发布前必过）

**国服不允许出现「杀」字**，原图的官方替身是 **杀 → 爱**（在基线 zhCN GameStrings 里的实证计数：`爱死` 329 处、`爱手` 74 处、`谋爱` 31 处、`击爱` 16 处）。原图自己只漏了 6 处（多在 `DocInfo/PatchNote*` 开发者笔记，游戏内不可见）。

| 原词 | 国服写法 | 备注 |
|---|---|---|
| 杀死 / 被杀死 | **爱死 / 被爱死** | 原图标准替身，用词最广 |
| 杀手 | **爱手** 或 **刺客** | 原图两种都有（「狂热爱手」「刺客」）；「刺」字原图自己用得很多，**不算违禁** |
| 击杀 | **击爱** | |
| 谋杀 | **谋爱** | 图鉴案底固定写法 = `非法闯入，谋爱`（对照键 `061FD1EE` / `9D81D408`） |
| 暗杀 | **暗算 / 取你性命**（或改写整句） | 「暗爱」原图没有，别硬造 |
| 刺杀 | **行刺** | 「刺」可用 |
| 死亡 / 死者 | 保留 | `死` 不禁，原图大量使用 |

- **自加文案（`strings-shw/gcz/tx.txt`）每次收尾都要 `grep -n 杀` 过一遍**；本类改动属"玩家可见文本"，与代码改动同等对待。
- 「爱死」这类替身**不是错字，不要"修正"**：天选者复用的 `gf_RASerialKillerActions` 悬停提示写「爱死」（键 `38BB1053`）是国服和谐设定，保持原样。
- **原图遗留的天选者素材（未接线，可复用）**：`B0292835` = 该角色的完整描述（「[非官方]一个天神的凡人化身，有着不朽之躯…若预测成功，那么在次日天选者将无法被公开处死」）、`47843C61` = 「- 你可召唤 5 次雷击」（**作者原始设计是 5 次**）、`19E7B48E` = 「你无法再次召唤雷击。」、`3790B10C` = 「你被 天选者 的雷击爱死了。」、`A22C4229` = 能力行、`6B6EC9D0` = 验尸官线索、`58366F04` = 死亡描述、`757361A4`/`A228729A` = 行动确认。这些键在现行脚本里**引用数为 0**（作者开发残留），我们的 天选者(3/32) 是这套未实装设计的落地。

### 能力开关

原图每个角色需要四组数组同时存在，缺一不可：

```galaxy
    gv_roleOptionExists[池][角色][i]     = true;          // 该开关存在
    gv_roleOptionsImportant[池][角色][i] = 2;             // 显示权重/样式
    gv_roleOptionsText[池][角色][i]      = StringExternal("Param/Value/键");  // 标签文案
    gv_roleOptions[池][角色][i]          = true/false;     // 默认值
```

开关标签**沿用原图既有措辞**（如「在夜间无敌」），不要自创说法。

### 阵营设计惯例

| 阵营 | 惯例 |
|---|---|
| **中立·致命** | **默认永久夜间无敌**（`gv_roleOptions[...][0] = true`，标签「在夜间无敌」） |
| 中立·温和 | 一般无夜间无敌 |
| 城镇 | 无夜间无敌；调查/保护类有各自开关 |

### 一个角色要改的地方（清单）

1. 名称/描述数组 + 完整定义块（`roleNameArray` / `roleDescriptionArray` / `roleInvestigatorArray` / 四组开关数组）
2. GameStrings 文案（名称、描述、开关标签、夜间演出文本）
3. 自设面板列表（`gv_rolesMenusItem[1]`）
4. 选中映射（`gt_OSRoleSelect_Func`，按列表索引 → 角色号）
5. 行动按钮（`gf_RA*Actions` + 分发链）
6. 夜晚准备（`gf_SequencePrep`）与结算（`gf_SequenceKills`）
7. 击杀助手（`gf_ES*Kill`）
8. **角色卡正文分支**（`gv_roleBoxText[lv_a][0..4]`，约 40620–42000 行）—— 这一段是**按 `gv_roles[lv_a][0]`（角色号）逐个硬编码**的，**不区分池**！踩过的坑：影武者是池 3 角色 13，而原图已有的 `if ((gv_roles[lv_a][0] == 13))` 分支是**池 1 角色 13（狱警）**，于是影武者套用了别人的正文。
   - 必须把已有分支限定池：`if (((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 13)))`
   - 再新增自己的分支：`if (((gv_roles[lv_a][1] == 3) && (gv_roles[lv_a][0] == 13)))`
   - `[0]` 角色介绍（会拼在「你的角色是 X」后面）、`[1]` 能力、`[2]` 特性、`[4]` 目标；`[6]` 由 `gf_RTMakeWinList` 自动生成
   - 另有两处角色详情：`gv_roleDescriptionArray[池][角色]`（约 86118 行，自设面板详情）和 `gv_roleBoxText`（游戏内角色卡）
9. 可选：变体角色串

> 漏任何一处都会出现"看起来加了但没生效"。改完按 `docs/ROLE-PIPELINE.md` 第 4 节逐项验证。

### 探员消息 / 警长消息 / 案底

| 项 | 字段 | 说明 |
|---|---|---|
| 警长 | 自动 | 警长拿到目标的**精确角色名**（`gv_roleNameArray[池][角色]`），无需配置；只有开了「免疫调查」的角色才查不到 |
| 探员 | `gv_roleInvestigatorArray[池][角色][0..1]` | 两个字段成组（[0] 主线索、[1] 附加线索） |
| 案底（图鉴） | `gv_e78AAFE7BDAAE58FAFE883BD[池][角色]` | 角色图鉴里显示的"典型案底" |
| 案底（运行时） | `gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][罪名索引]` | 玩家**实际做过**的事，调查时逐条判断 |

#### 探员类别对照表

| 类别 | 常量后缀 | 典型角色 |
|---|---|---|
| 市民类 | `E5B882E6B091E7B1BB` | 市民、**拥有调查免疫的角色**、间谍 |
| 判断力 | `E588A4E696ADE58A9B` | 警长、审计官 |
| 危险物品 | `E58DB1E999A9E789A9E59381` | 法医、陷害者（一般调查免疫） |
| 强大气场 | `E5BCBAE5A4A7E6B094E59CBA` | 教父、龙头（一般调查免疫） |
| 水管工 | `E6B0B4E7AEA1E5B7A5` | 审查员、陪侍、交际花、舞娘 |
| 监禁 | `E79B91E7A681` | 狱警、审讯者、绑架者 |
| 精神不稳定 | `E7B2BEE7A59E` | 退伍军人、小丑 |
| 锋利工具 | `E9948BE588A9E5B7A5E585B7` | 女巫、巫医、瘟疫散布者、医生 |
| **风衣（侦探类）** | `E9A38EE8A1A3` | 纵火者、影武者、观察者 |
| 武器 | `E6ADA6E599A8` | 连环杀手 |
| 不断移动 | `E4B88DE696ADE7A7BBE58AA8` | 巴士司机、保镖、冤魂 |
| 秘密会面 | `E7A798E5AF86E4BC9AE99DA2` | 共济会成员、协教徒 |
| 魅力 | `E9AD85E58A9B` | 市长、执法长、征募官 |
| **善于解读（探员类）** | `E59684E4BA8EE8A7A3E8AFBB` | 探员、联邦探员、参谋、伪装者、栽赃者、管家、渗透、诬陷 |

写法：`gv_roleInvestigatorArray[池][角色][0] = gv_investigator<后缀>1;`，`[1]` 用同后缀加 `2`。

#### 案底规则（重要：动态而非静态）

- 案底**只记玩家实际做过的事**，不是角色属性。例（影武者）：当晚有行动 → 非法闯入（`gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][0] = true`）；杀了人 → 谋杀（`[1] = true`）；整晚没动 → 两条都不记。
- 罪名索引：`[0]` 非法闯入、`[1]` 谋杀（**和谐文案「谋爱」**，键 `513FA9C0`/`BE9264D4`，勿自创「谋杀」文案）。
- 罪名标志写两份平行块（visitation ~11430 / action ~12123），每个有夜间行动的角色在其中各有分支；击杀函数 `gf_ES*Kill` 的真击杀分支（`gv_diedAtNight[目标] = true` 处）补写谋杀标志。观察者/监视者的图鉴犯罪可为**空白**（自建空值键 `GCZBLANK=`；**不要用 `F0A13008`——那是审查官能力文本，原图监视者曾错指向它**）。
- 调查者（警长/探员）夜间结算时读这些标记，任一为真播报「你的目标曾经有过案底！」（`33FE9712`），否则 `D903D005`。
- **案底只在行为真正生效时记录**：攻击被无敌挡下、被救治救回**不算**谋杀（影武者的标记只写在 `gf_KillPlayer` 成功之后）。
- **新增角色的调查清单**：①`gv_roleInvestigatorArray[池][角色][0..1]` 探员线索（按上表选类别）②`gv_e78AAFE7BDAAE58FAFE883BD[池][角色]` 图鉴案底文本 ③在自己的行动/结算代码里打运行时案底标记 ④警长消息无需配置（自动取角色名），只有该角色应免疫调查时才设「免疫调查」开关。

### 新增角色端到端流程（影武者 池3/31 已端到端验收，2026-09-10）

按顺序走，每一小步「改 → 静态校验 → 提交」：

**第 0 步：选槽位** —— 先查 3.3 确认空闲；**角色号 > 30 会触发一整类循环上界问题**（第 4/6/7 步），能用 ≤30 的空槽就用 ≤30。

**第 1 步：角色定义块**（`gf_InitializeVariables`，搜最近角色的定义块照抄结构）
- `gv_roleNameArray` / `gv_roleDescriptionArray` / `gv_roleOptionsText` / `gv_roleOptionsImportant` / `gv_roleOptionExists` / `gv_roleOptions` / `gv_bankSaveWeights` / `gv_roleInvestigatorArray[池][号][0..1]` / 图鉴案底 `gv_e78AAFE7BDAAE58FAFE883BD[池][号]`
- 拼音 `gv_roleNameInput[池][号]`（在 `gf_InitializeOther`）
- 要常驻帮助面板：`gv_roleOptions[池][号][10] = true;`

**第 2 步：GameStrings**（`work/blackhand/strings-<角色>.txt`，打包时 `--strings` 传入）
- 名称/描述/开关标签/夜间演出/死亡描述/验尸官线索等键；键名用角色前缀（影武者=SHW*）
- **共享键可覆盖**：`merge_strings` 对已存在的键整行替换。探员类别枚举（如侦探类 `F2239D82`）在尾部追加新角色名即可，共用该类的所有角色一起更新

**第 3 步：角色卡分支（两份，必须逐字段一致）**
- `gf_RTTownRoleText` / `gf_RTNeutralRoleText`（按池放）各加 `if (((gv_roles[lv_a][1] == 池) && (gv_roles[lv_a][0] == 号)))` 分支
- 阵营行 `[0]` 照抄同类：中立致命 = `CE62498E("无") + lv_t[2] + D7C97124(" (致命)")`——影武者曾因 NeutralRoleText 副本漏了「无」前缀，卡片只显示「(致命)」
- `[1]` 能力、`[2]` 特性、`[4]` 目标、`[6]` winList 自动；追加特性行 = 键内容自带 `<n/>` 前缀再 `+ 一个键`。**换行键陷阱见「特性行换行规范（shw124 事故）」**（`4467A310` 不是通用换行键）。

**第 4 步：帮助面板（角色参考卡页）**
- `gf_MakeHelpMenu` 的角色号循环上界 ≥ 新角色号（原图从 `gv_townMax`=30 起往下数）+ 第 1 步的 `[10]` 标志

**第 5 步：自设面板列表 + 选中映射** —— 见铁律 3.1，段内末尾追加，两处条数一致，脚本校验。**各段索引按 `gv_roleCategory` 独立计数**（黑手D等段从 1 重新开始），往某段末尾追加不影响其他段的映射

**第 5.5 步：审查页（灵魂猜测页）** —— `gf_ASE5AEA1E69FA5E98089E9A1B92` 的 `lp_picked` 上界 + `gt_ASE5AEA1E69FA5E7A1AEE5AE9A_Func` 映射。**该映射用「SelectedItem + 分段偏移」跳过无名角色**：新角色排在无名空位之后时要同时调上界与偏移（观察者=城镇上界 31 且 `>=30` 减 1；影武者=中立上界 18 且 `>=18` 加 12）。改完逐项推算「选中第 N 项 → 角色号」核对

**第 6 步：拼音匹配循环上界** —— `gt_Prefer_Func`(29)、`gt_Blacklist_Func`(24)、`gt_Init2_Func` 黑名单校验(19) 放宽到 ≥ 新角色号（`gt_Change_Func`=40 够用）；循环里 `roleNameArray != null` 自动跳过空位，放宽无害。不放宽的症状：`-prefer 拼音` 报「不是一个角色」

**第 7 步：几率/预计数量（随机池可见性）** —— `gf_OSComputeOptions` 里 5 处角色号循环（几率清零、模拟标志重置、几率计数、标志重置、归一化）原上界 `gv_townMax`。不放宽的症状：出现几率恒 0%、预计数量是未归一化的累加值（曾显示 1000）

**第 8 步：行动面板 + 夜晚逻辑**
- 行动按钮函数 `gf_RA*Actions`（每个存活其他玩家行配按钮）+ `gf_RAActions` 分发 + **AS 按钮点击触发器 A/B 两个都要写分支**（只写 A：按钮可见但点击不生效）
- `gf_SequencePrep`（记账）/ `gf_SequenceKills`（结算）/ `gf_CheckEnd`（残局计数、归零条件、数量比较）/ 阵营校验

**第 8.5 步：夜间目标的效果转换（欺骗者 / 女巫 / 巴士司机）** —— 新增带夜间目标的角色必须考虑这三者：巴士司机交换与欺骗者转向**共用 `gv_switched`**（`switched[对象]=转向对象`）；女巫控制走 `gv_witched[受害者]=女巫`，结算时重写受害者 `visitation = 女巫的 action[1]`（~10936），造访目的地被交换时连锁重写访客 visitation（~10959）。

- **原图标准模式**（效果按"造访目的地"投递，杀手杀 `visitation` 所指）：巴士/欺骗者/女巫经 visitation 重写自然生效，**无需额外代码**。
- **按目标身份直接投递的角色（如影武者）必须显式解析**：先判女巫控制（`gv_witched[自己]!=0 && gv_witchEligible && 未入狱 && 女巫有 action[1]` → 换成女巫的 action[1]），再过 `gv_switched`（盯 3、3 是欺骗者转向 7 → 实际看/杀 7）。**哪些槽位可被转换是设计决策且必须写进角色卡**（影武者：目标一可被交换，目标二结构性不可转——`action[x][1]` 全脚本只有重置与本人按钮写入）。
- 核对清单：①哪些槽位可被女巫替换 ②可否被 switched 转换 ③转换后判定与效果是否都落在转换后的目标 ④角色卡是否已说明 ⑤visitation 是否体现转换（影武者保持"表象去原目标"，观察者看得到）。

**第 9 步：击杀函数（`gf_ES*Kill`）死亡信息三件套**
- 字母码 `gv_deathMethod[目标]`：**用新码**（`K` 是连环杀手的，SK 函数里也有一份 → 锚点必须带函数特有上下文）；验尸官(1,10)选项2 私密播报扫描块（~13620）加字母分支
- 公示描述 `gv_deathText[目标]`：**照抄义警模式**（~26440）——`gv_deathDesc` 初始 false；`if(deathDesc==true){第一段; lv_c=true;} deathDesc=true; if(lv_c==false){主描述}`。**放反了 deathText 永远为空、白天没有死亡信息**
- 演出顺序（用户认可）：语音（如 `SoundLink("DarkTemplar_What",-1)`）→ `Wait` 语音时长（2.6s）→ 刀声 → 全场红字 → 目标私息。**函数顶部不要放公用出刀声**

**第 10 步：私密消息路由** —— 击杀/治疗目标的私息走 `gf_BHNotify`（目标非真实在线玩家时改发 `gv_host`，solo 可见；真实玩家只发本人），否则 solo 局「只有音效没有文字」。

**第 11 步：静态校验 + 打包部署** —— 逐函数落点 + 配平 + 条数校验 → `boot2_build.py` 打新文件名 → scp → 游戏内验证（帮助面板、角色卡、`-prefer`、探员线索、死亡信息、残局判定）

### 措辞约定：访问 vs 造访（shw110/111 沉淀）

- **自设/新角色的文案统一说「访问」**，不说「去了某人家中」「整夜未出门」「造访」。行为兜底规则写成一句特性行：**「如果目标一没有行动，则视作访问自己。」**（影武者 SHWBOX9）——有了它就不需要再解释「未出门」分支。
- 已按此措辞改写的键：影武者 SHWMODE1/2、SHWBOX7、SHWDEST1-3；观察者 GCZABIL（=「每晚观察一个人，获知有哪些角色访问了他。」）、GCZDESC、GCZNONE、GCZNOSELF、GCZACH。
- **原图自带的「造访」措辞保留不动**（用户 2026-09 明确）：`4A05D9F1`/`B9374B9B`（造访按钮标题）、`63403919`/`65E3235B`/`A14EF820`/`A5E3465E`/`D881AB31`（女巫控制与低语提示）、`C48670E6`（庇护者描述）、`DocInfo/PatchNote110`。不要顺手全局替换。

### 夜晚镜头体系（gf_NP*Camera，shw107/108 沉淀）

夜晚相机触发器 `gt_NPNightCamera` 启用期间，一个分发块（约 75003 行）按角色把每个玩家指派到一组固定循环机位 `gf_NP*Camera`：Dead / Jail(1,13狱警等) / Authority 政府厅(1,12)(1,19)(3,12) / Panorama 全景(1,2)(1,6)(3,7)**(3,13)** / Walk 街道 / Nature / Warehouse(2,5池非9) / Church(1,7)(1,14) / Evil(1,10)(3,4)(3,8)(3,10) / Paranoid(1,15)(1,17)(3,11)(3,14) / Stalker(1,4)(3,1)(3,5)(1,27)(1,28) / **Vantage 高点窥视(1,8)(1,16)(3,9)(1,31观察者)(3,31影武者)**。

- 新角色**必须**在分发块里指派一个镜头组，否则该角色夜晚没有专属循环镜头（无报错，纯缺失）。
- 原图遗留缺口：**史官 (1,30) 至今没有任何镜头组**（用户暂未要求补）。
- 组的选择按气质套用现成主题即可（用户认可：影武者/观察者=监视者的 Vantage，堕落审判者=警长的 Panorama）。

### 行动面板与开关按钮（shw110 沉淀）

- 双目标按钮 [5]/[6] 在 gf_ASShowBox 前的创建函数（约 39360）定位：`[5]` anchorTopRight **x=60（右）**、`[6]` anchorTopRight **x=120（左）**。点击处理在 `gt_ASActionButtonA/BNeutral_Func`（A=[5]→action[0]，B=[6]→action[1]）。视觉上「目标一在左、目标二在右」需**只对影武者**在 `gf_RAShadowActions` 里用 `DialogControlSetPosition(PlayerGroupSingle(lp_player))` 对调 x（120/60），不改写入槽位、不影响共用 [5]/[6] 的其他角色（巴士司机等）。
- 「开关」按钮（`gv_switchButtonItem`，tooltip 键 `94249CFE` 限定名单）由 `gt_ASSwitchButton_Func` 按角色分支处理（(3,15)冤魂 / (3,14)瘟疫 / (3,3)小丑 / **(3,31)影武者**）。新角色要支持开关：①在 `gt_ASSwitchButton_Func` 加角色分支（切换变量+播报状态）②在该角色 `gf_RA*Actions` 开头 `DialogControlSetEnabled(gv_switchButtonItem, …)` 启用并顺带播报当前状态（=每夜开始的状态提示，影武者借此实现模式提示）。
- 共用 `gv_e5BC80E585B3` 开关变量的角色（小丑/冤魂/影武者）互不冲突，分支各自独立。

### BankList.xml —— 「进图即清档」的真正根因（shw137 定案，2026-09-11）

**现象**：私有发布的改版图每局把存档重置（重新输名字、积分归零）。探针实测（`tools/bank_probe_build.py`，bank `SHBKPB`）本地与线上一致：任何时刻 `BankLoad("MBank13", 1)` **都返回空档**（`BankSectionCount=0`），但 `BankExists= true`、`BankSave` 正常写盘、文件就在硬盘上；`BankWait`、轮询重载、纯读取等待、补签名（两种 authorID 算法）**全部无效** —— 不是身份/时序/签名问题。

**根因**：引擎在地图加载时按包内 **`BankList.xml`** 预加载 bank，**不在表里的 bank，`BankLoad()` 永远读不出内容**（写入不受影响）。原图包 35 条（`MBank13`、`key` × 玩家 1–15），而我们的构建包只剩 5 条战役默认项（编辑器只在用 **GUI bank 动作**时登记条目，手写 Galaxy 不会）→ 读到"未预加载的空 bank" → 原图逻辑按新玩家处理 → 组装空档并保存 → 每局清档。

**修复（两件事，缺一不可 —— 已进管线）**：

1. **包内必须有 `BankList.xml` 声明**（预加载表，缺了 `BankLoad` 永远读不出内容）：

```bash
python3 tools/banklist_fix.py work/boot2-<name>.SC2Map            # 写回原图的 BankList.xml（参考 data/BankList.original.xml）
python3 tools/banklist_fix.py work/boot2-<name>.SC2Map --check    # 回读校验（断言 MBank13/key × 玩家 1..15）
```

2. **`BankLoad` 之后必须 `BankWait` 同步**（预加载是**异步**的，t=0 直接读会拿到空档；补上表只解决"能不能读"，"何时读完"要靠同步）：

```galaxy
    BankLoad("MBank13", lv_a);
    gv_bank[lv_a] = BankLastCreated();
    BankOptionSet(gv_bank[lv_a], c_bankOptionSignature, true);
    BankWait(gv_bank[lv_a]);          // shw138：等预加载/选项生效后的读取完成（放在 BankOptionSet 之后）
```

- wait 必须在 `BankLastCreated()` **之后**（dbg2 曾把 `BankWait(gv_bank[lv_a])` 放在赋值前，等的是空句柄 → 无效）；`gv_key[...]` 同理。
- **实证对照（dbg10 vs dbg11，同一份脚本只差 wait）**：dbg10 无 wait → `L: sc=0`、2 秒后才 `sc=2`；dbg11 有 wait → **`L: sc=2 seI=1 vB=" dddd"`（t=0 即真档）**，用户实测**不再要求输入名字** ✓。
- 参考表 `data/BankList.original.xml` 取自原图包；工具断言 `MBank13`/`key` 覆盖玩家 1–15、打包后 `Triggers`/`CustomLogic.galaxy` 成员仍在。
- 结论修正：shw134「引擎 BankVerify 失败即清空」只是**表象**（未预加载的 bank 本来就空，`BankVerify` 自然 false）；`BankOptionSet(c_bankOptionSignature,true)` 与存档重签**都不是**读档的必要条件。社区佐证：GA地精研究院帖「纯galaxy代码的方式不能读取bank？[已解决]」= 拆包发现 `BankList.xml` 机制 +「读取内容之前必须先加一条同步」。

### 打包管线（shw96 事故沉淀，shw141 固化为一键工具）

**boot2 系列只能用「复制上一版 + `sc2map.write` 直写 CustomLogic.galaxy」，绝不能用 `tools/sc2pack.py`**（shw96 事故：触发器读到旧脚本 → 「脚本读取失败：无法找到函数」+ UI layout 红字）。标准做法：

```bash
python3 tools/boot2_build.py --out work/boot2-<name>.SC2Map      # 四件套 + 全部回读断言
```

四件套（细节见上节）：①复制基线 `work/boot2-user.SC2Map`（**不要覆盖**）②直写工作区脚本（打包前自动跑 `galaxy_lint.py`，不过不打包）③合并 `strings-*.txt` → 包内 **zhCN** 表（漏 = 界面满是 `Param/Value/XXX` 原始键；`sc2map.GAME_STRINGS` 指的是 enUS，别拿它校验）④`banklist_fix.py` 写回 `BankList.xml`（漏 = 每局清档）。

- 回读断言：`Triggers` 在、`BankList.xml` 在、脚本含 `BankWait`、**`MUST_HAVE_KEYS` 全部存在**（缺任一即退出码 1）。只有基线已是上一版成品图、且确认键齐全时才用 `--skip-strings`。
- **文案源文件铁律**：`strings-*.txt` 一行一个 `键=值`；**一行粘两个键会静默吞键**——`strings-gcz.txt` 曾把 `GCZBOX2` 与 `GCZTNAME` 粘一行，导致天谴菜单名在所有构建里都显示原始键、`GCZBOX2` 值被污染（正是 `MUST_HAVE_KEYS` 抓出来的）。
- **boot2 包内结构**：`Triggers` + 2.7KB `MapScript.galaxy`（只含 `include "TriggerLibs/NativeLib"` 与 `include "CustomLogic"`）+ 完整 `CustomLogic.galaxy`；**触发器链引用 CustomLogic 里的函数**，故回读校验看包内 `CustomLogic.galaxy`（不是 MapScript）。
- **`sc2pack.py`**（rogue 等独立图用）把 galaxy 塞进 MapScript 并剥触发器 → boot2 缺触发器函数必炸，两条管线不能混。

### 胜利图（结算画面）体系（shw98/99 沉淀）

分发链：`gf_CheckEnd` 返回码 → `gf_EndGame(lp_end)` → 每码一个 `gf_ET*Win()`（约 20193–21390 行）→ 内部 `gf_WinScreen("<图>.dds", 玩家)` **全场同一张图** + 逐玩家胜利者判定（`gv_won=true`、bank 胜/败场计数 `[6]/[7]`、胜负按钮文案）。图码对照：1城镇 WinTown / 2黑手 WinMafia / 13三合 WinTriad / 3SK WinSerialKiller / 5生存者 WinSurvivor / 6小丑 WinJester / 7女巫 WinWitch / 8纵火 WinArsonist / 9处刑者 WinExecutioner / 10失忆 WinAmnesiac / 11邪教 WinCult / 12杀人狂 WinMassMurderer / 14审计 WinAuditor / 15法官 WinJudge / 16审判者+影武 / 17瘟疫 WinplaguerReal / 18冤魂 Winpossessio / 19系命 Winlifebonder / 20赌鬼 Winpossessio / 4无人 WinNobody。

- **图的位置**：原图那批（WinTown/WinMafia/…）在 `mm2.SC2Mod` 依赖里；**自加图放地图归档根目录即可覆盖/新增**（shw98 的 `WinCorruptInquisitor.dds`、`WinShadow.dds`）。
- **DDS 规格**（与作者自加图一致）：732×376、24bit 未压缩、无 mipmap，文件=128 字节头+RGB 字节（825824 字节整）。**头里的 mask 标注与实际字节序不符——按「bytes→PIL RGB」直读直写颜色即正确**，转制方法：`hdr = 旧图[:128]` + `Image.open(png).convert('RGB').resize((732,376)).tobytes()`。出图用 GPT 时给参考图（`~/win-ref/` 四张解包 PNG）+ 三条约束：无人物只留一件道具、涂鸦泼漆大字、混凝土墙底。
- **新增致命系角色的胜利三件套**：①`gf_CheckEnd` 主链加/并入判胜块（**必须用 shw96 语义**：城镇0+其他致命系0+邪教0+`(黑+三)<=1`+自己≥1，不要复刻原版 `黑=0&&三=0`）②`gf_ET*Win` 的胜利者名单加自己（漏了会像影武者 shw98 前那样「赢了却被记败场+失败音效」）③专属图 dds 入包+分支接线。
- **return 16 是共享块**：主链/2人残局/平局区三处 return 16 都进 `gf_ETCorruptInquisitorWin`，该函数服务一群中立（生存者/小丑/赌鬼/女巫/处刑者/失忆者/审计官/杀人狂/审判者/影武者）。函数开头先扫描存活定胜者（`lv_ci`/`lv_shw`，审判者优先——其雷击无视无敌），图按胜者分支；新角色并入时同步改扫描、名单、图分支三处。
- **已知死代码**：`gf_ETGamblerWin`（WinJester）无调用者；赌鬼实际走 `gf_ETE8B58CE9ACBC` 与冤魂共用 `Winpossessio.dds`；作者做好的 `Wingambler.dds`（骰子图，风格偏离原版）躺在包里未接线。
- 2 人残局区（~15910）与平局区（~16115）的 return 16 独立于主链，改主链语义时不要漏了核对这三处的一致性（shw99 后主链=审判者/影武者 `(黑+三)<=1`，残局区维持原样）。

### Galaxy 语言层陷阱（生成代码惯例）

- **SoundLink 的类型是 `soundlink`**（不是 `sound`）。自定义函数收音效参数必须声明 `soundlink`，写错则所有调用处「参数类型同函数定义不匹配」并连带整个脚本解析失败（整图报废、游戏内红屏）。
- **插入 while 广播循环要在声明区补** `playergroup autoXXX_g;` / `int autoXXX_var;`（漏声明 = 解析函数行出错）。
- **多函数共用的字符串不能做唯一锚点**（`DB5AD8F8`、`gv_deathDesc[...] = true` 在多个杀手函数出现）：锚点必须带函数特有上下文（角色号判断行、专属文本键）。
- **python 补丁断言失败时同命令块里后续的 commit/打包照常执行**——先单独跑补丁确认 exit 0 再提交打包；曾连续两次只提交了 strings、代码没进包。**heredoc 里裸换行就是新语句**：`python <<EOF` 失败后下一行 `scp && git` 照样跑 → 脏包被部署。打包+部署+提交要显式 `&&` 链接。
- **验证断言别写子串包含**：`s.count('(16) || (30) || (31))) {')` 这类短串会同时命中浏览与映射白名单（互为子串），count 是 11 不是 6——断言前先确认模式唯一。
- **白名单行的右括号层数不一致（shw84 事故）**：11 处编辑白名单 if 行并非统一 `== X)))` 结尾，部分行是 **4 层**（`== X))))`）。用统一子串替换会把 4 层行削掉一层 → `if` 解析失败、**整个脚本读取失败**。摘 OR 项必须**逐行**：定位含该项的行 → 去掉 ` || (…)` 整项 → 逐行断言 `()` 配平；且配平检查必须**先剥离字符串字面量**（61017 行含 `"("` 字面量，裸计数是已知误报）。
- **锁定???随机系机制（枷锁/血锈/捕风捉影）**：预览列表（`gv_rolesMenusItem[2]`）是**静态文本**，??? = 直接 `DialogControlAddItem(roleNameArray[8][1])`（随机组 8/1 = ???）。槽位经 bank 填 (8,1) 会被 `gf_VLoadSaveSlot` 校验（category>5）清零——原图 sotd 系是**绕过 bank 直接写 slots**。捕风捉影方案：真阵容进 slots（开局正常发牌）→ VLoadSaveSlot 后 `RemoveAllItems` + 重填 15 个 ??? + bank 掩写 (8,1)；从 11 处白名单摘掉 variantSelection 即锁定编辑。
- **断言过度也会误报**：①`assert 'KEY' not in s` 全文件禁键——键可能在别处有合法用途（`F0A13008` 是审查官能力文本，不能因一次误用就全文禁令）②GameStrings 行尾是 `\r\n`，比对空值键要 `l.replace('\\r','')` ③`s.find('函数名')` 命中的是**首次出现**（可能是文件前部的原型声明），定位调用点要用带 `();` 的完整调用文本或在函数行号区间内找。
- **斜体（shw87 已实证）**：SC2 富文本无斜体直标签（`<i>` 无效），斜体 = 字体样式 Italic 标志 + `<s val="样式名">`。地图 `NewFontStyles.SC2Style` 已加 `ModItalic`（fontflags="Italic"）/`ModItalic2`（styleflags="Italic"），**两种都渲染为斜体**。玩家输入 `-rename <i>x</i>` 经 `gf_BHItalicize` 改写为 `<s val="ModItalic">x</s>`（大小写闭合标签都处理），可与 `<c val>` 叠加；字体用 `#FontStandard` 保证 CJK。带标签的名字参与「按名字喊话」匹配时需照原样输入标签。
- **二改红线（无原作者授权）**：**严禁修改/删除原图硬编码 handle 管理员链的任何既有分支**（~56944 起的 87 个，只能**追加**）；给 handle 加权限一律走白名单追加。日后公开发布前必须收回测试放开项：prefer 会员/积分门（65440/65481）、大厅电脑计入（56020）等 `c_bhSoloBuild` 旁路。**存档迁移**：bank 命名空间绑定发布作者，玩家原档（`key`、`MBank13`）留在原作者目录、脚本无法跨命名空间读取（引擎沙箱），迁移 = 把两个 bank 复制到改版作者目录即可（**无需重签**，见下条；重签工具 `tools/bank_resign.py` 备查）。
- **不验签设计决定（shw139/143，取代 shw134 的临时旁路）**：目标是**原图存档直接复制即可用**（跨命名空间迁移、不重签）。两处一起关：①脚本侧三处 `BankVerify` 门槛（QQ/gift/I，3676/3680/3684 附近）加常量 `c_bhNoSigVerify = true`（条件前置，`BankVerify` 本身不执行）②`gt_Init2` 银行循环的 `BankOptionSet(gv_bank[lv_a], c_bankOptionSignature, …)` 改 **`false`**（引擎侧不签也不验；若为 `true`，引擎对**原作者签名**的档验签失败并清空内存内容 → 脚本看到空档 → 走新玩家分支 → 界面报「存档已重置」）。**原有的 `<Signature>` 行保留不动做兼容**，防篡改由地图级 Checker 承担（`Math=(points+1)×(points+3)` 等）。
  - 历史背景（shw134，已被上条取代）：曾以为引擎 `BankVerify` 失败即清档是唯一根因，只对 `c_bhSoloBuild` 短路放行；后经 BankList 定案证明那只是表象。
  - **迁移操作**：把 `key`、`MBank13` 两份档复制到改版作者命名空间即可（私有发布时作者 = 发布者本人 toon），无需重签。重签算法（`tools/bank_resign.py`）= SHA1(authorID + playerID + bankName + Σ(按名排序的 section.name + Σ(按名排序的 key.name + "Value" + 类型名 + 值)))，已实测可复现引擎签名。
- **测试指令**：`-reveal`（`gt_BHRevealRoles`，仅主机、游戏开始后）私密列出全部玩家**带色名字**（电脑N，N=玩家编号；投票面板左侧是楼层序，与编号无关）+角色名，用于验证调查结果/案底等
- 运行期报错先分新旧：`triggerControl(值:0)`、`StringWord(值:0)`、`CameraSetBounds region(值:0)`、`gv_roll点冷却 int[2] 越界` 等均为基线/单人测试固有，不是新改动引入

### 单人测试模式（-solo）

**地图起始门槛 = 4 人**：`gf_OS...` 初始化里 `PlayerGroupCount(gv_currentPlayers) <= 3` 会清空角色串（`lv_str[0]`/`lv_str[2]` 全 0）→ `gv_rolesAssigned != lv_b` 校验失败、开不了局。变体预设按人数逐档填写（~50188 起 `PlayerGroupCount(gv_tempPlayerGroup) == N` 分支），所以 1 人用变体开得起来；**自设路径**才被门槛卡住。

数据模型：

| 字段 | 含义 |
|---|---|
| `gv_categoriesArray[槽]` | 该槽选择的角色**池**（1 城镇 / 2 黑手党 / 3 中立 / 4 随机 / 5 三合会 / 8 随机组） |
| `gv_rolesArray[槽]` | 该槽选择的**角色号** |
| `gv_rolesAssigned` | 已选角色数量，必须等于非空槽位数 `lv_b` |

`-solo` 做的事（聊天输入，shw53 起定型）：①`gv_soloTest = true` 放行两处 `gv_rolesAssigned < / > PlayerGroupCount(...)` 校验（条件加 `&& (gv_soloTest == false)`，~43462/43476）②`TriggerEnable(gt_Prefer, true)`。

**不自动填角色**（`gf_BHSoloFill` 已删；shw51 的「补满 15 槽」方案废弃——填满后虚拟补位判「无空槽」反而不补人）：角色由测试者在自设里手动配置，空槽交给 `gt_Init2` 虚拟补位。命令注册 = `TriggerCreate` + `TriggerAddEventChatMessage(trigger, c_playerAny, "-solo", false)`，在 `InitTriggers` 调用 `gt_BHSolo_Init();`。

### 占位玩家与 -prefer 优选

`c_bhSoloBuild`（脚本常量，测试构建 = true）：

| 位置 | 作用 |
|---|---|
| `gt_Init2_Func` **实现开头** | 把 1~15 号**空槽位**加入 `gv_players`/`gv_currentPlayers`/`gv_alivePlayers`，名字「电脑N」，随机房屋。**必须在主玩家循环之前**——曾放在函数末尾（隔了 Wait 2+3+5 秒），发角色/建夜间面板时玩家还没补齐，夜间面板只剩自己一行 |
| `gt_Init2_Func` 玩家收集过滤 | 允许 `c_playerTypeComputer` 也算玩家 |
| `gt_DetectLeave_Func`（约 63356 行） | 不再把「未激活」当成「离开」（否则虚拟玩家会被判退场） |

`-prefer`（原图自带的优选命令，按**拼音**匹配 `gv_roleNameInput[池][角色]`）：

- 命令：`-prefer yingwuzhe`，多个用逗号（`-prefer yingwuzhe,shimin`）
- 原图限制：需 `gv_oP[玩家][1] == true`（会员），非会员扣 500 积分；测试构建下两处已放开（`gt_Prefer_Func`，~65210/65251）
- **新角色必须设拼音名**：`gv_roleNameInput[池][角色] = "xxx";`（影武者 = `yingwuzhe`），否则 `-prefer` 找不到它
- **测试构建下 prefer 必中（预锁，shw77 起）**：真实分发在 `gf_OSComputeOptions`（同函数兼营大厅几率模拟，`gv_emulate` 区分），玩家按随机顺序处理、无 prefer 的电脑随机占槽，原 solo 强制块轮到时槽已被占即静默落空（"将被首选"只是登记，不代表生效）。现为 `gf_OSRandomize` 之后预锁：`lv_bhPreferSlot[玩家]=槽`/`lv_bhReserved[槽]`，有 prefer 者强制改抽锁定槽、无 prefer 者抽到被锁槽拒绝重抽。**新增角色无需改动**，拼音存在即可被锁。

## 环境

| 项 | 值 |
|---|---|
| 远程 | `ssh -p 2222 administrator@100.94.140.84`（WSL，`/mnt/d` 即 `D:`） |
| 游戏 | `D:\StarCraft II`，版本 5.0.15.97579 |
| 编辑器 | 必须由用户在交互式桌面手动启动（SSH 启动会 D3D 报错） |
| 打包工具 | `tools/sc2map.py`（读/写 MPQ）、`tools/mpq.py`、`tools/mpqc/mpqtool` |
| 文本工具 | `tools/bh_roles.py`、`tools/bh_text.py` |

## 文档地图

| 文件 | 内容 |
|---|---|
| `AGENTS.md` | 本文件：工程约定、铁律、标准循环 |
| `docs/ROLE-PIPELINE.md` | 添加/修改角色的完整操作手册（含位置速查） |
| `docs/BLACKHAND-REWRITE.md` | 重写设计与实施进度 |
| `docs/BLACKHAND-ORIGINAL.md` | 原图逆向笔记（流程、计时、数据模型） |
| `docs/GALAXY-PIPELINE.md` | Galaxy 直写、打包、启动链路技术细节 |
| `docs/SHADOW-ROLE.md` | 影武者实现规格（作为"新角色"样板） |
| `docs/HANDOFF-SHADOW.md` / `docs/HANDOFF-NEXT.md` | **历史交接文档（已过期，停在 shw85 前后）**：影武者接入、槽位误判、自设面板双硬编码、目标转换规则等背景资料，只作追溯 |

### 审判台免死与处决点体系（shw114 沉淀，天选者 3/32）

- **处决只有一个收口 `gf_EExecution`**，但 9 个调用点：`gf_CheckVoteWin` 直决 lynType（3 处 lv_winner + 1 处缩进 20）、marshalled/court、`gf_Trial` 的 `trialDefense==false` 自动处决（2 处）、`gf_TrialVoteResults` 有罪判决、marshalled 的 `lv_hit`。**每处单独包守卫**，行级精确匹配包 else（不要子串替换——20 空格行含 12 空格子串）。
- **审判有罪判决的免死走「重定向到无罪分支」**：`gf_TrialVoteResults` 的 `if (有罪)` 追加 `&& !protected`，免死者在 else（无罪）分支开头揭露——无罪分支自带「放下台走回座位+白天继续投票+结束进夜」的完整恢复，**不要**在有罪分支跳过 EExecution（白天流程会悬死）。直决路径的免死用 `gf_TXSpare`（揭露+走回+复制 EExecution 日终尾巴：ASEndActions/TriggerStop(gt_DaySequence)/CheckEnd→NightTransition）。
- **「当天不能再投」= 在审判发起点禁投**（CheckVoteWin 各 lynchType 块 / DaySequence 副本 / `-try`）查 `gf_TXSparedToday` → 广播提示。**跳过审判必须同时恢复白天（shw127 事故）**：发起点此时已停投票面板、（trialPausesDay 时）把昼长改成 90001 并暂停计时器，只广播不恢复 = 白天永久卡死、不上台、模型冻住。恢复用 `gf_TXResumeDay()`（解除暂停+还原昼长 + UIClearMessages + trialOn=false + `gf_ASStartVote()`）。`-try` 无暂停/停票前置，只广播不恢复。
- **洞察机制（shw144）**：`-guess` 猜对时（判定在雷击结算块 `gv_roleNameInput[目标] == gv_txGuess[自己]` 处）`gv_txGuesses[玩家] += 1`：第 1 次私信 `TXGOD1`（你的洞察获得了神明的认可。）；第 2 次私信 `TXGOD2`（…众神给予你一次额外的雷击机会。）并 `gv_txStrikes[玩家] += 1`。**只判 `== 2`** 即天然"整局最多一次"；特性行 `TXBOXGOD` 挂在角色卡两处副本（`TXBOXGUESS` 后、`TXBOXFIXED` 前，必须同步）。
- **雷击次数的设计决定（用户 2026-09-11 定稿，不要"修正"）**：默认 **3 次**（作者遗留 `47843C61` 是 5 次；用户判断「真伤 + 免死同源」下 5 次 = 每夜出手 + 每天免死，故削到 3）。**选项「雷击四次/五次」保留**（`gv_roleOptions[3][32][2]/[3]`，默认关闭）；洞察 `+1` 可叠加，极限 **6 次**，用户接受。改默认值/删选项/加封顶都要先问用户。
- **`-guess` 三重前置 + 猜测绑定目标（shw147/148）**：0 余额时 `-guess` 在 `gt_TXGuess_Func`（~66230）**存储前就 return**；结算侧另有 `gv_txStrikes <= 0` 守卫、`gv_txBlessDay` 只在 `else` 写 → **无雷击不可能产生祝福**（不给按钮只是第三重保险）。`gv_txGuessTarget[玩家]` 绑定当时选中的目标，结算要求 `== gv_action[..][0]`，否则私信 `TXGUESSVOID`——不绑定会出现「猜 A、祝福来自杀 B」。取消猜测与每次真结算都要同时清 `gv_txGuess` 与 `gv_txGuessTarget`。
- **警长的「可查出X」开关体系与探员枚举（shw149 沉淀）**：
  - **开关槽位**：警长 = 池 1 / 角色 2，`gv_roleOptionExists/Important/Text/Options[1][2][i]` 四件套。原图 0–6 依次为 黑手D三合会 / 连环爱手(3,1) / 纵火者(3,5) / 协教徒(3,8,3,10) / 爱人狂(3,9) / 瘟疫散布者(3,14) / 冤魂(3,15)；自加 **7=影武者(3,31)**、**8=天选者(3,32)**、**9=堕落审判者(3,13)**，默认全部 `true`。
  - **消费点**：`gf_SequenceKills` 警长段（约 13575–13645）是一条 **if/else 链**，每项形如 `if ((gv_roles[gv_visitation[lv_a]][1] == 3) && (gv_roles[gv_visitation[lv_a]][0] == N) && (gv_roleOptions[1][2][i] == true))` → 播报「你的目标是一个 <角色>!」；链尾兜底 `D125BE9B`「你的目标不可疑。」。**漏接分支 = 警长查到该中立致命却报「不可疑」**（堕落审判者当年就是这个状态）。
  - **帮助面板只画 0..6**：`gf_MakeHelpMenu` 两条选项行循环上界 `autoCD856455_ae`（角色卡分支）/`auto2687B3BB_ae`（随机组分支）原为 **6**，须放宽到最大槽位号，否则新开关**看不见**（影武者 `SHWSW` 因此隐身一整个版本）。**自设面板（`gt_OSCheckboxes_Func`）只支持 0..6**：行用 `gv_rolePanelItem[lv_a+2]`/`[lv_a+7]`，该数组 `int[14]` ⇒ **索引 7/8/9 无法勾选**，只能帮助面板可见 + 默认生效。
  - **卡片特性行**：警长卡特性链在同一函数（~41414–41475，「犯罪记录」行 `A5BA7399` 之前按 `gv_roleOptions[1][2][i]` 逐项 `if (lv_c == true) 追加 <n/>- 行 else 首行`），新增开关**必须同时补特性行**（影武者当年缺的就是这行）。
  - **撰写补丁铁律**：往既有槽位序列尾部追加新槽位时锚点行必须**保留**——写 `old → old + new`，不要 `old → new`（shw149 首次补丁把 `gv_roleOptionsText[1][2][7] = SHWSW` 整行换掉 → 影武者开关文字变空，靠落点打印才发现）。
  - **探员枚举**：类别线索 = 「你的目标…」+「他像是个 A、B、C」两句，**共享键**（判断力 `BD8909A7` + `4881041F`；风衣 `CE7E2D14` + `F2239D82`）。新增角色**要加进对应类别枚举**，否则玩家永远猜不到（天选者就漏了）。**规则（用户明确）：被单独点名的应是中立致命之类值得怀疑的角色，城镇角色不写进去**——观察者是城镇故不进风衣名单，阵营由线索首句覆盖。基线 `89AB9993` 与 `4881041F` 同文但**零引用**（死键），只覆盖真正被引用的那个。
- 新命令注册样板：`gt_TXGuess_Init()`（TriggerCreate+TriggerAddEventChatMessage）+ 在 `InitTriggers` 跟随 `gt_Prefer_Init();` 调用；输入解析用 `StringReplaceWord(StringSub(EventChatMessage(false), …), " ", …)` + `StringCase(s,false)` 转小写后与 `gv_roleNameInput[池][号]` 比对。
- 拼音匹配循环 3 处随 >30 号角色放宽：Prefer `autoA667E0B3_ae`、Blacklist `auto06C73FD2_ae`、Init2 黑名单校验 `auto6D231E76_ae`；另 `gf_OSGenerateChances` 5 处几率循环 + 槽位加载校验 `> 31` 同步放宽（**注意不是** `gf_OSLoadBase64`/`gf_OSInitializeOptionsScreen`/`gf_OSCloseOptionsScreen`/`gt_OSVariantsMenuConfirm` 四处——见下条 shw115）。
- 验尸官死因字母码：扫描块（~13809）逐字母 if 链加分支；`T`/`X` 已占用，天选者用 `G`。
- **循环上界放宽前必须确认循环体访问的数组身份（shw115 事故）**：曾把 4 处 `auto*_ae = 31→32` 一律当角色循环放宽，实际 `auto3508CF23`(gf_OSLoadBase64)/`autoD02CB81C`(gf_OSInitializeOptionsScreen)/`autoAA8D2539`(gf_OSCloseOptionsScreen)/`auto74E062BB`(gt_OSVariantsMenuConfirm) 遍历的是 **`gv_optionsPanelItem`（`int[32]`）** → [32] 越界 ScriptError 打断选项屏初始化，整个自设/变体选择框消失；修正=回退 31。教训：**改上界前先看循环体第一行访问的数组名与维度**（`gv_optionsPanelItem[32]`、`gv_blacklist[16][26]`、`gv_roleChance[9][41]`），只有角色数组（roleNameArray 等 `[6][41]`）能放宽。`auto6D231E76` 是黑名单分词槽循环（写 `gv_blacklist[..][lv_b]`，维度 26），31 本就越界属基线噪声，勿动。
- **帮助面板卡片底色（shw146）**：F1 面板顶部那排小卡（`gv_roleHelpPanelItem[lv_x][0]`，`ui_waiting_playericon.dds`）底色由 `gf_MakeHelpMenu` **逐角色硬编码 `Color(...)`**，中立池链**只写到角色 16** ⇒ 新增中立角色（31/32）保持创建色 = **白**。补法：角色 13 分支之后、`CreateDialogItemLabel` 之前插 `if ((lv_role == N))`，设 ①`lv_t[5] = StringExternal("Param/Value/<角色>CARD")`（内容形如 `<c val="RRGGBB">`，卡片右下角**拼音首字母**上色，配套 `01EDEAB5` = `</c>`）②`libNtve_gf_SetDialogItemColor(gv_roleHelpPanelItem[lv_x][0], Color(R,G,B), PlayerGroupAll())`。`Color` 0–100 分量（`C0C0C0`→`75.29`）。`autoDDE9B838` 从 32 **往下**数 ⇒ 这两张卡在最左。
- **克隆卡片分支时锚点必须含分支闭合（shw117 事故）**：(3,32) 分支曾被插进影武者 (3,31) 分支**内部**（SHWBOX5 条件之后、SHWBOX7 无条件尾巴之前）——两层条件互斥 → 死代码（角色卡全空），而配平/条目数校验都发现不了（嵌套不破坏计数）。**正确锚点 = 影武者分支 `SoundPlay(SoundLink("Hercules_What"...));` 与其闭合 `}` 之后**，并打印前后各 10 行确认这个 `}` 闭合的是影武者分支。
- **数量型文案 + 选项开关（shw120）**：数字随开关变化的文案不要写死一个键——按选项分支选 3/4/5 三个键（卡片）或 `IntToText` 组装（夜 tip「你有X次…」）。数值本体（`gv_txStrikes`）在**角色卡分支里按选项赋值**（卡片函数开局每玩家执行一次，选项此时已定稿；帮助面板以 lv_a=0 调用同函数，写 `[0]` 无害）。`-guess` 无参数=取消：聊天注册只挂 `"-guess"`（不带尾空格），解析 `StringSub(msg, 7, …)` 空串即取消——一个注册覆盖带参与不带参，避免双事件重复触发。全场红字 = 键内嵌 `<c val="FF0000">`、`gf_CBSystemMessage` 的 Color 参数保持 `(0,0,0)`（同原图 90AC4EBA 杀人广播）。
- **公屏文本必须自带 `<s val="ModLeftSize16">…</s>`（shw129）**：`-magnify` 的实现是 `gf_CBMagnifyText` 对公屏对话框里**已渲染文本做样式标签字符串替换**（`gf_ELAddMessage`/`gf_CBSystemMessage` 收到 `gv_magnified` 标志时按大小档替换标签）→ 没带标签的自加广播不跟随放大。原图模板 = `<s val="ModLeftSize16"><c val="FF0000">文本</c></s>`；跨键拼接的整行（如 TXREV1+名字+TXREV2）开标签放首键尾、闭标签放末键尾。
- **特性行换行规范（shw124 事故）**：原图没有「纯换行」共用键。给 `gv_roleBoxText[][2]` 追加多行时把 `<n/>` 写进**每个键内容开头**，代码侧逐键 `+ StringExternal(...)`；不要复用任何原图键当换行前缀（先解包确认键内容——`4467A310`/`1045F9FD` 是「你拥有夜间无敌」行，被误当换行键后每行都会重复这句）。
- **`gv_roleNameArray` 元素是 `text` 不是 `string`（shw123 事故）**：临时变量接 `roleNameArray[..][..]`（StringExternal 返回 text）必须声明 `text`，否则脚本读取失败「不正确的类型（不允许进行隐式强制转换）」并红屏。配套：text 判空用 `== null`（不能 `== ""`）、`lv_r = null;` 初始化、拼接直接 `+ lv_r +`；`StringToText()` 只用于 string→text。注意 `gv_roleNameInput` 是 string（拼音比对不受影响）。

### 成就体系（shw150 沉淀，含自加成就「见微知著」）

两套数组（都在 `gf_CDisassembleMainBank`/`gf_CAssembleMainBank` 的 `I` 段里序列化，见 18575/18849 附近，循环上界 0..70 自动全量，**新增索引不需要改存档格式**）：

| 数组 | 维度 | 用途 |
|---|---|---|
| `gv_bankRoleAchievements[16][9][21]` | [玩家][池][角色号] | 角色向成就（以该角色获胜次数等）。**第三维只到 20** → 31/32 号角色**不能**用（越界，见铁律 9） |
| `gv_bankOtherAchievements[16][71]` | [玩家][成就索引] | 通用/事件成就。0–67 已用；5–8 被列表过滤（`(lv_d <= 4) || (lv_d >= 9)`），24/42 被排除；**自加用 68**（= 见微知著） |

**解锁三件套**（写在 `auto_gf_EndGame_TriggerFunc` 的胜利分支里，模板见索引 63/67 块 ~17320–17378）：

```galaxy
if ((gv_bankOtherAchievements[lv_a][68] == 0) && <条件>) {
    gv_bankOtherAchievements[lv_a][68] = 1;
    autoXXXX_g = gv_currentPlayers; autoXXXX_var = -1;
    while (true) {                                  // 全场广播（私密成就改成直接发 lv_a）
        autoXXXX_var = PlayerGroupNextPlayer(autoXXXX_g, autoXXXX_var);
        if (autoXXXX_var < 0) { break; }
        gf_CBSystemMessage((StringExternal("Param/Value/<前缀键>") + TextWithColor(PlayerName(lv_a), libNtve_gf_ConvertPlayerColorToColor(gv_playerColor[lv_a])) + StringExternal("Param/Value/<后缀键>")), autoXXXX_var, lv_a, 0, SoundLink("UI_BnetGameFound", -1), Color(0,0,0));
    }
    gf_GiveBonus(lv_a, 300);                        // 真加积分（gv_bankGeneralIntegers[玩家][3] + gv_points）
}
```

- **广播文案拆两个键**：前缀键 = `<s val="ModCenterSize16">`，后缀键 = `<c val="44FF88"> 赢得了成就 </c></s><s val="ModCenterSize16Bold"><c val="颜色">成就名</c></s><s val="ModCenterSize16"><c val="44FF88">!</c></s>`（照抄索引 63/67 的既有键形态；颜色用该角色/主题色）。
- **while 循环的两个变量必须补进该函数的自动变量声明区**（`playergroup autoXXXX_g; int autoXXXX_var;`，EndGame 的声明区 ~16493–16622），否则解析失败。
- **成就列表的名称映射链也要补**：约 59500 附近 `else if (autoE7789229_val == <索引>) { lv_x = StringExternal("Param/Value/<名称键>"); }`（在 67 之后追加）。名称键 = `<s val="ModCenterSize16Bold"><c val="颜色">成就名</c></s>`，**漏了列表里这一条就是空白**。
- 自加文案进 `strings-*.txt` 后，记得同时把键加进 `tools/boot2_build.py` 的 `MUST_HAVE_KEYS`（值要**带 `Param/Value/` 前缀**，与既有条目一致，否则回读断言会误判缺失）。

- **第二处名称链 = 管理命令 `-achieve <玩家名> <索引>`**（`gt_Achieve_Func`，需 `gv_oP[玩家][1]`，~60820，用的键与列表链**不同**）：漏补分支 → 该命令播报名字是 `null`（原图 67 号就缺）。过滤同列表；写入**无上界校验**（`-achieve x 99` 越界写）。这条路径可用来**实测成就播报**。

**存档兼容性（用户 2026-09-11 提问定案）**：`A2`（角色向）= 4 段×20 词、`A3`（通用）= **71 词**，都是**定长全量词表**（每次写满，与是否解锁无关，18583–18596 / 18586）⇒ **索引不越界就零兼容影响**（老档那些位本来就是 0）。**扩容**（>70 个通用成就 / 角色号 >20）要三件套：扩数组维度 + 扩读写上界 + **读取加空串保护**——`StringWord` 越界返回 `""`，`StringToInt("")` 会报触发器错误并**中断读档函数**（先例 18506；读档被打断 ⇒ 后面 Reports/Blacklist/胜场都不加载 ⇒ 看着像清档）。也可**新开 key/section**（如 `I/A5`，已不验签故无签名障碍）：只在一处判空、老结构不动，但**清理/重置路径（58817 清分、`gf_CDisassembleMainBank`、保存格）要同步清**。空位：**68 已用，69/70 可用**，另 17/34/62 亦空；5–8/42 被显示过滤排除。

**自加成就「见微知著」（索引 68，300 分，天选者 3/32）**：条件 = `gv_won` + 池3/角色32 + 存活 + `gv_txStrikes <= 0`（雷击用光）+ `gv_txGuesses >= 1`（至少猜对一次）+ `gv_txGuessBad == 0`（只要猜了就必须猜对）。为此新增 `int[16] gv_txGuessBad`（在 `gf_SequenceKills` 天选者块的**猜错**（TXGUESSBAD）与**作废**（TXGUESSVOID，换了目标）两处 `+= 1`；目标当夜已被别人杀死走 TXTGTDEAD，不结算、不记错、猜测保留到下一夜）。用户 2026-09-11 定稿：宁可放宽成「至少猜一次 + 猜了必须对」，不要求每次都猜（每雷击都必须猜对太难）。
