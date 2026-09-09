# 交接文档：SC2 银河编辑器触发器自动化与黑手：升温重建

> 初版：2026-09（上一会话）
> 更新：2026-09-09 15:00（本会话）— **路线变更：改为手写 Galaxy 直写管线**，详见 `docs/GALAXY-PIPELINE.md`
> 目的：跨会话交接全部进展、技术发现、当前状态与下一步计划

---

## 0.00 路线变更（最重要，先读）

**Trigger XML 直写 + 编辑器编译路线已停用。** 现主路线是**直接写 `MapScript.galaxy`**：

- 游戏在加载地图时自己编译 `MapScript.galaxy`，银河编辑器不再是必需环节；
- 依据：可正常游玩的 `work/mafia.SC2Map` 只有 `MapScript.galaxy`、没有 Triggers；
- 已端到端验证：手写 Galaxy 肉鸽脚本（单位、随机刷怪、攻击移动、击杀计数、三选一对话框、自定义升级）在游戏内全部生效；
- 三个致命坑：① `MapScript.galaxy` **不能有 BOM**（否则报 `脚本读取失败：无法找到函数`）且用 CRLF；② 必须用 `Support64\SC2Switcher_x64.exe` 启动，不能直接跑 `SC2_x64.exe`；③ 启动时 `D:\StarCraft II\Support64` 要在 PATH 里。
- 工具：`tools/sc2pack.py`（打包）、`tools/sc2run.py`（启动）、`tools/sc2test.py`（打包+启动+判定）、`tools/sc2status.py`（查状态）。
- **编辑器 Test Document 不可用于手写脚本**：它会用触发器树重新编译并覆盖 `MapScript.galaxy`。

完整说明见 `docs/GALAXY-PIPELINE.md`。

---

## 0. 本会话最重要的结论（先读这段）

1. **反编译器路线已放弃**（用户明确指示：通用反编译几乎不可能，不作为第一参考）。本项目的路线是**正向生成**：GUI 自动化操作银河编辑器 + 正向产出的触发器工程。
2. **上一会话的两个硬卡点全部解决**：
   - 单位类型参数（Game Link - Unit）：走 `V&alue` 模式的游戏链接浏览器（Search + 树），产出正确的 `<Value>Marine</Value><ValueType Type="gamelink"/><ValueGameType Type="Unit"/>`。
   - 点参数（Point）：走 `&Function` 模式的函数浏览器，选 `Start Location Of Player`，嵌套 player 参数自动填 Player 1。
   - 验证结果：动作从 `<Disabled/>` 变 enabled，编译产物 `libNtve_gf_UnitCreateFacingPoint(1, "Marine", 0, 1, PlayerStartLocation(1), UnitGetPosition(EventUnit()));`
3. **工具层已工程化**（不再是一次性 `/tmp/*.py`）：
   - `tools/sc2gui.py` — 统一入口，自动注入 P/Invoke + 辅助函数；`python3 tools/sc2gui.py probes/xxx.ps1`
   - `tools/mpq.py` — 读 .SC2Map（vendored mpyq），`ls / cat / x`
   - `probes/*.ps1` — 可复用的探测/操作脚本
4. **端到端链路已验证完成**：Test Document（菜单 23）启动游戏、触发器执行、用户在游戏内实际玩到（陆战队员 + 每 5 秒刷的敌对跳虫），`GameLogs\*ScriptError.txt` 零错误。**"GUI 建图 → 编译 → 游戏内运行"整条链路成立。**
5. **句柄不稳定**：进程不重启也会变，必须每次动态发现（见 §2.3）。

---

## 0.5 本会话（2026-09-09 凌晨）新增结论

**肉鸽验证闭环已全部完成**（地图 `C:\Users\Administrator\Desktop\bh-test.SC2Map`，本地副本 `work/bh-test12.SC2Map`）：

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| 全局变量（Integer / Dialog / Dialog Item） | ✓ | `TriggerStrings.txt` + `Triggers` XML 变量表 |
| 变量自增 / 变量引用嵌入文本参数 | ✓ | `gv_killCount += 1`、`IntToText(gv_killCount)` |
| 随机实数刷怪点 | ✓ | `Point((Random real between 16.0 and 112.0), ...)` |
| 对话框 + 3 按钮 | ✓ | 游戏内截图：增援 / 重装 / 精英 |
| **条件（Comparison 语法编辑器）** | ✓ | `BuffShown == 0`、`(Used dialog item) == BuffBtn1` |
| 银行存档（Open/Store/Save） | ✓ | 落盘 `Documents\StarCraft II\Banks\verify.SC2Bank`，内容 `<Section name="s"><Key name="k"><Value int="7"/>` |
| 游戏内运行零脚本错误 | ✓ | 删掉误入 Melee Initialization 的 Dialog 动作后，`ScriptError.txt` 不再生成 |
| 对话框按钮点击 → buff 生效 | ⏳ 待用户手点确认 | 合成鼠标事件被游戏过滤（见下） |

**关键新发现（重要，勿重复踩坑）**

