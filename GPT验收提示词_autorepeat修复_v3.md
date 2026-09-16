# 验收任务书(第三轮):对"有条件通过"三项整改的回应——接口事实修正/测试结论收窄/双死区披露

> **你的角色**:外部独立验收方(项目流程:人写任务书 → AI 实现 → 外部 AI 验收)。实现方为 Claude Code(本包作者/队友A),你独立判断。
> **轮次背景**:第一轮你不通过(4 项发现);第二轮(v2 材料)你结论 = **有条件通过**,认定第 1/2/4 项已整改、技术实现/范围历史通过,余三项待整改(你的第 5/6/7 点)。本轮逐项落实,请复审后给出最终结论。
> **验证能力分级(同 v2 口径)**:文案与事实一致性、代码写法、逻辑推理、文档自洽、git 输出转述内部一致性可仅凭本材料判断;日志原始真实性/仓库实际状态/命令可复现性属实现方执行输出原样转述(标 🔁);官方文档 URL 你可自行访问核对。

## 1. 你第二轮三项待整改的处置对照

| 你的项 | 你的要求 | 处置 |
|---|---|---|
| 5(事实错误) | §2 "原生 Linux 下 joy_node 读 /dev/input/js*" 不准确;应区分 joy=SDL/Linux input event 接口、joy_linux=/dev/input/js* 接口;并同步更新提示词内嵌全文 | **已改。** 交付文档 §2 连接方式整句重写(见 §4 全文中 §2 末段),并顺带注明实车换 joy_linux 时 autorepeat 默认 0.0 的关联风险(与 §3/§8 呼应,消除你指出的内部矛盾)。你说的接口区分与官方文档 Technical note 完全一致(证据见 §2 本任务书)。 |
| 6(表述过强) | §7 "手柄断开后重连不自行恢复"应改为"模拟 /joy 停发后恢复不自行恢复",并明示实体断开/重连未实测 | **已改。** 验证行改名"模拟 /joy 停发后恢复不自行恢复",结果列标注"✓(仅仿真)",并追加"实体手柄物理断开/重连未实测(真实断连涉及驱动层行为,不能由模拟停发外推)"。 |
| 7(披露补强) | §8 追加 joy 0.05 与本包 0.08 死区串联生效说明,注明非简单相加、需实体确认 | **已加。** 新增第 7 条:串联生效、joy 先在归一化轴做死区处理、本包死区作用其后,实际响应区与灵敏度非两数简单相加(受 joy 死区外重标定影响),须实体手柄现场确认后按需调 generic.yaml。 |

本轮**包代码/launch/config 零改动**,仅交付文档三处 + 证据归档。为保持证据链完整仍复跑了一轮全链验证(§5)。

## 2. 接口事实的证据(可自行访问核对)

官方文档 docs.ros.org/en/humble/p/joy/("joy 3.3.0 documentation")末节 **Technical note about interfacing with joysticks and game controllers on Linux** 原文:

> On Linux there are two different ways to interface with a joystick. ... The first interface is via the joystick driver subsystem, which generally shows up as a device in **/dev/input/js0** ... This is the way that the **"joy_linux" package** accesses the joystick. The second way to interface is through the generic event subsystem, which generally shows up as **/dev/input/event7** ... This is the way that **SDL (and hence this "joy" package)** accesses the joysticks.

即:ROS2 `joy_node`(SDL)走 `/dev/input/event*`;`/dev/input/js*` 属 joy_linux(ROS1 joy 同路径)。初版 §2"joy_node 读 /dev/input/js*"系事实错误,本轮更正。

## 3. 更正后代码全文(launch/teleop.launch.py,本轮未动,同 v2 §4)

