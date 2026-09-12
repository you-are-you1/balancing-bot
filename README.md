# balancing-bot
This is a Lego Robot Inventor/Spike Prime self-balancing robot which is remote controllable.

## PID controller
The robot uses a cascading PID controller to ensure it stays balanced. The inner layer uses the gyro sensor of the Inventor Hub to get the current angle and angular velocity and controls the motor power. 
The outer layer uses the motor position to control the tilt bias which encourages the robot to travel in a certain direction.

## Bluetooth remote control
The remote control uses Tkinter to create a GUI to connect to the robot and send it data. It uses the Bleak library to send commands using the Nordic UART Service which is supported by Pybricks.
The Inventor Hub then reads the commands via stdin (from usys module).
