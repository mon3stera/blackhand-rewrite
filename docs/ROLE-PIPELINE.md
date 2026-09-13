# 加 / 改一个角色：完整手册

> 配套：`AGENTS.md`（铁律与红线）、`docs/GALAXY-PIPELINE.md`（打包与启动链路）、`docs/BLACKHAND-REWRITE.md`（设计与进度）。
> **本手册写「现在怎么做」**。历史记忆里的行号一律会漂移——定位一律用工具（`tools/role_gen.py`、`tools/role_bootstrap.py --list`、`tools/role_block_scan.py`），不要照抄行号。

---

## 0. 先理解：角色在代码里没有「一个地方」

原图（编辑器从 72.8 MB 触发器树生成的脚本）把每个角色的逻辑摊平进 6 个函数族：角色定义、角色卡、行动面板点击、夜间结算、判胜、死亡演出。**这不是谁写乱了，是 Galaxy 的形状决定的**——没有 struct / enum / 函数指针，全图 `= {` 零出现（连数组字面量都没有），角色无处可"待"。

我们已经做的收口（做完了，别再回头手改）：

| 收口 | 内容 | 工具 |
|---|---|---|
| 写侧口子 | 访问 / 限制 / 案底一律走 `gf_BHVisit*` / `gf_BHBlock*` / `gf_BHCrime*` | `tools/bh_sys_open.py` |
| 角色卡统一入口 | 67 个调用点只说「渲染这个玩家的卡」，池判断收进 `gf_RTRoleCard` | `tools/role_card_dispatch.py` |
| 角色块一角色一函数 | 405 个 `gf_SK*` 函数（点击族 / 夜间族 / 白天族 / 角色设置族） | `tools/role_block_extract.py` + `tools/sk_verify.py` |
| 自设列表 | 数据源 `work/roles-list.json` + 生成器（行序 = 索引的双硬编码已消灭） | `tools/role_list_gen.py` |
| 角色登记 | spec + 校验器（上界族 / 审查页自洽 / 文案键 / 镜头 / 字母码） | `tools/role_gen.py` |
| 死代码 | 原图 16 个零引用函数 + 2 个孤儿包装函数已删除（−3,143 行） | `tools/dead_code_prune.py` |

⇒ **加一个角色现在的工作量 ≈ 1 份 spec + 1 个夜间/结算函数 + 1 处面板分支 + 文案**，其余由打包门兜住。

---

## 1. 选槽位（唯一不能靠工具的一步）

- 池号：`1` 城镇 / `2` 黑手D / `3` 中立 / `5` 三合会（`4`、`8` 是随机槽）。
- **判定槽位空闲必须查原图** `work/bh-src/MapScript.galaxy`，不能凭「没有名称数组」下结论：池 3 / 18 = 小金执行者（**已被误覆盖过一次**）；池 3 / 13 = `duoluoshenpanzhe`，原图只有拼音与开关、没有名称/描述，是真正可复用的遗留空槽。
- 红线：角色号 **> 30** 会踩 `gv_bankRoleAchievements[16][9][21]`（31 号起不得做银行成就检查）、`gf_VLoadSaveSlot` 的槽位校验、死因字母码表——加 >31 的角色要同步放宽上界族，`tools/role_gen.py` 的 `[1]` 会直接告诉你哪几处上界还没放开。
- 现任名单一眼看全：`python3 tools/role_bootstrap.py --list`。

---

## 2. 写 spec：`roles/<拼音>.json`

```bash
python3 tools/role_gen.py --dump 3/32      # 从脚本导出骨架（省得手抄错）
python3 tools/role_gen.py --apply          # 把缺的登记行补进脚本（幂等）
python3 tools/role_gen.py                  # 五项检查：上界族 / 文案键 / 审查页 / 镜头 / 字母码
```

