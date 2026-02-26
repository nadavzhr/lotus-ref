"""Shared mock for NetlistQueryService used by controller tests."""
from typing import Optional


class MockNetlistQueryService:
    """
    A configurable stub that satisfies the INetlistQueryService protocol.
    Test cases can set .net_matches, .canonical_map, and .templates to control behavior.
    """

    def __init__(self):
        # Maps (template, pattern, is_regex) -> list[str] of net matches
        self.net_matches: dict[tuple, list[str]] = {}
        # Maps (net_name, template) -> canonical name
        self.canonical_map: dict[tuple[str, Optional[str]], str] = {}
        # Set of known template names
        self.templates: set[str] = set()

    def find_matches(
        self,
        template_name: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> tuple[list[str], list[str]]:
        key = (template_name, net_name, net_regex)
        nets = self.net_matches.get(key, [])
        templates = [template_name] if nets and template_name else []
        return nets, templates

    def get_canonical_net_name(
        self, net_name: str, template_name: Optional[str] = None
    ) -> Optional[str]:
        return self.canonical_map.get((net_name, template_name))

    def get_matching_templates(self, template_pattern: str, is_regex: bool) -> set[str]:
        """Return matching templates. For non-regex, check exact membership."""
        if not is_regex:
            return {template_pattern} if template_pattern in self.templates else set()
        import re
        return {t for t in self.templates if re.search(template_pattern, t)}

    def template_exists(self, template_name: str) -> bool:
        return template_name in self.templates

    def net_exists(self, net_name: str, template_name: Optional[str] = None) -> bool:
        return self.get_canonical_net_name(net_name, template_name) is not None

    @staticmethod
    def normalize_net_for_template(name: str, template: str) -> str:
        """Strip a leading 'template:' prefix if present."""
        if template and ':' in name:
            prefix = f"{template}:"
            if name.lower().startswith(prefix.lower()):
                return name[len(prefix):]
        return name

    @staticmethod
    def has_bus_notation(net_name: str) -> bool:
        return "[" in net_name and ":" in net_name

    @staticmethod
    def expand_bus_notation(
        pattern: str, max_expansions: Optional[int] = None
    ) -> list[str]:
        """Simple expansion: net[0:2] -> [net[0], net[1], net[2]]"""
        import re
        m = re.match(r"^(.+)\[(\d+):(\d+)\]$", pattern)
        if not m:
            return [pattern]
        base, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        step = 1 if start <= end else -1
        result = [f"{base}[{i}]" for i in range(start, end + step, step)]
        if max_expansions is not None:
            result = result[:max_expansions]
        return result
