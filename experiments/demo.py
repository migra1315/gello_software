import pygame
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import tyro
import time

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



def main(args):
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