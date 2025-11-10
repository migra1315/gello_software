import time

import minimalmodbus
import serial
import threading
# from pynput import keyboard

class chingtekGripper():
    def __init__(self,PORT='/dev/ttyCH343USB0'):
        self.lock = threading.Lock()
        # 寄存器地址
        self.POSITION_HIGH_8 = 0x0102  # 位置寄存器高八位
        self.POSITION_LOW_8 = 0x0103  # 位置寄存器低八位
        self.SPEED = 0x0104
        self.FORCE = 0x0105
        self.MOTION_TRIGGER = 0x0108
        self.BAUD = 115200
        self.isOpen = False
        self.connect(PORT)  
        self.Activate()

    # 写入位置
    def write_position(self, value):
        with self.lock:
            self.instrument.write_long(self.POSITION_HIGH_8, value)

    # 写入速度
    def write_speed(self, speed):
        with self.lock:
            self.instrument.write_register(self.SPEED, speed, functioncode=6)

    # 写入力
    def write_force(self, force):
        with self.lock:
            self.instrument.write_register(self.FORCE, force, functioncode=6)

    # 触发运动
    def trigger_motion(self):
        with self.lock:
            self.instrument.write_register(self.MOTION_TRIGGER, 1, functioncode=6)

    def read_position(self):
        with self.lock:
            # 读取实时反馈位置信息 high（0x0609）和 low（0x060A）
            high_part = self.instrument.read_register(0x0609, functioncode=3)
            low_part = self.instrument.read_register(0x060A, functioncode=3)
            # 计算执行器实时位置
            return (high_part << 16) + low_part
    
    def connect(self, PORT = 'COM5'):
        self.PORT = PORT
        self.instrument = minimalmodbus.Instrument(self.PORT, 1)
        self.instrument.serial.baudrate = self.BAUD
        self.instrument.serial.timeout = 1     

    def close(self):
        print("-----")
        actual_position = self.joint_states_to_actual_position(0)
        self.write_position(actual_position)
        self.trigger_motion()
        self.isOpen = False


    def open(self):
        print("-----")
        actual_position = self.joint_states_to_actual_position(1)
        self.write_position(actual_position)
        self.trigger_motion()
        self.isOpen = True


    def Activate(self):
        #写入位置

        self.write_position(0)
        # 写入速度
        self.write_speed(100)

        # 写输入
        self.write_force(100)

        # 触发运动
        # self.trigger_motion()
        # time.sleep(0.5)

        # self.write_position(0)
        # self.trigger_motion()

    # 将关节位置转为实际位置
    def joint_states_to_actual_position(self,joint_state):
        '''
        0 完全闭合
        1 完全开启
        '''
        joint_state = 0 if joint_state < 0 else joint_state
        joint_state = 1 if joint_state > 1 else joint_state
        return 9000 - int((joint_state)*9000)
    
    # 将读取电机位置转为关节位置
    def motor_position_to_joint_states(self, motor_position):
        motor_position = 1000 if motor_position > 1000 else motor_position
        motor_position = 0 if motor_position < 0 else motor_position
        return (1000 - motor_position)/1000
    
    def print_position_continuously(self):
        """以10Hz的频率打印位置信息"""
        while True:
            current_position = self.motor_position_to_joint_states(self.read_position())
            print(f"Current position (10Hz): {current_position}")
            time.sleep(0.1)  # 10Hz

    def get_current_position(self):
        current_position = self.motor_position_to_joint_states(self.read_position())
        return current_position 
    
    def on_keyboard_pressed(self, key):    
        try:
            if(key.name == 'space'):
                if(self.isOpen):
                    self.close()
                    print('set position as 0')

                else:
                    self.open()     
                    print('set position as -1')

            # 读取位置信息并打印
            elif(key.name=='alt'):
                current_position = self.read_position()
                print(f"Current position: {current_position}")
        except:
    
               
            return

    def move(self,position,speed=100,force=100):
        # assert 0<=force<=100
        # assert 0<=speed<=100
        assert 0<=position<=1
        actual_position = self.joint_states_to_actual_position(position)
        # print("actual_position: ",actual_position)
        self.write_position(actual_position)
        self.trigger_motion()


if __name__ == '__main__':
  

    gripper = chingtekGripper(PORT='/dev/ttyCH343USB0')  
    gripper.close()       
    print(gripper.motor_position_to_joint_states(gripper.read_position()))   
    print(gripper.read_position())   
    # gripper.move(1)
    # gripper.write_position(9000)
    # gripper.trigger_motion()
    # """启动打印位置信息的线程"""
 
    # with keyboard.Listener(on_press=gripper.on_keyboard_pressed) as listener:
    #     listener.join()
  
    # foo = colorGripper()
    # # foo.close()
    # foo.close()
    # with keyboard.Listener(on_press=foo.on_keyboard_pressed) as listener:
    #     listener.join()
    # foo.open()