1. **元素面板只在列表选择真正变化时刷新**。用 `TVM_SELECTITEM` 选中"当前已选中的那一项"不会触发刷新，元素树会停留在上一个触发器上——本会话因此把 Dialog 事件/动作写进了 Melee Initialization，并在游戏里引发 `DialogSetVisible` 参数为 0 的脚本错误。**正确做法：先点一个相邻触发器，再点目标触发器**（`Select-Trigger` 已实现该逻辑）。
2. **事件参数不能引用全局变量**：`Dialog Item Is Used` 事件的控制参数，点 `&Variable` 后列表是**空的**（同样的变量在动作参数里能列出 3 个）。而且事件参数在触发器注册时就求值，此时对话框还没创建。**正确做法：事件留默认 `Any Dialog Item`，用条件 `(Used dialog item) == BuffBtnX` 区分按钮**（`Used Dialog Item` 函数在条件左槽的 `&Function` 浏览器里）。
3. **条件语法编辑器用法**：`Configure Condition` → 列表选 `Comparison` → 左槽是 `(` 按钮（打开 `Any Compare` 值选择器，可 `&Function`/`&Variable`）→ 中间 `==` → 右槽（显示为 `Value 2`）是具体值。选完左槽后句子会重排，必须重新枚举句子按钮再点右槽。
4. **合成输入**：`keybd_event`（键盘）**有效**（F10 能打开游戏菜单）；`SetCursorPos` + `mouse_event` / `SendInput`（鼠标）**无效**——SC2 用 raw input 且过滤注入事件。所以**游戏内点击类验证必须由用户在交互桌面上手点**。
5. **窗口截图**：`CopyFromScreen` 偶尔对全屏游戏返回全黑；`PrintWindow(PW_RENDERFULLCONTENT)` 对编辑器有效、对游戏无效。多试几次通常能抓到。工具：`tools/winshot.py`。
6. **PS 脚本必须带 UTF-8 BOM**：无 BOM 的 .ps1 被 PowerShell 按 ANSI(GBK) 解析，中文会变成语法错误。新增 `tools/pscheck.py` 可在跑长脚本前 5 秒内做语法检查。
7. **银行是可靠的机器可读验证通道**：`Bank - Open bank "x" for player 1` → `Store integer V as "key" of section "section" in bank (Last opened bank)` → `Save bank (Last opened bank)`，落盘路径 `%USERPROFILE%\Documents\StarCraft II\Banks\<name>.SC2Bank`（纯 XML）。以后所有游戏内验证都优先走银行。


---

## 0.6 【重大】Trigger XML 直写管线已打通（2026-09-09 06:00）

**结论：不再需要逐动作操作 GUI 对话框。** 用 Python 描述触发器 → 生成编辑器格式的 `Triggers` XML → 写入地图 MPQ → 让编辑器编译一次 → 得到 `MapScript.galaxy`。已验证：变量、事件、条件（含比较运算符）、动作、参数（字面量/预设/游戏链接/嵌套函数/变量引用）、**If/Then/Else 嵌套**、**For Each Integer 循环**、文本字符串。

### 管线（三条命令）

```bash
# 1. 用 spec 生成地图（spec 里 build() 返回 sc2gen.Gen）
python3 tools/sc2build.py work/gen_test2.py work/my.SC2Map
# 2. 拷到 Windows 桌面 + 目标文件名到 Temp
scp -P 2222 work/my.SC2Map  administrator@100.94.140.84:/mnt/c/Users/Administrator/Desktop/
scp -P 2222 work/compile_target.txt administrator@100.94.140.84:'/mnt/c/Users/Administrator/AppData/Local/Temp/sc2build_target.txt'
# 3. 编辑器当编译器：打开 → 制造一次改动 → 保存（自动重编译）
python3 tools/sc2gui.py --timeout 900 probes/compile_map.ps1
```

### 新增工具

| 工具 | 作用 |
| --- | --- |
| `tools/sc2catalog.py` | 解析 `NativeLib.TriggerLib` → `data/catalog.json`（2978 函数 / 6094 参数定义 / 2921 预设值 / 433 预设组 / 46 SubFuncType） |
| `tools/sc2gen.py` | **DSL → XML**：`Gen / Trigger / Variable / Call / Lit / PresetV / PresetElem / GameLink / VarRef` |
| `tools/sc2map.py` | 读写地图归档（`ls/cat/put/rm` + 字符串表合并） |
| `tools/mpqc/mpqtool.c` | StormLib 封装（list/extract/replace/add/delete），**MPQ 写入能力** |
| `tools/sc2build.py` | 一条命令：spec → 地图 + 字符串表 |
| `probes/compile_map.ps1` | 打开 → 审计 → 制造改动 → 保存 → 复核（带模态对话框守卫） |

### 关键格式知识（踩过的坑）

