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