```python
"""Launch file for racecar_teleop.

Two modes, selected by the ``use_joy`` launch argument:

  * ``use_joy:=true``  (default) — also launch the ``joy`` driver with an
    explicit ``autorepeat_rate``.  Humble's joy 3.3.0 already defaults to
    20.0, but 0.0 would mean publish-only-on-change (the ROS 1 joy and
    joy_linux default), which would trip the 0.3 s input timeout while
    driving with steady inputs — so pin it instead of relying on the
    driver/version default.
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
            description='joy_node autorepeat rate in Hz. joy (Humble, 3.3.0) '
                        'already defaults to 20.0 and republishes only on '
                        'change when set to 0.0 (the ROS 1 joy / joy_linux '
                        'default), which violates the <0.3 s /joy gap this '
                        'package requires — hence pinned explicitly. Keep '
                        'well above 1/input_timeout (~3.3 Hz); joy caps it '
                        'at 1000.0.'),
        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen',
            # Pin autorepeat_rate explicitly (see joy_autorepeat_rate above)
            # so the <0.3 s /joy gap never depends on driver/version defaults.
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

## 4. 更正后交付文档全文(docs/TELEOP_DELIVERY.md,57a3e0b,全文非节选;本轮改动处已用 ◀ 标注说明,正式文档中无此标记)

```markdown
# racecar_teleop 手柄遥控模块·交付说明

> **交付范围**:手柄输入解析、按键映射、速度指令生成、启动配置。**不包含**主项目车辆模型/底盘控制器/TF/赛道/导航参数的任何修改(本分支除新增本包与本文档外未动任何主线文件)。
> **交付形态**:独立功能分支,未合并 main。
> **验证口径**:⚠️ **仅仿真验证**(WSL2 中无实体手柄设备,全部测试用模拟 /joy 注入;实车与实体手柄均未测试)。

---

## 1. 包名 / 启动命令 / 依赖 / 测试环境

| 项 | 值 |
|---|---|
| 包名 | `racecar_teleop`(ament_python,v0.1.0,Apache-2.0) |
| 启动命令 | `ros2 launch racecar_teleop teleop.launch.py`(默认同时起 `joy_node`);`use_joy:=false` 只起映射节点(调试/测试用) |
| 运行依赖 | `rclpy`、`geometry_msgs`、`sensor_msgs`;`joy` 仅 `use_joy:=true` 时需要 |
| 测试环境 | WSL2 · Ubuntu 22.04 · ROS2 Humble;单元测试 46 项(pytest,无需 ROS 运行时);端到端 9 工况(模拟 /joy 20Hz 注入) |

## 2. 手柄型号与连接方式

**⚠️ 未实测任何实体手柄型号。** 键位按"通用双摇杆手柄"(Xbox 布局)配置:
axis 1=左摇杆 Y(速度)、axis 3=右摇杆 X(转向)、button 5=RB(使能)、button 4=LB(低速)。
所有轴/键编号集中在 `config/generic.yaml`,换手柄只改配置不改代码;**接入前必须打印实际 /joy 核对一次,不能按外壳印刷猜测**。
连接方式(注意接口区别,官方文档 Technical note):ROS2 `joy_node` 走 **SDL / Linux input event** 接口(`/dev/input/event*`);`/dev/input/js*` 是 **joy_linux 包(及 ROS1 joy)** 的接口。本包 launch 用 `joy`;实车若换 joy_linux,须同时注意其 `autorepeat_rate` 默认为 0.0(见 §3)。WSL2 下需 usbipd-win 直通(未验证,不排除现场折腾;设备直通不稳定时继续用模拟 /joy 做软件验收)。◀ 本轮修正接口事实错误

## 3. 接口

| 方向 | 话题 | 类型 | 频率 |
|---|---|---|---|
| 订阅 | `/joy` | `sensor_msgs/msg/Joy` | 需持续更新,间隔 **< 0.3 s**(否则超时停车);实测安装 ros-humble-joy 3.3.0,官方文档默认 `autorepeat_rate=20.0` 可满足此前提,设 0.0 才是**仅变化时发布**(ROS1 joy / joy_linux 的默认)。本包 launch **显式固定 20 Hz**不依赖驱动/版本默认值(launch 参数 `joy_autorepeat_rate` 可调,须明显大于 1/0.3≈3.33 Hz;joy 上限 1000) |
| 发布 | `/teleop/cmd_vel` | `geometry_msgs/msg/Twist` | **20 Hz**(`publish_rate`,队列深度 10;节点退出前主动发一次零速) |

