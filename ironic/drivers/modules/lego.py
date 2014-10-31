
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Ironic LEGO power manager.

Provides basic power control of virtual machines via a robotic arm.

For use in dev and test environments.

Currently supported environments are:
    NUCS
"""

import subprocess
import time

from oslo.config import cfg

from ironic.common import boot_devices
from ironic.common import exception
from ironic.common.i18n import _
from ironic.common import states
from ironic.conductor import task_manager
from ironic.drivers import base
from ironic.drivers import utils as driver_utils
from ironic.openstack.common import log as logging

legoev3_opts = [
    cfg.StrOpt('lego_ev3_classes_jar',
               default='/opt/stack/reBot/ev3classes.jar:/opt/stack/reBot/.',
               help='lego jars'),
    cfg.IntOpt('lego_press_time_on',
               default='500',
               help='Pressing time for power on.'),
    cfg.IntOpt('lego_press_time_off',
               default='7000',
               help='Pressing time for power off.'),
    cfg.StrOpt('lego_move_degrees',
               default='1440',
               help='Lego robotic arm move degrees.')
]

CONF = cfg.CONF
CONF.register_opts(legoev3_opts, group='lego')

LOG = logging.getLogger(__name__)

REQUIRED_PROPERTIES = {
    'lego_ev3_address': _("IP address or hostname of the Lego Mindstorms EV3."
                          "Required."),
    'lego_ev3_port': _("Port of the Lego Mindstorms EV3. Required.")
}
COMMON_PROPERTIES = REQUIRED_PROPERTIES.copy()
_BOOT_DEVICES_MAP = {
    boot_devices.DISK: 'hd',
    boot_devices.PXE: 'network',
    boot_devices.CDROM: 'cdrom',
}


def _execute_lego_ev3_process(args, shell=False):
    lego_ev3_classes_jar = CONF.lego.lego_ev3_classes_jar
    common_args = ['java', '-cp', lego_ev3_classes_jar]
    all_args = common_args + args
    LOG.debug(all_args)
    return(0,0,0)
    p = subprocess.Popen(all_args,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=shell)
    (out, err) = p.communicate()
    return (out, err, p.returncode)


def _bare_plastic_action(address, port, degrees, pause):
    args = ['BarePlasticAction', address, port, degrees, pause]
    (out, err, ret_val) = _execute_lego_ev3_process(args)
    if not ret_val:
        LOG.debug("BarePlasticAction succeeded.")
    else:
        LOG.debug("BarePlasticAction failed.")


def _bare_plastic_reset(address, port):
    args = ['BarePlasticReset', address]
    (out, err, ret_val) = _execute_lego_ev3_process(args)
    if not ret_val:
        LOG.debug("BarePlasticReset succeeded.")
    else:
        LOG.debug("BarePlasticReset failed.")


def _bare_plastic_rotate_motor(address, port, degrees):
    args = ['BarePlasticRotateMotor', address, port, degrees]
    (out, err, ret_val) = _execute_lego_ev3_process(args)
    if not ret_val:
        LOG.debug("BarePlasticRotateMotor succeeded.")
    else:
        LOG.debug("BarePlasticRotateMotor failed.")


def _power_on(driver_info):
    address = driver_info['address']
    port = driver_info['port']
    degrees = driver_info['lego_move_degrees']
    press_time = driver_info['lego_press_time_on']
    _bare_plastic_rotate_motor(address, port, degrees)
    time.sleep(press_time)
    _bare_plastic_rotate_motor(address, port, "-" + degrees)
    return states.POWER_ON


def _power_off(driver_info):
    address = driver_info['address']
    port = driver_info['port']
    degrees = driver_info['lego_move_degrees']
    press_time = driver_info['lego_press_time_off']
    _bare_plastic_rotate_motor(address, port, degrees)
    time.sleep(press_time)
    _bare_plastic_rotate_motor(address, port, "-" + degrees)
    return states.POWER_OFF


def _parse_driver_info(node):
    lego_address = node.driver_info.get('lego_ev3_address')
    lego_port = node.driver_info.get('lego_ev3_port')
    lego_press_time_on = (CONF.lego.lego_press_time_on / float(1000))
    lego_press_time_off = (CONF.lego.lego_press_time_off / float(1000))
    lego_move_degrees = CONF.lego.lego_move_degrees

    return {
        'address': lego_address,
        'port': lego_port,
        'lego_press_time_on': lego_press_time_on,
        'lego_press_time_off': lego_press_time_off,
        'lego_move_degrees': lego_move_degrees
    }


class LEGOPower(base.PowerInterface):

    def __init__(self):
        self._state = states.POWER_OFF

    def get_properties(self):
        return COMMON_PROPERTIES

    def validate(self, task):
        if not driver_utils.get_node_mac_addresses(task):
            raise exception.InvalidParameterValue(
                _("Node %s does not have any port associated with it.")
                % task.node.uuid)
        address = task.node.driver_info.get('lego_ev3_address')
        LOG.debug(address)

    def get_power_state(self, task):
        LOG.debug("get_power_state")
        LOG.debug(self._state)
        return self._state

    @task_manager.require_exclusive_lock
    def set_power_state(self, task, pstate):
        LOG.debug("set_power_state")
        LOG.debug(self._state)
        LOG.debug(pstate)

        driver_info = _parse_driver_info(task.node)

        if pstate == states.POWER_ON:
            self._state = _power_on(driver_info)
        elif pstate == states.POWER_OFF:
            self._state = _power_off(driver_info)
        else:
            raise exception.InvalidParameterValue(
                _("set_power_state called with invalid power state %s.")
                % pstate)

        if self._state != pstate:
            raise exception.PowerStateFailure(pstate=pstate)

    @task_manager.require_exclusive_lock
    def reboot(self, task):
        LOG.debug("reboot")
        LOG.debug(self._state)
        self._state = states.REBOOT
        LOG.debug(self._state)

        driver_info = _parse_driver_info(task.node)

        driver_info['macs'] = driver_utils.get_node_mac_addresses(task)
        current_pstate = self.get_power_state(task)
        if current_pstate == states.POWER_ON:
            self._state=_power_off(driver_info)

        self._state = _power_on(driver_info)

        if self._state != states.POWER_ON:
            raise exception.PowerStateFailure(pstate=states.POWER_ON)


class LEGOManagement(base.ManagementInterface):

    def get_properties(self):
        LOG.debug("Get properties")
        return COMMON_PROPERTIES

    def validate(self, task):
        LOG.debug("validate mgmt")

    def get_supported_boot_devices(self):
        return list(_BOOT_DEVICES_MAP.keys())
        LOG.debug("Get boot devices")

    @task_manager.require_exclusive_lock
    def set_boot_device(self, task, device, persistent=False):
        LOG.debug("set boot devices")

    def get_boot_device(self, task):
        response = {'boot_device': boot_devices.PXE, 'persistent': None}
        return response

    def get_sensors_data(self, task):
        pass
