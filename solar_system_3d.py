#!/usr/bin/python
""" solar system emulation
    period_number: end of the simulation by simulation time is defined for slowest simulated object's period
    iteration_per_rotation: how many calculation is performed for the slowest object
    screen_update_period: which defines that the screen is only updated after this amount of iterations
    fix_center: defines if the center object should move (1: no move, 0: not fixed)
    simulation_target defined defines which objects shall be used for the simulation
"""

import math
import subprocess
from collections import defaultdict
import pygame

# TODO: https://en.wikipedia.org/wiki/Apsidal_precession#General_relativity

# key parameters
# list name of objects part of the current simulation
# ['sun', 'mercury', 'venus', 'earth', 'moon', 'mars', 'phobos', 'deimos', 'jupiter', 'saturn',
# 'epimetheus', 'janus' 'uranus', 'neptune'] _ast
simulation_target = ['sun', 'earth', 'mars', 'earth_ast']
period_number = 240  # number of periods to be simulated (for the largest period time object)
iteration_per_rotation = 1080  # how many iteration shall be done for one period of fastest simulated period time object
screen_update_period = 100  # after how many iterations shall the screen be updated
fix_center = 1  # 1: the center object is the center of the screen coordinate system 0: the center object is also moves
center_overwrite = 1  # set to 1 if the screen center object shall be overwritten
new_center_object = 'mars'  # define new screen center object name
turning_coordinate = 1  # set to 1 if the coordinate system shall keep an axis on an object set to 0 to disable
turn_dir = 'earth'  # name of the objject shall be used as x axis


# Return CPU temperature and time spent to wait to cool down below 60°C (only works on raspberry PI)
def wait_for_cpu_temperature():
    try:
        std_result1 = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
        res = std_result1.communicate()[0].decode()
        temp1 = (float(res.replace('temp=', '').replace("'C\n", '')))
        std_result2 = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'],
                                       stdout=subprocess.PIPE)
        res = std_result2.communicate()[0].decode()
        temp2 = float(res) / 1000
    except OSError:
        return {'wait': 100, 'temp': 0}
    else:
        await = 500
        sum_wait = 0
        max_temperature = max(temp1, temp2)
        while max_temperature > 60:
            pygame.time.wait(await)
            sum_wait += await
            std_result1 = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
            res = std_result1.communicate()[0].decode()
            temp1 = (float(res.replace('temp=', '').replace("'C\n", '')))
            std_result2 = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'],
                                           stdout=subprocess.PIPE)
            res = std_result2.communicate()[0].decode()
            temp2 = float(res) / 1000
            max_temperature = max(temp1, temp2)
        return {'wait': sum_wait, 'temp': max_temperature}

pygame.init()


# class to store solar objects to draw
class Circle(pygame.sprite.Sprite):
    def __init__(self, color, size):
        # create a sprite for each object
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((size * 2, size * 2))
        self.image.fill((128, 128, 128))
        pygame.draw.circle(self.image, color, (int(math.floor(size)), int(math.floor(size))), int(size), 0)
        self.rect = self.image.get_rect()
        # make background transparent
        self.image.set_colorkey((128, 128, 128))

    # update position
    def set_new_position(self, scr_x, scr_y):
        self.rect.center = (scr_x, scr_y)