1. **文本参数**：不是 `<Value>…</Value><ValueType Type="string"/>`，而是**只有 `<ValueType Type="text"/>`**，文本放 `GameStrings.txt` 的 `Param/Value/<该 Param 元素自己的 Id>`。（写成 string 字面量会让编辑器把键名当文本显示。）
2. **字符串表位置**：文本参数值 → `enUS.SC2Data\LocalizedData\GameStrings.txt`；触发器名 → `TriggerStrings.txt` 的 `Trigger/Name/<trigger-id>`；变量名 → `Variable/Name/<var-id>`。
3. **参数顺序无关**：每个 `<Parameter>` 靠自己的 `<ParameterDef>` 定位；但**元素顺序按前序**（父元素写在子元素之前），与编辑器输出一致最安全。
4. **嵌套控制流**：父 `FunctionCall` 用 `<FunctionCall Type="FunctionCall" Id="child"/>` 列出子动作；**子元素自己带 `<SubFunctionType Type="SubFuncType" Library="Ntve" Id="slot"/>`**（IfThenElse：00000003=if / 00000004=then / 00000005=else；ForEachInteger：DAF49931=actions；While：20298AEC=Conditions + A1B37466=Actions）。参考实例：`/home/mon3tr/dev/sc2-trigger-decompiler/069-triggers.xml`（1803 处 SubFunctionType）。
5. **ID 空间按类型隔离**：FunctionDef / ParamDef / PresetValue / Preset 各自独立编号（`00000120` 既是 FunctionCall 也是别的类型）。PresetValue 元素**嵌在 Preset 元素内部**，解析必须递归（`root.iter("Element")`），且**不能按 identifier 做 key**（"any"/"none"/"true" 重名）。
6. **Preset 参数**：`type_element = Preset:<id>` 指明允许的预设组；组内成员用 `<Preset Type="PresetValue" …/>` 引用，同名值（如 `true`）要靠组名消歧 → `PresetV("do", "Do_Do_Not_Option")`。
7. **编辑器只在文档"脏"时才重编译**：单纯打开+保存不会重新生成 `MapScript.galaxy`。`probes/compile_map.ps1` 用「新建一个空触发器再删掉」制造脏状态。
8. **残留模态对话框会静默吞掉所有 WM_COMMAND**：本会话被 `Objects In Use` 卡了半小时（主窗口 `IsWindowEnabled=False`）。所有 GUI 脚本必须带 `Clear-StrayDialogs` 守卫（枚举顶层 #32770，点 Cancel/OK）。
9. **MPQ 写入**：StormLib（`/home/mon3tr/dev/StormLib`，已编译为 `libstorm.a`）。写入时**不要加密**（`MPQ_FILE_COMPRESS` 即可），否则 mpyq 读不了；SC2 两者都能读。归档内路径用反斜杠（`enUS.SC2Data\LocalizedData\GameStrings.txt`）。
10. **编辑器写地图时若发现字符串缺失**，会把 `Param/Value/<id>` 的值写成键名本身——出现这个现象就说明格式错了。

### 已验证的编译结果（gen_build.SC2Map）

```galaxy
// GenInit  : MapInit -> UIDisplayMessage + UnitCreateFacingPoint(Marine) + CameraPan(1, Point(64,64), 0.0, 0.0, 0.0, true)
// GenSpawn : TriggerAddEventTimePeriodic(gt_GenSpawn, 4.5, c_timeGame) -> Zergling at RandomFixed(20,100)
// GenKill  : TriggerAddEventUnitDied(gt_GenKill, null) -> gv_killCount += 1; if ((gv_killCount >= 3)) {…} else {…}
// GenLoop  : 条件 if (!((gv_killCount >= 3))) return false; 动作 for (…gv_loopI…) { 创建 Marine }
```

Test Document 运行该图：**无 ScriptError**。

### 尚未打通 / 待补

- **自定义库函数**（自己的 `gf_*`）：XML 里要带 `<FunctionDef Type="FunctionDef" Id="…">` 完整定义（不是引用），`Library` 属性也要带。当前只支持 Ntve 内置函数。
- **对话框变量绑定**：`SetVariable(var=VarRef(...), val=Call("DialogLastCreated"))` 这类已可用，但「事件参数引用变量」仍不行（游戏限制，见 §0.5）。
- **本地变量**：`<Element Type="Variable">` 挂在 Trigger 下、`Local Variables` 槽的编码未采集。
- **XML → spec 反向导出**（把编辑器建好的触发器读回 Python）尚未实现，对导入原图素材有用。
- 结构化 UI 元素（Listbox/Checkbox 等）只验证了 Button。

---

## 1. 任务背景与目标

### 1.1 大目标
**黑手：升温**（星际争霸 II 游戏大厅地图）重建——用正向生成的、可在银河编辑器中打开/编辑/重编译的触发器工程，替代原图的编译后 `MapScript.galaxy`。

用户已明确（重要约束）：
- **不要求一比一复刻原图**。原图有 bug 和架构问题，应重新设计规则核心、保留可复用素材与文案。
- 第一阶段只做**核心 10–15 个角色**；积分、银行、成就、模型商城、送礼、群友福利等外围元系统**暂不实现**。
- 黑手：升温与 `/home/mon3tr/dev/mafia-engine`（独立软件项目）**完全无关**，不要混淆。
- 设计边界 = SC2 银河编辑器实际能承载的能力。
- **反编译器不做第一参考**（见 §0.1）。

