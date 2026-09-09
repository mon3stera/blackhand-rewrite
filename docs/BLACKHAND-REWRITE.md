# 「黑手：升温」重写设计（第一阶段）

> 2026-09-09 用户确认。相关：`docs/BLACKHAND-ORIGINAL.md`（原图分析）、`docs/GALAXY-PIPELINE.md`（技术管线）

---

## 1. 目标与原则

- **只重写核心逻辑**；UI、地形、美术、数据（模型/技能/贴图）全部沿用原图。
- 基础地图 = 原图 `/tmp/blackhand-main.s2ma`（含 25 栋房屋地形、UI 贴图、依赖 mod）。
- 实现方式 = 重写 `MapScript.galaxy`，打包回原图结构，游戏直接加载（见 `docs/GALAXY-PIPELINE.md`）。
- 不要求一比一复刻；规则核心重新设计，文案与素材复用。

## 2. 已确认的规格

| 项 | 决定 |
| --- | --- |
| 玩家规模 | **15 人** |
| 房子 | 地形上每人一栋房（沿用原图地形）；**"出门访问"是纯逻辑**，无行走/寻路 |
| 投票 | 第一阶段只做**实名过半数审判** |
| UI | 沿用原版（行动面板、投票面板、死亡播报、镜头演出） |
| 演出 | 第一阶段一起做（死亡播报 / 镜头 / 遗言） |
| 时长 | 沿用原图数值（白天 1.2 分、夜晚 0.6 分、讨论 0.3 分、审判 0.8 分） |
| 胜负 | **城镇胜利 / 黑手党胜利 / 连环杀手胜利** 三种 |
| 外围系统 | 不做（积分、银行、成就、模型商城、送礼、轮盘、教程、圣诞模式等） |

## 3. 第一阶段角色（9 个）

| 角色 | 池 | 定位 | 能力（第一阶段语义） |
| --- | --- | --- | --- |
| 市民 | 城镇 | 基础 | 无能力 |
| 探员 | 城镇 | 调查模板 | 每晚调查一人：得知其当晚是否出门、以及是否"可疑" |
| 舞娘 | 城镇 | 限制模板 | 每晚限制一人：中断其夜间能力 |
| 警长 | 城镇 | 调查 | 每晚侦查一人有无犯罪记录（黑手党/连环杀手为有罪） |
| 义警 | 城镇 | 杀人模板 | 每晚射杀一人（次数有限，原图语义） |
| 教父 | 黑手党 | 首领 | 每晚击杀一人；夜间免疫一次攻击；调查显示为"无罪" |
| 参谋 | 黑手党 | 调查 | 每晚调查一人，得知其**确切角色** |
| 陪侍 | 黑手党 | 限制 | 每晚限制一人：中断其夜间能力 |
| 连环杀手 | 中立 | 杀人 | 每晚击杀一人；成为最后的存活者时胜利 |

待定：15 人的角色配比（建议 黑手党 3 = 教父+参谋+陪侍；中立 1 = 连环杀手；城镇 11 = 警长/探员/舞娘/义警 各 1 + 市民 7）。

## 4. 一局流程（第一阶段）

```
开局：分配角色 → 揭示身份与能力说明 → 第 1 天
循环：
  白天
    1. 播报昨夜死亡（沿用原图死法文案 + 镜头演出 + 遗言）
    2. 讨论（0.3 分）
    3. 实名投票：过半数 → 送上审判台
    4. 审判：辩护 → 全员实名投有罪/无罪（0.8 分）
    5. 有罪多于无罪 → 处决；否则宽恕
    6. 判胜
  夜晚
    1. "第 N 夜" 播报、关闭聊天
    2. 行动面板：每人选目标提交能力
    3. 行动窗口 0.6 分，最后 10 秒提示
    4. 结算：限制 → 保护 → 击杀 → 调查 → 死亡处理
    5. 判胜
```

## 5. 核心数据结构（计划）