## 4. 按键与摇杆映射(默认 generic.yaml)

| 输入 | 功能 | 行为 |
|---|---|---|
| axes[1] 左摇杆 Y | 前进/倒车 | 正=前进(0→+0.5 m/s),负=倒车(0→−0.3 m/s);倒车保留符号 |
| axes[3] 右摇杆 X | 转向 | 正=左转,等效自行车转向角 0→+0.35 rad,ω=v·tan(δ)/L |
| buttons[5] RB | **使能(按住才走)** | 保持按住才允许运动;松开→输出立即归零 |
| buttons[4] LB | 低速模式(按住) | 速度 ×0.4(前进上限变 0.2 m/s);设 −1 可禁用 |
| — | **停止** | 松开使能 / 摇杆回中(死区内) / 输入超时 0.3 s / 节点退出发零。**以上均为软件停止,本包不含、也未验证任何硬件急停** |

方向反转开关:`speed_axis_inverted` / `steering_axis_inverted`(配置项,不改代码)。

## 5. 输出语义与限幅参数

- `linear.x`:前进速度,m/s(正=前进,负=倒车);`angular.z`:偏航角速度,rad/s(正=左转)。**物理单位,不是 PWM 刻度**。
- 阿克曼换算 ω = v·tan(δ)/L;限幅/死区/超时:

| 参数 | 值 | 说明 |
|---|---|---|
| `max_speed_forward` | 0.5 m/s | 前进上限 |
| `max_speed_reverse` | 0.3 m/s | 倒车上限 |
| `max_steering_angle` | 0.35 rad | **等效自行车转向角**上限(保守值;不是单轮舵角限位 0.55) |
| `deadzone` | 0.08 | \|摇杆\|<0.08 → 输出 0(回中抖动不产生运动) |
| `input_timeout` | 0.3 s | /joy 超时即停车并**锁定** |
| `wheelbase` | **0.36 ⚠️** | **开发假设值,非实测**;主线仿真已用出厂值 0.305——接入日三处一起统一并重跑测试(见 §8) |

## 6. 手动/自动切换与 /cmd_vel 竞争

**❌ 未实现仲裁,本包不碰 `/cmd_vel`**(只发 `/teleop/cmd_vel`,与主线链路零接触)。
集成采用**方案 B 仲裁节点**:teleop 发 `/teleop/cmd_vel`、自动模块发 `/cmd_vel`,仲裁节点按模式/优先级/超时输出唯一 `/cmd_vel` → 现有 relay → 控制器。**直接把控制器 remap 到 /teleop/cmd_vel 仅限单源临时调试,禁止与自动源同时运行。** 仲裁节点属主项目集成工作,接口设计建议见 `docs/TELEOP_INTEGRATION_GUIDE.md`。

## 7. 验证证据(⚠️ 全部仅仿真)

| 验证项(对照交付清单) | 结果 | 证据 |
|---|---|---|
| 摇杆方向/回中/死区/限幅 | ✓ | 单测 46/46(含满杆=上限、NaN/越界/短数组保护、参数校验);e2e T1(前进满舵 v=+0.5000, ω=+0.5070)、T2(倒车反舵 v=−0.3000, ω=+0.3042)、T3(低速 v=+0.2000)、T5(死区 0.05→0),数值与映射数学**4 位小数精确一致**(容差 0.02) |
| 松开使能键后停止 | ✓ | e2e T4:松开后输出即时归零 |
| 输入超时后停止 | ✓ | e2e T6:停发 /joy 后 0.3 s 超时,一个发布周期内归零 |
| 模拟 /joy 停发后恢复不自行恢复 | ✓(仅仿真) | 超时后状态机**锁定**,恢复 /joy 注入不会动——必须"先松开使能、再重新按住"才重新武装;e2e T6a 复走验证。**实体手柄物理断开/重连未实测**(真实断连涉及驱动层行为,不能由模拟停发外推)◀ 本轮收窄表述 |
| 节点退出后下游超时停车 | ✓(仿真) | 本包退出前主动发零速;主线仿真 `sim_wiring` watchdog"指令停止→自动零速"已入 42 项验证(`evidence/verify_phase1_2026-09-15_r8_full.log` 第 6 节)。**实车未验证** |