### 1.2 当前阶段性任务（进行中）
**端到端验证"方法可行性"**：做一个简单肉鸽地图（roguelike）作为阶段性测试——
1. 开局给一个兵 ✓（已编译验证）
2. 随机刷各种怪（进行中：003 定时触发器）
3. 升级后可随机从 3 个 buff 里选（未开始）
4. 地形用自带平坦地形 ✓（默认地图）

链路已验证到 **编译**（`MapScript.galaxy` 中可见真实调用）；**游戏内运行（Test Document）尚未验证**。

### 1.3 已放弃的路线
- galaxy→Triggers XML 完美反编译（社区无稳定工具；用户判定不可行，不再作为第一参考）。
- 截图式 computer use 批量建触发器：慢且脆弱，不采用。

---

## 2. 环境信息（重要！）

### 2.1 Windows 访问
- SSH：`ssh -p 2222 administrator@100.94.140.84`（Tailscale；**SSH 端口 2222 落在 WSL**，所以 Windows 程序必须走 `/mnt/c/...` 路径调用，直接 `cmd.exe` 会报 not found）
- **推荐方式：不要手写 Base64**，用 `tools/sc2gui.py`：
  ```bash
  cd /home/mon3tr/dev/blackhand-rewrite
  python3 tools/sc2gui.py probes/param_panel.ps1     # 跑脚本文件
  python3 tools/sc2gui.py -c 'Write-Output (Find-Main)'  # 跑内联片段
  ```
  它内部：写 UTF-8-BOM 的 .ps1 → `scp` 到 `C:\Users\Administrator\AppData\Local\Temp\dsh_sc2gui.ps1` → `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`。
  **`-EncodedCommand` 只适合极短脚本**（32K 命令行上限，长脚本会 `Invalid argument`）。
- 文件传输：`scp -P 2222`，地图在 `C:\Users\Administrator\Desktop\`（WSL 路径 `/mnt/c/Users/Administrator/Desktop/`）。
- 读地图内容：`python3 tools/mpq.py ls|cat|x work/xxx.SC2Map`。

### 2.2 银河编辑器
- 版本 **5.0.15.97579**，进程 `SC2Editor_x64`。
- **必须由用户在交互式桌面手动启动**；从 SSH/WSL 启动会报 `Graphics device is not available at this time.`（GPU 上下文缺失）。会话期间编辑器保持开着即可远程操作。
- 编辑器窗口是 `#32770` 类对话框窗口，内部混用标准 Win32 控件与 Blizzard 自绘控件。

### 2.3 句柄：**必须动态发现，禁止硬编码**
实测即使进程不重启（PID 不变），主窗口与树的句柄也会变（本会话 28577038→921568、7016150→331646）。`tools/sc2gui.py` 已提供：
- `Find-Main` — 顶层 `#32770` 且标题含 `Triggers - [`
- `Get-Trees` — 返回 `@(触发器列表树, 元素树)`：左侧可见 SysTreeView32 / 右上可见 SysTreeView32，按 rect + 条目数挑选
- `Get-TreesInfo` — 调试用，列出所有树与条目数

历史基线（仅供理解布局，勿直接使用）：主窗口 28577038；触发器列表 7016150 rect 0,72,429,1019；元素树 1576824 rect 435,87,1705,560；Messages 33555894。

### 2.4 本地工作区
- 工作区：`/home/mon3tr/dev/blackhand-rewrite/`（`docs/`、`data/`、`tools/`、`probes/`、`work/`）
- 老管线（已放弃，仅作史料）：`/home/mon3tr/dev/sc2-trigger-decompiler/`（含 069/e66 真图 Triggers XML，可作 XML 结构参考）
- 临时文件在 `/tmp/`；地图副本与解包产物在 `work/`。

---

## 3. 已完成的工作

### 3.1 原图素材盘点（已完成）
- 黑手：升温主图 = `/tmp/blackhand-main.s2ma`（Windows Cache 下载，DocInfo/Name=黑手：升温），93 个文件，**无 Triggers/TriggerLibs**（只留编译后 MapScript.galaxy + TriggerStrings.txt）。
- 脚本事实源：`/tmp/mafia-s2ma/extracted/MapScript.galaxy`（87,973 行，212+ gt_ 触发器，约 600 个 gf_ 函数）、`GameStrings.zhCN.txt`。
- 依赖模组：`/tmp/blackhand-mods/`（Mafia Assets A.SC2Mod、mm2.SC2Mod、mm3.SC2Mod）。
- 角色表：`docs/role-catalog.md`（81 个角色：阵营/名称/拼音/描述）。
- 引擎能力边界：`docs/sc2-capabilities.md`。

### 3.2 Ntve 映射采集（已完成一批）
产出：`data/ntve-map.json`（含参数 ParamDef ID 与取值类型）、`data/action-list.txt`（1545 个动作名）、`data/event-list.txt`（108 个事件名）。

**首批事件映射**：
| 事件 | Ntve ID |
|---|---|
| Button Pressed | 4537C855 |
| Dialog Item Is Used | B5222B7D |
| Unit Dies | 00000090 |
| Timer Expires | 00000049 |
| Periodic Event | 6D565EB4 |
| Chat Message | 00000121 |
| Map Initialization | 00000120 |

