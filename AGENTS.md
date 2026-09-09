# AGENTS.md — 黑手：升温 脚本二改工程

> 本文件是**长期维护**的工程约定，任何改动前先读它。
> 详细操作手册见 `docs/ROLE-PIPELINE.md`；设计见 `docs/BLACKHAND-REWRITE.md`。

## 工程定位

- 以**原图**（黑手：升温）为基底，通过**外挂 Galaxy 脚本**替换/扩展核心逻辑；
- 保留原图地形、美术、UI、角色卡、行动面板与演出；
- 主脚本：`work/blackhand/CustomLogic.galaxy`（唯一维护目标）；
- 基线地图：`work/boot2-user.SC2Map`（含用户的变体修改，**不要覆盖**）；
- 仓库：https://github.com/mon3stera/blackhand-rewrite（私有）。

## 铁律

1. **大括号配平定位函数体**，不要用文本锚点。同一段代码在多个函数里出现，`replace(..., 1)` 会命中错的。
2. **插入后必须验证落点**：①全文 `{}` 配平 = 0；②**打印目标分支/函数的行号范围和条目数**，确认代码在正确的位置。只看配平不够——曾连续三次把代码插进错误的分支。
   - 追加规则：**修改 `if (...)` 条件时必须打印整行人工核对**。`()` 配平检查发现不了"括号位置错"——曾把 `!= 4)) {` 改成 `!= 4)) && (X) {`，配平通过但 `&&` 跑到了 `if` 外面，游戏报"需要一个左大括号"。正确形式是把新条件并入 `if` 内：`... && (X)) {`。
2a. **python 批量补丁：插入偏移必须在所有前置 replace 之后重新测量**（shw67 事故）。先 `rep()` 文件前部内容会使先前算好的 `start/end` 偏移失效，再用旧偏移做 `src[:end] + 插入 + src[end:]` 会把新函数插进行中间 → 整个脚本读取失败 → 游戏取名后卡死。正确顺序：①提取函数体（`\n}\n` 定位）→ ②对**提取文本**做所有替换 → ③做完其它 rep 后**重新 index 测插入点** → ④断言插入点前是 `}`/行首结构。插入后必须断言新函数定义位于行首且前后结构完整。
2b. **用字符串切片拼接 `if` 条件时逐行验证 `()` 配平**（shw69 事故）：`w[:-3]` 这类切片会把 `...16))) {` 削成 `...16))`，再拼 `|| (X))) {` 会多出一个 `)`——全文配平仍是 0，但该行 if 解析失败、脚本读取失败。修完必须对**每个被改的 if 行单独做 `line.count('(')==line.count(')')`** 检查。
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
- **现有自加预设**：菜单第 31 项「烙印」（`BHYIN01`，原为悬挂未定义键）→ variant 30 → `gf_VE78399E58DB0`；第 32 项「捕风捉影」（`GCZBNAME`）→ variant 31 → `gf_VBFCZOptions`（15 人=侦探/观察者/4城镇随机/城镇调查/政府/保护/教父(2,2)/陪侍(2,3)/黑手随机/影武者(3,31)/女巫(3,4)/中立温和，14/13/12 人递减城镇随机）。女巫=3/4、教父=2/2、陪侍=2/3。
- **预设允许增删改角色的白名单**（???类变体如随机:血锈保持锁定）：①目录浏览白名单（`gt_OSMenus_Func`，6 处 `gv_variantSelection == 16)))` 结尾的变体串）②选中映射白名单（`gt_OSRoleSelect_Func`，5 处 `== 12)))` 结尾的变体串）。两者都需含新预设的 variantSelection；添加按钮禁用集 `[1,4,8,9,10,11,12]` 不用动。
- **注意**：预设再次点「采纳设定」会重新跑 fill 覆盖手动修改（原图语义）。

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

- 案底**只记录玩家实际做过的事**，不是角色的固定属性。
- 例（影武者）：当晚有行动 → 非法闯入（`gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][0] = true`）；杀了人 → 谋杀（`[1] = true`）；整晚没动 → 两条都不记。
- 常见罪名索引：`[0]` 非法闯入、`[1]` 谋杀（**游戏内和谐文案为「谋爱」**，教父等原版击杀者同款；文案键 `513FA9C0`/`BE9264D4`，勿自创「谋杀」文案）。
- 罪名标志的写入位置是两份平行块（visitation 块 ~11430 / action 块 ~12123），每个有夜间行动的角色在其中各有分支；击杀函数 `gf_ES*Kill` 的真击杀分支（`gv_diedAtNight[目标] = true` 处）补写谋杀标志。观察者/监视者的图鉴犯罪可能为**空白**（用自建空值键 `GCZBLANK=`；**不要用 `F0A13008`——那是审查官的能力文本「你可调查2名活人的过往访问」，原图监视者曾错指向它**），不要给它们写案底文案。
- 调查者（警长/探员）在夜间结算时读取这些标记，任意一条为真就播报「你的目标曾经有过案底！」（文本键 `33FE9712`），否则播报无案底（`D903D005`）。
- 因此新角色若要"做了才有案底"，必须在**自己的行动/结算代码里**打标记，而不是只写图鉴字段。
- **案底只在行为真正生效时记录**：攻击被无敌挡下、被救治救回，都**不算**谋杀。例：影武者的谋杀标记只写在 `gf_KillPlayer` 成功执行之后；被无敌/救治拦下时两条罪名都不记。

