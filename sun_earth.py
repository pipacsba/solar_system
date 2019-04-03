#!/usr/bin/python
''' sun earth movement emulation by gravity

'''

import pygame
import sys
import time
import tempfile
import math
from math import pi, sin, cos, sqrt, asin, pow
from pygame.locals import *

m_earth = 5.972e24  # unit: kg 5.972e24
m_moon = 7.34767309e22  # unit: kg
m_sun = 1.989e30 # unit: kg 1.989e30
G = 6.67e-11  # unit: N*m^2/kg^2

#sun position and speed start-up conditions
sun_position_x = 0  # unit: m
sun_position_y = 0  # unit: m
sun_speed_x = 0     # unit: m
sun_speed_y = 0     # unit: m

#earth position/speed start-up conditions
earth_position_x = 147.095e9  # unit: m (distance of the perihelion) 147.095e9
earth_position_y = 0          # unit: m
earth_speed_y = 30300         # unit: m/s 30300
earth_speed_x = 0             # unit: m/s

year = 3.154e7  # unit: s
t = 0  # unit: s
dt = 3600  # unit: s

# plot setup
width = 768  # Window size
d = 1  # resolution
black = (0, 0, 0)  # Fore- and background colors
white = (255, 255, 255)
screen = pygame.display.set_mode((width, width))  # You can add FULLSCREEN as last parameter
screen.fill(black)
scale = width / (earth_position_x * 2.4)

min_dist = 1e12
max_dist = 0
while t < year:
    # calculate earth sun distance
    earth_sun_distance = sqrt(math.pow(sun_position_x - earth_position_x, 2) + math.pow(sun_position_y - earth_position_y, 2))
    # calculate the actual size of the gravity force
    grav_force_es = G * m_sun * m_earth / pow(earth_sun_distance, 2)
    # calculate the size of the acceleration caused by the grav force
    earth_acc = grav_force_es / m_earth
    sun_acc   = -grav_force_es / m_sun
    # calculate current angle of the gravity force/acceleration
    earth_sun_distance_deg = asin((sun_position_y - earth_position_y) / earth_sun_distance)
    # to be honest I do not see right now why it is only required for "x"
    if sun_position_x - earth_position_x > 0:
        x_dir = -1
    else:
        x_dir = 1
    # calculate the acceleration for the x and y axes
    earth_acc_x=earth_acc * cos(earth_sun_distance_deg) * x_dir
    earth_acc_y=earth_acc * sin(earth_sun_distance_deg)
    sun_acc_x = sun_acc * cos(earth_sun_distance_deg) * x_dir
    sun_acc_y = sun_acc * sin(earth_sun_distance_deg)
    # calculate the speed altered by the acceleration in dt time
    earth_speed_x = earth_speed_x - (earth_acc_x * dt)
    earth_speed_y = earth_speed_y + (earth_acc_y * dt)
    sun_speed_x = sun_speed_x - (sun_acc_x * dt)
    sun_speed_y = sun_speed_y + (sun_acc_y * dt)

    # needed for drawing
    prev_ex = earth_position_x * scale + width / 2
    prev_ey = -earth_position_y * scale + width / 2
    prev_sx = sun_position_x * scale + width / 2
    prev_sy = -sun_position_y * scale + width / 2

    # calculate the distance earth have been taken during dt with the calculated speed
    earth_position_x = earth_position_x + earth_speed_x * dt
    earth_position_y = earth_position_y + earth_speed_y * dt
    sun_position_x = sun_position_x + sun_speed_x * dt
    sun_position_y = sun_position_y + sun_speed_y * dt
    # needed for drawing
    ex = earth_position_x * scale + width / 2
    ey = -earth_position_y * scale + width / 2
    sx = sun_position_x * scale + width / 2
    sy = -sun_position_y * scale + width / 2
    # drawing
    pygame.draw.aaline(screen, white, (ex, ey), (prev_ex, prev_ey), 2)
    pygame.draw.aaline(screen, white, (sx, sy), (prev_sx, prev_sy), 2)
    pygame.display.update()
    # increase time
    t = t + dt
    # collect min!max earth sun distance
    if earth_sun_distance > max_dist:
        max_dist = earth_sun_distance
    if min_dist > earth_sun_distance:
        min_dist = earth_sun_distance

print('Minimal distance is:', min_dist)
print('Maximal distance is:', max_dist)