**首批动作映射**（节选关键）：
| 动作 | Ntve ID | | 动作 | Ntve ID |
|---|---|---|---|---|
| Text Message | 0366EE04 | | Kill Unit | 00000077 |
| If Then Else | 00000137 | | Create Dialog | BD9AF7D6 |
| Set Variable | 00000136 | | Create Dialog Item | 1005DE91 |
| Modify Variable (Integer) | A0F31305 | | Create Dialog Item (Button) | 096ADF1D |
| Wait | 00000242 | | Create Dialog Item (Label) | 613EA67B |
| Create Units Facing Point | C835E90F | | Show/Hide Dialog | 72C1FB76 |
| Create Units Facing Angle | 6C39A0DF | | Show/Hide Dialog Item | E37ACA0E |
| Clear Text Messages | 33E26C4B | | Destroy Dialog | F4B5BEE7 |
| Run Trigger | 00000116 | | Start Timer | 00000042 |
| Open Bank | 00000292 | | Set Unit Custom Value | 49392C74 |
| For Each Unit In Unit Group | 00000327 | | Set Unit Color | 8A467CA8 |
| For Each Player In Player Group | B525B112 | | Set Dialog Item Text | BA583993 |
| For Each Integer | 66474248 | | Play Sound | 651D9322 |
| Pan Camera | DC635AEF | | Issue Order | 00000089 |
| Move Unit Instantly | 0E8A5B30 | | Add Unit To Unit Group | 9435D821 |
| Remove Unit | 00000078 | | | |

事件/动作对话框列表顺序 = `event-list.txt` / `action-list.txt` 顺序（添加时 `LVM_SETITEMSTATE` 选中索引 + 点 OK）。

### 3.3 条件对话框（已确认）
- 标题是 **"Configure Condition"**（不是 "Condition"）。
- 样例：`(Owner of (Triggering unit)) == 1` = FunctionDef `C439C375`，参数 ParamDef `ABB380C4`(左值 FuncCall) / `51567265`(运算符 Preset `1E7A4625`) / `4A15EC5F`(右值 Value+ValueType int)。

### 3.4 参数编辑（本会话全部打通）
选中动作节点（**真实点击** WM_LBUTTONDOWN/UP）→ 主窗口底部出现参数按钮行（Button 按参数顺序）。

| 参数类型 | 路径 | 结果 |
|---|---|---|
| 文本 | 点按钮 → "Text" 对话框 → `V&alue` → RichEdit20W `WM_SETTEXT` → OK | ✓ |
| 单位类型 | 点按钮 → "Game Link - Unit" → `V&alue` → 浏览器（Search Edit id=200 + SysTreeView32 id=201 + 过滤下拉 195/196/197）→ Search 写 "Marine" → 展开 → 精确选节点 → OK | ✓ |
| 点 | 点按钮 → "Point" → `&Function` → Find 写 "Start Location" → SysListView32(id=43) 选 `Start Location Of Player` → OK（嵌套 player 自动填 Player 1） | ✓ |

要点：
- **Point 对话框的 OK 只在 Function/Preset 模式可用**；Value 模式是地形选点（不可自动化）。
- 搜索框是原生 `Edit`，`WM_SETTEXT` + 一次 WM_CHAR 空格/退格即可触发过滤。
- 动作仍带 `<Disabled/>` 且不编译 = 还有参数没填；参数齐全后保存时编辑器自动移除 `Disabled`。

### 3.5 肉鸽测试地图（bh-test.SC2Map，进行中）
见 §6。

---

## 4. 核心技术知识（新会话必读）

### 4.1 菜单命令 ID（WM_COMMAND=0x0111 发给主窗口）
| 命令 | ID | 备注 |
|---|---|---|
| New Trigger | 580 | **先真实点击触发器列表**，否则不生效 |
| New Event | 581 | 弹 Event 对话框 |
| New Condition | 582 | 弹 **Configure Condition** 对话框 |
| New Action | 583 | 弹 Action 对话框 |
| Save | 15 | 无对话框 |
| Save As | 16 | |
| Test Document | 23 | Ctrl+F9（**尚未验证**） |
| Script Test | 623 | Ctrl+Shift+F11 |
| Compile All | 616 | Data 菜单 |

### 4.2 GUI 自动化坑（都踩过，务必遵守）
1. **新建触发器后名称处于 inline 编辑状态**：必须点击元素树/空白处一次让它失焦，右侧元素树才会切换并可用。
2. **发 WM_COMMAND 前，目标树要"真实点击"**：`WM_SETFOCUS`/`TVM_SELECTITEM` 都不够，要给树控件发 `WM_LBUTTONDOWN/UP`（客户区坐标，如 (300,300)）。
3. **PowerShell 陷阱**：`if (Some-Func ...) { }` 会把函数内所有 `Write-Output` 吞进返回值。函数内诊断用 `Write-Host`。
4. 对话框期间主窗口 `enabled=False`；对按钮用 `PostMessage(BM_CLICK=0x00F5)`（阻塞式 SendMessage 会卡死 SSH 调用）。