#### 新增角色时的调查相关清单

1. `gv_roleInvestigatorArray[池][角色][0..1]` —— 探员线索（查上表选类别）
2. `gv_e78AAFE7BDAAE58FAFE883BD[池][角色]` —— 图鉴案底文本
3. 运行时案底标记 —— 在角色自己的行动/结算代码里设置 `gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][索引]`
4. 警长消息 —— 无需配置（自动取角色名）；若该角色应免疫调查，才设「免疫调查」开关

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
- `[1]` 能力、`[2]` 特性、`[4]` 目标、`[6]` winList 自动；**多行追加必须用带 `<n/>` 的键**（`4467A310` 带换行、`1045F9FD` 不带会拼在同一行）

**第 4 步：帮助面板（角色参考卡页）**
- `gf_MakeHelpMenu` 的角色号循环上界 ≥ 新角色号（原图从 `gv_townMax`=30 起往下数）+ 第 1 步的 `[10]` 标志

**第 5 步：自设面板列表 + 选中映射** —— 见铁律 3.1，段内末尾追加，两处条数一致，脚本校验。**各段索引按 `gv_roleCategory` 独立计数**（黑手D等段从 1 重新开始），往某段末尾追加不影响其他段的映射

**第 5.5 步：审查页（灵魂猜测页）** —— `gf_ASE5AEA1E69FA5E98089E9A1B92` 的 `lp_picked` 列表上界常量 + `gt_ASE5AEA1E69FA5E7A1AEE5AE9A_Func` 确认映射。**该映射用「SelectedItem + 分段偏移」跳过无名角色**（如城镇 >=22 加 1 跳过 1/22 空位）：新角色排在无名空位之后时，上界 +N 且按 `SelectedItem >= 新起点` 加差值偏移（城镇观察者=上界 31 且 `>=30` 减 1；影武者=中立上界 18 且 `>=18` 加 12）。改完用「选中第 N 项 → 角色号」逐项推算核对

**第 6 步：拼音匹配循环上界** —— `gt_Prefer_Func`(29)、`gt_Blacklist_Func`(24)、`gt_Init2_Func` 黑名单校验(19) 放宽到 ≥ 新角色号（`gt_Change_Func`=40 够用）；循环里 `roleNameArray != null` 自动跳过空位，放宽无害。不放宽的症状：`-prefer 拼音` 报「不是一个角色」

**第 7 步：几率/预计数量（随机池可见性）** —— `gf_OSComputeOptions` 里 5 处角色号循环（几率清零、模拟标志重置、几率计数、标志重置、归一化）原上界 `gv_townMax`。不放宽的症状：出现几率恒 0%、预计数量是未归一化的累加值（曾显示 1000）

**第 8 步：行动面板 + 夜晚逻辑**
- 行动按钮函数 `gf_RA*Actions`（每个存活其他玩家行配按钮）+ `gf_RAActions` 分发 + **AS 按钮点击触发器 A/B 两个都要写分支**（只写 A：按钮可见但点击不生效）
- `gf_SequencePrep`（记账）/ `gf_SequenceKills`（结算）/ `gf_CheckEnd`（残局计数、归零条件、数量比较）/ 阵营校验

**第 8.5 步：夜间目标的效果转换（欺骗者 / 女巫 / 巴士司机）** —— **新增带夜间目标的角色必须考虑这三者对目标的影响**：

