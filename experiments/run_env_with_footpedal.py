import glob
import time
import pygame
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import tyro
import sys
sys.path.append("/home/ju/Workspace/gello_software")
from gello.env import RobotEnv
from gello.robots.robot import PrintRobot
from gello.utils.launch_utils import instantiate_from_dict
from gello.zmq_core.robot_node import ZMQClientRobot
from gello.zmq_core.camera_node import ZMQClientCamera
from gello.agents.agent import Agent


def print_color(*args, color=None, attrs=(), **kwargs):
    import termcolor

    if len(args) > 0:
        args = tuple(termcolor.colored(arg, color=color, attrs=attrs) for arg in args)
    print(*args, **kwargs)


@dataclass
class Args:
    agent: str = "gello"
    robot_port: int = 6001
    wrist_camera_port: int = 5000
    base_camera_port: int = 5001
    hostname: str = "127.0.0.1"
    robot_type: str = "ur"  # only needed for quest agent or spacemouse agent
    hz: int = 100
    start_joints: Optional[Tuple[float, ...]] = None

    gello_port: Optional[str] = None
    mock: bool = False
    use_save_interface: bool = False
    data_dir: str = "~/bc_data"
    bimanual: bool = True
    verbose: bool = False
    footpedal_key: str = "space"  # Default key to use as footpedal
    def __post_init__(self):
        if self.start_joints is not None:
            self.start_joints = np.array(self.start_joints)

def run_control_onestep(
    env: RobotEnv,
    agent: Agent,
    print_timing: bool = True,
    use_colors: bool = False,
) -> None:
    """Run the main control loop.

    Args:
        env: Robot environment
        agent: Agent for control
        save_interface: Optional save interface for data collection
        print_timing: Whether to print timing information
        use_colors: Whether to use colored terminal output
    """
    # Check if we can use colors
    colors_available = False
    if use_colors:
        try:
            from termcolor import colored
            colors_available = True
            start_msg = colored("\rStart 🚀🚀🚀", color="green", attrs=["bold"])
        except ImportError:
            start_msg = "\rStart 🚀🚀🚀"
    else:
        start_msg = "\rStart 🚀🚀🚀"

    print(start_msg)

    start_time = time.time()
    obs = env.get_obs()

    if print_timing:
        num = time.time() - start_time
        message = f"\rTime passed: {round(num, 2)}          "

        if colors_available:
            print(
                colored(message, color="white", attrs=["bold"]), end="", flush=True
            )
        else:
            print(message, end="", flush=True)

    action = agent.act(obs)
    obs = env.step(action)

