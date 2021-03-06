'''!
@file       jointTask.py
@brief      Implements motor, encoder, and controller to control joints
@details    Creates a motor driver, encoder, and closed loop controller corresponding to
            a joint on the 3RRR planar parallel robot. The run function is used by
            the cotask scheduler to control the motion of each joint
@author     Jonathan Cederquist
@author     Tim Jain
@author     Philip Pang
@date       Last Modified 3/5/22
'''

import pyb
import utime
import RoboMotorDriver
import RoboEncoderDriver
import ClosedLoop

class JointTask:
    '''! 
    This class implements a motor, encoder, and control task to control robot joints. 
    '''
    
    def __init__ (self, ready, motor_const, encoder_const, kp, ki, setpoint, queue_theta):
        '''! 
        @brief                  Creates a JointTask object
        @details                Creates RoboMotorDriver, RoboEncoderDriver, and ClosedLoop
                                controller objects corresponding to the given constants to
                                control the motion of a joint on the 3 RRR planar parallel
                                robot.
        @param ready            A task_share.Share variable that is used as a flag to turn
                                off the joint motor when the robot shuts down
        @param motor_const      An integer denoting the motor associated with the joint.
                                Motor 1 corresponds to M1, pins PB5 and PB3
                                Motor 2 corresponds to M2, pins PA6 and PA7
                                Motor 3 corresponds to M3, pins PA9 and PB4
        @param encoder_const    An integer denoting the encoder associated with the motor.
                                Encoder 1 corresponds to pins PB6 and PB7 with timer 4
                                Encoder 2 corresponds to pins PC6 and PC7 with timer 8
                                Encoder 3 corresponds to pins PA0 and PA1 with timer 5
        @param kp               The proportional gain constant used for the closed loop controller
                                The constant should be given in units of [% duty cycle/degree]
        @param ki               The integral gain constatn used for the closed loop controller
                                The constant should be given in units of [% duty cycle * sec/degree]
        @param setpoint         The setpoint in degrees for the closed loop controller
        @param queue_theta      The task_share.Queue corresponding to this joint's theta value
        '''
        
        self.motor_const = motor_const
        
        self.ready = ready
        
        # Check motor number and create corresponding RoboMotorDriver
        if motor_const==1:
            pinB5 = pyb.Pin(pyb.Pin.board.PB5, pyb.Pin.OUT_PP)
            pinB3 = pyb.Pin(pyb.Pin.board.PB3, pyb.Pin.OUT_PP)
    
            self.motor = RoboMotorDriver.RoboMotorDriver(pinB5, pinB3, 2, 2)
            
        elif motor_const==2:
            pinA6 = pyb.Pin(pyb.Pin.board.PA6, pyb.Pin.OUT_PP)
            pinA7 = pyb.Pin(pyb.Pin.board.PA7, pyb.Pin.OUT_PP)
    
            self.motor = RoboMotorDriver.RoboMotorDriver(pinA6, pinA7, 3, 2)
            
        elif motor_const==3:
            pinA9 = pyb.Pin(pyb.Pin.board.PA9, pyb.Pin.OUT_PP)
            pinB4 = pyb.Pin(pyb.Pin.board.PB4, pyb.Pin.OUT_PP)
    
            self.motor = RoboMotorDriver.RoboMotorDriver(pinA9, pinB4, 3, 1)
        
        self.motor.set_duty_cycle(0)
        
        # Check encoder number and create corresponding RoboEncoderDriver
        if encoder_const==1:
            self.encoder = RoboEncoderDriver.RoboEncoderDriver(pyb.Pin(pyb.Pin.board.PB6), pyb.Pin(pyb.Pin.board.PB7), 4)
            
        elif encoder_const==2:
            self.encoder = RoboEncoderDriver.RoboEncoderDriver(pyb.Pin(pyb.Pin.board.PC6), pyb.Pin(pyb.Pin.board.PC7), 8)
            
        elif encoder_const==3:
            self.encoder = RoboEncoderDriver.RoboEncoderDriver(pyb.Pin(pyb.Pin.board.PA0), pyb.Pin(pyb.Pin.board.PA1), 5)
            
        # Create closed loop controller
        self.controller = ClosedLoop.ClosedLoop(kp, ki, setpoint)
        
        # Create variable to access queue of position values
        self.theta_queue = queue_theta
        
        # Create joint angle value
        self.theta = 0
        
        # Run calibration on creation of each joint
        self.calibrate()
        
        
    def run(self):
        '''!
        @brief      Generator which continuously updates the joint
        @details    Pulls the desired position from a shared queue, and updates
                    the joint motor, encoder, and controller accordingly
        '''
        
        while True:
            #Update angle from shared kinematics
            
            if self.ready.get() == 0:
                self.motor.set_duty_cycle(0)
                print("Motor Off")
                
            else:
                if self.theta_queue.any():
                    newTheta = self.theta_queue.get()
                else:
                    newTheta = self.theta
                if self.theta != newTheta:
                    self.theta = newTheta
                    self.controller.change_setpoint(self.theta)
                
                # Update encoder and change control signal
                self.encoder.update()
                self.motor.set_duty_cycle(self.controller.update(self.encoder.read()))
            yield(0)

    def calibrate(self):
        '''!
        @brief      Calibrates the joint encoder to the correct position
        @details    Waits for the user to manually move the link past the limit
                    switch ramp and sets the encoder value to the correct angle
                    after the link has moved back and forth across the limit
                    switch ramp.
        '''
        
        if self.motor_const == 1:
            limit = pyb.Pin(pyb.Pin.cpu.C4, pyb.Pin.PULL_DOWN)
            theta1 = 4
            theta2 = 6
        elif self.motor_const == 2:
            limit = pyb.Pin(pyb.Pin.cpu.C1, pyb.Pin.PULL_DOWN)
            theta1 = 122
            theta2 = 124
        elif self.motor_const == 3:
            limit = pyb.Pin(pyb.Pin.cpu.A5, pyb.Pin.PULL_DOWN)
            theta1 = 242
            theta2 = 243
        
        print("Calibrating motor " + str(self.motor_const))
        
        count = 0
        press = 0
        clicks = [0, 0]
        
        while True:
            self.encoder.update()
            if press == 1 and limit.value() == 0:
                press = 0
            if press == 0 and limit.value() == 1:
                clicks[count] = self.encoder.read()
                count += 1
                press = 1
                print("Limit found")
                
                if count == 2:
                    if(clicks[0] > clicks[1]):
                        self.encoder.setTheta(theta1)
                    elif (clicks[1] > clicks[0]):
                        self.encoder.setTheta(theta2)
                    else:
                        self.encoder.setTheta((theta1+theta2)/2)
                    print("calibration complete")
                    break
                
        
if __name__ == "__main__":
    pass
    