- **机制**：巴士司机交换与欺骗者藏身转向**共用 `gv_switched` 映射**（`switched[对象]=转向对象`）；女巫控制走 `gv_witched[受害者]=女巫`，结算时重写受害者 `visitation = 女巫的action[1]`（~10936 块），并在造访目的地被交换时连锁重写访客 visitation（~10959）。
- **原图标准模式**：效果按「造访目的地」投递（杀手杀 `visitation` 所指）→ 巴士/欺骗者经 visitation 重写自然生效，女巫控住也只改 visitation 就能带偏效果。走这条模式的新角色**无需额外代码**。
- **按目标身份直接投递的角色（如影武者）必须显式解析**：分发块里先判女巫控制（`gv_witched[自己]!=0 && gv_witchEligible && 未入狱 && 女巫有action[1]` → 目标替换为女巫的action[1]），再过 `gv_switched` 解析（例：盯3、3是欺骗者转向7 → 实际看7动线、杀7）。**哪些槽位可被转换是设计决策**，必须在角色卡特性里写明（影武者：目标一可被交换、目标二无法以任何形式被交换——`action[x][1]` 全脚本只有重置和本人按钮写入，结构性不可转）。
- 设计核对清单：①哪个/哪些槽位可被女巫替换 ②可否被 switched 转换 ③被转换后判定与效果是否都落在转换后的目标 ④角色卡特性是否已向玩家说明 ⑤造访记录（visitation）是否要体现转换（影武者保持"表象去原目标"，观察者看得到）。

**第 9 步：击杀函数（`gf_ES*Kill`）死亡信息三件套**
- 字母码 `gv_deathMethod[目标]`：**用新码**（`K` 是连环杀手的，SK 函数里也有一份，锚点必须带函数特有上下文）；验尸官(1,10)选项2 私密播报扫描块（~13620）加对应字母分支
- 公示描述 `gv_deathText[目标]`：**照抄义警模式**（约 26440 行）——`gv_deathDesc[目标]` 初始 false；`if(deathDesc==true){第一段; lv_c=true;} deathDesc=true; if(lv_c==false){主描述}`。主描述在 `lv_c==false`（首杀常态）追加；**放反了 deathText 永远为空、白天没有死亡信息**
- 夜间演出顺序（用户认可）：语音（如 `SoundLink("DarkTemplar_What",-1)`）→ `Wait` 语音时长（2.6s）→ 刀声 → 全场红字广播 → 目标私息。**函数顶部不要放公用出刀声**（会抢在语音前播放）

**第 10 步：私密消息路由** —— 发给击杀/治疗目标的私息走 `gf_BHNotify`（目标非真实在线玩家=虚拟补位时改发 `gv_host`，solo 可见；真实玩家只发本人）。否则 solo 局里「只有音效没有文字」

**第 11 步：静态校验 + 打包部署** —— 逐函数落点 + 配平 + 条数校验 → `sc2pack` 打新文件名 → scp → 游戏内验证（帮助面板、对局内角色卡、`-prefer`、探员线索、死亡信息、残局判定）

### Galaxy 语言层陷阱（生成代码惯例）

- **SoundLink 的类型是 `soundlink`**，不是 `sound`。自定义函数收音效参数必须声明 `soundlink`；写错则所有调用处「参数类型同函数定义不匹配」，并连带整个脚本解析失败（整图报废，游戏内红屏报错）
- **插入 while 广播循环必须在函数声明区补** `playergroup autoXXX_g;` 和 `int autoXXX_var;`（每个函数的自动变量各自声明；漏声明 = 解析函数行出错，脚本读取失败）
- **多函数共用的字符串不能做唯一锚点**（`DB5AD8F8`、`gv_deathDesc[...] = true` 等在多个杀手函数出现）：锚点必须带函数特有上下文（如角色号判断行、专属文本键）
- **python 补丁断言失败时，同一命令块里后续的 commit/打包命令照常执行**——先单独跑补丁确认 exit 0，再做提交打包；曾连续两次只提交了 strings、代码没进包
- **heredoc 脚本里的裸换行就是新语句**：`python <<EOF` 失败后，下一行的 `scp && git` 仍会执行——打包脚本的断言失败不阻止部署脏包。打包+部署+提交应显式 `&&` 链接，或先跑完打包脚本确认成功
- **验证断言别写子串包含**：`s.count('(16) || (30) || (31))) {')` 这类短串会同时命中浏览白名单和映射白名单（互为子串），count 是 11 不是预期 6——断言计数前先确认模式唯一性
- **断言过度也会误报**：①`assert 'KEY' not in s` 全文件禁键——键可能在别处有合法用途（F0A13008 是审查官能力文本，不能因一次误用就全文禁令）；②GameStrings 行尾是 `\r\n`，比对空值键要 `l.replace('\\r','')`；③`s.find('函数名')` 找到的是**首次出现**（可能是文件前部的原型声明），定位调用点要用带 `();` 的完整调用文本或在函数行号区间内找
- **测试指令**：`-reveal`（`gt_BHRevealRoles`，仅主机、游戏开始后）私密列出全部玩家序号+角色名，用于验证影武者探员线索/调查结果等
- 运行期报错先分新旧：`triggerControl(值:0)`、`StringWord(值:0)`、`CameraSetBounds region(值:0)`、`gv_roll点冷却 int[2] 越界` 等均为基线/单人测试固有，不是新改动引入