### 4.3 跨进程读取（本会话修正）
- **TVITEMW**：mask@0(0x11)、hItem@8、pszText@24、cchTextMax@32；`TVM_GETITEMW=0x113E`。
- **LVITEMW（64 位）**：mask@0、iItem@4、iSubItem@8、state@12、stateMask@16、**pszText@24、cchTextMax@32**；`LVM_GETITEMTEXTW=0x1073`。
  ⚠️ 旧笔记里的 `pszText@8/cchTextMax@16` 是 32 位布局，会让所有列表项读成空串。
- **ComboBox 的 `CB_GETLBTEXT` 不支持跨进程**（返回空）。读下拉项用 UI Automation：
  ```powershell
  Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($h)
  $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                [System.Windows.Automation.Condition]::TrueCondition)
  ```
  （注意 FindAll 必须给 Condition，否则报"参数计数为 1"；UIA 里 Blizzard 控件都暴露成 Pane，Name 有值，autoId 是控件 ID。）
- 树导航：`TVM_GETNEXTITEM=0x110A`（0=ROOT,1=NEXT,4=CHILD,9=CARET）、`TVM_SELECTITEM=0x110B`、`TVM_EXPAND=0x1102`(wParam=2)。

### 4.4 Triggers XML 格式（权威样本：`/tmp/bh6-Triggers`、069/e66 真图）
```xml
<TriggerData>
  <Root><Item Type="Trigger" Id="8位HEX"/>...</Root>
  <Element Type="Trigger" Id="8位HEX">
    <Event Type="FunctionCall" Id="..." />
    <Condition Type="FunctionCall" Id="..." />
    <Action Type="FunctionCall" Id="..." />
  </Element>
  <Element Type="FunctionCall" Id="...">
    <Disabled/>                                                      <!-- 参数不齐时 -->
    <FunctionDef Type="FunctionDef" Library="Ntve" Id="0366EE04" />
    <SubFunctionType Type="SubFuncType" Library="Ntve" Id="..."/>    <!-- 属于父节点的哪个块 -->
    <Parameter Type="Param" Id="..." />
  </Element>
  <Element Type="Param" Id="...">
    <ParameterDef Type="ParamDef" Library="Ntve" Id="0D120C33" />
    <!-- 取值四种形式： -->
    <Preset Type="PresetValue" Library="Ntve" Id="875889C8" />
    <Value>2</Value><ValueType Type="int" />                         <!-- 字面量 -->
    <Value>Marine</Value><ValueType Type="gamelink"/><ValueGameType Type="Unit"/>  <!-- 单位/技能等 -->
    <FunctionCall Type="FunctionCall" Id="..." />                    <!-- 函数调用 -->
    <ValueType Type="preset"/><ValueElement Type="Preset" Library="Ntve" Id="E85564CA"/> <!-- 预设引用 -->
  </Element>
</TriggerData>
```
- 嵌套控制流用 `SubFunctionType` 标记子元素属于哪个块（每个 FunctionCall 只能有一个）。
- 字符串字面量存 `enUS.SC2Data\LocalizedData\GameStrings.txt`，键 `Param/Value/<ParamElementId>=文本`；触发器显示名在 `TriggerStrings.txt`，键 `Trigger/Name/<TriggerId>`。

### 4.5 编译产物验证
保存后地图归档里有 `MapScript.galaxy`：
```bash
python3 tools/mpq.py cat work/x.SC2Map MapScript.galaxy work/x-MapScript.galaxy
sed -n '/gt_<Trigger>_Func/,/^}/p' work/x-MapScript.galaxy
```
- ENABLED 动作才出现在 `_Func`；DISABLED 动作被跳过。
- 事件注册在 `gt_xxx_Init`（`TriggerAddEventMapInit`、`TriggerAddEventTimePeriodic(t, 5.0, c_timeGame)`、`TriggerAddEventUnitDied`）。

---

## 5. 已验证 / 未验证清单

**已验证 ✓**
- 菜单命令创建触发器；添加事件/条件/动作（点击节点后发 581/582/583；模态框按索引选择 + OK）
- 树/列表跨进程读取（TVM_GETITEMW、LVM_GETITEMTEXTW 修正后）；下拉框用 UIA 读
- 保存地图（15）→ mpyq 解出官方 Triggers XML
- **文本参数**设置 → 动作 ENABLED → 编译出 `UIDisplayMessage`
- **单位类型参数**（Game Link - Unit，Value 模式浏览器）→ `Value+gamelink+ValueGameType Unit`
- **点参数**（Point，Function 模式浏览器）→ `Start Location Of Player` / `Point From XY`
- **删除触发器**：真实点击节点后发 `WM_COMMAND 536`（Edit > Clear，快捷键 Delete）
- 触发器 → MapScript.galaxy 编译，事件注册与动作调用均可见
- **Test Document（菜单 23）游戏内运行**：游戏进程 `SC2_x64` 启动，触发器执行，`GameLogs\*ScriptError.txt` 无错误
- 第一批 25+ Ntve 映射（含 ParamDef、取值类型）

**未验证 ✗ / 卡点**
- 变量定义（New Variable）与在参数中引用（`<Variable .../>`）
- 嵌套结构：If Then Else 加子动作（`SubFunctionType` 采集）
- Custom Script 动作（action-list 索引 243）的添加与脚本输入
- 随机函数（Random Integer / Random Point In Region）在 Function 浏览器中的定位
- MPQ 打包工具（本机无 pip/stormlib）——当前走 GUI 保存路线不需要