# define Solar objects
class SolarObject(object):
    # list to store object names
    name_index = defaultdict(list)
    # screen reality scale (re-calculated for the used objects run-time)
    scale = 1
    # maximum period time of objects (re-calculated for the used objects run-time)
    max_period = 1
    # minimum iteration time of objects (re-calculated for the used objects run-time)
    min_iteration_time = 86440e10
    # define which object is in the centre of the screen (re-calculated for the used objects run-time
    #   - based on last object without active 'parent')
    object_in_centre = 'sun'

    def __init__(self, name, parent, mass, max_speed, inclination_deg, color,
                 perihelion, aphelion, radius, obj_type, period, semi_major_axis):
        self.name = name  # name of the object
        self.parent = parent  # name of the object around this object's orbit is
        self.mass = mass  # unit: kg
        self.inclination_deg = inclination_deg
        self.inclination = math.radians(inclination_deg)  # unit rad
        self.color = color  # color used for drawing the object/orbit
        self.perihelion = perihelion  # unit: m
        self.aphelion = aphelion  # unit: m
        self.radius = radius  # unit: m
        self.object_type = obj_type  # star/planet/moon
        self.period = period  # unit: s
        self.semi_major_axis = semi_major_axis  # unit: m
        # all abjects are placed for it's perihelion, with it's maximum speed as orthogonal
        # all perihelion is at the x axis, in the centre of the screen
        self.x_position = self.perihelion * math.cos(self.inclination)
        self.y_position = 0
        self.z_position = self.perihelion * math.sin(self.inclination)
        self.x_acceleration = 0  # unit: m/s2
        self.y_acceleration = 0  # unit: m/s2
        self.z_acceleration = 0  # unit: m/s2
        self.max_speed = max_speed
        self.x_speed = 0  # unit: m/s
        self.y_speed = max_speed  # unit: m/s
        self.z_speed = 0  # unit: m/s
        # define next position as current position
        self.x_position_new = self.x_position  # unit: m
        self.y_position_new = self.y_position  # unit: m
        self.z_position_new = self.z_position  # unit: m
        # check if parent is existing
        parent_object_list = SolarObject.find_by_name(self.parent)
        if 0 < len(parent_object_list) and self.parent in simulation_target and self.name in simulation_target:
            parent_object = parent_object_list[0]
            self.x_position += parent_object.x_position
            self.y_position += parent_object.y_position
            self.z_position += parent_object.z_position
            self.x_speed += parent_object.x_speed
            self.y_speed += parent_object.y_speed
            self.z_speed += parent_object.z_speed
        elif self.name in simulation_target:
            # if no parent, than define this object as center object
            SolarObject.object_in_centre = self.name
        self.dist_min = 2 * abs(self.perihelion)  # variable to collect simulated perihelion results
        self.dist_max = 0  # variable to collect simulated aphelion results
        # define object drawing
        if self.object_type == 'star':
            self.circle = Circle(self.color, width / 400)
        elif self.object_type == 'planet':
            self.circle = Circle(self.color, width / 60)
        else:
            self.circle = Circle(self.color, width / 150)
        # add this to all object list
        all_objects.append(self)
        # add name to name_index (to be able to make quick search by name)
        SolarObject.name_index[self.name].append(self)
        # create empty list, used to avoid double calculation to save processor time
        self.others_acceleration_done = []

    # define method to make quick search by name
    @classmethod
    def find_by_name(cls, a_name):
        return SolarObject.name_index[a_name]

# Gravitational constant
G = 6.67408e-11  # unit: N*m^2/kg^2

# simulation time
t = 0  # unit: s

# some color definition
black = (0, 0, 0)  # Fore- and background colors
white = (255, 255, 255)
red = (255, 0, 0)
blue = (0, 0, 255)
green = (0, 255, 0)
yellow = (255, 255, 0)
purple = (255, 0, 255)
# plot setup
width = 800  # Window size
# create display
screen = pygame.display.set_mode((width, width), pygame.HWACCEL)
# create an other surface, so the the orbits can separately updated / drawn to the stars/planets/moons
background = pygame.Surface(screen.get_size())
# set background color
background.fill(black)
# at first copy the complete background to the display
screen.blit(background, (0, 0))
# create a sprites group so later these can be added to the display, and moved together
allSprites = pygame.sprite.Group()

all_objects = []
solar_system = []
# SolarObject(self, name, parent, mass, max_speed, inclination_deg, color,
#             perihelion, aphelion, radius, obj_type, period)
sun = SolarObject('sun',  # name
                  'none',  # parent
                  1.989e30,  # mass
                  0,  # max_speed
                  0,  # inclination [deg]
                  yellow,  # color
                  0,  # perihelion
                  0,  # aphelion
                  695700e3,  # radius
                  'star',  # object_type
                  1,  # period
                  0  # semi_major_axis
                  )
earth = SolarObject('earth',  # name
                    'sun',  # parent
                    5.972e24,  # mass
                    30290,  # max_speed
                    0,  # inclination [deg]
                    blue,  # color
                    147.09e9,  # perihelion
                    152.10e9,  # aphelion
                    6378.137e3,  # radius
                    'planet',  # object_type
                    365.256 * 86400,  # period
                    149.60e9  # semi_major_axis
                    )