### 单人测试模式（-solo）

**地图的起始门槛 = 4 人**：`gf_OS...` 初始化里 `PlayerGroupCount(gv_currentPlayers) <= 3` 会把角色串清空（`lv_str[0]`/`lv_str[2]` 全 0），于是 `gv_rolesAssigned != lv_b` 校验失败、开不了局。变体预设（如烙印）本身按人数逐档填写（约 50188 行起 `PlayerGroupCount(gv_tempPlayerGroup) == N` 分支），所以 1 人用变体是能开的；**自设路径**才会被门槛卡住。

数据模型：

| 字段 | 含义 |
|---|---|
| `gv_categoriesArray[槽]` | 该槽选择的角色**池**（1 城镇 / 2 黑手党 / 3 中立 / 4 随机 / 5 三合会 / 8 随机组） |
| `gv_rolesArray[槽]` | 该槽选择的**角色号** |
| `gv_rolesAssigned` | 已选角色数量，必须等于非空槽位数 `lv_b` |

`-solo` 命令做的事（聊天输入，shw53 起定型）：

1. `gv_soloTest = true` → 放行两处 `gv_rolesAssigned < / > PlayerGroupCount(...)` 校验（条件里加 `&& (gv_soloTest == false)`，约 43462 / 43476 行）
2. `TriggerEnable(gt_Prefer, true)`（该触发器在别处会被关闭）

**不再自动填角色**（`gf_BHSoloFill` 已删除；shw51 的「补满 15 槽」方案废弃——它把所有空槽填上角色后，虚拟补位判断「无空槽」反而不补人）。角色全部由测试者在自设里手动配置，空槽交给 `gt_Init2` 的虚拟补位。

聊天命令注册方式：`TriggerCreate` + `TriggerAddEventChatMessage(trigger, c_playerAny, "-solo", false)`，在 `InitTriggers` 里调用 `gt_BHSolo_Init();`。

### 占位玩家与 -prefer 优选

`c_bhSoloBuild`（脚本常量，测试构建 = true）：

| 位置 | 作用 |
|---|---|
| `gt_Init2_Func` **实现开头** | 把 1~15 号**空槽位**加入 `gv_players`/`gv_currentPlayers`/`gv_alivePlayers`，名字「电脑N」，随机房屋。**必须在主玩家循环之前**——曾放在函数末尾（隔了 Wait 2+3+5 秒），发角色/建夜间面板时玩家还没补齐，夜间面板只剩自己一行 |
| `gt_Init2_Func` 玩家收集过滤 | 允许 `c_playerTypeComputer` 也算玩家 |
| `gt_DetectLeave_Func`（约 63356 行） | 不再把「未激活」当成「离开」（否则虚拟玩家会被判退场） |

`-prefer`（原图自带的优选命令，按**拼音**匹配 `gv_roleNameInput[池][角色]`）：

- 命令：`-prefer yingwuzhe`，多个用逗号：`-prefer yingwuzhe,shimin`
- 原图限制：需要 `gv_oP[玩家][1] == true`（会员），非会员扣 500 积分；测试构建下两处都已放开（`gt_Prefer_Func`，约 65210 / 65251 行）
- `-solo` 会 `TriggerEnable(gt_Prefer, true)`（该触发器在别处会被关闭）
- **新角色必须设置拼音名**：`gv_roleNameInput[池][角色] = "xxx";`，否则 `-prefer` 找不到它（影武者 = `yingwuzhe`）
- **测试构建下 prefer 必中（预锁，shw77 起）**：真实分发在 `gf_OSComputeOptions`（同函数兼营大厅几率模拟，`gv_emulate` 区分）。玩家按**随机顺序**处理、无 prefer 的电脑会随机占槽，原 solo 强制块轮到时槽已被占即静默落空（"将被首选"只是登记确认，不代表生效）。现为 `gf_OSRandomize` 之后预锁：`lv_bhPreferSlot[玩家]=槽`/`lv_bhReserved[槽]`，有 prefer 者强制改抽锁定槽，无 prefer 者抽到被锁槽拒绝重抽。**新增角色无需为此改动**，拼音存在即可被锁。

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
| `docs/HANDOFF-SHADOW.md` | **影武者接入交接文档**：当前损坏状态、槽位误判（池3/18=小金执行者）、自设面板双硬编码机制、重置方案与重做清单 |
| `docs/HANDOFF-NEXT.md` | **【先读这份】** 当前进度交接：影武者/观察者/预设（捕风捉影、烙印）均已接入，最新部署 shw73（`-reveal` 测试指令），含逐版改动记录与待验证点 |