测试日志(本次交付前完整复跑,未截断):`evidence/teleop/colcon_build.log`、`evidence/teleop/pytest_unit.log`、`evidence/teleop/teleop_e2e.log`。autorepeat 整改轮次(2026-09-16):`evidence/teleop/teleop_fix_autorepeat_2026-09-16/`、`evidence/teleop/teleop_round2_2026-09-16/`、`evidence/teleop/teleop_round3_2026-09-16/`(均 clean build+46/46+e2e 9/9,未截断)。

## 8. 已知问题与未实现项(如实列出,不扩大范围)

1. **实体手柄零实测**:WSL2 无 `/dev/input/js*`;usbipd 直通未验证。轴/键号按通用布局假设,接入前须实测核对。
2. **仲裁节点未实现**(见 §6),本包不做也不越界做。
3. **wheelbase=0.36 开发假设**:主线已 0.305。接入日统一三处(本包 generic.yaml / 主线 params.yaml / Twist→Ackermann 反解 L)并重跑 e2e——满舵期望 ω 改 **0.5984 rad/s**(0.5·tan0.35/0.305;当前日志里的 0.5070 是按 0.36 的开发值)。
4. **实车未做**:PWM 转换层(1500+100x 刻度≠物理单位)、实车标定、硬件急停均不在本包,属主项目阶段 6。
5. 停止功能全部为**软件停止**(松使能/超时/退出发零),无任何硬件急停能力或宣称。
6. **【审计更正】joy autorepeat 默认值误判(2026-09-16,两轮整改)**:第一轮整改曾认定"Humble joy 默认 `autorepeat_rate=0.0`=仅变化时发布→稳住输入误超时"并据此将初版 §3 的"默认配置即满足"判为错误声明。外部验收(GPT)质疑后实测核查:本机实装 **ros-humble-joy 3.3.0**,官方文档(docs.ros.org/en/humble/p/joy/)明确默认 **`autorepeat_rate=20.0`**、`deadzone=0.05`("若设 0.0 则禁用重发"是参数语义说明而非默认值)——**该缺陷链不成立,初版 §3 声明原本正确**。误判根源:把 ROS1 wiki 的默认值 0.0 与"0.0=禁用"的语义混作 Humble 默认值。现保留的显式 `autorepeat_rate=20.0` 配置定位为**稳健性措施**:不依赖驱动/发行版默认值(ROS1 joy 与 joy_linux 默认即 0.0=仅变化发布,实车若换用此类驱动必须显式配置)。e2e 全部用 20 Hz 模拟注入(`use_joy:=false`),joy_node 路径仍只有构建+代码审查级验证。**实体手柄仍未实测**。
7. **双死区串联待实体标定**:joy_node 默认 `deadzone=0.05`(3.3.0)与本包 `deadzone=0.08` **串联生效**——joy 先在其归一化轴上做死区处理,本包死区再作用其后;实际响应区与摇杆灵敏度**不是两个数简单相加**(还受 joy 死区外重标定影响),须实体手柄现场确认手感与实际响应区后按需调整 `generic.yaml` 的 `deadzone`。◀ 本轮新增

## 9. 启动步骤(主项目侧)