```
int[15]  role          # 角色 id
int[15]  rolePool      # 阵营（1 城镇 / 2 黑手党 / 3 中立）
int[15]  actionTarget  # 今晚行动目标（0 = 未行动）
int[15]  visit         # 今晚去了谁家（逻辑）
bool[15] alive
bool[15] immune        # 教父夜间免疫
int[15]  kills         # 义警剩余次数等
int[15]  house         # 房屋点位索引
```

## 6. 与原来写法的差异（为什么重写）

原图 `MapScript.galaxy` 87,860 行，把流程写成超长顺序脚本（`gf_SequenceKills` 近千行 if 链），难以扩展。重写采用：

- 显式**阶段状态机** + 计时器，而不是顺序 `Wait` 长链；
- 角色能力统一走**钩子**：`OnNightChoice` / `OnVisit` / `OnAttacked` / `OnDeath` / `OnDayStart` / `OnVote`；
- 结算用**固定顺序的阶段列表**，每个角色只实现自己关心的钩子；
- 文案走 GameStrings 键。

## 7. 下一步

1. 从原图提取这 9 个角色的确切结算语义（调查结果分类、义警次数、教父免疫、限制的判定顺序）；
2. 提取可复用的 UI/演出代码（行动面板、投票面板、死亡播报、镜头）；
3. 写 `work/blackhand/` 下的第一版脚本骨架（阶段机 + 角色表 + 行动面板）；
4. 用 `tools/sc2test.py` 打包进原图并验证。

---

## 实现进度（补丁式重写）

### 构建管线

`tools/bh_build.py` 以原图脚本 `work/bh-src/MapScript.galaxy` 为底，把
`work/blackhand/patches/*.galaxy` 里的同名函数替换掉（按大括号配对整段删除），
再整文件追加补丁内容，输出 `work/blackhand/blackhand.galaxy`。

```bash
python3 tools/bh_build.py --check          # 只看替换了哪些函数
python3 tools/bh_build.py                  # 生成完整脚本
python3 tools/sc2test.py work/blackhand/blackhand.galaxy --name bh \
        --base work/blackhand-base.SC2Map --no-data \
        --strings work/blackhand/strings.txt --wait 60
```

- `--base work/blackhand-base.SC2Map`（= 原图副本）提供地形/美术/依赖/数据。
- `--no-data` 防止注入肉鸽的 UpgradeData.xml 覆盖原图数据。
- `--strings` 把 `work/blackhand/strings.txt` 的键合并进地图 zhCN GameStrings。

### 已替换的函数

| 文件 | 函数 | 作用 |
| --- | --- | --- |
| `00_roles.galaxy` | — | 角色/阵营常量、重写状态变量、`gf_BHLog`、调试开关 |
| `10_win.galaxy` | `gf_CheckEnd` | 三档判胜：城镇 / 黑手党 / 连环杀手 |
| `20_assign.galaxy` | `gf_DisplayRoles` | 固定阵容分配（自适应人数）+ 沿用原图身份展示 |
| `30_night.galaxy` | `auto_gf_NightTransition_TriggerFunc` | 夜晚：面板、计时、结算、转白天 |
| `30_night.galaxy` | `gf_BHResolveNight` / `gf_BHKillAtNight` / `gf_BHIsEvil` | 9 角色夜间结算 |
| `40_day.galaxy` | `auto_gf_DayTransition_TriggerFunc` | 白天：播报、讨论、实名投票、审判、处决、判胜 |

### 复用而非重写的部分

- 行动面板 `gf_ASInitializeActionDialogs` / `gf_ASShowBox` / `gf_ASStartVote` /
  `gf_ASStopVote` / `gf_ASEndActions`。
- 角色按钮可见性 `gf_RSTownSetup` / `gf_RSMafiaSetup2` / `gf_RSNeutralSetup`
  （已覆盖 9 个目标角色的分支）。
- 按钮点击 → `gv_action` 的写入逻辑（`gt_ASActionButton*`）、投票写入
  （`gt_ASVote` → `gv_voteCount`）、审判票（`gt_ASTrialVote` → `gv_trialVotes[0]`）。