**重要经验（本会话踩到）**
- **空白模板地图没有出生点**：`PlayerStartLocation(1)` 在游戏内报 `AngleBetweenPoints` 参数错误。刷兵点用 `Point From XY`（地图 129×129，取 64,64）等具体坐标，不要依赖出生点。
- 机器可读的游戏内验证 = `C:\Users\Administrator\Documents\StarCraft II\GameLogs\*ScriptError.txt`（每次 Test Document 生成一份，含出错触发器名与行号）。

---

## 6. 当前地图状态（bh-test.SC2Map）

Windows：`C:\Users\Administrator\Desktop\bh-test.SC2Map`
本地最新：`work/bh-test5.SC2Map`（已解出 `work/bh-test5-MapScript.galaxy`）

触发器（6 个，前两个是遗留）：
1. `Melee Initialization`（模板自带，勿动）
2. `Untitled Trigger 001`（采集遗留，32 动作，多数 DISABLED；可删）
3. `Untitled Trigger 002`（肉鸽初始化）：MapInit → 字幕 `rogue_start` + `Create 1 Marine for player 1 at (Start location of player 1)`
4. `Untitled Trigger 003`（刷怪）：Periodic 5s → 字幕 `spawn` + `Create 1 Zergling for player 2 at (Start location of player 1)`
5. `Untitled Trigger 004`（击杀）：Unit Dies → 字幕 `unit died`
6. `Untitled Trigger 005`（空）

**编译产物（`work/bh-test5-MapScript.galaxy`）**：
```galaxy
libNtve_gf_UnitCreateFacingPoint(1, "Marine",   0, 1, PlayerStartLocation(1), PlayerStartLocation(1));  // 002 MapInit
libNtve_gf_UnitCreateFacingPoint(1, "Zergling", 0, 2, PlayerStartLocation(1), PlayerStartLocation(1));  // 003 periodic 5s
TriggerAddEventMapInit / TriggerAddEventTimePeriodic(5.0) / TriggerAddEventUnitDied(null)
```
GameStrings：`Param/Value/62B531FB=rogue_start`、`143E6AEB=spawn`、`ADFBAA21=unit died`

**下一步**：Test Document（菜单 23）——等用户许可后再启动游戏进程。

---

## 7. 下一步

**阶段 A（黑手：升温 重写，主线 —— 现在可以开始了）**
- 用 `tools/sc2gen.py` 的 DSL 写**声明式触发器工程**：一个 spec 模块 = 一张地图的全部触发器。
- 先做骨架：Setup / Night / Resolve / Day / Vote / Trial / Execute / CheckWin 阶段 + 状态变量 + 玩家角色表变量。
- 需要补的能力（按优先级）：
  1. **本地变量**（`Local Variables` 槽的 XML 编码，需采集一次）
  2. **自定义库函数**（`gf_*`：XML 里要写完整 FunctionDef + Library 属性）
  3. XML → spec 反向导出（用于把编辑器里建好的触发器读回 Python，方便搬运原图素材）
  4. 更多 UI 元素（Listbox / Checkbox / Label）、对话框按钮事件（事件参数不能引用变量 → 用条件比较 `Used dialog item`）
- 第一批角色（10–15 个）落地后，用 Test Document + ScriptError 做回归。

**阶段 B（收尾，需要用户配合一次）**
- 游戏内点一次「增援」按钮 → 读 `Banks\verify.SC2Bank` 确认点击链路。

**阶段 C（工程化）**
- spec 模块化：角色定义、阶段表、文案表分离成数据文件。
- 自动回归：每次 build 后自动跑 `compile_map.ps1` + Test Document + 抓 ScriptError（需要用户授权自动启动游戏）。
- 地图版本管理：每次 build 输出带序号的地图副本。

---

## 8. 关键文件索引

