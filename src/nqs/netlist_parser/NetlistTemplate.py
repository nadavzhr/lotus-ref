from __future__ import annotations

from .NetlistNet import *


class NetlistTemplate:

    def __init__(self, name, pin_names, is_top_cell=False):
        self._name = name
        self._lower_name = name.lower()
        self._sub_instances = []
        self._self_instances = []
        self._devices = []
        self._resistors = []
        self._nets = []
        self._interface_nets = []
        self._sub_instance_name_map = {}
        self._net_name_map = {}
        self._device_name_map = {}
        self._resistor_name_map = {}
        self._is_top_cell = is_top_cell
        for pin_name in pin_names:
            if pin_name.lower() in self._net_name_map:
                raise ValueError(f'Failed to add pin {pin_name} to template {name}, pin name is duplicated')
            net = NetlistNet(pin_name, is_interface=True)
            self._nets.append(net)
            self._interface_nets.append(net)
            self._net_name_map[pin_name.lower()] = net

    def get_name(self, lower=True):
        return self._lower_name if lower else self._name

    def get_sub_instances(self):
        return self._sub_instances

    def find_sub_instance(self, instance_name):
        return self._sub_instance_name_map.get(instance_name.lower())

    def get_sub_instance(self, sub_instance_name):
        sub_instance = self._sub_instance_name_map.get(sub_instance_name.lower())
        if sub_instance is None:
            raise ValueError(f'Failed to get sub instance {sub_instance_name}')
        return sub_instance

    def get_self_instances(self):
        return self._self_instances

    def get_devices(self):
        return self._devices

    def find_device(self, device_name):
        return self._device_name_map.get(device_name.lower())

    def get_device(self, device_name):
        device = self._device_name_map.get(device_name.lower())
        if device is None:
            raise ValueError(f'Failed to get device {device_name}')
        return device

    def get_resistors(self):
        return self._resistors

    def find_resistor(self, resistor_name):
        return self._resistor_name_map.get(resistor_name.lower())

    def get_resistor(self, resistor_name):
        resistor = self._resistor_name_map.get(resistor_name.lower())
        if resistor is None:
            raise ValueError(f'Failed to get resistor {resistor_name}')
        return resistor

    def get_nets(self):
        return self._nets

    def get_interface_nets(self):
        return self._interface_nets

    def find_net(self, net_name):
        return self._net_name_map.get(net_name.lower())

    def get_net(self, net_name):
        net = self._net_name_map.get(net_name.lower())
        if net is None:
            raise ValueError(f'Failed to get net {net_name}')
        return net

    def is_top_cell(self):
        return self._is_top_cell

    def add_sub_instance(self, instance):
        if instance.get_name().lower() in self._sub_instance_name_map:
            raise ValueError(
                f'Failed to add instance {instance.get_name()} to template {self._name}, instance already exists')
        self._sub_instances.append(instance)
        self._sub_instance_name_map[instance.get_name().lower()] = instance

    def add_self_instance(self, instance):
        self._self_instances.append(instance)

    def add_device(self, device):
        if device.get_name().lower() in self._device_name_map:
            raise ValueError(
                f'Failed to add device {device.get_name()} to template {self._name}, device already exists')
        self._devices.append(device)
        self._device_name_map[device.get_name().lower()] = device

    def add_resistor(self, resistor):
        if resistor.get_name().lower() in self._resistor_name_map:
            raise ValueError(
                f'Failed to add resistor {resistor.get_name()} to template {self._name}, resistor already exists')
        self._resistors.append(resistor)
        self._resistor_name_map[resistor.get_name().lower()] = resistor

    def get_or_add_net(self, net_name):
        net = self._net_name_map.get(net_name.lower())
        if not net:
            net = NetlistNet(net_name)
            self._nets.append(net)
            self._net_name_map[net_name.lower()] = net
        return net
