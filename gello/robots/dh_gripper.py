
import serial
# from pynput import keyboard
from time import sleep

class dh_device(object) :
    def __init__(self):
        self.serialPort = serial.Serial()

    def connect_device(self,portname, Baudrate) :
        ret = -1
        #print('portname: ', portname)
        self.serialPort.port = portname
        self.serialPort.baudrate = Baudrate
        self.serialPort.bytesize = 8
        self.serialPort.parity = 'N'
        self.serialPort.stopbits = 1
        self.serialPort.set_output_flow_control = 'N'
        self.serialPort.set_input_flow_control = 'N'

        self.serialPort.open()
        if(self.serialPort.isOpen()) :
            print('Serial Open Success')
            ret = 0
        else :
            print('Serial Open Error')
            ret = -1
        return ret

    def disconnect_device() :
        if(self.serialPort.isOpen()) :
            self.serialPort.close()
        else :
            return

    def device_wrire(self, write_data) :
        write_lenght = 0
        if(self.serialPort.isOpen()) :
            write_lenght = self.serialPort.write(write_data)
            if(write_lenght == len(write_data)) :
                return write_lenght
            else :
                print('write error ! send_buff :',write_data)
                return 0;
        else :
            return -1

    def device_read(self, wlen) :
        responseData = [0,0,0,0,0,0,0,0]
        if(self.serialPort.isOpen()) :
            responseData = self.serialPort.readline(wlen)
            #print('read_buff: ',responseData.hex())
            return responseData
        else :
            return -1
        

    """description of class"""

class dh_modbus_gripper(object):
    gripper_ID = 0x01
    def __init__(self):
        self.m_device = dh_device()

    def CRC16(self,nData, wLength) :
        if nData==0x00:
            return 0x0000
        wCRCWord=0xFFFF
        poly=0xA001
        for num in range(wLength):
            date = nData[num]
            wCRCWord = (date & 0xFF)^ wCRCWord
            for bit in range(8) : 
                if(wCRCWord&0x01)!=0:
                    wCRCWord>>=1
                    wCRCWord^= poly
                else:
                    wCRCWord>>=1
        return wCRCWord

    def open(self,PortName,BaudRate) :
        ret = 0
        ret = self.m_device.connect_device(PortName, BaudRate)
        if(ret < 0) :
            print('open failed')
            return ret
        else :
            print('open successful')
            return ret

    def close(self) :
        self.m_device.disconnect_device()

    def WriteRegisterFunc(self,index, value) :
        send_buf = [0,0,0,0,0,0,0,0]
        send_buf[0] = self.gripper_ID
        send_buf[1] = 0x06
        send_buf[2] = (index >> 8) & 0xFF
        send_buf[3] = index & 0xFF
        send_buf[4] = (value >> 8) & 0xFF
        send_buf[5] = value & 0xFF

        crc = self.CRC16(send_buf,len(send_buf)-2)
        send_buf[6] = crc & 0xFF
        send_buf[7] = (crc >> 8) & 0xFF

        send_temp = send_buf
        ret = False
        retrycount = 3

        while ( ret == False ):
            ret = False

            if(retrycount < 0) :
                break
            retrycount = retrycount - 1

            wdlen = self.m_device.device_wrire(send_temp)
            if(len(send_temp) != wdlen) :
                print('write error ! write : ', send_temp)
                continue

            rev_buf = self.m_device.device_read(8)
            if(len(rev_buf) == wdlen) :
                ret = True
        return ret

    def ReadRegisterFunc(self,index) :
        send_buf = [0,0,0,0,0,0,0,0]
        send_buf[0] = self.gripper_ID
        send_buf[1] = 0x03
        send_buf[2] = (index >> 8) & 0xFF
        send_buf[3] = index & 0xFF
        send_buf[4] = 0x00
        send_buf[5] = 0x01

        crc = self.CRC16(send_buf,len(send_buf)-2)
        send_buf[6] = crc & 0xFF
        send_buf[7] = (crc >> 8) & 0xFF

        send_temp = send_buf
        ret = False
        retrycount = 3

        while ( ret == False ):
            ret = False

            if(retrycount < 0) :
                break
            retrycount = retrycount - 1

            wdlen = self.m_device.device_wrire(send_temp)
            if(len(send_temp) != wdlen) :
                print('write error ! write : ', send_temp)
                continue

            rev_buf = self.m_device.device_read(7)
            if(len(rev_buf) == 7) :
                value = ((rev_buf[4]&0xFF)|(rev_buf[3] << 8))
                ret = True
            #('read value : ', value)
        return value

    def Initialization(self) :
        self.WriteRegisterFunc(0x0100,0xA5)
        
    def SetTargetPosition(self,refpos) :
        self.WriteRegisterFunc(0x0103,refpos);

    def SetTargetForce(self,force) :
        self.WriteRegisterFunc(0x0101,force);
        
    def SetTargetSpeed(self,speed) :
        self.WriteRegisterFunc(0x0104,speed);

    def GetCurrentPosition(self) :
        return self.ReadRegisterFunc(0x0202);

    def GetCurrentTargetForce(self) :
        return self.ReadRegisterFunc(0x0101);

    def GetCurrentTargetSpeed(self) :
        return self.ReadRegisterFunc(0x0104);

    def GetInitState(self) :
        return self.ReadRegisterFunc(0x0200);

    def GetGripState(self) :
        return self.ReadRegisterFunc(0x0201);

    """description of class"""

