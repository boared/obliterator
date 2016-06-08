#!/usr/bin/python
#
#   Copyright 2016 Eder Perez https://github.com/eaperz
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# 
# OBLITERATOR
#
#    A face tracking foam missile launcher!
#
#    Usage: obliterator.py [camera_id] [mode]
#
#       camera_id:
#           An integer representing which webcam is installed on Turret
#
#       mode:
#           track - Only point to a target, don't shoot (default)
#           attack - Point and shoot to a target
#
#    Press 'q' to quit the program
#
#    Requirements:
#        * A Dream Cheeky Thunder USB Missile Launcher
#        * A webcam mounted on top of the missile launcher
#        * Python 2.7+
#        * Python PyUSB Support and its dependencies
#        * Tested on Windows but should work on Mac and Linux also
#
# This software uses code based on Retaliation implementation of Cheeky
# Thunder USB device controlling (https://github.com/codedance/Retaliation).
#
# Author: Eder Perez <https://github.com/eaperz>
#

import platform
import time
import sys
import usb.core
import usb.util
import cv2

CAMERAID = None
MODE = None
TURRET = None
TURRET_TYPE = None

RADIUS = 3
CENTER_COLOR = (255, 0, 0)
RECTANGLE_COLOR = (0, 255, 0)
TARGET_COLOR = (0, 0, 255)

# Protocol command bytes
DOWN    = 0x01
UP      = 0x02
LEFT    = 0x04
RIGHT   = 0x08
FIRE    = 0x10
STOP    = 0x20

def usage():
    print "Usage: obliterator.py [camera_id] [mode]"
    print ""
    print "   camera_id:"
    print "     An integer representing which webcam is installed on Turret"
    print ""
    print "   mode:"
    print "     track - Only point to a target, don't shoot (default)"
    print "     attack - Point and shoot to a target"
    print ""
    print "Press 'q' to quit the program"

def checkParameters(arglist):
    global CAMERAID
    global MODE
    
    # Only camera ID passed as argument (default mode = track)
    if len(arglist) == 2:
        try:
            CAMERAID = int(arglist[1])
            MODE = "track"
        except ValueError:
            usage()
            exit()
    # Both camera ID and mode passed as argument
    elif len(arglist) == 3:
        try:
            CAMERAID = int(arglist[1])
            MODE = arglist[2]
        except ValueError:
            usage()
            exit()
    # Argument list failed
    else:
        usage()
        exit()


def setupTurret():
    global TURRET
    global TURRET_TYPE

    TURRET = usb.core.find(idVendor=0x2123, idProduct=0x1010)
    TURRET_TYPE = "Thunder"

    if TURRET is None:
        TURRET = usb.core.find(idVendor=0x0a81, idProduct=0x0701)
        if TURRET is None:
            raise ValueError('Device not found')
        else:
            TURRET_TYPE = "Original"

    # On Linux we need to detach usb HID first
    if "Linux" == platform.system():
        try:
            TURRET.detach_kernel_driver(0)
        except Exception:
            pass  # Already unregistered

    TURRET.set_configuration()


def sendCmd(cmd):
    if "Thunder" == TURRET_TYPE:
        TURRET.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, cmd, 0x00,0x00,0x00,0x00,0x00,0x00])
    elif "Original" == TURRET_TYPE:
        TURRET.ctrl_transfer(0x21, 0x09, 0x0200, 0, [cmd])


def sendMove(cmd, duration_ms):
    sendCmd(cmd)
    time.sleep(duration_ms / 1000.0)
    sendCmd(STOP)


def led(cmd):
    if "Thunder" == TURRET_TYPE:
        TURRET.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, cmd, 0x00,0x00,0x00,0x00,0x00,0x00])
    elif "Original" == TURRET_TYPE:
        print("There is no LED on this device")


# Returns only the biggest rectangle among all detected faces
def getBiggerFace(faces):
    biggerFace = None
    biggerSLength = 0
    for (x, y, w, h) in faces:
        slength = ((x + x+w)/2)**2 + ((y + y+h)/2)**2
        if ( slength > biggerSLength ):
            biggerFace = (x, y, w, h)
            biggerSLength = slength
    return biggerFace


def main(arglist):
    checkParameters(arglist)
    
    capture = cv2.VideoCapture(CAMERAID)
    
    if (not capture.isOpened()):
        print "Failed to setup camera."
        exit()

    # Get the screen center
    center = (int(capture.get(3) / 2), int(capture.get(4) / 2))
    
    faceCascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')

    setupTurret()

    while(True):
        ret, frame = capture.read()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = faceCascade.detectMultiScale(gray, 
                                             scaleFactor=1.1,
                                             minNeighbors=5,
                                             minSize=(30, 30),
                                             flags=cv2.CASCADE_SCALE_IMAGE)

        biggerFace = getBiggerFace(faces)
        hasFace = biggerFace is not None

        target = (0, 0)

        # Draw a rectangle around detected face
        if hasFace:
            target = ((biggerFace[0] + biggerFace[0] + biggerFace[2])/2, 
                      (biggerFace[1] + biggerFace[1] + biggerFace[3])/2)
            cv2.rectangle(frame, 
                          (biggerFace[0], biggerFace[1]), 
                          (biggerFace[0]+biggerFace[2], biggerFace[1]+biggerFace[3]), 
                          RECTANGLE_COLOR, 2)
            cv2.circle(frame, target, RADIUS, TARGET_COLOR, -1)
            led(1)
        else:
            led(0)

        cv2.circle(frame, center, RADIUS, CENTER_COLOR, -1)
        cv2.imshow('Obliterator', frame)

        x = center[0] - target[0]
        y = center[1] - target[1]
        cmdX = STOP
        cmdY = STOP
        if x < 0:
            cmdX = RIGHT
        else:
            cmdX = LEFT
        if y < 0:
            cmdY = DOWN
        else:
            cmdY = UP

        if hasFace:
            dist = biggerFace[2]/2 # Half rectangle width
            if x*x + y*y > dist:
                sendMove(cmdX, 10)
                sendMove(cmdY, 10)
            elif MODE == 'attack':
                sendCmd(FIRE)
                time.sleep(0.05)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    led(0)
    capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main(sys.argv)