spec 字段：`name_key`、`desc_key`、`investigator`（探员线索 2 条）、`crime_key`（图鉴「犯罪可能」）、`options`（开关四件套：存在 / 权重 / 文案键 / 默认值）、`flag10`、`pinyin`、`guessable`、`review_status`。

**交互（交换 / 调查 / 限制 / 审查）不写进 spec**（2026-09-13 定稿）：角色间交互是开放集合，新角色还会带来新机制，声明只会过期 ⇒ **一律以代码实现为准**；spec 里的 `interactions` 只是设计笔记，不参与判定。

---

## 3. 文案（GameStrings）

`work/blackhand/strings-<前缀>.txt`，一行一个 `键=值`（**一行粘两个键会静默吞键**）。需要的键：

| 用途 | 数组 |
|---|---|
| 角色名 / 描述 | `gv_roleNameArray` / `gv_roleDescriptionArray` |
| 探员线索、图鉴犯罪 | `gv_roleInvestigatorArray` / `gv_e78AAFE7BDAAE58FAFE883BD` |
| 开关标签 | `gv_roleOptionsText` |
| 角色卡五栏 | `gv_roleBoxText[lv_a][n]` |

规范：
- 名称格式 `<c val="颜色">名字</c>`；渐变（`<c val="上-下">`）**每段必须 8 位 ARGB**——6 位色值是非法标签，会让整图「无法运行游戏」且**没有 ScriptError**（shw131 事故）。
- 能力行空两行后接天蓝 `<c val="BBDDFF">…</c>`。
- **国服和谐**：不得出现「杀」字（用「爱」），打包第 7b 步会自动按词表清洗 `=` 右侧；自加文案收尾仍要 `grep -n 杀`。
- 键的存在性由 `role_gen` 的 **[1b] 文案键存在性** 检查（零数据维护，覆盖全部角色；活角色缺键直接拦打包）。

---

## 4. 角色卡（只写自己池的那一个函数）

| 池 | 函数 |
|---|---|
| 1 城镇 | `gf_RTTownRoleText` |
| 2 黑手D | `gf_RTMafiaRoleText` |
| 3 中立 | `gf_RTNeutralRoleText` |
| 5 三合会 | `gf_RTTriadRoleText` |

五栏含义：`[0]` 卡头 / `[1]` 能力 / `[2]` 特性 / `[4]` **身份白** / `[6]` 胜利。
- 调用点一律走 `gf_RTRoleCard(lp_player)`，**不要**在别处直接调池函数（`role_card_check` 会拦）。
- `[0]` 可以不写（函数开头按名字数组统一写）；**`[4]` 最容易漏**——漏了界面直接显示原始键名（shw192 事故）。
- 城镇/黑手D/三合会的 `[6]` 写在角色块之外（函数级共用尾部），中立池写在每块里 ⇒ 检查口径是「每块 `[1][2][4]` + 函数级有 `[6]`」。

---

## 5. 夜间行为：写成独立函数

```galaxy
// 宿主（gf_SequencePrep / Kills / After / After2 或面板点击族）里只留一行：
if ((gv_roles[lv_a][1] == 3) && (gv_roles[lv_a][0] == N)) {
    gf_SKK_3_<拼音>(lv_a);
}
```

- 命名 `gf_SK<家族标签>_<池>_<拼音>(int lv_a)`，**标签必须全局唯一**（点击族 A/A2/B，夜间 P/U/K/F/G，白天 Y/W/C/O，角色设置 R/N/M/T/V）——重名不同签名是编译错误，`galaxy_lint` 第 6 项会抓。
- **守卫条件原样留在调用点**，不要把池/角色判断搬进函数。
- **不要给参数赋值**（Galaxy 传值，写不回传）；**不要抽「块内写、块外读」的局部变量**（`lv_y` 事故：赋的是被调函数的局部，写丢失）。
- 跨块共享的数组只能提升为「函数专属全局 + 入口清零」（`tools/role_local_promote.py`）。
- 含 `Wait` 没问题——普通 `void` 函数也能写 Wait，约束是**调用链必须源自触发器**（打包门第 0f 步 `tools/wait_graph_check.py` 会检查）。
- 已有角色可随时用 `python3 tools/role_block_scan.py --min 80` 看还有哪些大块没抽（按「块体行 / 总行」挑，别按函数长度挑）。

