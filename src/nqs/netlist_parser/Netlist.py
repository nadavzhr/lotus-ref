from typing import Union

class Netlist:
    """
    Main class in the _netlist module - holding the schematic netlist

    All names in the module are kept with upper/lower case as provided
    Functions that returns names have option to return names in lower case, default is true

    All searches by name are case insensitive

    Functions for searching object by name have two flavors:
    find_x : searches for x, returns None if not found
    get_x: searches for x, throws an exception if not found

    Functions for getting lists of hierarchical names:
    get_template_instance_names - returns list of hierarchical names of all instances of template_name
    get_device_instance_names - returns list of hierarchical names of all devices of device_name in template_name
    get_net_instance_names - returns list of hierarchical names of all nets that connect to net_name in template_name
    """

    def __init__(self):
        self._template_name_map = {}
        self._top_cell = None

    def find_template(self, template_name):
        return self._template_name_map.get(template_name.lower())

    def get_template(self, template_name):
        template = self._template_name_map.get(template_name.lower())
        if template is None:
            raise ValueError(f'Failed to get template {template_name}')
        return template

    def get_templates(self):
        return self._template_name_map.values()

    def get_number_of_templates(self):
        return len(self._template_name_map)

    def get_top_cell(self):
        return self._top_cell

    def add_template(self, template):
        template_name = template.get_name()
        if template_name.lower() in self._template_name_map:
            raise ValueError(f'Failed to add template {template_name} to Netlist, template already exists')
        self._template_name_map[template_name.lower()] = template
        if template.is_top_cell():
            self._top_cell = template

    def get_template_instance_names(self, template_name, lower=True):
        """
        Returns list of hierarchical names of all instances of template_name
        Returns an empty list if the template does not exist
        """

        def instance_step(current_name, current_template, instance_names):
            if current_template.is_top_cell():
                instance_names.append(current_name[:-1])
                return
            for instance in current_template.get_self_instances():
                new_name = f'{instance.get_name(lower)}/{current_name}'
                instance_step(new_name, instance.get_parent_template(), instance_names)

        template = self.find_template(template_name)
        instance_name_list = []
        if template:
            instance_step('', template, instance_name_list)
        return instance_name_list

    def get_device_instance_names(self, template_name, device_name, lower=True):
        """
        Returns list of hierarchical names of all instances of device_name inside template_name
        Returns an empty list if the device does not exist
        """
        device_name_list = []
        device = self.find_device(template_name, device_name)
        if device:
            for instance_name in self.get_template_instance_names(template_name, lower):
                device_name_list.append(f'{instance_name}/{device.get_name(lower)}')
        return device_name_list

    def get_net_instance_names(self, template_name, canonical_net_name, lower=True):
        """
        Returns a list of hierarchical names of all instances of canonical_net_name inside template_name
        Net name should be the correct hierarchical name of the net within the template.
        For example, if net n1 in template t1 connects to interface n2 of a sub_instance i2,
        then the canonical_net_name should be n1 and cannot be given as i2/n2.
        Returns an empty list if the template does not exist or the net does not exist in the template.
        """
        net_name_list = []
        template_net = self.get_net(canonical_net_name, template_name)
        template = self.find_template(template_name)
        if template is None or template_net is None:
            return net_name_list
        if template_net.is_interface():
            net_name_list = self._get_interface_net_instance_net_names(template, template_net, lower)
        else:
            for instance_name in self.get_template_instance_names(template_name, lower):
                if instance_name:
                    net_name_list.append(f'{instance_name}/{canonical_net_name}')
                else:
                    net_name_list.append(f'{canonical_net_name}')
        return net_name_list

    def get_template_of_instance(self, instance_name):
        """
        Returns template of given hierarchical instance name, throws exception on error.
        Instance name should not start with the top cell template name.
        """
        def get_template_step(template, instance_names):
            instance = template.get_sub_instance(instance_names[0])
            new_template = instance.get_template()
            if len(instance_names) == 1:
                return new_template
            else:
                return get_template_step(new_template, instance_names[1:])

        instance_name_list = instance_name.split('/')
        current_template = self.get_top_cell()
        return get_template_step(current_template, instance_name_list)


    def get_canonical_net_name(self,
                                  net_name: str,
                                  template_name: str = None,
                                  lower: bool = True
                                  ) -> Union[tuple['NetlistNet', str], tuple[None, None]]:
        """
        Returns the NetlistNet object and the correct hierarchical name of net within template_name.

        Args:
            net_name: the hierarchical name of the net within template_name, for example n1 or i2/n2.
                      May not be the correct hierarchical name (canonical) of the net within template_name,
                      but must be a valid hierarchical name that resolves to a net within template_name.
            template_name: the name of the template to search within, if '' or None, searches within the top cell template.
            lower: whether to return the hierarchical name in lower case. Default is True.
        
        Returns:
            A tuple of (NetlistNet object of the net, correct hierarchical name of the net within the template scope)
            or (None, None) if net_name is not found in template_name.
        
        Examples:
        Assume top cell is t1,
        t1 has:
            - sub_instance i2 of template t2, and t2 has a sub_instance i3a of template t3.
            - sub_instance i3b of template t3
        n1 is an interface net in t1, and it connects to interface net n2 in t2 through instance i2, and n2 connects to interface net n3 in t3 through instance i3a.
        a2 is an internal net in t2, and it connects to interface net a3 in t3 through instance i3a.

        +----------------------------------------------------------------------------------------------------------+
        |              Template t1 (top cell)                                                                      |
        |                                                                                                          |
        |      # n1                                                                                                |
        |      #                                                                                                   |
        |   +--●-------------------------------------------+                                                       |
        |   |  #         i2 : template t2                  |                                                       |
        |   |  #####                                       |                                                       |
        |   |      ################################################################################                |   
        |   |      #                                       |                                      #                |
        |   |      # n2             ############ a2        |                                      #                |
        |   |      #                           #           |                                      #                |
        |   |   +--●---------------------------●--------+  |       +--●---------------------------●--------+       |
        |   |   |  #     i3a : template t3     #        |  |       |  i3b : template t3           #        |       |
        |   |   |  # n3                        # a3     |  |       |                              # a3     |       |
        |   |   |  #                           #        |  |       |                              #        |       |
        |   |   |                                       |  |       |                                       |       |
        |   |   +---------------------------------------+  |       +---------------------------------------+       |
        |   |                                              |                                                       |
        |   +----------------------------------------------+                                                       |
        |                                                                                                          |
        +----------------------------------------------------------------------------------------------------------+

        1. Interface net:
            - get_canonical_net_name(t1, n1)
            - get_canonical_net_name(t1, i2/n2)
            - get_canonical_net_name(t1, i2/i3a/n3)
            will ALL return the same NetlistNet object of n1, and the correct hierarchical name n1.
        2. Non-interface net:
            - get_canonical_net_name(t2, a2)
            - get_canonical_net_name(t2, i3a/a3)
            will ALL return the same NetlistNet object of a2, and the correct hierarchical name a2.
        3. Interface net with multiple paths to top:
            - get_canonical_net_name(t1, i2/i3a/n3)
            - get_canonical_net_name(t1, i3b/a3)
            will ALL return the same NetlistNet object of n1, and the correct hierarchical name n1.
        4. Interface net within a non-top-cell template:
            - get_canonical_net_name(t2, n2)
            - get_canonical_net_name(t2, i3a/n3)
            will ALL return the same NetlistNet object of n2, and the correct hierarchical name n2.
        """
        def get_net_with_path(current_template: 'NetlistTemplate',
                              net_name: str,
                              current_path: list,
                              lower: bool = True
                              ) -> Union[tuple['NetlistNet', str], tuple[None, None]]:
            """
            Navigate through net_name to find the net and track the path.
            
            Args:
                current_template: Current template being searched
                net_name: Remaining net name path to navigate
                current_path: List of instance names traversed so far
            
            Returns:
                Tuple of (net, path) or (None, None) if not found
            """
            net_name_parts = net_name.split('/')
            if len(net_name_parts) == 1:
                # Final net name
                net = current_template.find_net(net_name_parts[0])
                return net, current_path if net else (None, None)
            
            # Navigate through sub-instance
            sub_instance_name = net_name_parts[0]
            sub_instance = current_template.find_sub_instance(sub_instance_name)
            if sub_instance is None:
                return None, None
            
            new_path = current_path + [sub_instance.get_name(lower)]
            return get_net_with_path(
                sub_instance.get_template(), 
                '/'.join(net_name_parts[1:]), 
                new_path
            )
        
        def trace_interface_to_top(root_template: 'NetlistTemplate',
                                   current_net: 'NetlistNet',
                                   path_from_root: list,
                                   lower: bool = True
                                   ) -> tuple['NetlistNet', str]:
            """
            Trace an interface net upward to find the topmost net and its correct path.
            
            Args:
                root_template: The starting template (constant throughout recursion)
                current_net: Current net being traced
                path_from_root: List of instance names from root_template to template containing current_net
            
            Returns:
                Tuple of (top_net, full_hierarchical_name)
            """
            def get_instance_by_path(template: 'NetlistTemplate', instance_path: list):
                current_template = template
                current_instance = None
                for instance_name in instance_path:
                    current_instance = current_template.get_sub_instance(instance_name)
                    current_template = current_instance.get_template()
                return current_instance

            # Base case: reached the root template level
            if not path_from_root:
                return current_net, current_net.get_name(lower)
            
            # If current net is an interface, trace upward
            if current_net.is_interface():
                try:
                    # Get the deepest instance in the path
                    instance = get_instance_by_path(root_template, path_from_root)
                    # Get the connected net in the parent template
                    connected_net = instance.get_connected_net(current_net)
                except ValueError as e:
                    raise e
            
                # Recursively trace upward with shorter path
                return trace_interface_to_top(root_template, connected_net, path_from_root[:-1])
            else:
                # Current net is not an interface, so this is the topmost net
                # Build the correct hierarchical name
                full_path = '/'.join(path_from_root + [current_net.get_name(lower)])
                return current_net, full_path
        
        if not net_name:
            raise ValueError("Net name cannot be empty")
        
        if not isinstance(net_name, str):
            raise ValueError(f"Net name must be a string, got {type(net_name).__name__}")
            
        if template_name:
            starting_template = self.find_template(template_name)
            if not starting_template:
                raise ValueError(f"Template '{template_name}' not found")
        else:
            starting_template = self.get_top_cell()
            if not starting_template:
                raise ValueError("No top cell defined in netlist")
        
        net, path = get_net_with_path(starting_template, net_name, [])
        if net is None:
            return None, None
        
        if net.is_interface():
            if path:
                # Net is an interface at a lower hierarchy level, trace upward
                return trace_interface_to_top(starting_template, net, path)
            else:
                # Interface net at the starting template level - already at top for this scope
                return net, net.get_name(lower)
        
        full_hierarchical_name = '/'.join((path or []) + [net.get_name(lower)])
        
        return net, full_hierarchical_name

    def get_hierarchical_net_name_of_pin_instance(self, instance_name, pin_name, lower=True):
        """
        Returns hierarchical name of net connected to pin_name in instance_name, throws exception on error.
        Instance name should not start with the top cell template name.
        """
        def get_net_step(template, instance_name_list, interface_name):
            if len(instance_name_list) == 1:
                instance_name = instance_name_list[0]
                instance = template.find_sub_instance(instance_name)
                if instance:
                    new_template = instance.get_template()
                    new_net = new_template.get_net(interface_name)
                    if not new_net.is_interface():
                        raise ValueError(
                            f'Net {interface_name} in template {new_template.get_name()} is not an interface')
                    connected_net = instance.get_connected_net(new_net)
                    return connected_net, connected_net.get_name(lower)
                device = template.find_device(instance_name)
                if device:
                    connected_net = device.get_connected_net(interface_name)
                    return connected_net, connected_net.get_name(lower)
                resistor = template.find_resistor(instance_name)
                if resistor:
                    connected_net = resistor.get_connected_net(interface_name)
                    return connected_net, connected_net.get_name(lower)
                raise ValueError(f'In template {template.get_name(lower)}, '
                                   f'{instance_name} is not an instance, device, or resistor')
            else:
                instance = template.get_sub_instance(instance_name_list[0])
                new_template = instance.get_template()
                current_net, current_net_name = get_net_step(new_template, instance_name_list[1:], interface_name)
                if current_net.is_interface():
                    new_net = instance.get_connected_net(current_net)
                    return new_net, new_net.get_name(lower)
                else:
                    new_net_name = f'{instance.get_name(lower)}/{current_net_name}'
                    return current_net, new_net_name

        top_template = self.get_top_cell()
        if instance_name == '':
            net = top_template.get_net(pin_name)
            if not net.is_interface():
                raise ValueError('Net {pin_name} is not a top level interface')
            return pin_name
        instance_name_split = instance_name.split('/')
        net, net_name = get_net_step(top_template, instance_name_split, pin_name)
        return net_name

    def get_hierarchical_pin_names_on_net(self, net_name, lower=True):
        """
        Returns a list of the hierarchical names of all pins on a given net name.
        Net name should be the correct hierarchical name of the net.
        """
        def get_pins_step(net, instance_name, pin_name_list):
            for sub_instance, sub_instance_net in net.get_connected_sub_instances():
                sub_instance_name = instance_name + sub_instance.get_name(lower)
                pin_name = sub_instance_name + '%' + sub_instance_net.get_name(lower)
                pin_name_list.append(pin_name)
                get_pins_step(sub_instance_net, sub_instance_name + '/', pin_name_list)
            for device, device_pin_name in net.get_connected_devices():
                pin_name = instance_name + device.get_name(lower) + '%' + device_pin_name
                pin_name_list.append(pin_name)
            for resistor, resistor_pin_name in net.get_connected_resistors():
                pin_name = instance_name + resistor.get_name(lower) + '%' + resistor_pin_name
                pin_name_list.append(pin_name)

        pin_name_list = []
        net = self.get_net(net_name)
        if net is None:
            raise ValueError(f'Failed to find net {net_name}')
        last_separator = net_name.rfind('/')
        if last_separator == -1:
            if net.is_interface():
                pin_name_list += [net_name]
            current_instance_name = ''
        else:
            current_instance_name = net_name[:last_separator+1]
        get_pins_step(net, current_instance_name, pin_name_list)
        return pin_name_list

    def _get_interface_net_instance_net_names(self, interface_net_template, interface_net, lower=True):
        """
        Handles the case of an interface net in get_net_instance_names
        """
        def interface_net_instance_step(template, net, interface_net_instance_names):
            if template.is_top_cell():
                interface_net_instance_names.add(net.get_name(lower))
                return
            for instance in template.get_self_instances():
                parent_template = instance.get_parent_template()
                instance_connected_net = instance.get_connected_net(net)
                if instance_connected_net.is_interface():
                    interface_net_instance_step(
                        parent_template, instance_connected_net, interface_net_instance_names)
                else:
                    for instance_name in self.get_template_instance_names(parent_template.get_name(lower)):
                        if instance_name:
                            interface_net_instance_names.add(f'{instance_name}/{instance_connected_net.get_name(lower)}')
                        else:
                            interface_net_instance_names.add(f'{instance_connected_net.get_name(lower)}')


        interface_net_instance_names_set = set()
        interface_net_instance_step(interface_net_template, interface_net, interface_net_instance_names_set)
        return list(interface_net_instance_names_set)

    def find_device(self, template_name, device_name):

        def get_device_step(current_template, current_device_name_list):
            name = current_device_name_list[0]
            if len(current_device_name_list) == 1:
                return current_template.find_device(name)
            sub_instance = current_template.find_sub_instance(name)
            if sub_instance:
                return get_device_step(sub_instance.find_template(), current_device_name_list[1:])
            return False

        template = self.find_template(template_name)
        if not template or device_name == '':
            return None
        device_name_list = device_name.split('/')
        return get_device_step(template, device_name_list)

    def get_net(self, canonical_net_name, template_name=None):
        # For a given template_name and the full hierarchical name of a net within the template
        # Returns the corresponding NetlistNet object.
        # If template_name is not provided, uses the top cell
        # If net_name is not the correct full hierarchical name within the template of any net,
        # Returns None

        def get_net_step(current_template, current_net_name_list):
            name = current_net_name_list[0]
            if len(current_net_name_list) == 1:
                return current_template.find_net(name)
            sub_instance = current_template.find_sub_instance(name)
            if sub_instance:
                return get_net_step(sub_instance.get_template(), current_net_name_list[1:])
            return None

        if template_name:
            template = self.find_template(template_name)
        else:
            template = self.get_top_cell()
        if not template or canonical_net_name == '':
            return None
        net_name_list = canonical_net_name.split('/')
        net = get_net_step(template, net_name_list)
        if net is None or (net.is_interface() and len(net_name_list) > 1):
            # If canonical_net_name has sub-hierarchies, and the net that was found is an interface net,
            # then canonical_net_name is not the correct full hierarchical name of the net within the template.
            # This use case is not supported by Netlist class
            return None
        return net

    def get_alternative_hierarchical_net_names(self,
                                               net_name: str,
                                               template_name: str = None,
                                               lower: bool = True
                                               ) -> list[str]:
        """
        Returns all alternative hierarchical names for net_name within template_name scope.

        The returned list contains all hierarchical names that resolve to the same net object
        within the selected template scope (for example: n0, ib/n1, ib/ic/n2, ...).
        If net_name is not found in the selected scope, an empty list is returned.
        """
        net, canonical_name = self.get_canonical_net_name(net_name, template_name, lower)
        if net is None:
            return []

        canonical_parts = canonical_name.split('/')
        initial_instance_path = '/'.join(canonical_parts[:-1]) if len(canonical_parts) > 1 else ''

        alternative_names = set()

        def collect_names(current_net, instance_path, path_stack):
            net_id = id(current_net)
            if net_id in path_stack:
                return

            current_name = f'{instance_path}/{current_net.get_name(lower)}' if instance_path else current_net.get_name(lower)
            alternative_names.add(current_name)

            next_path_stack = set(path_stack)
            next_path_stack.add(net_id)
            for sub_instance, sub_instance_net in current_net.get_connected_sub_instances():
                next_instance_path = (
                    f'{instance_path}/{sub_instance.get_name(lower)}' if instance_path else sub_instance.get_name(lower)
                )
                collect_names(sub_instance_net, next_instance_path, next_path_stack)

        collect_names(net, initial_instance_path, set())
        return sorted(alternative_names)
    
    def get_all_nets(self, template_name: str, lower: bool=True) -> list[tuple['NetlistNet', str]]:
        """
        Returns a list of tuples of (NetlistNet object, hierarchical name) for all nets in the template.
        The hierarchical name is the correct hierarchical name of the net within the template scope.
        If template_name is not found, an empty list is returned.
        """
        def net_find_step(current_instance_name, current_template, net_list):
            for net in current_template.get_nets():
                if not net.is_interface():
                    net_list.append(f'{current_instance_name}{net.get_name(lower)}')
            for instance in current_template.get_sub_instances():
                instance_name = f'{current_instance_name}{instance.get_name(lower)}/'
                net_find_step(instance_name, instance.get_template(), net_list)

        all_nets = []
        template = self.find_template(template_name)
        if template:
            for interface_net in template.get_interface_nets():
                all_nets.append(f'{interface_net.get_name(lower)}')

            net_find_step('', template, all_nets)

        ret = []
        for net_name in all_nets:
            net, canonical_net_name = self.get_canonical_net_name(net_name, template_name, lower)
            if net is not None:
                ret.append((net, canonical_net_name))
        return ret