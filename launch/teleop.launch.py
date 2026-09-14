"""Launch file for racecar_teleop.

Two modes, selected by the ``use_joy`` launch argument:

  * ``use_joy:=true``  (default) — also launch the ``joy`` driver.
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


def generate_launch_description():
    pkg = 'racecar_teleop'
    config = os.path.join(
        get_package_share_directory(pkg), 'config', 'generic.yaml')
    use_joy = LaunchConfiguration('use_joy')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_joy', default_value='true',
            description='Launch the joy driver node in addition to teleop'),
        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen',
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