---

## 6. 访问 / 限制 / 案底：一律走口子

| 口子 | 用途 |
|---|---|
| `gf_BHVisit(lp_player, lp_target)` | 访问了谁（写 `gv_visitation`） |
| `gf_BHVisitAction(lp_player, lp_target)` | 访问且目标是行动目标（写 `gv_action` 路径） |
| `gf_BHVisitSelf(lp_player)` | **不登门**（访问自己：不被观察、不触发交换、不触发退伍军人警戒） |
| `gf_BHVisitNone(lp_player)` | 明确无访问 |
| `gf_BHSetBlocker(gf_BHUnblock/gf_BHBlock)` | 限制（舞娘/陪侍/三合会3 那套） |
| `gf_BHCrime / gf_BHCrimeTrespass / gf_BHCrimeMurder` | 案底（`[0]` 非法闯入 / `[1]` 谋爱） |

四条硬约束（每加一个角色都要逐条给出结论）：

1. **交换干扰类**（女巫 / 巴士司机）：结算读 `gv_action` 的角色**免疫交换**；走 `gf_BHVisitAction` 的角色**受影响**。弄清楚自己的读法并在卡面写明。
2. **调查类**（探员 / 警长 / 侦探 / 监视者）：必须写对 `gv_visitation`，含「访问自己」的写法。
3. **限制类**（舞娘 / 陪侍 / 三合会3）：被限制的角色，**结算块必须自己读 `gv_roleblocked[自己] == 0`**（影武者 shw219 教训；堕落审判者至今仍有此漏洞）。
4. **审查员必须能猜出它**：`gf_ASGuessRole` 映射 + 上界 + 拼音，由 `role_gen` 的 `[2]` 守。

---

## 7. 行动面板与开关按钮

- **两处必须同步**：①触发条件 `gt_ASActionButtonA/B<Town|Mafia|Triad|Neutral>_Func` ②面板搭建 `gf_RA*Actions`。漏改面板 ⇒ 自己的座位按钮被兜底隐藏或目标二选不了自己（shw222 事故）。**可见性即可点性**。
- 无行动角色用 `gf_RANoActions(lp_player)`，不要自造隐藏逻辑。
- **开关按钮两步**：①`gt_ASSwitchButton_Func` 加该角色分支（切换标志 + 播报）②该角色 `gf_RA*Actions` 开头 `DialogControlSetEnabled(gv_switchButtonItem, …, true/false)` 并播报当前状态。
- 开关默认值的时序：`gf_RA*Actions` **每晚都跑**（由 `gf_NightTransition` 驱动）⇒ 只生效一次的默认值必须加 `gv_dayNumber == 1` 守卫，否则每晚覆盖玩家用 `-on`/`-off` 做的切换。

---

## 8. 外围登记（多半已自动化，跑一次工具就知道漏没漏）

| 项 | 做法 | 谁守 |
|---|---|---|
| 夜间镜头组 | 在 `gt_NPNightCamera_Func` 分发块加机位（不在表中 = 无镜头且**不报错**） | `role_gen` `[1c]` |
| 阵营旗标 `lv_c` | 新角色不登记会与城镇同场被误报「缺少对立的阵营。」 | 人工（开局校验） |
| 审查页 | `gf_ASGuessRole` 映射 + 上界 + 拼音 | `role_gen` `[2]` |
| 死因字母码 | 追加字母要避开占用表（由工具打印，不用再背） | `role_gen` `[1d]` |
| 首胜记账 | 必须用 `gv_originalRole`（开局发到的角色），否则被转化后记错身份 | 人工 |
| 自设列表 | 改 `work/roles-list.json` → `python3 tools/role_list_gen.py --apply` | 门 `0c` |
| 帮助面板 | 城镇/中立等分档上界 | `role_gen` `[1]` |
| 成就索引 | 三处必须对得上：列表链 `gt_Stats_Func` / 命令链 `gt_Achieve_Func`（`-achieve`）/ 解锁写入 `gv_bankOtherAchievements[16][71]`；漏一处 ⇒ 列表空白或命令播报 `null`（shw151 教训） | `role_gen` `[1e]` |

