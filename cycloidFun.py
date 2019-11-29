#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct  6 16:43:09 2019

@author: chris
"""

import math
import FreeCAD
from FreeCAD import Base
import Part


def QT_TRANSLATE_NOOP(scope, text):
    return text


def toPolar(x, y):
    return (x ** 2.0 + y ** 2.0) ** 0.5, math.atan2(y, x)


def toRect(r, a):
    return r * math.cos(a), r * math.sin(a)


def calcyp(ToothCount, Eccentricity, ToothPitch, a):
    return math.atan(math.sin(ToothCount * a) / (
            math.cos(ToothCount * a) + (ToothCount * ToothPitch) / (Eccentricity * (ToothCount + 1))))


def calcX(ToothCount, Eccentricity, ToothPitch, RollerDiameter: float, a):
    return (ToothCount * ToothPitch) * math.cos(a) + Eccentricity * \
           math.cos((ToothCount + 1) * a) - float(RollerDiameter) / 2.0 * \
           math.cos(calcyp(ToothCount, Eccentricity, ToothPitch, a) + a)


def calcY(ToothCount: int, Eccentricity, ToothPitch, RollerDiameter: float, a):
    return (ToothCount * ToothPitch) * math.sin(a) + Eccentricity * \
           math.sin((ToothCount + 1) * a) - float(RollerDiameter) / 2.0 * \
           math.sin(calcyp(ToothCount, Eccentricity, ToothPitch, a) + a)


def clean1(a):
    """ return -1 < a < 1 """
    return min(1, max(a, -1))


def calcPressureAngle(ToothCount, ToothPitch, RollerDiameter, angle):
    """ calculate the angle of the cycloidalDisk teeth at the angle """
    ex = 2.0 ** 0.5
    r3 = ToothPitch * ToothCount
    #        p * n
    rg = r3 / ex
    pp = rg * (ex ** 2.0 + 1 - 2.0 * ex * math.cos(angle)) ** 0.5 - float(RollerDiameter) / 2.0
    return math.asin(clean1(((r3 * math.cos(angle) - rg) / (pp + float(RollerDiameter) / 2.0)))) * 180 / math.pi


def calcPressureLimit(ToothCount, ToothPitch, Eccentricity, RollerDiameter, a):
    ex = 2.0 ** 0.5
    r3 = ToothPitch * ToothCount
    rg = r3 / ex
    q = (r3 ** 2.0 + rg ** 2.0 - 2.0 * r3 * rg * math.cos(a)) ** 0.5
    x = rg - Eccentricity + (q - float(RollerDiameter) / 2.0) * (r3 * math.cos(a) - rg) / q
    y = (q - float(RollerDiameter) / 2.0) * r3 * math.sin(a) / q
    return (x ** 2.0 + y ** 2.0) ** 0.5


def checkLimit(v: FreeCAD.Vector, PressureAngleOffset, minrad, maxrad):
    """ if x,y outside limit return x,y as at limit, else return x,y
        :type v: FreeCAD.Vector """
    r, a = toPolar(v.x, v.y)
    if (r > maxrad) or (r < minrad):
        r = r - PressureAngleOffset
        v.x, v.y = toRect(r, a)
    return v


def minmaxRadius(H):
    """ Find the pressure angle limit circles """
    ToothCount= H['ToothCount']
    ToothPitch= H['ToothPitch']
    RollerDiameter= H['RollerDiameter']
    Eccentricity= H['Eccentricity']
    PressureAngleLimit= H['PressureAngleLimit']

    minAngle = -1.0
    maxAngle = -1.0
    for i in range(0, 180):
        x = calcPressureAngle(ToothCount, ToothPitch, RollerDiameter, float(i) * math.pi / 180)
        if (x < PressureAngleLimit) and (minAngle < 0):
            minAngle = float(i)
        if (x < -PressureAngleLimit) and (maxAngle < 0):
            maxAngle = float(i - 1)
    minRadius = calcPressureLimit(ToothCount, ToothPitch, Eccentricity, RollerDiameter, minAngle * math.pi / 180)
    maxRadius = calcPressureLimit(ToothCount, ToothPitch, Eccentricity, RollerDiameter, maxAngle * math.pi / 180)
    return minRadius, maxRadius


def generatePinBase(H):
    """ create the base that the fixedRingPins will be attached to """
    ToothCount = H["ToothCount"]
    ToothPitch = H["ToothPitch"]
    RollerDiameter = H["RollerDiameter"]
    RollerHeight = H["RollerHeight"]
    DriverPinDiameter = H["DriverPinDiameter"]
    BaseHeight = H["BaseHeight"]
    DriverDiskHeight = H["DriverDiskHeight"]
    ShaftDiameter = H["ShaftDiameter"]
    minRadius, maxRadius = minmaxRadius(H)
    pinBase = Part.makeCylinder(maxRadius + float(RollerDiameter)*2, BaseHeight) # base of the whole system
    dd = Part.makeCylinder(float(minRadius) * 0.75+ 0.1, DriverDiskHeight*2, Base.Vector(0, 0,BaseHeight-DriverDiskHeight-1)) #hole for the driver disk to fit in
    pinBase = pinBase.cut(dd)
    # generate the pin locations
    for i in range(0, ToothCount + 1):
        x = ToothPitch * ToothCount * ( math.cos(2.0 * math.pi / (ToothCount + 1) * i))
        y = ToothPitch * ToothCount * ( math.sin(2.0 * math.pi / (ToothCount + 1) * i))
        if (x>0):
            x += RollerDiameter/2
        else:
            x -= RollerDiameter/2
        if (y>0):
            y+= RollerDiameter/2
        else:
            y-= RollerDiameter/2
        negfixedRingPin = Part.makeCylinder(float(RollerDiameter)/2.0 +0.5 , RollerHeight, Base.Vector(x, y, 0))
        fixedRingPin = Part.makeCylinder(float(RollerDiameter) , RollerHeight, Base.Vector(x, y, BaseHeight))
        fixedRingPinpin = Part.makeCylinder(float(RollerDiameter)/2.0 , BaseHeight / 2.0 +RollerHeight, Base.Vector(x, y, BaseHeight))
        pinBase = pinBase.cut(negfixedRingPin) #make a hole if multple gearboxes are in line
        pinBase = pinBase.fuse(fixedRingPinpin) # make the pins the cycloid gear uses, and the part that goes into the above hole
        pinBase = pinBase.fuse(fixedRingPin) # make the pins the cycloid gear uses
    # need hole for eccentric shaft, add a bit so not too tight
    # todo  allow user values for sizes
    # todo allow bearing option
    shaft = Part.makeCylinder(float(ShaftDiameter)/ 2.0,BaseHeight*2,Base.Vector(0,0,-BaseHeight))
    return pinBase.cut(shaft)


def generateEccentricShaft(H):
    RollerDiameter = H["RollerDiameter"]
    RollerHeight = H["RollerHeight"]
    Eccentricity = H["Eccentricity"]
    DriverPinDiameter = H["DriverPinDiameter"]
    BaseHeight = H["BaseHeight"]
    ShaftDiameter = H["ShaftDiameter"]
    DriverDiskHeight = H["DriverDiskHeight"]
    CycloidalDiskHeight =  H["CycloidalDiskHeight"]
    # add a circle in the center of the cam
    #print("shaft",RollerDiameter,Eccentricity)
    e = Part.makeCylinder(float(RollerDiameter) / 2.0, BaseHeight+CycloidalDiskHeight, Base.Vector(-Eccentricity, 0, 0))
    d = Part.makeCylinder(float(ShaftDiameter)/ 2.0,BaseHeight*2,Base.Vector(0,0,-BaseHeight)) # one base out sticking out the bottom, one base height through the base
    d = d.fuse(e)

    minRadius, maxRadius = minmaxRadius(H)
    #cyl = Part.makeCylinder(float(minRadius)*0.75,RollerHeight)
    #cyl = cyl.fuse(generatePinBase(H).translate(Base.Vector(0,0,-BaseHeight)))
    #d = d.fuse(cyl)
    return d


"""
def points(self, num=10):
    pts = involute_points(num=num)
    rot = rotation3D(-math.pi / z / 2.0)
    pts = rot(pts)
    ref = reflection3D(math.pi / 2.0)
    pts1 = ref(pts)[::-1]
    rot = rotation3D(2.0 * math.pi / z)
    if add_foot:
        return (array([
            array([pts[0], pts[1]]),
            pts[1:],
            array([pts[-1], pts1[0]]),
            pts1[:-1],
            array([pts1[-2.0], pts1[-1]])
        ]))
    else:
        return (array([pts, array([pts[-1], pts1[0]]), pts1]))
