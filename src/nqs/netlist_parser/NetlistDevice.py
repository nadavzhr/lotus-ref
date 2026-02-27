

class NetlistDevice:

    pin_names = ['d', 'g', 's']

    def __init__(self, name, connected_nets):
        self._name = name
        self._lower_name = name.lower()
        if len(connected_nets) != 3:
            raise ValueError(f'Device {name} initialized with invalid nets {connected_nets}')
        self._connected_nets = connected_nets

    def get_name(self, lower=True):
        return self._lower_name if lower else self._name

    def get_connected_nets(self):
        return self._connected_nets

    def find_connected_net(self, pin_name):
        try:
            index = self.pin_names.index(pin_name)
        except ValueError:
            return None
        return self._connected_nets[index]

    def get_connected_net(self, pin_name):
        net = self.find_connected_net(pin_name)
        if net is None:
            raise ValueError(f'Device {self._name} does not have pin {pin_name}')
        return net