```bash
# 1) 把本包放进工作区 src/ 后(本分支已置于 hwcart_sim/src/racecar_teleop)
cd hwcart_sim
rm -rf build install log && colcon build --symlink-install   # ⚠️ 必须清理重建
source install/setup.bash

# 2) 起(仿真里验证:先起仿真,再起 teleop)
ros2 launch racecar_teleop teleop.launch.py            # 实体手柄/正式形态
ros2 launch racecar_teleop teleop.launch.py use_joy:=false   # 调试:只起映射节点

# 3) 验证输出
ros2 topic echo /teleop/cmd_vel     # 按住 RB+推杆应有非零;松开 RB 立即归零
```

⚠️ **colcon 增量构建陷阱**:改/删 Python 文件后不清理 `build install log` 会跑旧代码出假结果(实测踩过)。

## 10. 本分支修改文件清单

- 新增 `hwcart_sim/src/racecar_teleop/`(包本体:setup.py / package.xml / launch / config / racecar_teleop/{mapping,state,teleop_node}.py / test/test_mapping.py / conftest.py / README.md / resource / setup.cfg)
- 新增 `docs/TELEOP_DELIVERY.md`(本文档)
- 新增 `evidence/teleop/`(三份完整测试日志)
- **未修改任何主线文件**(车辆模型/控制器/TF/赛道/导航参数零触碰)
```

*(说明:文档 §7 测试日志行也已随本轮归档同步为三轮列表;◀ 标注仅为本任务书提示改动位置,仓库正式文档中无此标记。§8 条目 1 中"WSL2 无 /dev/input/js*"一句与 §2 新接口描述的关系:WSL2 默认无 usbipd 直通时既无 event* 也无 js* 设备,该句描述的是当前实测状态,保留原措辞。)*

## 5. 第三轮验证证据(2026-09-16 复跑,🔁实现方执行输出原样转述)

本轮包代码/launch/config 零改动(仅 docs),复跑目的:证明文档改动未影响构建与测试,保持证据链完整。环境:WSL2 `xiaoche` · Ubuntu 22.04 · ROS2 Humble(joy 3.3.0)。流程:rsync → `rm -rf build install log` → `colcon build` → 单测 → e2e(`use_joy:=false`,20Hz 注入,DOMAIN 43)。

**colcon_build.log(全文)**:

```
Starting >>> racecar_teleop
Finished <<< racecar_teleop [0.95s]

Summary: 1 package finished [1.32s]
```

**pytest_unit.log(全文)**:

```
..............................................                           [100%]
46 passed in 0.04s
```

**teleop_e2e.log(全文)**:

```
== 清场检查 ==
清场OK(无任何 ros2 launch 进程)
启动日志关键行:
[INFO] [teleop_node-1]: process started with pid [447]
[teleop_node-1] [INFO] [1789539810.611994717] [teleop_node]: racecar_teleop started: /joy -> /teleop/cmd_vel at 20.0 Hz, input_timeout 0.30 s
== 运行 e2e ==
=== 用例结果 ===
[PASS] reset_松开武装: v=+0.0000(期望+0.0000) w=+0.0000(期望+0.0000) n=12
[PASS] T1_前进满舵: v=+0.5000(期望+0.5000) w=+0.5070(期望+0.5070) n=22
[PASS] T4_松开使能停车: v=+0.0000(期望+0.0000) w=+0.0000(期望+0.0000) n=8
[PASS] T2_倒车反舵: v=-0.3000(期望-0.3000) w=+0.3042(期望+0.3042) n=22
[PASS] T3_低速模式: v=+0.2000(期望+0.2000) w=+0.0000(期望+0.0000) n=22
[PASS] T5_死区内为零: v=+0.0000(期望+0.0000) w=+0.0000(期望+0.0000) n=22
[PASS] T6a_复走验证武装: v=+0.5000(期望+0.5000) w=+0.5070(期望+0.5070) n=22
[PASS] T6_停发输入超时: v=+0.0000(期望+0.0000) w=+0.0000(期望+0.0000) n=20
[PASS] 超时收敛: 最后非零指令 t=15.37s (停发于15.40s,滞后-0.03s,阈值0.8s)
=== 汇总: PASS=9 FAIL=0 ===
回收OK
HARNESS_RC=0
HARNESS_RC=0
```

*(末尾 HARNESS_RC=0 两次系执行脚本与 harness 各回显一次,原样保留。T6a/T6 行含期望值字段,与 round2 一致。)*

## 6. git 证据(🔁实现方执行输出原样转述)

**提交序列(交付仓库 ~/hwcart_sim,分支 feat/racecar-teleop,均未 push)**:

```
9ec97e7 docs(teleop): §7 测试日志行补记 round3 归档(57a3e0b 遗漏)
57a3e0b docs(teleop): 第三轮验收整改——接口区分/测试结论收窄/双死区披露
4ad1c9c fix(teleop): 更正 joy autorepeat 默认值口径(第一轮"默认0.0"定性有误)
bcffdc9 修复:joy autorepeat 缺省导致的超时误触发(01a3374 遗留)
01a3374 交付:racecar_teleop手柄遥控模块(仅仿真验证)
ed613bd 阶段1仿真车:阿克曼四轮车+雷达/相机/IMU+一键验证42项全绿
```

**git show --stat 9ec97e7(补记提交,1 file,1+/1-)**:

```
9ec97e7 docs(teleop): §7 测试日志行补记 round3 归档(57a3e0b 遗漏)
 docs/TELEOP_DELIVERY.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

