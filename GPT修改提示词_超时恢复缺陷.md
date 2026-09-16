# 任务书：修复 01a3374 交付中的超时误触发/恢复缺陷（joy_node autorepeat）

> 角色：你（GPT）是本修复任务的实现者。按本任务书完成修复，禁止扩大范围。
> 项目：hwcart_sim 阶段1 配套手柄遥控包 `racecar_teleop`（feat/racecar-teleop 分支，交付 commit **01a3374**）。

## 1. 代码位置（三份拷贝，改主副本后同步）

| 拷贝 | 路径 | 说明 |
|---|---|---|
| **主副本（在此改）** | `E:\study\racecar_teleop\`（Windows，独立 git 仓库） | 纯 Python 分层：mapping.py / state.py / teleop_node.py + launch/config/test |
| 构建验证拷贝 | WSL(xiaoche) `~/teleop_ws/src/racecar_teleop/`（rsync 同步，无 git） | clean colcon build + 46 单测 + 9 e2e 在这里跑 |
| 交付拷贝 | WSL `~/hwcart_sim/src/racecar_teleop/`（分支 feat/racecar-teleop = 01a3374，远程 github.com/MilkSliceKing/Astrahuaweicar 私有） | 交付归档；文档 `docs/TELEOP_DELIVERY.md` 在 hwcart_sim 仓库根 docs/ 下 |

## 2. 缺陷描述（已定位、已核实，勿再自行排查方向偏离）

**现象链**：真实手柄场景下，驾驶员按住使能键（RB）并稳住油门正常行驶时，手柄状态无变化 → `joy_node` 不发任何 `/joy` 消息 → 0.3 s 后 `racecar_teleop` 输入超时 → 误判"手柄断开"→ 锁定并输出零速 → 行驶中无故反复停车，且每次都要"松开使能再按住"才能恢复。

**根因（两处，同一缺陷）**：

1. `launch/teleop.launch.py` 第 29–33 行启动 `joy_node` 时**未传任何参数**：

```python
Node(
    package='joy', executable='joy_node', name='joy_node',
    output='screen',
    condition=IfCondition(use_joy),
),
```

ROS2 Humble 的 joy 包 `autorepeat_rate` **默认 0.0 = 禁用重发，只在手柄状态变化时发布**（官方文档：https://docs.ros.org/en/humble/p/joy/ ）。包内 `input_timeout=0.3 s` 的前提是"/joy 持续更新、间隔 < 0.3 s"，此前提在默认 joy_node 下不成立。注意：许多手柄摇杆存在微小抖动、且 joy 侧 `deadzone` 默认 0.0，抖动会凑巧持续产生"变化"掩盖该问题——**修复不得依赖这种偶然**。

2. `docs/TELEOP_DELIVERY.md` 第 29 行（接口表）错误声称："`joy_node` 自带 autorepeat，默认配置即满足"——与事实相反，必须一并更正。README 无此错误声明，不用动。

**为什么测试没发现**：全部 e2e 用 `use_joy:=false` + 20 Hz 模拟注入 `/joy`，从未经过真实 joy_node，前置条件假设未被检验。

**已排除的方向（勿改）**：`state.py` 的超时锁定与"先松开再按住"恢复逻辑本身经审查与 e2e T6/T6a 验证是正确的——缺陷不在状态机，在 /joy 供给前提。

## 3. 修复要求

### 3.1 launch/teleop.launch.py

给 `joy_node` 显式配置 `autorepeat_rate`，并做成 launch 参数：

- 新增 `DeclareLaunchArgument('joy_autorepeat_rate', default_value='20.0', ...)`（描述里写明单位 Hz、取值依据见下）。
- joy Node 加 `parameters=[{'autorepeat_rate': ParameterValue(LaunchConfiguration('joy_autorepeat_rate'), value_type=float)}]`。
- 必须用 `from launch_ros.parameter_descriptions import ParameterValue` 包一层 `value_type=float`——Humble 下直接传 `LaunchConfiguration` 会变成 string 类型参数，joy_node 侧参数类型不符。
- 取值依据（写进参数 description）：需满足 `/joy` 间隔 < `input_timeout`(0.3 s)，即 > 1/0.3 ≈ 3.33 Hz 并留裕量；默认 20.0 Hz 与 `publish_rate` 及 e2e 注入频率一致；上限 1000.0（joy 官方限制）。
- `use_joy:=false` 路径行为必须完全不变（e2e 注入模式不受影响）。

### 3.2 docs/TELEOP_DELIVERY.md（hwcart_sim 仓库）

- 第 29 行接口表：改为如实描述——joy 默认 autorepeat_rate=0.0（仅变化发布），本包 launch 已显式设 20 Hz（launch 参数 `joy_autorepeat_rate` 可调），并给出取值下限依据。
- §8 已知问题：追加一条如实披露：交付初版（01a3374）漏配 joy autorepeat、且文档误称"默认即满足"；本修复为 launch 显式配置 + 文档更正；实体手柄仍未实测。

### 3.3 明确禁止改动（范围红线）

- 不改 `state.py`/`mapping.py`/`teleop_node.py` 任何逻辑与参数（`input_timeout`、限幅、死区、使能语义、ω 数学全不动）。
- 不改 generic.yaml 的现有键值（wheelbase 0.36→0.305 统一是另一件已立案的事，勿混入）。
- 不动 hwcart_sim 主线任何文件；不实现仲裁节点；不合并 main。
- 不顺手重构、不改测试断言数值。

## 4. 验收标准（全部满足才算完成）

1. [ ] `teleop.launch.py` 按上述要求传入 float 类型的 `autorepeat_rate`（默认 20.0，launch 参数名 `joy_autorepeat_rate`）。
2. [ ] `TELEOP_DELIVERY.md` 第 29 行错误声明已更正，§8 已追加披露，前后文无残留矛盾（通读全文一遍）。
3. [ ] 单测仍 46/46（纯 pytest，Windows 或 WSL 均可跑：`python -m pytest test/ -v`）。
4. [ ] WSL 侧按项目流程重跑：rsync 主副本 → teleop_ws → **rm -rf build install log 后 clean colcon build**（ament_python 增量构建不清旧文件的坑，必须 clean）→ 46/46 → e2e 9/9（数值期望不变，ω 仍按 wheelbase 0.36 口径）。
5. [ ] 若重跑证据，日志按项目规则归档：完整未截断、日期轮次命名，入 hwcart_sim `evidence/teleop/`（.gitignore 已有 `!evidence/*.log` 例外，勿新建会被 `*.log` 吞掉的目录）。
6. [ ] 提交在 feat/racecar-teleop 分支（hwcart_sim 仓库）或主副本仓库，提交信息说明"修复 joy autorepeat 缺省导致的超时误触发"，不夹带其他改动。

## 5. 背景参考（只读，不属本次改动）

- 车为阿克曼四轮（非差速），Twist 语义 linear.x=m/s、angular.z=rad/s，ω=v·tan(δ)/L。
- 主线 wheelbase 已统一出厂值 0.305（car_controller_new.cpp, b25baa6），本包接入日三处一起改并重跑 e2e——与本任务无关。
- WSL 内跑网络 git 必须 `GIT_TERMINAL_PROMPT=0`；推送用 Windows 侧 git。
