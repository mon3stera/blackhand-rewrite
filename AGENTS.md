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
3.4 **Test Document 的大厅属性为空** → `gv_variantSelection` 不落在任何分档里 → **自设角色列表全空、添加按钮不亮**。测试构建下必须在 `gt_OSMenus_Func` 开头强制 `gv_variantSelection = 1`（`c_bhSoloBuild` 守卫）。
4. **改角色要同时改多处**：名称/描述数组 → GameStrings → 能力开关 → 自设面板 → 选择映射 → 行动按钮 → 夜晚准备/结算。漏一处就"看起来加了但没生效"。
5. **回退文件前先列出已完成的所有改动**，`git checkout` 会把未提交的清理一起还原。
6. **部署用新文件名**（编辑器打开中的地图被锁定），部署后确认 `scp` 无 `failed to upload`。
7. **每次改完立刻提交**，提交信息写清"第几步 / 改了什么"。
8. **测试地图统一放 `D:\StarCraft II\Maps\Test\`**，不要放桌面。

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
| **风衣（侦探类）** | `E9A38EE8A1A3` | 纵火者、影武者 |
| 武器 | `E6ADA6E599A8` | 连环杀手 |
| 不断移动 | `E4B88DE696ADE7A7BBE58AA8` | 巴士司机、保镖、冤魂 |
| 秘密会面 | `E7A798E5AF86E4BC9AE99DA2` | 共济会成员、协教徒 |
| 魅力 | `E9AD85E58A9B` | 市长、执法长、征募官 |
| **善于解读（探员类）** | `E59684E4BA8EE8A7A3E8AFBB` | 探员、联邦探员、参谋、伪装者、栽赃者、管家、渗透、诬陷 |

写法：`gv_roleInvestigatorArray[池][角色][0] = gv_investigator<后缀>1;`，`[1]` 用同后缀加 `2`。

#### 案底规则（重要：动态而非静态）

- 案底**只记录玩家实际做过的事**，不是角色的固定属性。
- 例（影武者）：当晚有行动 → 非法闯入（`gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][0] = true`）；杀了人 → 谋杀（`[1] = true`）；整晚没动 → 两条都不记。
- 常见罪名索引：`[0]` 非法闯入、`[1]` 谋杀。
- 调查者（警长/探员）在夜间结算时读取这些标记，任意一条为真就播报「你的目标曾经有过案底！」（文本键 `33FE9712`），否则播报无案底（`D903D005`）。
- 因此新角色若要"做了才有案底"，必须在**自己的行动/结算代码里**打标记，而不是只写图鉴字段。
- **案底只在行为真正生效时记录**：攻击被无敌挡下、被救治救回，都**不算**谋杀。例：影武者的谋杀标记只写在 `gf_KillPlayer` 成功执行之后；被无敌/救治拦下时两条罪名都不记。

#### 新增角色时的调查相关清单

1. `gv_roleInvestigatorArray[池][角色][0..1]` —— 探员线索（查上表选类别）
2. `gv_e78AAFE7BDAAE58FAFE883BD[池][角色]` —— 图鉴案底文本
3. 运行时案底标记 —— 在角色自己的行动/结算代码里设置 `gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][索引]`
4. 警长消息 —— 无需配置（自动取角色名）；若该角色应免疫调查，才设「免疫调查」开关

### 单人测试模式（-solo）

**地图的起始门槛 = 4 人**：`gf_OS...` 初始化里 `PlayerGroupCount(gv_currentPlayers) <= 3` 会把角色串清空（`lv_str[0]`/`lv_str[2]` 全 0），于是 `gv_rolesAssigned != lv_b` 校验失败、开不了局。变体预设（如烙印）本身按人数逐档填写（约 50188 行起 `PlayerGroupCount(gv_tempPlayerGroup) == N` 分支），所以 1 人用变体是能开的；**自设路径**才会被门槛卡住。

数据模型：

| 字段 | 含义 |
|---|---|
| `gv_categoriesArray[槽]` | 该槽选择的角色**池**（1 城镇 / 2 黑手党 / 3 中立 / 4 随机 / 5 三合会 / 8 随机组） |
| `gv_rolesArray[槽]` | 该槽选择的**角色号** |
| `gv_rolesAssigned` | 已选角色数量，必须等于非空槽位数 `lv_b` |

`-solo` 命令做的事（聊天输入）：

1. `gv_soloTest = true`
2. `gf_BHSoloFill()`：把 1..玩家数 范围内为空的槽位填成 **市民**（池 1 / 角色 1），保留已有选择
3. `gv_rolesAssigned = PlayerGroupCount(gv_currentPlayers)`
4. 绕过两处 `gv_rolesAssigned < / > PlayerGroupCount(...)` 校验（条件里加 `&& (gv_soloTest == false)`）

聊天命令注册方式：`TriggerCreate` + `TriggerAddEventChatMessage(trigger, c_playerAny, "-solo", false)`，在 `InitTriggers` 里调用 `gt_BHSolo_Init();`。

### 占位玩家与 -prefer 优选

`c_bhSoloBuild`（脚本常量，测试构建 = true）：

| 位置 | 作用 |
|---|---|
| `gt_Init2_Func` 末尾 | 把 1~15 号**空槽位**加入 `gv_players`/`gv_currentPlayers`/`gv_alivePlayers`，名字「电脑N」，随机房屋 |
| `gt_Init2_Func` 玩家收集过滤 | 允许 `c_playerTypeComputer` 也算玩家 |
| `gt_DetectLeave_Func`（约 63356 行） | 不再把「未激活」当成「离开」（否则虚拟玩家会被判退场） |

`-solo` 的 `gf_BHSoloFill()` 空位填充为**混合阵营**（前 3 个非主机槽位黑手党、其余市民），否则会因「缺少对立的阵营」校验失败。

`-prefer`（原图自带的优选命令，按**拼音**匹配 `gv_roleNameInput[池][角色]`）：

- 命令：`-prefer yingwuzhe`，多个用逗号：`-prefer yingwuzhe,shimin`
- 原图限制：需要 `gv_oP[玩家][1] == true`（会员），非会员扣 500 积分；测试构建下两处都已放开（`gt_Prefer_Func`，约 65210 / 65251 行）
- `-solo` 会 `TriggerEnable(gt_Prefer, true)`（该触发器在别处会被关闭）
- **新角色必须设置拼音名**：`gv_roleNameInput[池][角色] = "xxx";`，否则 `-prefer` 找不到它（影武者 = `yingwuzhe`）

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
| `docs/HANDOFF-NEXT.md` | **【先读这份】** 自设面板「添加」按钮问题交接：当前 reset 点、已排查线索、影武者工作所在分支、下一步建议 |