def main(args):
    if args.mock:
        robot_client = PrintRobot(8, dont_print=True)
        camera_clients = {}
    else:
        camera_clients = {
            # you can optionally add camera nodes here for imitation learning purposes
            #  "wrist": ZMQClientCamera(port=args.wrist_camera_port, host=args.hostname),
            #  "base": ZMQClientCamera(port=args.base_camera_port, host=args.hostname),
        }
        robot_client = ZMQClientRobot(port=args.robot_port, host=args.hostname)
    env = RobotEnv(robot_client, control_rate_hz=args.hz, camera_dict=camera_clients)

    agent_cfg = {}
    if args.bimanual:
        if args.agent == "gello":
            # dynamixel control box port map (to distinguish left and right gello)
            right = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAFPVNW-if00-port0"
            left = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0"
            agent_cfg = {
                "_target_": "gello.agents.agent.BimanualAgent",
                "agent_left": {
                    "_target_": "gello.agents.gello_agent.GelloAgent",
                    "port": left,
                },
                "agent_right": {
                    "_target_": "gello.agents.gello_agent.GelloAgent",
                    "port": right,
                },
            }
        else:
            raise ValueError(f"Invalid agent name for bimanual: {args.agent}")

        # System setup specific. This reset configuration works well on our setup. If you are mounting the robot
        # differently, you need a separate reset joint configuration.
        # going to start position
        print("Going to start position")
        reset_joints_left = np.deg2rad([0, -90, -90, -90, 90, 0, 0])
        reset_joints_right = np.deg2rad([0, -90, 90, -90, -90, 0, 0])
        reset_joints = np.concatenate([reset_joints_left, reset_joints_right])
        curr_joints = env.get_obs()["joint_positions"]
        max_delta = (np.abs(curr_joints - reset_joints)).max()
        steps = min(int(max_delta / 0.01), 100)

        for jnt in np.linspace(curr_joints, reset_joints, steps):
            env.step(jnt)
    else:
        if args.agent == "gello":
            gello_port = args.gello_port
            if gello_port is None:
                usb_ports = glob.glob("/dev/serial/by-id/*")
                print(f"Found {len(usb_ports)} ports")
                if len(usb_ports) > 0:
                    gello_port = usb_ports[0]
                    print(f"using port {gello_port}")
                else:
                    raise ValueError(
                        "No gello port found, please specify one or plug in gello"
                    )
            agent_cfg = {
                "_target_": "gello.agents.gello_agent.GelloAgent",
                "port": gello_port,
                "start_joints": args.start_joints,
            }
            if args.start_joints is None:
                reset_joints = np.deg2rad(
                    [0, -90, 90, -90, -90, 0, 0]
                )  # Change this to your own reset joints
            else:
                reset_joints = np.array(args.start_joints)

            curr_joints = env.get_obs()["joint_positions"]
            print("---------------------")
            print(curr_joints)
            if reset_joints.shape == len(curr_joints):
            # if reset_joints.shape == curr_joints.shape:
                max_delta = (np.abs(curr_joints - reset_joints)).max()
                steps = min(int(max_delta / 0.01), 100)

                for jnt in np.linspace(curr_joints, reset_joints, steps):
                    env.step(jnt)
                    time.sleep(0.001)
        else:
            raise ValueError("Invalid agent name")

    agent = instantiate_from_dict(agent_cfg)


    # 注释掉原有的控制循环，因为我们将使用脚踏控制功能
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Robot Teleoperation Control")
    clock = pygame.time.Clock()

    # Set up font for displaying instructions
    try:
        font = pygame.font.SysFont("Arial", 24)
    except:
        font = pygame.font.Font(None, 24)

    # Get footpedal key code
    footpedal_key_code = getattr(pygame, f"K_{args.footpedal_key.lower()}", pygame.K_SPACE)

    # State variables
    pedal_press_count = 0
    last_pedal_state = False
    teleoperation_active = False
    calibration_done = False

    # Main control loop with footpedal functionality
    print("Starting robot teleoperation with footpedal control")
    print(f"Use {args.footpedal_key.upper()} key as footpedal")
    print("Step 1: Press footpedal twice quickly to calibrate")
    print("Step 2: Press and hold footpedal to start teleoperation")
    print("Step 3: Release footpedal to stop teleoperation")
    print("Step 4: Repeat from step 1 to recalibrate")

    last_press_time = 0


    try:
        while True:
            # Handle events
            current_pedal_state = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                
            # Check key state (continuous check)
            keys = pygame.key.get_pressed()
            current_pedal_state = keys[footpedal_key_code]
            if current_pedal_state:
                last_press_time = time.time()
            # Logic for footpedal double press calibration
            current_time = time.time()
            if not calibration_done and current_pedal_state and not last_pedal_state:
                # Pedal pressed
                if current_time - last_press_time < 0.5: pedal_press_count += 1 # Double press within 0.5s
                else:pedal_press_count = 1
                print('pedal_press_count',pedal_press_count)
                
                # Calibration when double pressed
                if pedal_press_count == 2:
                    print("Calibrating: Moving slave robot to master position...")
                    # **************************************************
                    # 判断主从机械臂位置是否同步
                    while(1):
                        start_pos = agent.act(env.get_obs())
                        print("gello机械臂的当前角度",start_pos)

                        obs = env.get_obs()
                        joints = obs["joint_positions"]
                        print("ur机械臂的当前角度",joints)

                        abs_deltas = np.abs(start_pos - joints)
                        id_max_joint_delta = np.argmax(abs_deltas)

                        max_joint_delta = 0.8

                        if (abs_deltas[id_max_joint_delta] < max_joint_delta):
                            break

                        id_mask = abs_deltas > max_joint_delta
                        print(id_mask)
                        ids = np.arange(len(id_mask))[id_mask]
                        for i, delta, joint, current_j in zip(
                            ids,
                            abs_deltas[id_mask],
                            start_pos[id_mask],
                            joints[id_mask],
                        ):
                            print(
                                f"\rjoint[{i}]: \t delta: {delta:4.3f} , leader: \t{joint:4.3f} , follower: \t{current_j:4.3f}"
                            )
                            time.sleep(0.1)

                    # **************************************************
                    # 主从机械臂位置接近后，开始同步，增加循环重试机制
                    print(f"Start pos: {len(start_pos)}", f"Joints: {len(joints)}")
                    assert len(start_pos) == len(joints), \
                        f"agent output dim = {len(start_pos)}, but env dim = {len(joints)}"

                    max_sync_attempts = 5  # 最大同步尝试次数
                    sync_threshold = 0.5  # 同步阈值
                    sync_completed = False
                    
                    for attempt in range(max_sync_attempts):
                        print(f"\nAttempt {attempt + 1}/{max_sync_attempts} to synchronize robot positions...")
                        
                        # 执行同步操作
                        max_delta = 0.05
                        for _ in range(25):
                            obs = env.get_obs()
                            command_joints = agent.act(obs)
                            current_joints = obs["joint_positions"]
                            delta = command_joints - current_joints
                            max_joint_delta = np.abs(delta).max()
                            if max_joint_delta > max_delta:
                                delta = delta / max_joint_delta * max_delta
                            env.step(current_joints + delta)
                        
                        # 判断是否完成同步
                        obs = env.get_obs()
                        joints = obs["joint_positions"]
                        action = agent.act(obs)
                        joint_differences = action - joints
                        print("Joint differences after sync attempt:", joint_differences)
                        
                        # 检查是否所有关节差异都在阈值范围内
                        if not (joint_differences > sync_threshold).any():
                            print(f"Synchronization successful! All joint differences are within {sync_threshold} threshold.")
                            sync_completed = True
                            break
                        else:
                            # 打印哪些关节差异过大
                            joint_index = np.where(joint_differences > sync_threshold)[0]
                            print(f"Synchronization failed. Joints with differences > {sync_threshold}:")
                            for j in joint_index:
                                print(f"  Joint [{j}], leader: {action[j]:.4f}, follower: {joints[j]:.4f}, diff: {joint_differences[j]:.4f}")
                            print(f"Retrying synchronization...")
                    
                    # 如果多次尝试后仍未完成同步，发出警告退出
                    if not sync_completed:
                        print("\nWARNING: Could not complete synchronization after multiple attempts.")
                        exit(1)

                    print("Calibration complete!")
                    calibration_done = True
                    pedal_press_count = 0
                    continue
                 # Teleoperation when pedal is held and calibrated
            if current_pedal_state and calibration_done:
                if not teleoperation_active:
                    print("Teleoperation started")
                    teleoperation_active = True
                print('start teleoperation')
                run_control_onestep(env, agent, use_colors=True)


            # stop teleoperation when pedal is released
            if  not current_pedal_state and teleoperation_active and calibration_done:
                print("Teleoperation stopped")
                teleoperation_active = False
            
            # # Reset calibration if pedal is not pressed for a long time
            if not current_pedal_state and calibration_done and current_time - last_press_time > 5.0:
                calibration_done = False
                print("Calibration reset: Press footpedal twice to recalibrate")
            
            # Update display
            screen.fill((0, 0, 0))
            
            # Display status
            status_text = "Status: "
            if not calibration_done:
                status_text += "Ready for calibration (double press footpedal)"
                color = (255, 255, 0)  # Yellow
            elif teleoperation_active:
                status_text += "Teleoperation active"
                color = (0, 255, 0)  # Green
            else:
                status_text += "Ready (press footpedal to start)"
                color = (0, 255, 255)  # Cyan
            
            text = font.render(status_text, True, color)
            screen.blit(text, (20, 20))
            
            # Display instructions
            if not calibration_done:
                inst_text = "Double press SPACE to calibrate"
            else:
                inst_text = "Hold SPACE for teleoperation"
            
            inst = font.render(inst_text, True, (255, 255, 255))
            screen.blit(inst, (20, 60))
            
            pygame.display.flip()
            last_pedal_state = current_pedal_state
            
            # Limit frame rate
            clock.tick(args.hz)


    except KeyboardInterrupt:
        print("\nShutting down teleoperation")
    finally:
        pygame.quit()
    
 
if __name__ == "__main__":
    main(tyro.cli(Args))