---

## 9. 打包门（六道，全自动）

```bash
python3 tools/boot2_build.py --out work/boot2-shw<NNN>.SC2Map
```

| 步 | 检查 | 工具 |
|---|---|---|
| 0 | 语法与结构（配平 / 声明 / 未声明标识符 / 重复定义 …） | `galaxy_lint.py` |
| 0b | 角色卡覆盖 + 池专属不变式 + 栏位 | `role_card_check.py --strict` |
| 0c | 自设列表与数据源逐字节一致 | `role_list_gen.py --check` |
| 0d | 抽出函数结构不变式（void / 不给参数赋值 / 标识符可解析） | `sk_verify.py` |
| 0e | 上界族 / 文案键 / 审查页 / 镜头 / 字母码 / spec 登记 | `role_gen.py` |
| 0f | Wait 调用图（含 Wait 的函数必须源自触发器） | `wait_graph_check.py` |

随后是八件套（复制基线 → 直写脚本 → 样式 → 字体 → 贴图 → 说明与加载页 → zhCN 文案合并 → BankList 写回）+ 回读断言。任一门非 0 都会**停止打包**。

---

## 10. 实测清单

1. 出正式包 + **solo 包**（临时把 `c_bhSoloBuild` / `c_bhSoloFill` 置 `true` 打包，**打完立即还原为 `false`**，并从包内回读确认）。
2. 部署到 `D:\StarCraft II\Maps\Test\` 的**新文件名**，双端 `md5` + 字节数核对。
3. `File → Test Document` 进图；异常看 `Documents\StarCraft II\GameLogs\*ScriptError.txt` **最近一次**。
4. 必看：角色卡五栏、开局面板按钮、夜间结算与播报、审判/处决路径、胜利画面。
5. 运行期报错先分新旧：`triggerControl(值:0)`、`StringWord(值:0)`、`CameraSetBounds region(值:0)` 等是基线/单人测试固有。

---

## 11. 事故对照表（每道门挡的是哪次事故）

| 历史事故 | 现在由谁挡 |
|---|---|
| 角色卡漏 `[4]` 身份白 ⇒ 界面显示原始键名（shw192） | 门 `0b` 栏位检查 |
| 卡片多副本不同步（shw117/144/191） | `gf_RTRoleCard` 派发 + 池专属不变式 |
| 新角色漏阵营旗标 ⇒ 误报「缺少对立的阵营。」（shw118） | 人工（开局校验） |
| 审查页猜不出 / 上界漏（shw205/216/217） | 门 `0e` `[2]` |
| 自设列表索引漂移（「只能末尾追加」时代） | 门 `0c` + 生成器 |
| 成就名漏补一处链条目 ⇒ 列表空白 / `-achieve` 播报 `null`（shw151） | 门 `0e` `[1e]` 三处索引一致性 |
| 抽出函数重名不同签名 ⇒ 编译错误（shw243） | `galaxy_lint` 第 6 项 |
| 抽出块漏拷 `auto*` 声明 ⇒ 脚本读取失败（shw239） | `galaxy_lint` 第 2 项 + `sk_verify` |
| 跨块共享局部被抽走 ⇒ 目标丢失 | `sk_verify` 无干扰判据 |
| 含 `Wait` 的函数被非触发器上下文调用 | 门 `0f` |
| 死代码里改了半天没生效（`gf_SequenceBullshitBackup`） | 死代码已删 + `dead_code_prune.py` 可复核 |
