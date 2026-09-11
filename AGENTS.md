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

## 知识索引（AGENTS.md 放通用知识，专题在记忆里）

**本文件只放「每个任务都用得上」的铁律、标准循环与红线**；下列专题已迁入项目记忆，用 `ctx_search` 按表格里的关键词检索（不要凭印象改，先搜）：

| 要做的事 | 检索词 |
|---|---|
| 加/改成就、成就存档兼容、见微知著、影缝 | 「成就体系 见微知著 影缝 gv_bankOtherAchievements A3」 |
| 加/改变体预设、随机槽选项、座席排序 | 「预设系统 preset_gen 随机槽使能串 座席排序」 |
| 单人测试、虚拟占位补位、-prefer 优选 | 「单人测试 -solo 占位玩家 prefer」 |
| 新增/改造角色（11 步流程、清单、死亡三件套） | 「新增角色端到端流程」「一个角色要改的地方」 |
| 夜晚镜头组、行动面板/开关按钮、访问措辞 | 「夜晚镜头体系 行动面板 开关按钮 措辞 访问」 |
| 「进图即清档」根因、bank 预加载与 BankWait | 「bank 清档 BankList BankWait」 |
| 探员线索 / 案底 / 警长「可查出X」开关 | 「探员 警长 案底 可查出 gv_roleInvestigatorArray」 |
| 胜利图、结算画面、dds 出图规格 | 「胜利图 WinScreen dds 图码」 |
| Galaxy 语言陷阱、补丁与断言踩坑 | 「Galaxy 陷阱 soundlink 断言 白名单 斜体」 |
| 天选者(3/32) 规格、洞察/雷击/免死、新角色 UI 坑 | 「天选者 雷击 guess 洞察 卡片底色 换行」 |
| 审判台免死、处决点、跳过审判恢复白天 | 「审判台 免死 处决 gf_EExecution gf_TXResumeDay」 |
| 角色号 >30 要放宽的上界、死因字母码、命令注册 | 「上界 放宽 数组身份 shw115 验尸官 字母码 命令注册」 |

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
4. **改角色要同时改多处**：完整清单见「知识索引」里的记忆（搜「新增角色端到端流程」）。漏一处就"看起来没生效"。
5. **回退文件前先列出已完成的所有改动**，`git checkout` 会把未提交的清理一起还原。
6. **部署用新文件名**（编辑器打开中的地图被锁定），部署后确认 `scp` 无 `failed to upload`。
7. **每次改完立刻提交**，提交信息写清"第几步 / 改了什么"。
8. **测试地图统一放 `D:\StarCraft II\Maps\Test\`**，不要放桌面。
9. **角色号上限红线**：`gv_bankRoleAchievements` 维度是 `int[16][9][21]`——角色卡分支里 `[xx][1][角色号]` 用 21 以上的角色号会数组越界（ScriptError 41358）；31 号角色**不得**做银行成就检查。`gf_VLoadSaveSlot` 的槽位加载校验曾用 `> gv_townMax(30)` 把 31 号槽清零（预设列表空行+实际阵容缺人），已放宽为 `> 31`；再加大于 31 的角色号需同步放宽。

- **`SoundLink` 的参数类型是 `soundlink`**（不是 `sound`）：自定义函数收音效参数写错类型 → 所有调用处报「参数类型同函数定义不匹配」并连带整个脚本解析失败（整图报废）。

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

- 测试指令 `-reveal`（`gt_BHRevealRoles`，仅主机、游戏开始后）私密列出全部玩家**带色名字**（电脑N，N=玩家编号；投票面板左侧是楼层序，与编号无关）+ 角色名，用于验证调查结果/案底等。
- 运行期报错先分新旧：`triggerControl(值:0)`、`StringWord(值:0)`、`CameraSetBounds region(值:0)`、`gv_roll点冷却 int[2] 越界` 等均为基线/单人测试固有，不是新改动引入。

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

### 银行与存档（不验签设计决定 + 迁移）

- **不验签设计决定（shw139/143，取代 shw134 的临时旁路）**：目标是**原图存档直接复制即可用**（跨命名空间迁移、不重签）。两处一起关：①脚本侧三处 `BankVerify` 门槛（QQ/gift/I，3676/3680/3684 附近）加常量 `c_bhNoSigVerify = true`（条件前置，`BankVerify` 本身不执行）②`gt_Init2` 银行循环的 `BankOptionSet(gv_bank[lv_a], c_bankOptionSignature, …)` 改 **`false`**（引擎侧不签也不验；若为 `true`，引擎对**原作者签名**的档验签失败并清空内存内容 → 脚本看到空档 → 走新玩家分支 → 界面报「存档已重置」）。**原有的 `<Signature>` 行保留不动做兼容**，防篡改由地图级 Checker 承担（`Math=(points+1)×(points+3)` 等）。
  - 历史（shw134，已被取代）：曾以为引擎 `BankVerify` 失败即清档是唯一根因，只对 `c_bhSoloBuild` 短路放行；BankList 定案证明那只是表象。
- **迁移操作**：把 `key`、`MBank13` 两份档复制到改版作者命名空间即可（私有发布时作者 = 发布者本人 toon），**无需重签**。重签算法（`tools/bank_resign.py` 备查）= SHA1(authorID + playerID + bankName + Σ(按名排序的 section.name + Σ(按名排序的 key.name + "Value" + 类型名 + 值)))，已实测可复现引擎签名。
- **「进图即清档」的根因与实证在记忆里**：搜「bank 清档 BankList BankWait」——包内 `BankList.xml` 必须声明 `MBank13`/`key`（否则 `BankLoad` 永远空档），且 `BankLoad` 后必须 `BankWait` 同步；两件事分别由打包管线的 `banklist_fix.py` 与脚本内 `BankWait` 保证，**漏任一件症状都是每局清档**。

### 打包管线（shw96 事故沉淀，shw141 固化为一键工具）

**boot2 系列只能用「复制上一版 + `sc2map.write` 直写 CustomLogic.galaxy」，绝不能用 `tools/sc2pack.py`**（shw96 事故：触发器读到旧脚本 → 「脚本读取失败：无法找到函数」+ UI layout 红字）。标准做法：

```bash
python3 tools/boot2_build.py --out work/boot2-<name>.SC2Map      # 五件套 + 全部回读断言
```

五件套（BankList 那件的根因见记忆）：①复制基线 `work/boot2-user.SC2Map`（**不要覆盖**）②直写工作区脚本（打包前自动跑 `galaxy_lint.py`，不过不打包）③并入样式表 `work/blackhand/NewFontStyles.SC2Style`（斜体 `ModItalic` 的定义处；漏 = 名字里的 `<i>` 改写后无样式可查、不斜体，shw88–153 一直是这个状态）④合并 `strings-*.txt` → 包内 **zhCN** 表（漏 = 界面满是 `Param/Value/XXX` 原始键；`sc2map.GAME_STRINGS` 指的是 enUS，别拿它校验）⑤`banklist_fix.py` 写回 `BankList.xml`（漏 = 每局清档）。

- 回读断言：`Triggers` 在、`BankList.xml` 在、脚本含 `BankWait`、**`MUST_HAVE_KEYS` 全部存在**（缺任一即退出码 1）。只有基线已是上一版成品图、且确认键齐全时才用 `--skip-strings`。
- **文案源文件铁律**：`strings-*.txt` 一行一个 `键=值`；**一行粘两个键会静默吞键**——`strings-gcz.txt` 曾把 `GCZBOX2` 与 `GCZTNAME` 粘一行，导致天谴菜单名在所有构建里都显示原始键、`GCZBOX2` 值被污染（正是 `MUST_HAVE_KEYS` 抓出来的）。
- **boot2 包内结构**：`Triggers` + 2.7KB `MapScript.galaxy`（只含 `include "TriggerLibs/NativeLib"` 与 `include "CustomLogic"`）+ 完整 `CustomLogic.galaxy`；**触发器链引用 CustomLogic 里的函数**，故回读校验看包内 `CustomLogic.galaxy`（不是 MapScript）。
- **`sc2pack.py`**（rogue 等独立图用）把 galaxy 塞进 MapScript 并剥触发器 → boot2 缺触发器函数必炸，两条管线不能混。

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
