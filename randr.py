#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Cihangir Akturk <cihangir.akturk@tubitak.gov.tr>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# it's now parsing xrandr's output
# we probably want to reconfigure this to use python.Xlib randr, see
# https://stackoverflow.com/questions/8705814/get-display-count-and-resolution-for-each-display-in-python-without-xrandr

from __future__ import print_function
import subprocess
from six import iteritems
import re

debug=0
        

class Mode(object):
    """docstring for Mode"""
    def __init__(self, width, height, freq, current, preferred):
        super(Mode, self).__init__()
        self.width = width
        self.height = height
        self.freq = freq
        self.current = current
        self.preferred = preferred

    def resolution(self):
        return self.width, self.height

    def __str__(self):
        return '[{0}x{1}, {2}, curr: {3}, pref: {4}]'.format(self.width,
                                                             self.height,
                                                             self.freq,
                                                             self.current,
                                                             self.preferred)

    def cmd_str(self):
        return '{0}x{1}'.format(self.width, self.height)

    __repr__ = __str__


class ScreenSettings(object):
    """docstring for ScreenSettings"""
    def __init__(self):
        super(ScreenSettings, self).__init__()
        self.reset()

    def reset(self):
        self.resolution = None
        self.is_primary = False
        self.is_enabled = True
        self.rotation = None
        self.position = None
        self.dirty = False
        self.details = {}


class Screen(object):
    def __init__(self, name, primary, rot, modes):
        super(Screen, self).__init__()

        self.name = name
        self.primary = primary
        self.details = {}

        # dirty hack
        self.rotation = None
        for r in modes:
            if r.current:
                self.rotation = rot
                self.curr_mode = r
                break

        # list of Modes (width, height)
        self.supported_modes = modes

        self.set = ScreenSettings()
        self.set.is_enabled = self.is_enabled()

    def is_connected(self):
        return len(self.supported_modes) != 0

    def is_enabled(self):
        for m in self.supported_modes:
            if m.current:
                return True
        return False

    def available_resolutions(self):
        return [(r.width, r.height) for r in self.supported_modes]

    def check_resolution(self, newres):
        if newres not in self.available_resolutions():
            raise ValueError('Requested resolution is not supported', newres)

    def set_resolution(self, newres):
        """Sets the resolution of this screen to the supplied
           @newres parameter.

        :newres: must be a tuple in the form (width, height)

        """
        if not self.is_enabled():
            raise ValueError('The Screen is off')

        self.check_resolution(newres)
        self.set.resolution = newres

    def set_as_primary(self, is_primary):
        """Set this monitor as primary

        :is_primary: bool

        """
        self.set.is_primary = is_primary

    def set_enabled(self, enable):
        """Enable or disable the output

        :enable: bool

        """
        self.set.is_enabled = enable

    def rotate(self, direction):
        """Rotate the output in the specified direction

        :direction: one of (normal, left, right, inverted)

        """
        self.set.rotation = direction

    def set_position(self, relation, relative_to):
        """Position the output relative to the position
        of another output.

        :relation: TODO
        :relative_to: output name (LVDS1, HDMI eg.)
        """
        self.set.position = (relation, relative_to)
    
    def add_details(self, details, keep_old=False):
        """ 
        Add details (assumed dict) to Screen; update if details already exist.
        Set keep_old=True to avoid over-writing existing values.
        """
        if keep_old:
            details.update(self.details)
            self.details = details
        else:
            self.details.update(details)
        
    def set_brightness(self, brightness):
        """Brightness value (0...1; larger numbers are also possibe but give ugly white-out)
        """
        self.set.details['Brightness']=brightness
            
    def set_gamma(self, gamma):
        """Gamma correction value (R, G, B tuple in range 0...1)
        """
        self.set.details['Gamma']=':'.join(str(g) for g in gamma)
    
    def get_gamma(self):
        """Gamma correction value (R, G, B tuple in range 0...1)
        """
        return tuple(float(v) for v in self.details['Gamma'].split(':'))
    
    def build_cmd(self):
        if not self.name:
            raise ValueError('Cannot apply settings without screen name',
                             self.name)
        if self.set.resolution:
            self.check_resolution(self.set.resolution)

        has_changed = False

        cmd = ['xrandr', '--output', self.name]

        # set resolution
        if self.is_enabled() and \
                self.curr_mode.resolution() == self.set.resolution \
                or not self.set.resolution:
            cmd.append('--auto')
        else:
            res = self.set.resolution
            cmd.extend(['--mode', '{0}x{1}'.format(res[0], res[1])])
            has_changed = True

        # Check if this screen is already primary
        if not self.primary and self.set.is_primary:
            cmd.append('--primary')
            has_changed = True

        if self.set.rotation and self.set.rotation is not self.rotation:
            rot = rot_to_str(self.set.rotation)
            if not rot:
                raise ValueError('Invalid rotation value',
                                 rot, self.set.rotation)
            cmd.extend(['--rotate', rot])
            has_changed = True

        if self.set.position:
            rel, rel_to = self.set.position
            rel = pos_to_str(rel)
            cmd.extend([rel, rel_to])
            has_changed = True

        if self.is_enabled() and not self.set.is_enabled:
            if has_changed:
                raise Exception('--off: this option cannot be combined with other options')
            cmd.append('--off')
            has_changed = True

        for key in self.set.details:
            # ugly hack; --auto is only needed for some of the other options so we remove it here
            try: cmd.remove('--auto')
            except ValueError: pass
            # find keys which have been updated:
            if not self.details or self.set.details[key] != self.details[key]:
                if key=='Brightness':
                    cmd.extend(['--brightness', str(self.set.details[key]) ])
                elif key=='Gamma':
                    cmd.extend(['--gamma', self.set.details[key] ])
        
        return cmd

    def apply_settings(self):
        exec_cmd(self.build_cmd())
        self.set.reset()

    def __str__(self):
        return '[{0}, primary: {1}, modes: {2}, conn: {3}, rot: {4}, '\
                'enabled: {5}]'.format(self.name,
                                       self.primary,
                                       len(self.supported_modes),
                                       self.is_connected(),
                                       rot_to_str(self.rotation),
                                       self.is_enabled())

    __repr__ = __str__


