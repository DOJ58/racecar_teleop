# 验收任务书：joy autorepeat 超时误触发修复（01a3374 遗留缺陷）

> **你的角色**：外部独立验收方（本项目流程：人写任务书 → AI 实现 → 外部 AI 验收）。实现方为 Claude Code（本包作者/队友A），你与其无利益关联，独立判断。
> **你无文件系统访问能力**，本任务书已内嵌全部待审材料（修改后代码全文、文档前后对照、完整验证输出）。只依据本材料验收。

## 1. 被验收对象

| 项 | 值 |
|---|---|
| 项目 | hwcart_sim 阶段1 配套手柄遥控包 `racecar_teleop` |
| 分支/提交 | 交付仓库 feat/racecar-teleop：原交付 **01a3374** → 本次修复 **bcffdc9**（未 push）；Windows 主副本 main：**e022a8b** |
| 修改文件 | `launch/teleop.launch.py`（唯一代码改动）+ `docs/TELEOP_DELIVERY.md`（§3/§7/§8）+ 新增证据目录 |
| 原始任务书 | 《修复 01a3374 交付中的超时误触发/恢复缺陷（joy_node autorepeat）》——修复要求见 §3 本任务书摘要 |

## 2. 缺陷回顾（验收基准）

- 现象链：真实手柄稳住输入正常行驶 → 手柄状态无变化 → joy 默认 `autorepeat_rate=0.0`（**仅变化时发布**，官方文档 https://docs.ros.org/en/humble/p/joy/ ）→ `/joy` 静默 → 0.3s 输入超时误触发 → 行驶中无故锁定停车，需"松开-重按使能"恢复。
- 初版交付文档 §3 曾错误声称"joy_node 自带 autorepeat，默认配置即满足"。
- e2e 全绿未暴露：全部用 `use_joy:=false` + 20Hz 模拟注入，从未经过真实 joy_node。
- 已排除方向：`state.py` 超时/恢复状态机本身逻辑正确（e2e T6/T6a 验证），缺陷在 /joy 供给前提。

## 3. 原任务书修复要求（摘要）

1. launch 给 joy_node 显式传 `autorepeat_rate`，做成 launch 参数，默认 20.0 Hz，须 `ParameterValue(..., value_type=float)`（防 Humble 字符串类型坑）；`use_joy:=false` 路径行为不变。
2. 交付文档 §3 更正错误声明、§8 追加如实披露。
3. 红线：不改 state.py/mapping.py/teleop_node.py/generic.yaml 任何逻辑与参数；wheelbase 0.36→0.305 统一（另一已立案任务）不得混入；不动主线文件；不实现仲裁；不合并 main。
4. 验收线：单测 46/46；WSL clean rebuild（rm -rf build install log）后 e2e 9/9 数值期望不变；日志未截断按日期轮次归档入 `evidence/teleop/`。

## 4. 修改后代码全文（launch/teleop.launch.py，唯一代码改动）

```python
"""Launch file for racecar_teleop.

Two modes, selected by the ``use_joy`` launch argument:

  * ``use_joy:=true``  (default) — also launch the ``joy`` driver, with a
    nonzero ``autorepeat_rate`` (joy's default 0.0 publishes only on change,
    which silences /joy during steady inputs and spuriously trips the 0.3 s
    input timeout).
  * ``use_joy:=false`` — launch ONLY the mapping node, so a separate simulated
    ``/joy`` publisher can feed it (avoids two publishers on the same topic).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = 'racecar_teleop'
    config = os.path.join(
        get_package_share_directory(pkg), 'config', 'generic.yaml')
    use_joy = LaunchConfiguration('use_joy')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_joy', default_value='true',
            description='Launch the joy driver node in addition to teleop'),
        DeclareLaunchArgument(
            'joy_autorepeat_rate', default_value='20.0',
            description='joy_node autorepeat rate in Hz. joy defaults to 0.0 '
                        '(publish only on change), which does NOT satisfy the '
                        '<0.3 s /joy gap this package requires; keep well '
                        'above 1/input_timeout (~3.3 Hz). joy caps it at '
                        '1000.0. 20.0 matches publish_rate and the e2e '
                        'injection rate.'),
        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen',
            # See joy_autorepeat_rate above: without an explicit nonzero rate
            # the default event-driven /joy stream trips the input timeout on
            # perfectly steady (connected, driving) inputs.
            parameters=[{
                'autorepeat_rate': ParameterValue(
                    LaunchConfiguration('joy_autorepeat_rate'), value_type=float),
            }],
            condition=IfCondition(use_joy),
        ),
        Node(
            package=pkg, executable='teleop_node', name='teleop_node',
            output='screen',
            parameters=[config],
            # Defaults already match /joy and /teleop/cmd_vel; kept explicit so
            # the main project can remap here without touching the code.
            remappings=[
                ('/joy', '/joy'),
                ('/teleop/cmd_vel', '/teleop/cmd_vel'),
            ],
        ),
    ])
```