- 身份卡文本 `gf_RTTownRoleText` / `gf_RTMafiaRoleText` / `gf_RTNeutralRoleText`。
- 死亡处理 `gf_KillPlayer`、私聊 `gf_CBSystemMessage`、计时条 `gf_TBStartTimer2`。

### 夜晚结算顺序

1. 收集 `gv_action[p][0]` → `gv_visitation[p]`。
2. 舞娘 / 陪侍限制目标 → `gv_roleblocked[target] = 1`。
3. 黑手党目标：教父优先，否则成员多数票。
4. 义警 / 连环杀手击杀（教父夜间无敌，同一目标只死一次）。
5. 调查：警长（案底，教父免疫）、探员（是否出门 + 是否可疑）、参谋（真实角色）。

### 白天流程

死亡播报 → `gf_CheckEnd` → 讨论（`gv_discussionLength`）→ 实名投票
（`gv_dayLength`，`gv_voteCount` 过半才审判）→ 审判（`gv_trialLength`，
`gv_trialVotes[0]` 过半才处决）→ `gf_CheckEnd` → 下一夜。

### 调试开关（正式构建前必须关闭）

`work/blackhand/patches/00_roles.galaxy`：

- `c_bhDebugNoWin = true`：`gf_CheckEnd` 恒返回 0，单人测试不会立刻结束。
- `c_bhDebugFast = true`：白天 6s、夜晚 6s、讨论 3s、审判 6s。

`gf_BHLog(section, key, value)` 把进度写进 `BHLog.SC2Bank`（roles / phase / meta）。

### 重要环境限制

`SC2_x64.exe -run <map>` 这种直启方式在本机只会跑到图形初始化就退出（原图、
肉鸽图、重写图都一样），**不能用来做游戏内行为验证**。自动验证只能确认
“脚本编译通过、无 ScriptError”；实际玩法需要用户在游戏里手动开局测试。

---

## 本地测试环境打通记录（2026-09-09 晚）

### 1. "无法运行游戏" 的真正原因（容器层，与脚本无关）

原图是发布版 `.s2ma`，用 `-run` 直启会被客户端拒绝（弹「无法运行游戏」），三个必要条件缺一不可：

| 条件 | 说明 | 修复 |
|---|---|---|
| `ComponentList.SC2Components` | 发布版 `.s2ma` 里没有这个文件；编辑器另存过的地图（如 `黑手升温-史官.SC2Map`）有 | `tools/bh_map.py` 注入模板 `work/blackhand/ComponentList.SC2Components` |
| `DocumentInfo` 依赖带 `,file:` 回退 | 原图写纯 `bnet:Mafia Assets A/1.0/179538` | `tools/bh_deps.py` |
| **`DocumentHeader` 依赖带 `,file:` 回退** | **游戏实际读的是这份**（NUL 分隔字符串表），只改 DocumentInfo 无效 | 同上 |

桌面会话必须处于解锁/渲染状态（锁屏时 D3D 设备丢失、进程秒退、截屏全黑）。

### 2. 脚本层修掉的三个 bug

1. `BankValueGetFromString` 不存在 → 正确名是 `BankValueGetAsString`（原图用了 28 次）。Galaxy 报的是「无效的参数列表」，完全误导。
2. 补丁里复制了编辑器生成的 for-each 写法，引用了**别的函数内部**的 `autoXXXX_ae/_ai` 局部常量 → 报「解析时出错，可能缺失分号」。已全部改成 `for (lv_x = 1; lv_x <= 15; lv_x += 1)`。
3. 原图自带 bug：`int[2] gv_rollE782B9E586B7E58DB4` 被 1..15 号玩家的循环索引，每秒报一次「正在尝试访问超过数组边界的元素」。改成 `int[16]`。

### 3. 工具链补充

