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


def minmaxRadius(ToothCount, ToothPitch, RollerDiameter, Eccentricity, PressureAngleLimit):
    """ Find the pressure angle limit circles """
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


def generatePinBase(ToothCount, ToothPitch, RollerDiameter, Eccentricity, RollerHeight, DriverPinDiameter, baseHeight,
                    PressureAngleLimit):
    """ create the base that the fixedRingPins will be attached to """
    min_radius, max_radius = minmaxRadius(ToothCount, ToothPitch, RollerDiameter, Eccentricity, PressureAngleLimit)
    pinBase = Part.makeCylinder(max_radius + float(RollerDiameter), baseHeight)
    # generate the pin locations
    for i in range(0, ToothCount + 1):
        x = ToothPitch * ToothCount * math.cos(2.0 * math.pi / (ToothCount + 1) * i)
        y = ToothPitch * ToothCount * math.sin(2.0 * math.pi / (ToothCount + 1) * i)
        fixedRingPin = Part.makeCylinder(float(RollerDiameter) / 2.0, RollerHeight, Base.Vector(x, y, 0))
        pinBase = pinBase.fuse(fixedRingPin)
    accesshole = Part.makeCylinder(DriverPinDiameter / 2.0, 10000)
    pinBase.cut(accesshole)
    return pinBase


def generateEccentricShaft(RollerDiameter, RollerHeight, Eccentricity):
    # add a circle in the center of the cam
    print("shaft",RollerDiameter,Eccentricity)
    return Part.makeCylinder(float(RollerDiameter) / 2.0, RollerHeight, Base.Vector(-Eccentricity, 0, 0))


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


def generateCycloidalDiskArray(ToothCount, ToothPitch, RollerDiameter, Eccentricity, LineSegmentCount,
                               PressureAngleLimit, PressureAngleOffset):
    """ make the array to be used in the bspline
        that is the cycloidalDisk
    """
    minRadius, maxRadius = minmaxRadius(ToothCount, ToothPitch, RollerDiameter, Eccentricity, PressureAngleLimit)
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


def generateCycloidalDisk(ToothCount, ToothPitch, RollerDiameter, Eccentricity, LineSegmentCount, PressureAngleLimit,
                          PressureAngleOffset, baseHeight, CycloidalDiskHeight,DiskHoleCount):
    """
    make the complete cycloidal disk
    """
    minRadius, maxRadius = minmaxRadius(ToothCount, ToothPitch, RollerDiameter, Eccentricity, PressureAngleLimit)
    a = Part.BSplineCurve(
        generateCycloidalDiskArray(ToothCount, ToothPitch, RollerDiameter, Eccentricity, LineSegmentCount,
                                   PressureAngleLimit, PressureAngleOffset)).toShape()
    w = Part.Wire([a])
    f = Part.Face(w)
    # need to cut out the eccentric shaft hole
    # Part.makeCylinder(float(RollerDiameter) / 2.0, RollerHeight, Base.Vector(-Eccentricity, 0, 0))
    print("disk",RollerDiameter,Eccentricity)
    es = Part.makeCircle(float(RollerDiameter) /2.0,Base.Vector(0,0,0))
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
    e.translate(Base.Vector(-Eccentricity, 0, baseHeight + 0.1))
    return e

def testgenerateCycloidalDisk(ToothCount=12, ToothPitch=4, RollerDiameter=4.7, Eccentricity=2.35,
                              LineSegmentCount=400, PressureAngleLimit=50,
                          PressureAngleOffset=0, baseHeight=10, CycloidalDiskHeight=4,DiskHoleCount=6):
    espoints = [];
    espoints.append(Base.Vector(RollerDiameter / 2 - Eccentricity, 0, 0))
    espoints.append(Base.Vector(0, -RollerDiameter / 2, 0))
    espoints.append(Base.Vector(RollerDiameter / 2 + Eccentricity, 0, 0))
    espoints.append(Base.Vector(0, RollerDiameter / 2, 0))
    espoints.append(Base.Vector(RollerDiameter / 2 - Eccentricity, 0, 0))

    es = Part.BSplineCurve(espoints).toShape()
    esw = Part.Wire([es])
    # fc = f.cut(esw)
    espoints = [];
    espoints.append(Base.Vector(RollerDiameter / 2 - Eccentricity, 0, 0))
    espoints.append(Base.Vector(0, -RollerDiameter / 2, 0))
    espoints.append(Base.Vector(RollerDiameter / 2 + Eccentricity, 0, 0))
    espoints.append(Base.Vector(0, RollerDiameter / 2, 0))
    espoints.append(Base.Vector(RollerDiameter / 2 - Eccentricity, 0, 0))

    es = Part.BSplineCurve(espoints).toShape()
    esw = Part.Wire([es])
    esf = Part.Face(esw)
    e = esf.extrude(FreeCAD.Vector(0, 0, CycloidalDiskHeight))
    e.translate(Base.Vector(-Eccentricity, 0, baseHeight + 0.1))
    #return e
    return generateCycloidalDisk(ToothCount, ToothPitch, RollerDiameter, Eccentricity, LineSegmentCount, PressureAngleLimit,
                          PressureAngleOffset, baseHeight, CycloidalDiskHeight,DiskHoleCount)
