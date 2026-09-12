from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Button, Color, Direction, Port, Side, Stop, Axis
from pybricks.robotics import DriveBase
from pybricks.tools import wait, StopWatch

hub = InventorHub(top_side=-Axis.X, front_side=Axis.Z)
leftMotor = Motor(Port.A)
rightMotor = Motor(Port.B)

watch = StopWatch()

hub.speaker.volume(30)

#PID constants for motor speed
kp = 19
ki = 0.2
kd = 8

i = 0
i_pos = 0

kp_pos = 0.05
kd_pos = 0.001

targetAngle = 1.75
targetPos = 0
targetAngleBiasLimit = 0.7

leftMotor.reset_angle(0)

lastTime = watch.time()
lastPos = 0

def runMotors(leftSpeed, rightSpeed):

    # avoid motor deadzone
    # if (speed > 0 and speed < 10):
    #     speed = 10
    # elif (speed < 0 and speed > -10):
    #     speed = -10

    leftMotor.dc(-leftSpeed)
    rightMotor.dc(rightSpeed)

while True:
    currentTime = watch.time()
    dt = currentTime - lastTime
    lastTime = currentTime

    currentPos = leftMotor.angle()
    posError = currentPos - targetPos
    
    # determine tilt offset with PD control which encourages 
    # robot toward target position
    p_pos = kp_pos * posError
    if (dt == 0):
        d_pos = 0
    else:
        d_pos = -kd_pos * ((currentPos - lastPos) / dt)
    lastPos = currentPos

    targetAngleBias = p_pos + d_pos
    if (targetAngleBias > targetAngleBiasLimit):
        targetAngleBias = targetAngleBiasLimit
    elif (targetAngleBias < -targetAngleBiasLimit):
        targetAngleBias = -targetAngleBiasLimit
 
    currentAngle = hub.imu.tilt()[0]
    angleError = currentAngle - targetAngle - targetAngleBias

    # stop program if robot falls
    if (abs(currentAngle) > 30):
        break

    # determine motor speed with PID control
    p = kp * angleError
    i = i + (ki * angleError * dt)
    d = kd * hub.imu.angular_velocity(-Axis.X)
    # angular velocity more accurate than using difference between last angle and current angle

    motorPower = p + i + d
    runMotors(motorPower, motorPower)










