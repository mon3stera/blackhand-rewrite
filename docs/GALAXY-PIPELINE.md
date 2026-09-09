# 手写 Galaxy 直写管线（当前主路线）

> 2026-09-09 打通并验证。**取代** Trigger XML 直写 + 编辑器编译路线。
> 结论：地图的 `MapScript.galaxy` 由**游戏自己在加载时编译**，银河编辑器不是必需的。

---

## 1. 为什么放弃 Trigger XML

Trigger XML 是编辑器的内部序列化格式，写出健壮的 XML 等于逆向编辑器的「触发器 → XML」逻辑：

- 参数按 `ParamDef` id 绑定，但**元素顺序、Preset 引用、`SubFunctionType` 槽位、文本参数走 GameStrings** 等细节都要逐条对齐；
- 报错信息极度贫瘠（"Invalid parameter, possibly an incorrect variable name"，且不给具体参数）；
- 一次改动要经过「写 XML → 编辑器打开 → 制造脏状态 → 保存 → 编译」多步，每步都可能卡住；
- 编辑器保存会**用触发器树重新生成脚本，覆盖手写内容**。

Galaxy 是类 C 语言，报错带行号，可直接调用 native / Ntve API，并且有大量现成参考（见 §5）。

## 2. 已验证的事实（含反例）

| 事实 | 证据 |
| --- | --- |
| 游戏自己编译 `MapScript.galaxy` | `work/mafia.SC2Map` 是正常可玩图，含 4.7 MB 纯文本 `MapScript.galaxy`，**没有 Triggers 文件** |
| 去掉 Triggers 组件后仍可加载 | `sc2pack.py --strip-triggers` + 手写脚本 → 游戏内正常运行 |
| 保留陈旧 Triggers 也不影响 | 游戏不读 Triggers，只有编辑器读 |
| 自定义升级数据生效 | `Base.SC2Data\GameData\UpgradeData.xml` 中 `RogueStartSpeed` 让陆战队员移速变 3.5（游戏内读数确认） |
| 编辑器 Test Document **不能**用 | 它会用触发器树重新编译，把手写 `MapScript.galaxy` 覆盖成空脚本 → `脚本读取失败：无法找到函数` |

## 3. 三个必须遵守的约束（踩过的坑）

1. **`MapScript.galaxy` 必须是无 BOM 的 UTF-8 + CRLF 换行。**
   带 BOM 时游戏报 `脚本读取失败：无法找到函数`（错误信息完全误导）。
   验证过的正常脚本（编辑器生成的、mafia 的）都是「无 BOM + CRLF」。
2. **必须通过 `Support64\SC2Switcher_x64.exe` 启动游戏**，不能直接跑 `SC2_x64.exe`。
   直接跑：`exitcode=-1073741515`（`STATUS_DLL_NOT_FOUND`）或写完 `SystemInfo.txt` 后立刻退出。
3. **启动环境需要 `D:\StarCraft II\Support64` 在 PATH 里**，工作目录设为版本目录。
   （编辑器 Test Document 的父子进程链就是 `SC2Editor → SC2Switcher_x64 → SC2_x64`。）

## 4. 工具链

| 工具 | 作用 |
| --- | --- |
| `tools/sc2pack.py` | 把 `.galaxy` 打进 `.SC2Map`（替换 `MapScript.galaxy`、注入自定义数据、可选剥离 Triggers） |
| `tools/sc2run.py` | 部署到 `D:\StarCraft II\Maps\Test\` 并经计划任务在交互会话启动游戏 |
| `tools/sc2test.py` | 一次完成「打包 → 清空日志 → 启动 → 判定结果」，输出 `LOADED` / `SCRIPT ERROR` |
| `tools/sc2status.py` | 查看进程、最新 GameLogs、最新 ScriptError、银行文件 |
| `tools/sc2map.py` / `tools/mpqc/mpqtool` | 归档读写（StormLib） |
| `tools/sc2catalog.py` + `data/catalog.json` | NativeLib 的 2978 个函数 / 6094 个参数签名索引（查 API 用） |

常用命令：

```bash
python3 tools/sc2test.py work/rogue.galaxy --name rogue --wait 45          # 打包+启动+判定
python3 tools/sc2test.py work/rogue.galaxy --name rogue --strip-triggers   # 产出无 Triggers 的干净图
python3 tools/sc2run.py work/rogue.SC2Map --keep                           # 只启动，留着玩
python3 tools/sc2status.py                                                 # 查状态/错误
```

## 5. Galaxy 参考素材

| 素材 | 价值 |
| --- | --- |
| `work/mafia.SC2Map` 的 `MapScript.galaxy`（8.8 万行） | 完整工程范式：`InitLibs/InitGlobals/InitTriggers/InitMap`、对话框、数组、循环、银行 |
| 编辑器生成的 `MapScript.galaxy`（任意 `bh-rogueN.SC2Map`） | 每个触发器动作对应的确切 Galaxy 调用 |
| `data/catalog.json` | Ntve 函数签名、预设常量（如 `c_unitPropMovementSpeed`） |
| 原版「黑手：升温」的 `MapScript.galaxy` | 正式重写的逻辑参考 |

脚本骨架（引擎调用 `InitMap()`）：

```galaxy
include "TriggerLibs/NativeLib"

int gv_killCount;
trigger gt_Init;

bool gt_Init_Func (bool testConds, bool runActions) {
    if (!runActions) {
        return true;
    }

    UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("hello"));
    return true;
}

void gt_Init_Init () {
    gt_Init = TriggerCreate("gt_Init_Func");
    TriggerAddEventMapInit(gt_Init);
}

void InitLibs () {
    libNtve_InitLib();
}

void InitGlobals () {
    gv_killCount = 0;
}

void InitTriggers () {
    gt_Init_Init();
}

void InitMap () {
    InitLibs();
    InitGlobals();
    InitTriggers();
}
```

## 6. 肉鸽验证图现状（`work/rogue.galaxy`）

- 开局：陆战队员 ×1（移速 3.5 = 基础 2.25 + `RogueStartSpeed` 1.25）、镜头到中心、字幕显示 `speed=` 实际读数；
- 刷怪：每 6 秒 1 只跳虫，随机点生成并攻击移动到中心；
- 击杀：仅统计玩家 2 单位，字幕显示累计击杀；
- 奖励：每 3 杀弹出三选一（攻击/攻速/移速/生命/护盾，五选三不重复），顶部居中三个按钮 + 三行描述；
- 点击：应用对应升级（`TechTreeUpgradeAddLevel`），字幕回显 `buff: 名称 hp=… spd=…`，关闭并销毁对话框；
- 临时测试项：`RogueTestAtk`（+50 攻击）用于秒杀跳虫、快速验证升级链路。

## 7. 下一步

1. 去掉临时 +50 攻击，正式调整数值平衡；
2. 用 Galaxy 重写「黑手：升温」核心逻辑（第一阶段 10–15 个角色），参考原图 `MapScript.galaxy`；
3. 需要时引入轻量代码生成（Python 模板/宏）处理重复结构，暂不引入 Galaxy++ 等第三方转译器。