"""


def generateCycloidalDiskArray(H):
    ToothCount = H["ToothCount"]
    ToothPitch = H["ToothPitch"]
    RollerDiameter = H["RollerDiameter"]
    Eccentricity = H["Eccentricity"]
    LineSegmentCount = H["LineSegmentCount"]
    PressureAngleOffset = H["PressureAngleOffset"]
    """ make the array to be used in the bspline
        that is the cycloidalDisk
    """
    minRadius, maxRadius = minmaxRadius(H)
    q = 2.0 * math.pi / float(LineSegmentCount)
    i = 0

    v1 = Base.Vector(calcX(ToothCount, Eccentricity, ToothPitch, RollerDiameter, q * i),
                     calcY(ToothCount, Eccentricity, ToothPitch, RollerDiameter, q * i), 0)
    v1 = checkLimit(v1, PressureAngleOffset, minRadius, maxRadius)

    cycloidalDiskArray = []
    cycloidalDiskArray.append(v1)
    for i in range(0, LineSegmentCount):
        v2 = Base.Vector(
            calcX(ToothCount, Eccentricity, ToothPitch, RollerDiameter, q * (i + 1)),
            calcY(ToothCount, Eccentricity, ToothPitch, RollerDiameter, q * (i + 1)),
            0)
        v2 = checkLimit(v2, PressureAngleOffset, minRadius, maxRadius)
        cycloidalDiskArray.append(v2)
    return cycloidalDiskArray


def generateCycloidalDisk(H):
    """
    make the complete cycloidal disk
    """
    RollerDiameter = H["RollerDiameter"]
    Eccentricity = H["Eccentricity"]
    BaseHeight = H["BaseHeight"]
    CycloidalDiskHeight = H["CycloidalDiskHeight"]
    DiskHoleCount = H["DiskHoleCount"]

    minRadius, maxRadius = minmaxRadius(H)
    #get shape of cycloidal disk
    a = Part.BSplineCurve(generateCycloidalDiskArray(H)).toShape()
    w = Part.Wire([a])
    f = Part.Face(w)
    # need to cut out the eccentric shaft hole, add a bit so it isn't too tight,
    # todo add option for bearing here
    es = Part.makeCircle(float(RollerDiameter) /2.0+0.5,Base.Vector(0,0,0))
    esw = Part.Wire([es])
    esf = Part.Face(esw)
    fc = f.cut(esf)
    for i in range(0, DiskHoleCount ):
        x = minRadius/2 * math.cos(2.0 * math.pi / (DiskHoleCount) * i)
        y = minRadius/2 * math.sin(2.0 * math.pi / (DiskHoleCount) * i)
        drivinghole= Part.makeCircle(RollerDiameter*2,Base.Vector(x,y,0))
        esw = Part.Wire([drivinghole])
        esf = Part.Face(esw)
        fc = fc.cut(esf)

    #fc = f.fuse(esw)
    e = fc.extrude(FreeCAD.Vector(0, 0, CycloidalDiskHeight))
    e.translate(Base.Vector(-Eccentricity, 0, BaseHeight + 0.1))
    return e

def generateDriverDisk(H):
    minRadius,maxRadius = minmaxRadius(H)
    DiskHoleCount = H["DiskHoleCount"]
    DriverDiskHeight = H["DriverDiskHeight"]
    RollerDiameter = H["RollerDiameter"]
    RollerHeight = H["RollerHeight"]
    Eccentricity = H["Eccentricity"]
    ShaftDiameter = H["ShaftDiameter"]
    BaseHeight = H["BaseHeight"]
    CycloidalDiskHeight =  H["CycloidalDiskHeight"]
    dd = Part.makeCylinder(float(minRadius) * 0.75, DriverDiskHeight, Base.Vector(0, 0,0)) # the main driver disk
    for i in range(0, DiskHoleCount):
        x = minRadius / 2 * math.cos(2.0 * math.pi / (DiskHoleCount) * i)
        y = minRadius / 2 * math.sin(2.0 * math.pi / (DiskHoleCount) * i)
        fixedRingPin = Part.makeCylinder(float(RollerDiameter*2 - Eccentricity) , CycloidalDiskHeight, Base.Vector(x, y, CycloidalDiskHeight)) #driver pins
        dd = dd.fuse(fixedRingPin)

    fp = dd.translate(Base.Vector(0,0,BaseHeight - DriverDiskHeight))
    # need to make hole for eccentric shaft, add a bit so not to tight
    #todo  allow user values for sizes
    #todo allow bearing option
    shaft = Part.makeCylinder(float(ShaftDiameter)/ 2.0,BaseHeight*2,Base.Vector(0,0,-BaseHeight))
    fp = fp.cut(shaft)
    return fp

def generateDefaultHyperParam():
    hyperparameters = {
        "Eccentricity": 4.7 / 2,
        "ToothCount": 12,
        "DiskHoleCount":6,
        "LineSegmentCount": 400,
        "ToothPitch": 4,
        "RollerDiameter": 4.7,
        "RollerHeight": 5.0,
        "CenterDiameter": 5.0,
        "PressureAngleLimit": 50.0,
        "PressureAngleOffset": 0.0,
        "BaseHeight":10.0,
        "DriverPinDiameter":12,
        "DriverPinHeight":10.0,
        "DriverDiskHeight":4.0,
        "CycloidalDiskHeight":4,
        "ShaftDiameter":13.0
        }
    return hyperparameters

def testgenerateEccentricShaft():
    return generateEccentricShaft(generateDefaultHyperParam())

def testgeneratePinBase():
    return generatePinBase(generateDefaultHyperParam())

def testgenerateDriverDisk():
    return generateDriverDisk(generateDefaultHyperParam())

def testgenerateCycloidalDisk():
    return generateCycloidalDisk(generateDefaultHyperParam())
