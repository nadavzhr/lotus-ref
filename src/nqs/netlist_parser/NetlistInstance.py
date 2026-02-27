from __future__ import annotations


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .NetlistNet import NetlistNet

class NetlistInstance:

    def __init__(self, name, template, connected_nets, parent_template):
        self._name = name
        self._lower_name = name.lower()
        self._template = template
        self._parent_template = parent_template
        self._interface_connections = {}
        self._connected_nets = {}

        if len(connected_nets) != len(template.get_interface_nets()):
            raise ValueError(f'Failed to create instance {name} of template {template}, '
                               f'number of connected nets does not equal number of template interface nets')
        for net, interface_net in zip(connected_nets, template.get_interface_nets()):
            self._interface_connections[interface_net] = net
            self._connected_nets[net] = interface_net

    def get_name(self, lower=True):
        return self._lower_name if lower else self._name

    def get_template(self):
        return self._template

    def get_parent_template(self):
        return self._parent_template

    def get_connected_net(self, interface_net):
        connected_net = self._interface_connections.get(interface_net)
        if connected_net is None:
            raise ValueError(f'Failed to get net of instance {self._name} '
                               f'connected to interface net {interface_net.get_name()}')
        return connected_net

    def get_interface_connected_net(self, connected_net: 'NetlistNet'):
        interface_net = self._connected_nets.get(connected_net)
        if interface_net is None:
            raise ValueError(f'Failed to get interface net of instance {self._name} '
                               f'connected to net {connected_net.get_name()}')
        return interface_net