class RotateDirection(object):
    Normal, Left, Inverted, Right = range(1, 5)
    valtoname = {Normal: 'normal', Left: 'left',
                 Inverted: 'inverted', Right: 'right'}
    nametoval = dict((v, k) for k, v in iteritems(valtoname))


def rot_to_str(rot):
    if rot in RotateDirection.valtoname:
        return RotateDirection.valtoname[rot]
    return None


def str_to_rot(s):
    if s in RotateDirection.nametoval:
        return RotateDirection.nametoval[s]
    return RotateDirection.Normal


class PostitonType(object):
    LeftOf, RightOf, Above, Below, SameAs = range(1, 6)
    valtoname = {LeftOf: '--left-of', RightOf: '--right-of',
                 Above: '--above', Below: '--below', SameAs: '--same-as'}
    nametoval = dict((v, k) for k, v in iteritems(valtoname))


def pos_to_str(n):
    return PostitonType.valtoname[n]


def str_to_pos(s):
    return PostitonType.nametoval[s]


def exec_cmd(cmd):
    # throws exception CalledProcessError
    if(debug>1):print("Cmd:", cmd)
    try:
        s = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except Exception as e:
        print(e)
        return []
    try:
        s = s.decode()
    except AttributeError:
        pass

    return s.split('\n')


def create_screen(name_str, modes=None):
    rot = None
    sc_name = name_str.split(' ')[0]

    # if connected
    if modes:
        fr = name_str.split(' ')
        if len(fr) > 2:
            rot = str_to_rot(name_str.split(' ')[3])

    return Screen(sc_name, 'primary' in name_str, rot, modes)

def parse_xrandr_details(screens, lines):
    """ Extract details, like gamma and brightness, from xrandr --verbose output
    """
    rxscreen = re.compile(r'^(\S+)\s+\b[dis]*connected\b')
    rxdetail = re.compile(r'^\t(\w+):\s+(.*)')
    
    screen_no = -1 # so we get 0 after first increment
    details={}

    for line in lines:
        if(debug>1):print("Parsing:", line)
        is_name_line = re.search(rxscreen, line)
        if is_name_line:
            # first, store previous details (if any) in current screen:
            if details:
                if(debug):print("Details:", details)
                screens[screen_no].add_details(details)
                details={}
            if(debug):print("Name:", line.rstrip())
            screen_no+=1
            screen_name=is_name_line.group(1)
            if screens[screen_no].name!=screen_name:
                print('Inconsistent output', screens[screen_no].name, screen_name)
        else:
            key_value_data = re.search(rxdetail, line)
            if key_value_data:
                key=key_value_data.group(1)
                value=key_value_data.group(2)
                details[key]=value
            
    if details: # add remaining details to last screen:
        screens[screen_no].add_details(details)
    
    # nothing to return, as details were added to screens


def parse_xrandr(lines):
    """ Extract screens, states and modes from xrandr output
    """
    rx = re.compile(r'^\s+(\d+)x(\d+)\s+((?:\d+\.)?\d+)([* ]?)([+ ]?)')
    rxconn = re.compile(r'\bconnected\b')
    rxdisconn = re.compile(r'\bdisconnected\b')

    sc_name_line = None
    sc_name = None
    width = None
    height = None
    freq = None
    current = False
    preferred = False

    screens = []
    modes = []

    for i in lines:
        if re.search(rxconn, i) or re.search(rxdisconn, i):
            if sc_name_line:
                newscreen = create_screen(sc_name_line, modes)
                screens.append(newscreen)
                modes = []

            sc_name_line = i

        else:
            r = re.search(rx, i)
            if r:
                width = int(r.group(1))
                height = int(r.group(2))
                freq = float(r.group(3))
                current = r.group(4).replace(' ', '') == '*'
                preferred = r.group(5).replace(' ', '') == '+'

                newmode = Mode(width, height, freq, current, preferred)
                modes.append(newmode)

    if sc_name_line:
        screens.append(create_screen(sc_name_line, modes))

    return screens
    
def screens(details=False):
    """Get all screens.
       details=True also grabs detailed settings (as in xrandr --verbose)
    """
    cmd=['xrandr']
    screens = parse_xrandr(exec_cmd(cmd))
    if details: 
        cmd.append('--verbose')
        parse_xrandr_details(screens, exec_cmd(cmd))
    return screens


def connected_screens(details=False):
    """Get connected screens
    """
    return [s for s in screens(details) if s.is_connected()]


def enabled_screens(details=False):
    return [s for s in connected_screens(details) if s.is_enabled()]


def set_all_brightness(screens, brightness):
    """ set brightness for all screens in list
    """
    for screen in screens:
        screen.set_brightness(brightness)


def set_all_gamma(screens, gamma):
    """ set gamma for all screens in list
    """
    for screen in screens:
        screen.set_gamma(gamma)


def apply_all_settings(screens):
    """ apply settings for all screens in list
    """
    for screen in screens:
        screen.apply_settings()