moon = SolarObject('moon',  # name
                   'earth',  # parent
                   7.34767309e22,  # mass
                   1082,  # max_speed
                   5.145,  # inclination [deg]
                   white,  # color
                   0.3633e9,  # perihelion
                   0.4055e9,  # aphelion
                   1738.1e3,  # radius
                   'moon',  # object_type
                   27.3217 * 86400,  # period
                   0.3844e9  # semi_major_axis
                   )
mercury = SolarObject('mercury',  # name
                      'sun',  # parent
                      3.3011e23,  # mass
                      58.98e3,  # max_speed
                      7,  # inclination [deg]
                      white,  # color
                      46.00e9,  # perihelion
                      69.82e9,  # aphelion
                      2439.7e3,  # radius
                      'planet',  # object_type
                      87.969 * 86400,  # period
                      0.3844e9  # semi_major_axis
                      )
venus = SolarObject('venus',  # name
                    'sun',  # parent
                    4.8675e24,  # mass
                    35.26e3,  # max_speed
                    3.39,  # inclination [deg]
                    green,  # color
                    107.48e9,  # perihelion
                    108.94e9,  # aphelion
                    6051.8e3,  # radius
                    'planet',  # object_type
                    224.701 * 86400,  # period
                    108.21e9  # semi_major_axis
                    )
mars = SolarObject('mars',  # name
                   'sun',  # parent
                   0.64171e24,  # mass
                   26.50e3,  # max_speed
                   1.85,  # inclination [deg]
                   red,  # color
                   206.62e9,  # perihelion
                   249.23e9,  # aphelion
                   3396.2e3,  # radius
                   'planet',  # object_type
                   686.980 * 86400,  # period
                   227.92e9  # semi_major_axis
                   )
phobos = SolarObject('phobos',  # name
                     'mars',  # parent
                     10.6e15,  # mass
                     2.138e3,  # max_speed
                     1.08,  # inclination [deg]
                     white,  # color
                     9234.42e3,  # perihelion
                     9517.58e3,  # aphelion
                     13.0e3,  # radius
                     'moon',  # object_type
                     0.31891 * 86400,  # period
                     9378e3  # semi_major_axis
                     )
deimos = SolarObject('deimos',  # name
                     'mars',  # parent
                     2.4e15,  # mass
                     1.3513e3,  # max_speed
                     1.79,  # inclination [deg]
                     blue,  # color
                     23455.5e3,  # perihelion
                     23470.9e3,  # aphelion
                     7.8e3,  # radius
                     'moon',  # object_type
                     1.26244 * 86400,  # period
                     23459e3  # semi_major_axis
                     )
jupiter = SolarObject('jupiter',  # name
                      'sun',  # parent
                      1898.19e24,  # mass
                      13.72e3,  # max_speed
                      1.304,  # inclination [deg]
                      white,  # color
                      740.52e9,  # perihelion
                      816.62e9,  # aphelion
                      71492e3,  # radius
                      'planet',  # object_type
                      4332.589 * 86400,  # period
                      778.57e9  # semi_major_axis
                      )
saturn = SolarObject('saturn',  # name
                     'sun',  # parent
                     568.34e24,  # mass
                     10.18e3,  # max_speed
                     2.485,  # inclination [deg]
                     yellow,  # color
                     1352.55e9,  # perihelion
                     1514.50e9,  # aphelion
                     60268e3,  # radius
                     'planet',  # object_type
                     10759.22 * 86400,  # period
                     1433.53e9  # semi_major_axis
                     )
epimetheus = SolarObject('epimetheus',  # name
                         'saturn',  # parent
                         0.0053e20,  # mass
                         15.87e3,  # max_speed
                         0.34,  # inclination [deg]
                         yellow,  # color
                         152.02e6,  # perihelion
                         151.422e6,  # aphelion
                         65e3,  # radius
                         'moon',  # object_type
                         0.6942 * 86400,  # period
                         151410e3  # semi_major_axis
                         )
janus = SolarObject('janus',  # name
                    'saturn',  # parent
                    0.0190e20,  # mass
                    15.87e3,  # max_speed
                    0.14,  # inclination [deg]
                    red,  # color
                    152.1e6,  # perihelion
                    151.472e6,  # aphelion
                    102e3,  # radius
                    'moon',  # object_type
                    0.6945 * 86400,  # period
                    151460e3  # semi_major_axis
                    )
