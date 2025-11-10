from typing import Dict
import sys
sys.path.append("/home/ju/Workspace/gello_software")
import numpy as np
from gello.robots.robot import Robot
import time

class URRobot(Robot):
    """A class representing a UR robot."""

    def __init__(self, robot_ip: str = "192.168.1.10", no_gripper: bool = False, gripper_type: str = "chingtek"):
        import rtde_control
        import rtde_receive

        [print("in ur robot") for _ in range(4)]
        try:
            self.robot = rtde_control.RTDEControlInterface(robot_ip)
        except Exception as e:
            print(e)
            print(robot_ip)

        self.r_inter = rtde_receive.RTDEReceiveInterface(robot_ip)
        if not no_gripper :
            if gripper_type == 'dh':
                from gello.robots.dh_gripper import dh_gripper
                self.gripper = dh_gripper()
                print("gripper dh connected")
            elif gripper_type == 'chingtek':
                from gello.robots.chingtek_gripper import chingtekGripper
                self.gripper = chingtekGripper()
                print("gripper chingtek connected")
            else :
                print("no suitable gripper")
                no_gripper = True


        # self.movej([0.,-1.57,1.57,-3.14,-1.57,1.57])

        [print("connect") for _ in range(4)]

        self._free_drive = False
        self.robot.endFreedriveMode()
        # self.set_freedrive_mode(True)
        self._use_gripper = not no_gripper
        # self.gripper_lock = threading.Lock()

    def num_dofs(self) -> int:
        """Get the number of joints of the robot.

        Returns:
            int: The number of joints of the robot.
        """
        if self._use_gripper:
            return 7
        return 6

    def _get_gripper_pos(self) -> float:
        
        time.sleep(0.01)
        # with self.gripper_lock:
        gripper_pos = self.gripper.get_current_position()
        return gripper_pos

    def get_joint_state(self) -> np.ndarray:
        """Get the current state of the leader robot.

        Returns:
            T: The current state of the leader robot.
        """
        robot_joints = self.r_inter.getActualQ()
        if self._use_gripper:
            gripper_pos = self._get_gripper_pos()
            pos = np.append(robot_joints, gripper_pos)
        else:
            pos = robot_joints
        return pos

    def command_joint_state(self, joint_state: np.ndarray) -> None:
        """Command the leader robot to a given state.

        Args:
            joint_state (np.ndarray): The state to command the leader robot to.
        """
        velocity = 0.5
        acceleration = 0.5
        dt = 1.0 / 500  # 2ms
        lookahead_time = 0.2
        gain = 100

        robot_joints = joint_state[:6]
        t_start = self.robot.initPeriod()
        self.robot.servoJ(
            robot_joints, velocity, acceleration, dt, lookahead_time, gain
        )

        self.robot.waitPeriod(t_start)

        if self._use_gripper:
            # 定义夹爪控制函数
            # def handle_gripper():
            #     with self.gripper_lock:
            #         if joint_state[-1] < 0.5 and self.gripper.isOpen:
            #             self.gripper.close()
            #         if joint_state[-1] > 0.5 and not self.gripper.isOpen:
            #             self.gripper.open()
            
            # # 启动线程执行夹爪控制，不阻塞主函数
            # gripper_thread = threading.Thread(target=handle_gripper)
            # gripper_thread.start()

            if joint_state[-1]< 0.5 and self.gripper.isOpen:
                self.gripper.move(0)
                self.gripper.isOpen = False
                print("move 0")
            if joint_state[-1]> 0.5 and not self.gripper.isOpen:
                self.gripper.move(0.7)
                self.gripper.isOpen = True

                print("move 700")


            # gripper_pos = joint_state[-1] * 1000
            # print(gripper_pos)
            # self.gripper.move(int(gripper_pos), 100, 20)

    def movej(self,joint_state):
        velocity = 0.5
        acceleration = 0.5
        self.robot.moveJ(
            joint_state, velocity, acceleration
        )
        time.sleep(2)

    def freedrive_enabled(self) -> bool:
        """Check if the robot is in freedrive mode.

        Returns:
            bool: True if the robot is in freedrive mode, False otherwise.
        """
        return self._free_drive

    def set_freedrive_mode(self, enable: bool) -> None:
        """Set the freedrive mode of the robot.

        Args:
            enable (bool): True to enable freedrive mode, False to disable it.
        """
        if enable and not self._free_drive:
            self._free_drive = True
            self.robot.teachMode()
        elif not enable and self._free_drive:
            self._free_drive = False
            self.robot.endTeachdriveMode()

    def get_observations(self) -> Dict[str, np.ndarray]:
        joints = self.get_joint_state()
        pos_quat = np.zeros(7)
        gripper_pos = np.array([joints[-1]])
        return {
            "joint_positions": joints,
            "joint_velocities": joints,
            "ee_pos_quat": pos_quat,
            "gripper_position": gripper_pos,
        }


def main():
    robot_ip = "192.168.123.101"
    ur = URRobot(robot_ip, no_gripper=True)
    ur.movej([0.,-1.57,-1.57,-1.57,1.57,0.])
    # ur.set_freedrive_mode(True)
    print(ur.robot.teachMode())
    
    print( ur.robot.getFreedriveStatus())
    time.sleep(10)
    print(ur.robot.endTeachMode())
    # print(ur.get_observations())


if __name__ == "__main__":
    main()
