from __future__ import annotations

import gzip

from .Netlist import *
from .NetlistTemplate import *
from .NetlistInstance import *
from .NetlistResistor import *
from .NetlistDevice import *


class NetlistBuilder:
    
    def __init__(self,  logger):
        self._logger = logger
    
    def read_spice_file(self, top_cell_name, filename='', _file_manager=None, file_tag='', debug=False):
        """
        Builds Netlist from spice file

        Spice file can be provided either with filename or with _file_manager and file_tag
        """

        if filename and _file_manager:
            raise ValueError('read_spice_file called with both a filename and a _file_manager')

        if filename:
            self._logger.info(f'Reading {filename}')
            if filename.endswith('.gz'):
                file = gzip.open(filename, 'rt')
            else:
                file = open(filename, 'r')
        elif _file_manager:
            file = _file_manager.open_file(file_tag, 'r')
        else:
            raise ValueError('read_spice_file called without filename or _file_manager')

        netlist = Netlist()
        just_read_template_line = False
        in_template = False
        template: NetlistTemplate = None
        template_name = ''
        template_pin_names = []
        just_read_instance_line = False
        just_read_device_line = False
        just_read_resistor_line = False
        instance_line_list = []
        device_line_list = []
        resistor_line_list = []

        counter = 0
        for line in file:
            counter += 1
            try:
                line = line.lstrip()
                if not line or line.startswith('*'):
                    continue
                line_list = line.split()

                if just_read_template_line:
                    if line_list[0] == '+':
                        template_pin_names += line_list[1:]
                        continue
                    else:
                        if not template_pin_names:
                            raise ValueError(f'Template {template_name} has no pins')
                        if debug:
                            self._logger.debug(f'Read template {template_name} with pins {template_pin_names}')
                        is_top_cell = (template_name == top_cell_name)
                        template = NetlistTemplate(template_name, template_pin_names, is_top_cell=is_top_cell)
                        just_read_template_line = False

                if just_read_instance_line:
                    # Instance line name format
                    # X<instance_name> <net1> ... <netN> <template_name>
                    # For instances of pcells, there are additional parameters that are ignored here:
                    # X<instance_name> <net1> ... <netN> <template_name> <param1=val1> ... <paramN=valN>
                    if line_list[0] == '+':
                        instance_line_list += line_list[1:]
                        continue
                    else:
                        check_pcell_param=True
                        while(check_pcell_param):
                            if '=' in instance_line_list[-1]:
                                instance_line_list.pop()
                            else:
                                check_pcell_param=False
                        instance_name = instance_line_list[0][1:]
                        if not instance_name:
                            raise ValueError(f'In spice file, failed to get instance name')
                        if len(instance_line_list) < 2:
                            raise ValueError(f'Failed to get template name of instance {instance_name}')
                        instance_template_name = instance_line_list[-1]
                        instance_pin_names = instance_line_list[1:-1]
                        instance_template = netlist.find_template(instance_template_name)
                        if not instance_template:
                            raise ValueError(f'Failed to get template {instance_template_name}')
                        connected_nets = []
                        for instance_pin in instance_pin_names:
                            connected_net = template.get_or_add_net(instance_pin)
                            connected_nets.append(connected_net)
                        instance = NetlistInstance(instance_name, instance_template, connected_nets, template)
                        instance_template.add_self_instance(instance)
                        for connected_net, pin in zip(connected_nets, instance_template.get_interface_nets()):
                            connected_net.add_connected_sub_instance(instance, pin)
                        template.add_sub_instance(instance)
                        if debug:
                            self._logger.debug(f'Read instance {instance_name} of template {instance_template_name}')
                        just_read_instance_line = False

                if just_read_device_line:
                    if line_list[0] == '+':
                        device_line_list += line_list[1:]
                        continue
                    else:
                        device_name = device_line_list[0]
                        if len(device_line_list) < 4:
                            raise ValueError(f'Device {device_name} is missing net names')
                        device_net_names = device_line_list[1:4]
                        connected_nets = []
                        for device_net_name in device_net_names:
                            connected_net = template.get_or_add_net(device_net_name)
                            connected_nets.append(connected_net)
                        device = NetlistDevice(device_name, connected_nets)
                        for connected_net, pin_name in zip(connected_nets, NetlistDevice.pin_names):
                            connected_net.add_connected_device(device, pin_name)
                        template.add_device(device)
                        just_read_device_line = False

                if just_read_resistor_line:
                    if line_list[0] == '+':
                        resistor_line_list += line_list[1:]
                        continue
                    else:
                        resistor_name = resistor_line_list[0]
                        if len(resistor_line_list) < 3:
                            raise ValueError(f'Resistor {resistor_name} is missing net names')
                        resistor_net_names = resistor_line_list[1:3]
                        connected_nets = []
                        for resistor_net_name in resistor_net_names:
                            connected_net = template.get_or_add_net(resistor_net_name)
                            connected_nets.append(connected_net)
                        resistor = NetlistResistor(resistor_name, connected_nets)
                        for connected_net, pin_name in zip(connected_nets, NetlistResistor.pin_names):
                            connected_net.add_connected_resistor(resistor, pin_name)
                        template.add_resistor(resistor)
                        just_read_resistor_line = False

                if line_list[0].lower() == '.subckt':
                    just_read_template_line = True
                    in_template = True
                    if len(line_list) < 2:
                        raise ValueError(f'Encountered .subckt line without template name: {line}')
                    template_name = line_list[1]
                    template_pin_names = line_list[2:]
                    continue

                if in_template:
                    if line_list[0].lower() == '.ends':
                        # Build template
                        netlist.add_template(template)
                        if debug:
                            self._logger.debug(f'Adding template {template_name}, '
                                               f'{len(template.get_sub_instances())} instances inside')
                        in_template = False
                        template_name = ''
                        continue

                    if line_list[0].startswith('X'):
                        just_read_instance_line = True
                        instance_line_list = line_list
                        continue

                    if line_list[0].startswith('M'):
                        just_read_device_line = True
                        device_line_list = line_list
                        continue

                    if line_list[0].startswith('R'):
                        just_read_resistor_line = True
                        resistor_line_list = line_list
                        continue

                    self._logger.error(f'Unrecognized line in {template.get_name()}: {line}')

            except ValueError as ex:
                file.close()
                raise ValueError(f'While reading spice file on line {counter}: {ex}. Line: {line}')
            except BaseException:
                file.close()
                raise

        file.close()

        if netlist.get_top_cell() is None:
            raise ValueError(f'Failed to find template with top cell name {top_cell_name} in spice file')

        return netlist