uranus = SolarObject('uranus',  # name
                     'sun',  # parent
                     86.813e24,  # mass
                     7.11e3,  # max_speed
                     0.772,  # inclination [deg]
                     white,  # color
                     2741.30e9,  # perihelion
                     3003.62e9,  # aphelion
                     25559e3,  # radius
                     'planet',  # object_type
                     30588.740 * 86400,  # period
                     2872.46e9  # semi_major_axis
                     )
neptune = SolarObject('neptune',  # name
                      'sun',  # parent
                      102.413e24,  # mass
                      5.50e3,  # max_speed
                      1.769,  # inclination [deg]
                      blue,  # color
                      4444.45e9,  # perihelion
                      4545.67e9,  # aphelion
                      24764e3,  # radius
                      'planet',  # object_type
                      60189 * 86400,  # period
                      4495.06e9  # semi_major_axis
                      )

save_time = 1
scale_overwrite = 1
# list of objects part of the current simulation
for orbit in all_objects:
    if orbit.name in simulation_target:
        solar_system.append(orbit)

for orbit_name in simulation_target:
    if 0 == len(SolarObject.find_by_name(orbit_name)) and orbit_name.__contains__('_ast'):
        orig_orbit_name = orbit_name.replace(' ', '')[:-4]
        print('Object with _ast name found for orbit: ', orig_orbit_name)
        copy_orbit = SolarObject.find_by_name(orig_orbit_name)[0]
        parent_orbit = SolarObject.find_by_name(copy_orbit.parent)[0]

        mass = copy_orbit.mass / 3
        hill_radii = copy_orbit.semi_major_axis * math.pow(mass / 3 / parent_orbit.mass, 1 / 3)
        x = hill_radii * 0.5
        position = copy_orbit.aphelion - x
        semi_major_axis = copy_orbit.semi_major_axis / copy_orbit.aphelion * position
        speed_circle = math.sqrt(G * (parent_orbit.mass + copy_orbit.mass) / semi_major_axis)
        f = math.pow(2 - position / semi_major_axis, 0.5)
        speed = speed_circle * f * f
        orbit2 = SolarObject(orbit_name,  # name
                             copy_orbit.parent,  # parent
                             mass,  # mass
                             -speed,  # max_speed
                             copy_orbit.inclination_deg,  # inclination [deg]
                             purple,  # color
                             -position,  # perihelion
                             copy_orbit.aphelion,  # aphelion
                             copy_orbit.radius,  # radius
                             copy_orbit.object_type,  # object_type
                             copy_orbit.period,  # period
                             copy_orbit.semi_major_axis  # semi_major_axis
                             )
        solar_system.append(orbit2)

# focus point of the emulation is set for the last defined object without parent object
# and set the center system initial speed to 0
# get object for center orbit
old_center_object = SolarObject.object_in_centre
# with the below command the screen center object can be overwritten
if center_overwrite == 1:
    SolarObject.object_in_centre = new_center_object
    scale_overwrite = 2
center_orbit = SolarObject.find_by_name(SolarObject.object_in_centre)[0]
x_pos_center = center_orbit.x_position
y_pos_center = center_orbit.y_position
z_pos_center = center_orbit.z_position
# 2nd place the closest object to the center and set the center system initial speed to 0
for orbit in solar_system:
    orbit.x_position -= x_pos_center
    orbit.y_position -= y_pos_center
    orbit.z_position -= z_pos_center
print('Center object of the current simulation is:', SolarObject.object_in_centre)

# also re-calculate the scale factor for the screen
SolarObject.scale = 1
for orbit in solar_system:
    if orbit.aphelion != 0:
        orbit.scale = width / (orbit.aphelion * 2.2)
    else:
        orbit.scale = 1
    if orbit.scale < SolarObject.scale and orbit.parent in simulation_target:
        SolarObject.scale = orbit.scale
SolarObject.scale = SolarObject.scale / scale_overwrite
# place the simulated objects to the adjusted position according to center object, and add to sprites to draw it
for orbit in solar_system:
    # set sprites new position based on the updated position of the relevant objects
    orbit.circle.set_new_position(orbit.x_position * SolarObject.scale + width / 2,
                                  -orbit.y_position * SolarObject.scale + width / 2)
    # add the orbits to the sprites list
    allSprites.add(orbit.circle)
    # calculate iteration time for all objects
    dtt = orbit.period / iteration_per_rotation
    # find maximum period time
    if SolarObject.max_period < orbit.period and orbit.name != old_center_object:
        SolarObject.max_period = orbit.period
    # find smallest iteration time
    if dtt < SolarObject.min_iteration_time and orbit.period > 100 and orbit.name != old_center_object:
        SolarObject.min_iteration_time = dtt