| 文件 | 说明 |
|---|---|
| `tools/sc2catalog.py` | **NativeLib.TriggerLib → data/catalog.json**（函数/参数/预设/子函数槽目录） |
| `tools/sc2gen.py` | **Trigger DSL → XML**（Gen/Trigger/Variable/Call/Lit/PresetV/GameLink/VarRef） |
| `tools/sc2build.py` | **一条命令：spec → .SC2Map**（含字符串表合并） |
| `tools/sc2map.py` | 地图归档读写（ls/cat/put/rm + merge_strings） |
| `tools/mpqc/mpqtool.c` | StormLib 封装（MPQ 写入能力；源码 200 行，gcc 直接编译） |
| `probes/compile_map.ps1` | **编辑器当编译器**：打开→审计→制造改动→保存→复核 |
| `work/gen_test2.py` | 生成器参考 spec（变量/条件/嵌套/循环全都有） |
| `data/catalog.json` | 解析后的 Ntve 目录（2978 函数 / 6094 参数 / 2921 预设值） |
| `tools/sc2gui.py` | GUI 自动化统一入口（P/Invoke + 辅助函数 + SSH 传输） |
| `tools/pscheck.py` | 远程 PowerShell 语法检查（跑长脚本前必做） |
| `tools/winshot.py` | 抓 Windows 桌面截图（编辑器/游戏） |
| `tools/mpq.py` | 读 .SC2Map（ls/cat/x） |
| `tools/vendor/mpyq.py` | vendored mpyq 0.2.5（只读） |
| `probes/audit_triggers.ps1` | **全量审计**：逐个触发器 dump 事件/条件/动作（改动后必跑） |
| `probes/finish_buffs.ps1` | 批量配置 buff 动作参数 + 条件 |
| `probes/remove_leftovers.ps1` | 清理误入其他触发器的动作/事件 |
| `probes/click_buff2.ps1` | 鼠标点击尝试（结论：被游戏过滤，无效） |
| `probes/add_banktest.ps1` | 银行读写验证（模板，可复用） |
| `probes/*.ps1` | 可复用探测/操作脚本（param_panel / unit_dialog / unit_search / unit_set / point_func / point_set / save_map） |
| `work/` | 地图副本、解包产物、`last.ps1`（最近一次运行的 PS 脚本） |
| `data/ntve-map.json` | 首批函数 Ntve/ParamDef/取值映射 |
| `data/action-list.txt` | 1545 动作名（索引映射） |
| `data/event-list.txt` | 108 事件名 |
| `docs/role-catalog.md` | 原图 81 角色表 |
| `docs/sc2-capabilities.md` | 引擎能力边界 |
| `/tmp/mafia-s2ma/extracted/MapScript.galaxy` | 黑手升温原脚本（事实源） |
| `/tmp/blackhand-main.s2ma` | 黑手升温主图归档 |
| `/home/mon3tr/dev/sc2-trigger-decompiler/069-triggers.xml`、`e66-triggers.xml` | 真图 Triggers XML（结构参考，反编译器路线已放弃） |

---

## 9. 长线备忘（原图分析结论，供规则设计参考）
- 原图角色编号：退伍军人 (1,17)、陪侍 (2,3)、审计官 (3,11)、连环杀手 (3,1)、杀人狂 (3,9)。
- 结算顺序关键函数：gf_SequencePrep / gf_SequenceKills / gf_SequenceAfter / gf_SequenceAfter2 / gf_CheckEnd / gf_EndGame。
- 实测结论（用户游戏内验证过，勿推翻）：陪侍限制 + 审计官审计警戒老兵 = 老兵变市民，陪侍/审计官不死。
- 审计官=转化者（黑手党→门徒/三合会→暴徒/其他→市民），不是查身份。
- 新架构建议：Setup/Night/Resolve/Day/Vote/Trial/Execute/CheckWin 显式阶段 + 状态屏障，避免原图的巨型函数与隐式全局态。

---

## 10. 给新会话的第一个动作建议
1. `python3 tools/sc2gui.py -c 'Write-Output (Find-Main); Get-Trees'` 确认编辑器活着、句柄动态发现正常（不要用旧句柄）。
2. `python3 tools/sc2gui.py probes/audit_triggers.ps1` 全量审计当前地图（它会自己处理"先点邻居再点目标"的刷新问题）。
3. `python3 tools/mpq.py cat work/bh-test12.SC2Map MapScript.galaxy` 对照编译产物。
4. 改任何东西前：先 `scp` 一份地图副本到 `work/`；改完 `pscheck.py` 查语法 → 跑脚本 → `audit_triggers.ps1` 复核 → 保存 → Test Document → 查 `ScriptError.txt`。
5. 需要用户配合的只有一件事：**游戏内手点对话框按钮**（合成鼠标无效）。

---

## 11. 当前地图 bh-test.SC2Map 内容（2026-09-09 05:45）

**触发器**
- `Untitled Trigger 002`：Map Init → 字幕 `rogue_start` → 创建 1 陆战队员(玩家1, 64,64) → `Pan Camera` 玩家1 到 (64,64)（0 秒）
- `Untitled Trigger 003`：每 5 秒 → 字幕 `spawn` → 玩家2 跳虫，位置随机 (16–112, 16–112)，朝向 (64,64)
- `Untitled Trigger 004`：任意单位死亡 → 字幕 `IntToText(KillCount)` → `KillCount += 1`
- `BuffChoice`：每 25 秒 + 条件 `BuffShown == 0` → 创建 500×400 对话框 + 3 按钮（增援/重装/精英）→ 显示 → `BuffShown = 1`
- `Buff1/2/3`：事件 `Any Dialog Item is used` + 条件 `(Used dialog item) == BuffBtnN`
  - Buff1：2 陆战队员 + 隐藏对话框 + 银行写 `verify/Buff1/buffs=1`
  - Buff2：1 劫掠者 + 隐藏对话框
  - Buff3：1 雷神 + 隐藏对话框

**变量**：`KillCount=0 <Integer>`、`BuffShown=0 <Integer>`、`BuffDialog <Dialog>`、`BuffBtn1/2/3 <Dialog Item>`

**已知遗留**：对话框显示位置偏右（锚点/UI 缩放待查）；Melee Initialization 模板触发器已删除（避免肉鸽局被判平局结束）。