*(如实披露:57a3e0b 的三处替换脚本未覆盖 §7 测试日志行,提交后实现方自检发现该行仍写"两轮复跑"而 evidence 已有 round3,随即以 9ec97e7 补记——上为本任务书 §4 内嵌全文的当前实际状态。)*

**git show --stat 57a3e0b(本轮,4 files,29+/2-)**:

```
57a3e0b docs(teleop): 第三轮验收整改——接口区分/测试结论收窄/双死区披露
 docs/TELEOP_DELIVERY.md                              |  5 +++--
 .../teleop/teleop_round3_2026-09-16/colcon_build.log |  4 ++++
 .../teleop/teleop_round3_2026-09-16/pytest_unit.log  |  2 ++
 .../teleop/teleop_round3_2026-09-16/teleop_e2e.log   | 20 ++++++++++++++++++++
 4 files changed, 29 insertions(+), 2 deletions(-)
```

**git ls-files evidence/teleop/**:共 **12 份**日志已跟踪(初版 3 + round1 3 + round2 3 + round3 3;round2 验收时已核 9 份,本轮新增 3 份:)

```
evidence/teleop/teleop_round3_2026-09-16/colcon_build.log
evidence/teleop/teleop_round3_2026-09-16/pytest_unit.log
evidence/teleop/teleop_round3_2026-09-16/teleop_e2e.log
```

**git status --short(57a3e0b 提交后)**:空输出,工作区干净。

**Windows 主副本(E:\study\racecar_teleop,main)**:本轮无文件改动(交付文档仅存在于 hwcart_sim 仓库),HEAD 仍为 **c3a5c6a**(与 §3 代码一致);你上轮已在主副本实跑 46/46。

## 7. 请你复审并输出最终结论

1. **逐项核对 §1 三项整改**:是否按你第 5/6/7 点要求落实到指定位置;内嵌全文是否同步。
2. **事实复核**:§2 接口区分与官方文档 Technical note 是否一致;§4 全文有无残留"/dev/input/js* 属 joy_node"或"实体断连已验证"类表述。
3. **新增第 7 条措辞**:双死区串联的描述是否准确、有无过度宣称(未给具体等效数值,仅描述定性影响并指向实体标定——请评估该克制程度是否恰当)。
4. **输出格式**(沿用项目口径):结论 = **通过 / 有条件通过 / 不通过**;逐项给理由;若仍有整改项,列文件+位置+期望行为。

---
*附注:本任务书承接 v2(其 §1/§2/§3/§6/§7 的事实与证据未被本轮推翻,如需可对照)。实现方本轮完整提交说明见 hwcart_sim 57a3e0b commit message。三轮验收历史:v1 不通过 → v2 有条件通过 → 本材料。*