- `tools/bh_map.py`：一条命令构建（build → 离线检查 → pack → 注入 ComponentList → 修依赖 → 调试 fixup）。
- `tools/bh_check.py`：离线静态检查（未定义函数、残留 `auto` 变量、`for ( ;`、括号平衡）。Galaxy 编译错误信息极其误导，这一步能提前拦下大部分问题。
- `tools/bh_deps.py`：依赖回退修复。
- `tools/sc2test.py` 判定修正：必须 SC2 进程存活 20 秒才算 `LOADED`。

### 4. 本地测试支持

**虚拟 handle（已实现）**：本地局 `PlayerHandle()` 为空，原图 501 处调用会让银行/存档格/预设全废。`bh_map.py` 把整份脚本的 `PlayerHandle(` 改写成 `gf_BHHandle(`（哨兵保护自己的定义，避免递归）；`gf_BHHandle` 在真实 handle 为空时合成 `1-S2-1-100X`。实测 503 处调用、仅剩 1 处原生调用（helper 内部）。

**占位角色（filler，待实现，方案 B：调试开关/聊天命令）**：

- 数据：`const string c_bhFillerSlots = "2,3,4";` 在 Init 里解析成 `gv_bhFiller[16]`；`gf_BHIsFiller(p)` 查询。
- 白天：filler 不投票、不参与提名，但仍算存活。
- 夜晚：filler 按概率随机使用能力，或直接不动。
- 其他一切照常（分配角色、存活统计、判胜都算它），这样才接近真人局。
- 可选：解析聊天消息 `-ai 2,3,4` 在运行时设置，不必重新构建。

**大厅人数门槛（调试放宽）**：`gf_OSCheckOptionsA` 里按变体检查（变体1需 ≥4 人、8/9/10 需 ≥10 人）。`DEBUG_BUILD=True` 时把这条置为 `(false)`，单人也能点开始。

### 5. 已知遗留

- 原图 `GameUIOverride.SC2Layout` 引用 5.0.15 已不存在的框架（`ChatBar/ChatBarTemplate/*`、`WaitingForPlayersDialog/...`、`StandardTemplates/StandardMenuButtonTemplate`），进游戏后左上角一串布局警告；不致命，但原图部分自定义 UI 覆盖会失效。
- 单人开局会立刻走判胜（正好可用来验证 `gf_CheckEnd`）。
- 大厅里的"预设"列表依赖存档格+handle，本地首次为空，存一次后可用；右侧角色列表与角色预算由 `gv_currentPlayers`/变体算出，1 人时为空。

### 6. 发布路线：外部脚本引入（解决编辑器覆盖 MapScript.galaxy）

问题：编辑器保存/发布时会按触发器树重编译并覆盖 `MapScript.galaxy`，手写脚本会被清空。

方案：把脚本变成地图里的**外部脚本文件**，由触发器在 Map Initialization 时 include 并调用。

1. `tools/bh_map.py` 产出的 `work/blackhand/blackhand.galaxy`，把四个入口函数改名为 `BH_InitLibs` / `BH_InitGlobals` / `BH_InitTriggers` / `BH_InitMap`，并追加 `BH_InitAll()` 依次调用它们 → 存成 `work/blackhand/CustomGameScript.galaxy`（已生成）。
2. 编辑器打开地图 → 导入管理器（F9）导入 `CustomGameScript.galaxy`（落到地图归档根目录）。
3. 新建触发器：事件 = Map Initialization；动作 = 自定义脚本（Custom Script），内容：
   ```
   include "CustomGameScript"
   BH_InitAll();
   ```
4. 保存 → 编辑器重新生成（空的）`MapScript.galaxy`，地图启动时由触发器加载我们的脚本。
5. 之后即可正常发布（私有/街机）。

注意：入口必须全部改名，只改 `InitMap` 不够（编辑器生成的脚本同样会定义 `InitLibs`/`InitGlobals`/`InitTriggers`）。编辑器保存后会重写依赖表（会自动带上 `,file:` 回退），但 `ComponentList.SC2Components` 需要确认是否保留。