# define iteration time as calculated
dt = SolarObject.min_iteration_time
print('iteration time: ', dt)
# set drawing counter to 0
draw = 0
# define end of the simulation by simulation time
sim_end_time = SolarObject.max_period * period_number
# perform the emulation
while t <= sim_end_time:
    # 1st step calculate the acceleration for each orbit separately
    for orbit in solar_system:
        for others in solar_system:
            # if gravity vectors between the two object is not yet calculated
            if others.name != orbit.name and orbit.name not in others.others_acceleration_done:
                # calculate distance between the two objects
                dist = math.sqrt(math.pow(others.x_position - orbit.x_position, 2) +
                                 math.pow(others.y_position - orbit.y_position, 2) +
                                 math.pow(others.z_position - orbit.z_position, 2))
                # calculate gravity force affecting orbit
                gravitational_force = G * orbit.mass * others.mass / math.pow(dist, 2)
                # calculate the size of the acceleration caused by the gravity force
                acc_relative = gravitational_force
                """
                    acc = acc_relative / orbit.mass
                    # calculation using trigonometric functions
                    dist_xy = math.sqrt(math.pow(others.x_position - orbit.x_position, 2) +
                                        math.pow(others.y_position - orbit.y_position, 2))
                    # calculate current angle of the gravity force/acceleration
                    acc_rad_y = math.asin((others.y_position - orbit.y_position) / dist_xy)
                    acc_rad_z = math.acos(dist_xy / dist)
                    # to be honest I do not see right now why it is only required for "x"
                    if (others.x_position - orbit.x_position) > 0:
                        x_dir = -1
                    else:
                        x_dir = 1
                    if orbit.z_position > 0:
                        z_dir = 1
                    else:
                        z_dir = -1
                    # calculate the acceleration for the x and y axes

                    x_acceleration = acc * math.cos(acc_rad_y) * x_dir * math.cos(acc_rad_z)
                    y_acceleration = acc * math.sin(acc_rad_y) * math.cos(acc_rad_z)
                    z_acceleration = acc * math.sin(acc_rad_z) * z_dir
                """
                # calculation using direct proportion to space vector (using the fact that the position vector
                #     and the force/acceleration vector is parallel, but the length is different)
                x_acceleration = -acc_relative * ((others.x_position - orbit.x_position) / dist)
                y_acceleration = acc_relative * ((others.y_position - orbit.y_position) / dist)
                z_acceleration = - acc_relative * ((others.z_position - orbit.z_position) / dist)

                # using the unified acceleration vectors calculate the actual acceleration change using the object mass
                orbit.x_acceleration += x_acceleration / orbit.mass
                orbit.y_acceleration += y_acceleration / orbit.mass
                orbit.z_acceleration += z_acceleration / orbit.mass

                # if optimized run, than also calculate the acceleration for the other object
                if save_time == 1:
                    others.x_acceleration += -x_acceleration / others.mass
                    others.y_acceleration += -y_acceleration / others.mass
                    others.z_acceleration += -z_acceleration / others.mass
                    orbit.others_acceleration_done.append(others.name)

                # Collecting some min/max values to verify model
                if others.name == orbit.parent:
                    if orbit.dist_max < dist:
                        orbit.dist_max = dist
                    elif dist < orbit.dist_min:
                        orbit.dist_min = dist
                elif others.parent == orbit.name and save_time == 1:
                    if others.dist_max < dist:
                        others.dist_max = dist
                    elif dist < others.dist_min:
                        others.dist_min = dist
    # 2nd step calculate the new position/speed for each orbit separately
    for orbit in solar_system:
        # calculate the speed altered by the acceleration in dt time
        orbit.x_speed = orbit.x_speed - (orbit.x_acceleration * dt)
        orbit.y_speed = orbit.y_speed + (orbit.y_acceleration * dt)
        orbit.z_speed = orbit.z_speed - (orbit.z_acceleration * dt)
        # calculate the distance have been taken during dt with the calculated speed
        orbit.x_position_new = orbit.x_position + orbit.x_speed * dt
        orbit.y_position_new = orbit.y_position + orbit.y_speed * dt
        orbit.z_position_new = orbit.z_position + orbit.z_speed * dt
    # if the center point is fixed by fix_center variable, than move the center object (and all other related to it)
    move_x = 0
    move_y = 0
    move_z = 0
    # if the center object shall not move on the screen, than move everything with this offset
    if fix_center:
        # detect offset
        move_x = center_orbit.x_position_new
        move_y = center_orbit.y_position_new
        move_z = center_orbit.z_position_new
        # move everything with the offset
        for orbit in solar_system:
            orbit.x_position_new -= move_x
            orbit.y_position_new -= move_y
            orbit.z_position_new -= move_z
    # 2.5th step, if requested turn the coordinate system
    if turning_coordinate == 1:
        orbit = SolarObject.find_by_name(turn_dir)[0]
        turn_angle = - math.atan2(orbit.y_position_new, orbit.x_position_new)
        for orbit in solar_system:
            x = orbit.x_position_new * math.cos(turn_angle) - orbit.y_position_new * math.sin(turn_angle)
            y = orbit.x_position_new * math.sin(turn_angle) + orbit.y_position_new * math.cos(turn_angle)
            orbit.x_position_new = x
            orbit.y_position_new = y
            x_speed = orbit.x_speed * math.cos(turn_angle) - orbit.y_speed * math.sin(turn_angle)
            y_speed = orbit.x_speed * math.sin(turn_angle) + orbit.y_speed * math.cos(turn_angle)
            orbit.x_speed = x_speed
            orbit.y_speed = y_speed
    # 3rd step draw and make ready for next iteration
    for orbit in solar_system:
        # drawing in memory
        pygame.draw.aaline(background, orbit.color,
                           (orbit.x_position * SolarObject.scale + width / 2,
                            -orbit.y_position * SolarObject.scale + width / 2),
                           (orbit.x_position_new * SolarObject.scale + width / 2,
                            -orbit.y_position_new * SolarObject.scale + width / 2), 1)
        # update current position
        orbit.x_position = orbit.x_position_new
        orbit.y_position = orbit.y_position_new
        orbit.z_position = orbit.z_position_new
        # clear acceleration for next iteration
        orbit.x_acceleration = 0
        orbit.y_acceleration = 0
        orbit.z_acceleration = 0
        orbit.others_acceleration_done = []

    # to reduce runtime, update the screen less regularly
    screen_update = screen_update_period * dt
    if draw < int(t / screen_update):  # screen update frequency definition
        # clear objects
        # trick: background surface changes are taken over
        # (as the recent changes are exactly where the objects were shown)
        # if the above trick is not good enough than replace the below command (significantly slower)
        allSprites.clear(screen, background)
        # screen.blit(background, (0, 0))

        # update objects position
        for orbit in solar_system:
            orbit.circle.set_new_position(orbit.x_position * SolarObject.scale + width / 2,
                                          -orbit.y_position * SolarObject.scale + width / 2)
        # redraw objects
        allSprites.draw(screen)
        # needed to avoid Windows watchdog to react
        pygame.event.get()
        # drawing to screen
        pygame.display.flip()
        draw += 1
        wait = wait_for_cpu_temperature()
        print('{0:.3f}'.format(t * 100 / sim_end_time), '%',
              ' wait:', wait['wait'], ' temp:', wait['temp'])
    # relative time of next iteration step
    t += dt

# re-create final picture only to show the orbit paths
screen.blit(background, (0, 0))
pygame.image.save(screen, 'solar_system.PNG')
# print collected data
for orbit in solar_system:
    if orbit.name != old_center_object:
        print('Minimum distance of ', '{0: <12}'.format(orbit.name), 'is: ', '{0:.5e}'.format(orbit.dist_min),
              ' expected value is: ', '{0:.5e}'.format(orbit.perihelion),
              ' deviation: ', '{0:.5f}'.format(((1 - orbit.perihelion / (orbit.dist_min+1)) * 100)), '%')
        print('Maximum distance of ', '{0: <12}'.format(orbit.name), 'is: ', '{0:.5e}'.format(orbit.dist_max),
              ' expected value is: ', '{0:.5e}'.format(orbit.aphelion),
              ' deviation: ', '{0:.5f}'.format(((1 - orbit.aphelion / orbit.dist_max) * 100)), '%')
# end of file
