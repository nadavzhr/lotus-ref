"""
SPICE-file-based NetlistQueryService.

Parses a SPICE netlist file (.sp) to extract subcircuit hierarchy, nets, and
canonical net name mappings.  Provides the same INetlistQueryService interface
as the original FlyNetlist-backed implementation but requires no external
dependencies beyond the standard library.
"""
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from threading import RLock
from functools import lru_cache
from typing import Optional
from dataclasses import dataclass, field
import logging


def _get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = _get_logger(__name__)


# ------------------------------------------------------------------
# SPICE parser data structures
# ------------------------------------------------------------------

@dataclass
class SubcktInstance:
    """A subcircuit instantiation (X-line) inside a parent subcircuit."""
    inst_name: str          # instance name without leading 'X'
    connections: list[str]  # positional net connections
    subckt_name: str        # name of the sub-circuit template


@dataclass
class SubcktDef:
    """Parsed .SUBCKT definition."""
    name: str
    ports: list[str]
    instances: list[SubcktInstance] = field(default_factory=list)
    local_nets: set[str] = field(default_factory=set)


# ------------------------------------------------------------------
# SPICE parser
# ------------------------------------------------------------------

def parse_spice_file(path: str | Path) -> dict[str, SubcktDef]:
    """Parse a SPICE file and return a dict of subcircuit definitions."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    subckts: dict[str, SubcktDef] = {}
    current: Optional[SubcktDef] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue

        upper = line.upper()

        if upper.startswith(".SUBCKT"):
            tokens = line.split()
            name = tokens[1].lower()
            ports = [p.lower() for p in tokens[2:]]
            current = SubcktDef(name=name, ports=ports, local_nets=set(ports))
            continue

        if upper.startswith(".ENDS"):
            if current is not None:
                subckts[current.name] = current
                current = None
            continue

        if current is None:
            continue

        tokens = line.split()
        dev_name = tokens[0]

        if dev_name.upper().startswith("X"):
            # Subcircuit instance: X<name> <nets...> <subckt>
            inst_name = dev_name[1:].lower()
            subckt_template = tokens[-1].lower()
            connections = [t.lower() for t in tokens[1:-1]]
            current.instances.append(
                SubcktInstance(inst_name, connections, subckt_template)
            )
            for net in connections:
                current.local_nets.add(net)

        elif dev_name.upper().startswith("M"):
            # MOSFET: M<name> drain gate source bulk MODEL ...
            nets = [t.lower() for t in tokens[1:5]]
            for net in nets:
                current.local_nets.add(net)

    return subckts


# ------------------------------------------------------------------
# Hierarchy expansion
# ------------------------------------------------------------------

def _build_template_data(
    subckts: dict[str, SubcktDef],
    template_name: str,
) -> tuple[set[str], dict[str, str]]:
    """
    Recursively expand the hierarchy for *template_name* and return:
      - canonical_nets: the set of unique canonical net names
      - alias_map: mapping every reachable hierarchical path → canonical name

    A canonical name is the shortest hierarchical path that refers to a
    given physical net within the template.
    """
    defn = subckts[template_name]
    # Union-find style: map every net to a canonical representative.
    # Start with all local nets pointing to themselves.
    alias_map: dict[str, str] = {}
    for net in defn.local_nets:
        alias_map[net] = net

    def _find(n: str) -> str:
        """Chase aliases to the canonical name."""
        visited = set()
        while alias_map.get(n, n) != n:
            if n in visited:
                break
            visited.add(n)
            n = alias_map[n]
        return n

    def _preference(name: str) -> tuple:
        """Lower tuple = higher preference as canonical name."""
        is_port = name in port_set
        is_local = "/" not in name
        depth = name.count("/")
        return (not is_port, not is_local, depth, len(name), name)

    def _merge(child: str, parent: str) -> None:
        """Merge two net aliases, keeping the more preferred as canonical."""
        pc = _find(parent)
        cc = _find(child)
        if pc == cc:
            return
        if _preference(cc) < _preference(pc):
            alias_map[pc] = cc
        else:
            alias_map[cc] = pc

    port_set = set(defn.ports)

    # Expand each subcircuit instance
    for inst in defn.instances:
        child_def = subckts.get(inst.subckt_name)
        if child_def is None:
            continue

        # Build a pin mapping: child_port → parent_net
        pin_map: dict[str, str] = {}
        for i, child_port in enumerate(child_def.ports):
            if i < len(inst.connections):
                pin_map[child_port] = inst.connections[i]

        # Recursively get the child's canonical nets and alias map
        child_canonical, child_aliases = _build_template_data(subckts, inst.subckt_name)

        # For each canonical net in the child, create a hierarchical path
        for child_net in child_canonical:
            hier_path = f"{inst.inst_name}/{child_net}"
            alias_map[hier_path] = hier_path  # start as self

            # If the child canonical net is a port, it maps to the parent connection
            if child_net in pin_map:
                parent_net = pin_map[child_net]
                _merge(hier_path, parent_net)

        # For each alias in the child, create a hierarchical alias
        for child_alias, child_target in child_aliases.items():
            hier_alias = f"{inst.inst_name}/{child_alias}"
            hier_target = f"{inst.inst_name}/{child_target}"
            alias_map[hier_alias] = hier_alias  # register it

            # Resolve: if child_target is a port, it maps upward
            if child_target in pin_map:
                parent_net = pin_map[child_target]
                _merge(hier_alias, parent_net)
            else:
                _merge(hier_alias, hier_target)

    # Flatten alias_map so every entry points directly to canonical
    all_keys = list(alias_map.keys())
    for k in all_keys:
        alias_map[k] = _find(k)

    canonical_nets = set(alias_map.values())
    return canonical_nets, alias_map


# ------------------------------------------------------------------
# SpiceNetlistQueryService
# ------------------------------------------------------------------

class SpiceNetlistQueryService:
    """
    NetlistQueryService backed by a parsed SPICE netlist file.

    Provides the same INetlistQueryService protocol as the original
    FlyNetlist-backed ``NetlistQueryService`` but works entirely from
    a ``.sp`` file — no external dependencies required.
    """

    BUS_PATTERN = re.compile(r"\[(\d+)[:-](\d+)\]")
    INDEX_PATTERN = re.compile(r"\[(\d+)\]")
    MAX_BUS_EXPANSION = 10000
    SQLITE_MAX_VARS_PER_QUERY = 900

    def __init__(self, cell: str, spice_file: str | Path):
        logger.info("Initializing SpiceNetlistQueryService")

        self._db_lock = RLock()
        self._is_closed = False

        spice_path = Path(spice_file)
        if not spice_path.exists():
            raise FileNotFoundError(f"Spice file not found: {spice_file}")

        logger.info("Parsing spice file: %s", spice_path)
        self._subckts = parse_spice_file(spice_path)

        self._top_cell = cell.lower()
        if self._top_cell not in self._subckts:
            raise RuntimeError(
                f"Cell '{cell}' not found in spice file. "
                f"Available: {sorted(self._subckts.keys())}"
            )

        self._all_templates: set[str] = set(self._subckts.keys())
        logger.debug("Templates loaded: %s", sorted(self._all_templates))

        # Build per-template canonical nets and alias maps
        self._canonical_nets: dict[str, set[str]] = {}
        self._alias_maps: dict[str, dict[str, str]] = {}
        for tpl in self._all_templates:
            cn, am = _build_template_data(self._subckts, tpl)
            self._canonical_nets[tpl] = cn
            self._alias_maps[tpl] = am

        self._all_nets_in_templates = self._canonical_nets

        # SQLite for efficient search
        self._init_database()

        # Canonical net ID infrastructure for conflict detection
        self._build_canonical_id_table()
        self._build_instance_paths()

        logger.info("SpiceNetlistQueryService ready (top cell: %s)", self._top_cell)

    # ==================================================================
    # PUBLIC METHODS
    # ==================================================================

    def get_top_cell(self) -> str:
        return self._top_cell

    def get_all_templates(self) -> set[str]:
        return self._all_templates.copy()

    def get_matching_templates(self, template_pattern: str, is_regex: bool) -> set[str]:
        if not template_pattern:
            return set()
        normalized = template_pattern if is_regex else template_pattern.lower()
        return set(self._get_matching_templates(normalized, is_regex))

    def template_exists(self, template_name: str) -> bool:
        return self._normalize_template_name(template_name) is not None

    def get_all_nets_in_template(self, template: Optional[str] = None) -> set[str]:
        normalized = self._normalize_template_name(template)
        if normalized is None:
            return set()
        return self._all_nets_in_templates.get(normalized, set())

    @lru_cache(maxsize=256)
    def net_exists(self, net_name: str, template_name: Optional[str] = None) -> bool:
        normalized = self._normalize_template_name(template_name)
        if normalized is None:
            return False
        return self._resolve_canonical_net_name(normalized, net_name.lower()) is not None

    def get_canonical_net_name(
        self, net_name: str, template_name: Optional[str] = None
    ) -> Optional[str]:
        normalized = self._normalize_template_name(template_name)
        if normalized is None:
            return None
        return self._resolve_canonical_net_name(normalized, net_name.lower())

    @lru_cache(maxsize=256)
    def find_matches(
        self,
        template_name: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> tuple[list[str], list[str]]:
        if not net_name:
            return [], []

        template_name = template_name or self._top_cell
        template_name = template_name.lower() if not template_regex else template_name
        net_name = net_name.lower() if not net_regex else net_name

        matching_templates = self._get_matching_templates(template_name, template_regex)
        if not matching_templates:
            return [], []

        matching_nets = set(
            self._get_matching_nets(matching_templates, net_name, net_regex)
        )

        if not net_regex and not self.has_bus_notation(net_name):
            matching_nets.update(
                self._get_matching_alias_nets(matching_templates, net_name)
            )

        matching_nets_sorted = sorted(matching_nets)

        matched_templates = sorted(
            set(
                net.split(":")[0] if ":" in net else self._top_cell
                for net in matching_nets_sorted
            )
        )

        return matching_nets_sorted, matched_templates

    # ==================================================================
    # CANONICAL NET ID — CONFLICT DETECTION
    # ==================================================================

    @lru_cache(maxsize=256)
    def resolve_to_canonical_ids(
        self,
        template: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> frozenset[int]:
        """
        Resolve a rule pattern to top-cell canonical net IDs.

        This is the primary entry point for conflict detection.  Given a
        template/net pattern (with optional regex flags), it finds all
        matching nets and maps them through the hierarchy to their
        top-cell canonical net IDs (integers).

        Returns a frozenset of integer canonical net IDs.
        """
        if not net_name:
            return frozenset()

        tpl_name = (template or self._top_cell)
        tpl_name = tpl_name.lower() if not template_regex else tpl_name
        net_norm = net_name.lower() if not net_regex else net_name

        matching_templates = self._get_matching_templates(tpl_name, template_regex)
        if not matching_templates:
            return frozenset()

        result_ids: set[int] = set()
        for tpl in matching_templates:
            resolved = self._resolve_matching_nets_in_template(
                tpl, net_norm, net_regex,
            )
            for net in resolved:
                ids = self._resolve_tpl_net_to_top_ids(tpl, net)
                if ids:
                    result_ids.update(ids)

        return frozenset(result_ids)

    def canonical_net_name(self, net_id: int) -> Optional[str]:
        """Return the canonical net name string for a given integer ID."""
        return self._id_net_map.get(net_id)

    # ==================================================================
    # STATIC / CLASS METHODS
    # ==================================================================

    @staticmethod
    def normalize_net_for_template(name: str, template: Optional[str]) -> str:
        if template and ":" in name:
            prefix = f"{template}:"
            if name.lower().startswith(prefix.lower()):
                return name[len(prefix):]
        return name

    @staticmethod
    def has_bus_notation(net_name: str) -> bool:
        return bool(SpiceNetlistQueryService.BUS_PATTERN.search(net_name))

    @staticmethod
    def expand_bus_notation(
        pattern: str, max_expansions: Optional[int] = None
    ) -> list[str]:
        if max_expansions is not None and max_expansions <= 0:
            return []

        count = [0]

        def _expand(current_pattern: str) -> list[str]:
            if not current_pattern or not SpiceNetlistQueryService.has_bus_notation(
                current_pattern
            ):
                if max_expansions is not None:
                    count[0] += 1
                    if count[0] > max_expansions:
                        raise ValueError(
                            f"Bus expansion exceeded limit ({max_expansions}) "
                            f"for pattern '{pattern}'"
                        )
                return [current_pattern]

            match = SpiceNetlistQueryService.BUS_PATTERN.search(current_pattern)
            if not match:
                return [current_pattern]

            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                start, end = end, start

            prefix = current_pattern[: match.start()]
            suffix = current_pattern[match.end() :]
            expanded = []
            for i in range(start, end + 1):
                expanded.extend(_expand(f"{prefix}[{i}]{suffix}"))
            return expanded

        if not pattern or not SpiceNetlistQueryService.has_bus_notation(pattern):
            return [pattern]

        return _expand(pattern)

    # ==================================================================
    # PRIVATE METHODS
    # ==================================================================

    def _normalize_template_name(self, template_name: Optional[str]) -> Optional[str]:
        if template_name is None or template_name.strip() == "":
            return self._top_cell
        normalized = template_name.strip().lower()
        return normalized if normalized in self._all_templates else None

    @lru_cache(maxsize=4096)
    def _resolve_canonical_net_name(
        self, template_name: str, net_name: str
    ) -> Optional[str]:
        if not net_name:
            return None
        alias_map = self._alias_maps.get(template_name, {})
        canonical = alias_map.get(net_name)
        if canonical is not None:
            return canonical
        # Check if it's already a canonical net
        canonical_set = self._canonical_nets.get(template_name, set())
        if net_name in canonical_set:
            return net_name
        return None

    def _get_matching_templates(
        self, template_name: str, template_regex: bool
    ) -> list[str]:
        if not template_regex:
            results = self._execute_sql_query(
                "SELECT name FROM templates WHERE name = ? LIMIT 1",
                (template_name,),
            )
            return [results[0][0]] if results else []
        try:
            results = self._execute_sql_query(
                "SELECT name FROM templates WHERE name REGEXP ?",
                (template_name,),
            )
            return [row[0] for row in results]
        except Exception as e:
            logger.error("Error matching template pattern '%s': %s", template_name, e)
            return []

    def _get_matching_nets(
        self, templates: list[str], net_name: str, net_regex: bool
    ) -> list[str]:
        if isinstance(templates, str):
            templates = [templates]
        if not templates or not net_name:
            return []

        net_name = net_name.lower() if not net_regex else net_name

        if net_regex:
            return self._match_nets_regex(templates, net_name)
        elif self.has_bus_notation(net_name):
            return self._match_nets_bus(templates, net_name)
        else:
            return self._match_nets_exact(templates, net_name)

    def _match_nets_regex(self, templates: list[str], net_name: str) -> list[str]:
        if not templates:
            return []
        placeholders = ",".join("?" * len(templates))
        try:
            results = self._execute_sql_query(
                f"""
                SELECT t.name, n.net_name
                FROM nets n
                JOIN templates t ON n.template_id = t.id
                WHERE t.name IN ({placeholders}) AND n.net_name REGEXP ?
                """,
                (*templates, net_name),
            )
        except Exception as e:
            logger.error("Error matching net regex '%s': %s", net_name, e)
            return []
        return self._format_net_results(results)

    def _match_nets_bus(self, templates: list[str], net_name: str) -> list[str]:
        if not templates:
            return []
        try:
            expanded = self.expand_bus_notation(
                net_name, max_expansions=self.MAX_BUS_EXPANSION
            )
        except ValueError as e:
            logger.warning(str(e))
            return []
        if not expanded:
            return []

        t_placeholders = ",".join("?" * len(templates))
        available = max(1, self.SQLITE_MAX_VARS_PER_QUERY - len(templates))
        results = []
        for start in range(0, len(expanded), available):
            chunk = expanded[start : start + available]
            n_placeholders = ",".join("?" * len(chunk))
            chunk_results = self._execute_sql_query(
                f"""
                SELECT t.name, n.net_name
                FROM nets n
                JOIN templates t ON n.template_id = t.id
                WHERE t.name IN ({t_placeholders}) AND n.net_name IN ({n_placeholders})
                """,
                (*templates, *chunk),
            )
            results.extend(chunk_results)
        return self._format_net_results(results)

    def _match_nets_exact(self, templates: list[str], net_name: str) -> list[str]:
        if not templates:
            return []
        placeholders = ",".join("?" * len(templates))
        results = self._execute_sql_query(
            f"""
            SELECT t.name, n.net_name
            FROM nets n
            JOIN templates t ON n.template_id = t.id
            WHERE t.name IN ({placeholders}) AND n.net_name = ?
            """,
            (*templates, net_name),
        )
        return self._format_net_results(results)

    def _get_matching_alias_nets(
        self, templates: list[str], net_name: str
    ) -> set[str]:
        if not templates or not net_name:
            return set()
        matched: set[str] = set()
        for tpl in templates:
            canonical = self._resolve_canonical_net_name(tpl, net_name)
            if canonical is not None:
                matched.add(self._format_single_net_result(tpl, canonical))
        return matched

    def _format_single_net_result(self, template_name: str, net_name: str) -> str:
        return net_name if template_name == self._top_cell else f"{template_name}:{net_name}"

    def _format_net_results(self, results) -> list[str]:
        return [
            self._format_single_net_result(row[0], row[1]) for row in results
        ]

    # ==================================================================
    # CANONICAL NET ID — BUILD METHODS
    # ==================================================================

    def _build_canonical_id_table(self) -> None:
        """Assign integer IDs to all top-cell canonical nets."""
        top_canonical = sorted(self._canonical_nets[self._top_cell])
        self._net_id_map: dict[str, int] = {
            name: i for i, name in enumerate(top_canonical)
        }
        self._id_net_map: dict[int, str] = dict(enumerate(top_canonical))
        logger.debug(
            "Canonical net ID table: %d top-cell nets", len(self._net_id_map),
        )

    def _build_instance_paths(self) -> None:
        """Build mapping: template → list of instance paths in top cell hierarchy."""
        self._template_instances: dict[str, list[str]] = defaultdict(list)

        def traverse(template: str, prefix: str) -> None:
            defn = self._subckts.get(template)
            if defn is None:
                return
            for inst in defn.instances:
                path = f"{prefix}/{inst.inst_name}" if prefix else inst.inst_name
                child = inst.subckt_name
                if child in self._subckts:
                    self._template_instances[child].append(path)
                    traverse(child, path)

        traverse(self._top_cell, "")
        logger.debug(
            "Instance paths: %s",
            {k: len(v) for k, v in self._template_instances.items()},
        )

    @lru_cache(maxsize=8192)
    def _resolve_tpl_net_to_top_ids(self, tpl: str, net: str) -> frozenset[int]:
        """
        Lazily compute the top-cell canonical net IDs for a single
        (template, canonical_net_within_template) pair.

        For the top cell this is a 1:1 identity mapping.  For child
        templates the net is expanded through every instance path and
        resolved via the top cell alias map.

        Results are cached so repeated lookups are free.
        """
        if tpl == self._top_cell:
            net_id = self._net_id_map.get(net)
            return frozenset({net_id}) if net_id is not None else frozenset()

        top_alias = self._alias_maps[self._top_cell]
        paths = self._template_instances.get(tpl, [])
        ids: set[int] = set()
        for path in paths:
            hier = f"{path}/{net}"
            top_canonical = top_alias.get(hier)
            if top_canonical is not None:
                net_id = self._net_id_map.get(top_canonical)
                if net_id is not None:
                    ids.add(net_id)
        return frozenset(ids)

    def _resolve_matching_nets_in_template(
        self, template: str, net_name: str, net_regex: bool,
    ) -> set[str]:
        """
        Find canonical nets within *template* that match *net_name*.

        Returns a set of canonical-within-template net names.
        """
        if net_regex:
            results = self._execute_sql_query(
                """SELECT n.net_name FROM nets n
                   JOIN templates t ON n.template_id = t.id
                   WHERE t.name = ? AND n.net_name REGEXP ?""",
                (template, net_name),
            )
            return {row[0] for row in results}

        if self.has_bus_notation(net_name):
            try:
                expanded = self.expand_bus_notation(
                    net_name, max_expansions=self.MAX_BUS_EXPANSION,
                )
            except ValueError:
                return set()
            resolved: set[str] = set()
            for name in expanded:
                canonical = self._resolve_canonical_net_name(template, name)
                if canonical:
                    resolved.add(canonical)
            return resolved

        # Exact match (with alias resolution)
        canonical = self._resolve_canonical_net_name(template, net_name)
        return {canonical} if canonical else set()

    # ==================================================================
    # SQLITE DATABASE
    # ==================================================================

    def _init_database(self) -> None:
        self._db_path = ":memory:"
        self._db_conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._db_conn.row_factory = sqlite3.Row

        def _regexp(expr, item):
            if item is None:
                return 0
            try:
                return 1 if re.search(expr, item, re.IGNORECASE) else 0
            except re.error:
                return 0

        self._db_conn.create_function("REGEXP", 2, _regexp)
        cursor = self._db_conn.cursor()

        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA journal_mode = OFF")
        cursor.execute("PRAGMA cache_size = 100000")
        cursor.execute("PRAGMA temp_store = MEMORY")

        cursor.execute(
            """
            CREATE TABLE templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE nets (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                net_name TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        """
        )

        sorted_templates = sorted(self._all_templates)
        templates_data = [(i, tpl) for i, tpl in enumerate(sorted_templates)]
        template_id_map = {tpl: i for i, tpl in enumerate(sorted_templates)}

        cursor.executemany(
            "INSERT INTO templates (id, name) VALUES (?, ?)", templates_data
        )

        nets_data = []
        for tpl, nets in self._all_nets_in_templates.items():
            tid = template_id_map[tpl]
            nets_data.extend((tid, net) for net in nets)

        cursor.executemany(
            "INSERT INTO nets (template_id, net_name) VALUES (?, ?)", nets_data
        )

        cursor.execute("CREATE INDEX idx_template_name ON templates(name)")
        cursor.execute("CREATE INDEX idx_nets_template ON nets(template_id)")
        cursor.execute("CREATE INDEX idx_nets_name ON nets(net_name)")
        cursor.execute(
            "CREATE INDEX idx_nets_template_name ON nets(template_id, net_name)"
        )

        self._db_conn.commit()
        cursor.execute("PRAGMA synchronous = NORMAL")

    def _execute_sql_query(self, query: str, params: tuple = ()) -> list:
        if self._is_closed:
            raise RuntimeError("SpiceNetlistQueryService is closed")
        with self._db_lock:
            cursor = self._db_conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def close(self) -> None:
        self._cleanup_database()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _cleanup_database(self) -> None:
        if not hasattr(self, "_db_lock"):
            return
        with self._db_lock:
            if getattr(self, "_is_closed", False):
                return
            try:
                if hasattr(self, "_db_conn") and self._db_conn:
                    self._db_conn.close()
            except Exception:
                pass
            finally:
                self._is_closed = True
            self.net_exists.cache_clear()
            self.find_matches.cache_clear()
            self.resolve_to_canonical_ids.cache_clear()
            self._resolve_canonical_net_name.cache_clear()
            self._resolve_tpl_net_to_top_ids.cache_clear()

    def __del__(self):
        self._cleanup_database()
