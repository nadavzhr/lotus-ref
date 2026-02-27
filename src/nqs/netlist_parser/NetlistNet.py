class NetlistNet:

    def __init__(self, name, is_interface=False):
        self._name = name
        self._lower_name = name.lower()
        self._is_interface = is_interface
        self._connected_sub_instances = []
        self._connected_devices = []
        self._connected_resistors = []

    def get_name(self, lower=True):
        return self._lower_name if lower else self._name

    def is_interface(self):
        return self._is_interface

    def get_connected_sub_instances(self):
        return self._connected_sub_instances

    def get_connected_devices(self):
        return self._connected_devices

    def get_connected_resistors(self):
        return self._connected_resistors

    def add_connected_sub_instance(self, sub_instance, sub_instance_net):
        self._connected_sub_instances.append((sub_instance, sub_instance_net))

    def add_connected_device(self, device, pin_name):
        self._connected_devices.append((device, pin_name))

    def add_connected_resistor(self, resistor, pin_name):
        self._connected_resistors.append((resistor, pin_name))