## 5. 文档修改前后对照（docs/TELEOP_DELIVERY.md）

**§3 接口表 /joy 行**

- 改前：`需持续更新,间隔 < 0.3 s(否则超时停车);joy_node 自带 autorepeat,默认配置即满足`
- 改后：`需持续更新,间隔 < 0.3 s(否则超时停车);⚠️ joy 默认 autorepeat_rate=0.0 仅在手柄状态变化时发布,不满足此前提——本包 launch 已显式设 20 Hz(launch 参数 joy_autorepeat_rate 可调,须明显大于 1/0.3≈3.33 Hz;joy 上限 1000)`

**§7 测试日志行**：追加 `autorepeat 修复轮(2026-09-16)复跑:evidence/teleop/teleop_fix_autorepeat_2026-09-16/(clean build+46/46+e2e 9/9,未截断)。`

**§8 已知问题**：追加第 6 条——`【已修复】交付初版(01a3374)漏配 joy autorepeat:launch 启动 joy_node 时未传参,而 Humble 默认 autorepeat_rate=0.0=仅变化时发布——真实手柄稳住输入行驶时 /joy 静默,0.3 s 误触发超时锁定、行驶中无故停车,且 §3 初版误称"默认配置即满足"。e2e 未暴露此问题是因为全部用 20 Hz 模拟注入(use_joy:=false),未经过真实 joy_node。修复:launch 显式 autorepeat_rate=20.0(launch 参数可调)+本文档更正。实体手柄仍未实测。`

## 6. 验证证据（2026-09-16 复跑，WSL2 · Ubuntu 22.04 · ROS2 Humble）

流程：rsync 主副本→teleop_ws → **rm -rf build install log** → colcon build → 单测 → e2e（`use_joy:=false`，20Hz 注入，DOMAIN 43）。

```
== colcon clean build ==
Summary: 1 package finished [1.45s]
== unit tests ==
46 passed in 0.04s
== e2e ==
清场OK(无任何 ros2 launch 进程)
[teleop_node]: racecar_teleop started: /joy -> /teleop/cmd_vel at 20.0 Hz, input_timeout 0.30 s
[PASS] reset_松开武装: v=+0.0000 w=+0.0000 n=12
[PASS] T1_前进满舵: v=+0.5000(期望+0.5000) w=+0.5070(期望+0.5070) n=22
[PASS] T4_松开使能停车: v=+0.0000 w=+0.0000 n=8
[PASS] T2_倒车反舵: v=-0.3000(期望-0.3000) w=+0.3042(期望+0.3042) n=22
[PASS] T3_低速模式: v=+0.2000 w=+0.0000 n=22
[PASS] T5_死区内为零: v=+0.0000 w=+0.0000 n=22
[PASS] T6a_复走验证武装: v=+0.5000 w=+0.5070 n=22
[PASS] T6_停发输入超时: v=+0.0000 w=+0.0000 n=20
[PASS] 超时收敛: 最后非零指令 t=15.40s (停发于15.40s,滞后-0.00s,阈值0.8s)
=== 汇总: PASS=9 FAIL=0 ===  HARNESS_RC=0
```

三份完整未截断日志已归档 `evidence/teleop/teleop_fix_autorepeat_2026-09-16/`（colcon_build.log / pytest_unit.log / teleop_e2e.log）。

交付仓库提交（bcffdc9）：5 files changed, 48 insertions(+), 3 deletions(-) = launch + 文档 + 3 份日志，无其他文件。

## 7. 请你独立审查并给结论

**技术正确性**：
1. `ParameterValue(LaunchConfiguration(...), value_type=float)` 在 Humble 下是否是传 float 参数给 joy_node 的正确写法？默认 '20.0' 解析结果？
2. 默认 20.0 Hz 的依据链是否成立（>1/input_timeout≈3.33Hz 留裕量；=publish_rate；≤1000 上限）？
3. `use_joy:=false`（e2e 注入）路径是否确实零影响？
4. 修复是否真正覆盖缺陷链（稳住输入→静默→误超时）？joy autorepeat 之后，"真断连"场景下手柄停发→超时锁定是否仍然有效？

**范围合规**：对照 §3 红线逐条核对（状态机/映射/参数/wheelbase/主线文件/仲裁/合并）。

**文档一致性**：§3/§7/§8 修改后是否自洽、有无残留矛盾或过度宣称（特别是"实体手柄仍未实测"的如实性）。

**残余风险**（请补充你识别到的，至少评估）：实体手柄零实测（WSL2 无 /dev/input/js*，usbipd 未验证）；joy_node 自身 `deadzone` 默认 0.0 未配置与本包死区的交互；e2e 未运行真实 joy_node，本修复的 joy_node 路径本身只有"构建+代码审查"级验证。

**输出格式**（沿用项目口径）：结论 = 通过 / 有条件通过 / 不通过；逐项给理由；若有条件通过或不通过，列出明确整改项（文件+位置+期望行为）。