class dh_gripper():
    def __init__(self, baudrate=115200, port='/dev/ttyCH343USB2'):
            
        self.m_gripper = dh_modbus_gripper()
        self.m_gripper.open(port,baudrate)
        self.m_gripper.Initialization();
        

        self.initstate = 0
        while(self.initstate != 1):
            self.initstate = self.m_gripper.GetInitState()
            sleep(0.2)
        print('gripper init')
        self.isOpen = True
        self.write_force(10)
        self.write_speed(100)

        self.g_state = 0
        self.close()

    def write_force(self,force=100):
        '''
        设置力大小，最大100,最小0
        '''
        self.m_gripper.SetTargetForce(force)

    def write_speed(self,speed=100):
        '''
        设置速度大小，最大100,最小0
        '''
        self.m_gripper.SetTargetSpeed(speed)


    def write_position(self,position):
        '''
        写入目标位置，0闭合，1000张开
        '''
        self.g_state = 0
        self.m_gripper.SetTargetPosition(position)
        while(self.g_state == 0) :
            self.g_state = self.m_gripper.GetGripState()
            sleep(0.2)
        
    def write_position_without_wait(self,position):
        '''
        写入目标位置，0闭合，1000张开
        '''
        self.g_state = 0
        self.m_gripper.SetTargetPosition(position)

    def close(self):
        '''
        夹爪闭合
        '''
        self.write_position(0)
        self.isOpen = False

    def open(self):
        '''
        夹爪张开
        '''
        self.write_position(700)
        self.isOpen = True

    def move(self,position,speed=100,force=40):
        # assert 0<=force<=100
        # assert 0<=speed<=100
        assert 0<=position<=1
        # self.write_force(force)
        # self.write_speed(speed)
        actual_position = int(position*1000)
        self.write_position_without_wait(actual_position)


    def disable_gripper(self):
        '''
        失能夹爪
        '''
        self.m_gripper.close()
       
    def get_current_position(self):
        return self.m_gripper.GetCurrentPosition()/1000

    def on_keyboard_pressed(self, key):    
        try:
            if(key.name == 'space'):
                if(self.isOpen):
                    self.close()
                    print('set position as 0')

                else:
                    self.open()     
                    print('set position as -1')

        except:
    
               
            return
 




if __name__ == '__main__':
    import time
    import random

    foo = dh_gripper(port='/dev/ttyCH343USB2')
    foo.move(0.7)

    time.sleep(5)
    t1 =  time.time()
    # foo.close()
    # foo.write_position_without_wait(0)
    foo.move(0)
    t2 =  time.time()
    print(foo.get_current_position())
    t3 =  time.time()
    # foo.move(0.7)
    # foo.write_position_without_wait(1000)
    # foo.open()
    t4 =  time.time()

    print(f'close:{t2-t1}\nread:{t3-t2}\nopen:{t4-t3}')

    # foo.open()
    # with keyboard.Listener(on_press=foo.on_keyboard_pressed) as listener:
    #     listener.join()
            
