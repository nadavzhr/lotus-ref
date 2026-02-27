import re
import sqlite3
from threading import RLock
from functools import lru_cache
from typing import Optional, TYPE_CHECKING
import logging
from pathlib import Path

if TYPE_CHECKING:
    from .netlist_parser.Netlist import Netlist
    from .netlist_parser.NetlistBuilder import NetlistBuilder

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        # Configure logger with a simple console handler if not already configured
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

logger = get_logger(__name__)

class NetlistQueryService:
    """
    Service for querying netlist templates and nets with regex and bus notation support.
    Supports efficient exact and completion queries using an in-memory SQLite database.
    """

    BUS_PATTERN = re.compile(r'\[(\d+)[:-](\d+)\]')
    INDEX_PATTERN = re.compile(r'\[(\d+)\]')  # Matches individual indices like [0], [1], etc.
    MAX_BUS_EXPANSION = 10000
    SQLITE_MAX_VARS_PER_QUERY = 900

    def __init__(self, cell: str, spice_file: 'Path', netlist: 'NetlistBuilder'):
        """
        Initialize the NetlistQueryService.

        Loads the spice file and builds netlist data structures for pattern matching.

        Args:
            cell: Name of the cell to load from the spice file
            spice_file: Path to the spice file
            netlist: Builder for working with netlist data

        Raises:
            FileNotFoundError: If the spice file cannot be found
            RuntimeError: If any other error occurs during initialization
        """
        logger.info("Initializing NetlistQueryService")

        # Initialize lifecycle controls early so cleanup/destructor are safe
        # even if initialization fails part-way through.
        self._db_lock = RLock()
        self._is_closed = False

        try:
            logger.info(f"Loading spice file for cell '{cell}': {spice_file}")
            self._netlist = netlist.read_spice_file(cell, str(spice_file))
            logger.info(f"Successfully loaded netlist for cell: {cell}")
        except FileNotFoundError as e:
            logger.critical(f"Spice file not found: {e.filename}")
            raise FileNotFoundError(f"Spice file not found: {e.filename}.") from e
        except Exception as e:
            logger.critical(f"Error loading netlist: {e}", exc_info=True)
            raise RuntimeError(f"Error loading netlist: {e}") from e

        self._top_cell = self._netlist.get_top_cell().get_name().lower()
        logger.debug(f"Top cell identified: {self._top_cell}")

        self._all_templates: set[str] = set(
                        [t.get_name().lower() for t in self._netlist.get_templates()]
        )
        logger.debug(f"Total templates loaded: {len(self._all_templates)}")

        # Keep canonical net names in memory for fast SQL-backed lookups.
        self._all_nets_in_templates = self._build_canonical_net_map()
        logger.debug("Finished building in-memory netlist structures")
        
        # Initialize SQLite database for efficient large querying
        logger.debug("Initializing SQLite database for netlist queries")
        self._init_database()

        # Canonical net ID infrastructure for conflict detection
        self._build_canonical_id_table()
        logger.debug("Finished initializing NetlistQueryService")


###########################################################################
############################ PUBLIC METHODS ###############################
###########################################################################
    
    def get_top_cell(self) -> str:
        """
        Get the name of the top cell in the netlist.

        Returns:
            str: Name of the top cell
        """
        return self._top_cell

    def get_all_templates(self) -> set[str]:
        """
        Get all available templates in the netlist.

        Returns:
            set: Set of all template names in the loaded netlist
        """
        return self._all_templates.copy()
    
    def get_matching_templates(self, template_pattern: str, is_regex: bool) -> set[str]:
        """
        Get matching templates for a given pattern.
        
        Args:
            template_pattern: The template name or regex pattern to match
            is_regex: Whether the template_pattern is a regex
        Returns:
            set: Set of matching template names
        """
        if not template_pattern:
            return set()

        normalized_pattern = template_pattern if is_regex else template_pattern.lower()
        return set(self._get_matching_templates(normalized_pattern, is_regex))

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a specific template exists in the netlist.

        Args:
            template_name (str): Name of the template to check
        Returns:
            bool: True if the template exists, False otherwise
        """
        normalized_template = self._normalize_template_name(template_name)
        return normalized_template is not None

    def get_all_nets_in_template(self, template: Optional[str] = None) -> set[str]:
        """
        Get all nets in a specific template.

        Args:
            template (Optional[str]): Name of the template to retrieve nets for.
                If None or empty, top cell is used.

        Returns:
            set: Set of net names in the template or empty set if template not found
        """
        normalized_template = self._normalize_template_name(template)
        if normalized_template is None:
            return set()
        return self._all_nets_in_templates.get(normalized_template, set())

    @lru_cache(maxsize=256)
    def net_exists(self, net_name: str, template_name: Optional[str] = None) -> bool:
        """
        Check if a specific net exists in the netlist, optionally within a given template.

        Args:
            net_name (str): Name of the net to check
            template_name (Optional[str]): Name of the template to check within, or None for top cell
        Returns:
            bool: True if the net exists, False otherwise
        """
        normalized_template = self._normalize_template_name(template_name)
        if normalized_template is None:
            return False

        return self._resolve_canonical_net_name(normalized_template, net_name.lower()) is not None

    def get_canonical_net_name(self, net_name: str, template_name: Optional[str] = None) -> Optional[str]:
        """
        Get the canonical net name for a given net name and template.

        Args:
            net_name (str): The net name to resolve
            template_name (Optional[str]): The template name to look within (None for top cell)

        Returns:
            Optional[str]: The canonical net name if found, otherwise None
        """
        normalized_template = self._normalize_template_name(template_name)
        if normalized_template is None:
            return None

        return self._resolve_canonical_net_name(normalized_template, net_name.lower())

    @lru_cache(maxsize=256)
    def find_matches(self, template_name: Optional[str], net_name: str,
                     template_regex: bool, net_regex: bool) -> tuple[list[str], list[str]]:
        """
        Find matches for a template and net pattern in the netlist.

        Uses regular expressions if specified to match templates and nets.
        Supports bus notation (e.g., net[1-3]) when regex is disabled.
        Results are cached using lru_cache for performance.

        Args:
            template_name (Optional[str]): Name or pattern of the template to match, can be None
            net_name (str): Name or pattern of the net to match, required
            template_regex (bool): Whether template_name should be treated as a regex pattern
            net_regex (bool): Whether net_name should be treated as a regex pattern

        Returns:
            tuple: (net_matches, template_matches) where:
                                - net_matches (list): list of matching canonical nets in "template:net" format
                - template_matches (list): list of templates that have matching nets
                  (subset of templates matching template_name if regex, otherwise just the specified template)
        """
        if not net_name:
            return [], []


        template_name = template_name or self._top_cell

        # Only lowercase if not regex - regex patterns may be case-sensitive
        template_name = template_name.lower() if not template_regex else template_name
        net_name = net_name.lower() if not net_regex else net_name

        matching_templates = self._get_matching_templates(template_name, template_regex)
        if not matching_templates:
            return [], []

        matching_nets = set(self._get_matching_nets(matching_templates, net_name, net_regex))

        # As of now - only add alias matches for non-regex patterns without bus notation
        # Regex/Bus add significant undefined complexity, therefore we currently do not support them
        if not net_regex and not self.has_bus_notation(net_name):
            matching_nets.update(self._get_matching_alias_nets(matching_templates, net_name))

        matching_nets = sorted(matching_nets)

        # Extract templates that actually have matching nets for the template matches list
        matching_templates = sorted(set(
            net.split(':')[0] if ':' in net else self._top_cell
            for net in matching_nets
        ))

        return matching_nets, matching_templates

    @lru_cache(maxsize=256)
    def find_net_instance_names(self, template: str, net_name: str) -> set[str]:
        """Find all instance names for a specific net in a template.
        
        Args:
            template: Template name
            net_name: Exact net name to find instances for
            
        Returns:
            Set of instance names of the specified net
        """
        normalized_template = self._normalize_template_name(template)
        if normalized_template is None:
            return set()

        canonical_name = self._resolve_canonical_net_name(normalized_template, net_name.lower())
        if canonical_name is None:
            return set()

        return set(self._netlist.get_net_instance_names(normalized_template, canonical_name))

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

###########################################################################
############################ STATIC METHODS ##############################
###########################################################################

    @staticmethod
    def normalize_net_for_template(name: str, template: Optional[str]) -> str:
        """
        Normalize a template-qualified net name for use with a specific template.

        Strips a leading 'template:' prefix when it matches the given template,
        so the bare net name can be used for queries. Only the first colon is
        considered — colons inside bus notation (e.g. net[0:2]) are preserved.

        This is the inverse of ``_format_single_net_result``.
        """
        if template and ':' in name:
            prefix = f"{template}:"
            if name.lower().startswith(prefix.lower()):
                return name[len(prefix):]
        return name

    @staticmethod
    def has_bus_notation(net_name: str) -> bool:
        """
        Check if net name contains bus notation.
        """
        return bool(NetlistQueryService.BUS_PATTERN.search(net_name))

    @staticmethod
    def expand_bus_notation(pattern: str, max_expansions: Optional[int] = None) -> list[str]:
        """
        Expand a bus notation pattern into a list of all possible concrete names.
                
        Examples:
            "mynet[1:3]" -> ["mynet[1]", "mynet[2]", "mynet[3]"]
            "my[1:2]net[3:4]" -> ["my[1]net[3]", "my[1]net[4]", "my[2]net[3]", "my[2]net[4]"]
        
        Args:
            pattern (str): The pattern with bus notation [start:end]
            max_expansions (Optional[int]): Optional hard limit for generated nets.
            
        Returns:
            list: All expanded concrete names
        """
        if max_expansions is not None and max_expansions <= 0:
            return []

        count = [0]

        def _expand(current_pattern: str) -> list[str]:
            if not current_pattern or not NetlistQueryService.has_bus_notation(current_pattern):
                if max_expansions is not None:
                    count[0] += 1
                    if count[0] > max_expansions:
                        raise ValueError(
                            f"Bus expansion exceeded limit ({max_expansions}) for pattern '{pattern}'"
                        )
                return [current_pattern]

            match = NetlistQueryService.BUS_PATTERN.search(current_pattern)
            if not match:
                return [current_pattern]

            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                start, end = end, start

            prefix = current_pattern[:match.start()]
            suffix = current_pattern[match.end():]
            expanded_values = []

            for i in range(start, end + 1):
                expanded_values.extend(_expand(f"{prefix}[{i}]{suffix}"))

            return expanded_values

        if not pattern or not NetlistQueryService.has_bus_notation(pattern):
            return [pattern]

        return _expand(pattern)

    def collapse_bus_notation(self, net_names: list[str]) -> Optional[str]:
        """
        Collapse a list of net names with bus notation into a compact representation.
        Examples:
            ["mynet[1]", "mynet[2]", "mynet[3]"] -> "mynet[1:3]"
            ["my[1]net[3]", "my[1]net[4]", "my[2]net[3]", "my[2]net[4]"] -> "my[1:2]net[3:4]"
            ["mynet"] -> "mynet"
        """
        if not net_names:
            return None

        normalized_names = [name.lower() for name in net_names]
        if len(normalized_names) == 1:
            return normalized_names[0]

        # Extract numeric indices and a structural template
        index_lists = []
        template = None

        for name in normalized_names:
            # Try to extract indices from both [num:num] and [num] patterns
            bus_indices = self.BUS_PATTERN.findall(name)  # Returns list of (start, end) tuples
            if bus_indices:
                # Flatten the bus notation ranges into individual indices
                indices = [int(idx) for pair in bus_indices for idx in pair]
            else:
                # Try individual index pattern [num]
                indices = [int(x) for x in self.INDEX_PATTERN.findall(name)]
            
            index_lists.append(indices)

            # Replace indices with placeholders to get structure
            # First replace bus patterns, then individual indices
            structure = self.BUS_PATTERN.sub("[]", name)
            structure = self.INDEX_PATTERN.sub("[]", structure)
            
            if template is None:
                template = structure
            elif template != structure:
                # Different structures → cannot collapse safely
                return None

        if not index_lists or not index_lists[0]:
            unique_names = set(normalized_names)
            return next(iter(unique_names)) if len(unique_names) == 1 else None

        expected_dimensions = len(index_lists[0])
        if any(len(indices) != expected_dimensions for indices in index_lists):
            return None

        # Transpose indices by dimension
        dimensions = list(zip(*index_lists))

        # Build collapsed ranges
        collapsed_dims = []
        for dim in dimensions:
            values = sorted(set(dim))
            if values == list(range(min(values), max(values) + 1)):
                # Use single index notation if start and end are the same
                if values[0] == values[-1]:
                    collapsed_dims.append(f"[{values[0]}]")
                else:
                    collapsed_dims.append(f"[{values[0]}:{values[-1]}]")
            else:
                # Non-contiguous → cannot collapse
                return None

        # Ensure full Cartesian coverage to avoid false-positive collapse
        expected_count = 1
        for dim in dimensions:
            expected_count *= len(set(dim))
        if expected_count != len(set(normalized_names)):
            return None

        # Reconstruct name
        result = template
        for dim in collapsed_dims:
            result = result.replace("[]", dim, 1)

        return result

###########################################################################
############################ PRIVATE METHODS ##############################
###########################################################################

    def _get_matching_templates(self, template_name: str, template_regex: bool) -> list[str]:
        """
        Get list of templates that match the given pattern.
        """
        if not template_regex:
            results = self._execute_sql_query(
                'SELECT name FROM templates WHERE name = ? LIMIT 1',
                (template_name,)
            )
            return [results[0][0]] if results else []

        try:
            results = self._execute_sql_query(
                'SELECT name FROM templates WHERE name REGEXP ?',
                (template_name,)
            )
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error matching template pattern '{template_name}': {e}")
            return []

    def _get_matching_nets(self, templates: list[str], net_name: str, net_regex: bool) -> list[str]:
        """
        Get all matching nets across the given templates using a single SQL query.
        """
        if isinstance(templates, str):
            templates = [templates]
        if not templates:
            return []

        if not net_name:
            return []

        net_name = net_name.lower() if not net_regex else net_name

        if net_regex:
            return self._match_nets_regex(templates, net_name)
        elif self.has_bus_notation(net_name):
            return self._match_nets_bus(templates, net_name)
        else:
            return self._match_nets_exact(templates, net_name)

    def _match_nets_regex(self, templates: list[str], net_name: str) -> list[str]:
        """
        Match nets by regex pattern across all given templates in a single SQL query.
        """
        if not templates:
            return []
        placeholders = ','.join('?' * len(templates))
        try:
            results = self._execute_sql_query(
                f'''
                SELECT t.name, n.net_name
                FROM nets n
                JOIN templates t ON n.template_id = t.id
                WHERE t.name IN ({placeholders}) AND n.net_name REGEXP ?
                ''',
                (*templates, net_name)
            )
        except Exception as e:
            logger.error(f"Error matching net regex pattern '{net_name}': {e}")
            return []
        return self._format_net_results(results)

    def _match_nets_bus(self, templates: list[str], net_name: str) -> list[str]:
        """
        Match nets by bus notation across all given templates in a single SQL query.
        """
        if not templates:
            return []

        try:
            expanded = NetlistQueryService.expand_bus_notation(
                net_name,
                max_expansions=self.MAX_BUS_EXPANSION
            )
        except ValueError as e:
            logger.warning(str(e))
            return []

        if not expanded:
            return []

        t_placeholders = ','.join('?' * len(templates))
        available_for_nets = max(1, self.SQLITE_MAX_VARS_PER_QUERY - len(templates))
        results = []
        for start in range(0, len(expanded), available_for_nets):
            net_chunk = expanded[start:start + available_for_nets]
            n_placeholders = ','.join('?' * len(net_chunk))
            chunk_results = self._execute_sql_query(
                f'''
                SELECT t.name, n.net_name
                FROM nets n
                JOIN templates t ON n.template_id = t.id
                WHERE t.name IN ({t_placeholders}) AND n.net_name IN ({n_placeholders})
                ''',
                (*templates, *net_chunk)
            )
            results.extend(chunk_results)

        return self._format_net_results(results)

    def _match_nets_exact(self, templates: list[str], net_name: str) -> list[str]:
        """
        Match nets by exact name across all given templates in a single SQL query.
        """
        if not templates:
            return []
        placeholders = ','.join('?' * len(templates))
        results = self._execute_sql_query(
            f'''
            SELECT t.name, n.net_name
            FROM nets n
            JOIN templates t ON n.template_id = t.id
            WHERE t.name IN ({placeholders}) AND n.net_name = ?
            ''',
            (*templates, net_name)
        )
        return self._format_net_results(results)

    def _normalize_template_name(self, template_name: Optional[str]) -> Optional[str]:
        if template_name is None or template_name.strip() == '':
            return self._top_cell

        normalized = template_name.strip().lower()
        return normalized if normalized in self._all_templates else None

    @lru_cache(maxsize=4096)
    def _resolve_canonical_net_name(self, template_name: str, net_name: str) -> Optional[str]:
        if not net_name:
            return None

        try:
            _, canonical_name = self._netlist.get_canonical_net_name(
                net_name=net_name,
                template_name=template_name,
                lower=True,
            )
        except Exception as e:
            logger.debug(
                "Failed canonical resolution for net '%s' in template '%s': %s",
                net_name,
                template_name,
                e,
            )
            return None

        return canonical_name.lower() if canonical_name is not None else None

    def _get_matching_alias_nets(self, templates: list[str], net_name: str) -> set[str]:
        if not templates or not net_name:
            return set()

        matched_canonical_nets: set[str] = set()

        for template in templates:
            canonical_name = self._resolve_canonical_net_name(template, net_name)
            if canonical_name is not None:
                matched_canonical_nets.add(self._format_single_net_result(template, canonical_name))

        return matched_canonical_nets

    def _build_canonical_net_map(self) -> dict[str, set[str]]:
        canonical_nets_in_templates: dict[str, set[str]] = {}

        for template in self._all_templates:
            canonical_nets_in_templates[template] = {
                canonical_name.lower()
                for _, canonical_name in self._netlist.get_all_nets(template)
            }

        return canonical_nets_in_templates

    def _format_single_net_result(self, template_name: str, net_name: str) -> str:
        return net_name if template_name == self._top_cell else f'{template_name}:{net_name}'

    def _format_net_results(self, results) -> list[str]:
        """
        Format SQL results (template_name, net_name) into 'template:net' strings.
        Nets belonging to the top cell are returned without a prefix.
        """
        return [
            self._format_single_net_result(row[0], row[1])
            for row in results
        ]

###########################################################################
#################### CANONICAL NET ID — CONFLICT DETECTION ################
###########################################################################

    def _build_canonical_id_table(self) -> None:
        """Assign integer IDs to all top-cell canonical nets."""
        top_canonical = sorted(self._all_nets_in_templates.get(self._top_cell, set()))
        self._net_id_map: dict[str, int] = {
            name: i for i, name in enumerate(top_canonical)
        }
        self._id_net_map: dict[int, str] = dict(enumerate(top_canonical))
        logger.debug(
            "Canonical net ID table: %d top-cell nets", len(self._net_id_map),
        )

    @lru_cache(maxsize=8192)
    def _resolve_tpl_net_to_top_ids(self, tpl: str, net: str) -> frozenset[int]:
        """
        Compute the top-cell canonical net IDs for a single
        (template, canonical_net_within_template) pair.

        Uses find_net_instance_names (which delegates to the netlist
        library) to resolve through the hierarchy, then maps names to
        integer IDs.

        Results are cached so repeated lookups are free.
        """
        names = self.find_net_instance_names(tpl, net)
        return frozenset(
            self._net_id_map[n] for n in names if n in self._net_id_map
        )

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
                expanded = NetlistQueryService.expand_bus_notation(
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

###########################################################################
############################ SQLITE DATABASE ##############################
###########################################################################

    def _init_database(self) -> None:
        """Initialize in-memory SQLite database with netlist data.
        
        Creates an in-memory database for efficient net completion queries.
        The database includes tables with proper indexes for fast searching.
        The database is cleaned up when this service is closed.
        
        Performance optimizations applied:
        - In-memory database (much faster than file-based for this use case)
        - Disabled journaling during bulk insert
        - Batch inserts with executemany
        - Indexes created AFTER data insertion (faster for bulk loads)
        """
        # Use in-memory database for maximum speed (data is rebuilt each session anyway)
        self._db_path = ':memory:'
        self._db_conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._db_conn.row_factory = sqlite3.Row
        def _regexp(expr, item):
            if item is None:
                return 0
            try:
                return 1 if re.search(expr, item, re.IGNORECASE) else 0
            except re.error:
                return 0  # Invalid regex patterns do not match anything
        self._db_conn.create_function("REGEXP", 2, _regexp)
        cursor = self._db_conn.cursor()
        
        # Performance pragmas for bulk insert
        cursor.execute('PRAGMA synchronous = OFF')
        cursor.execute('PRAGMA journal_mode = OFF')
        cursor.execute('PRAGMA cache_size = 100000')  # Larger cache for bulk operations
        cursor.execute('PRAGMA temp_store = MEMORY')
        
        # Create templates table (no indexes yet - add after data)
        cursor.execute('''
            CREATE TABLE templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Create nets table with foreign key to templates (no indexes yet)
        cursor.execute('''
            CREATE TABLE nets (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                net_name TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        ''')
        
        # Populate the database - prepare all data first
        sorted_templates = sorted(self._all_templates)
        templates_data = [(i, template) for i, template in enumerate(sorted_templates)]
        template_id_map = {template: i for i, template in enumerate(sorted_templates)}
        
        # Batch insert templates
        cursor.executemany('INSERT INTO templates (id, name) VALUES (?, ?)', templates_data)
        
        # Prepare all nets data at once
        nets_data = []
        for template, nets in self._all_nets_in_templates.items():
            template_id = template_id_map[template]
            nets_data.extend((template_id, net) for net in nets)
        
        # Batch insert all nets
        cursor.executemany('INSERT INTO nets (template_id, net_name) VALUES (?, ?)', nets_data)
        
        # Create indexes AFTER data insertion (much faster for bulk loads)
        cursor.execute('CREATE INDEX idx_template_name ON templates(name)')
        cursor.execute('CREATE INDEX idx_nets_template ON nets(template_id)')
        cursor.execute('CREATE INDEX idx_nets_name ON nets(net_name)')
        cursor.execute('CREATE INDEX idx_nets_template_name ON nets(template_id, net_name)')
        
        self._db_conn.commit()
        
        # Reset pragmas to safer defaults for runtime queries
        cursor.execute('PRAGMA synchronous = NORMAL')
    
    def _execute_sql_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SQL query and return all results.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            List of result rows
        """
        if self._is_closed:
            raise RuntimeError("NetlistQueryService is closed")

        with self._db_lock:
            cursor = self._db_conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def close(self) -> None:
        """Explicitly close DB resources for this service instance."""
        self._cleanup_database()

    def __enter__(self):
        """Allow usage as a context-managed service."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close DB resources when leaving context-manager scope."""
        self.close()
    
    def _cleanup_database(self) -> None:
        """Cleanup database connection."""
        if not hasattr(self, '_db_lock'):
            return

        with self._db_lock:
            if getattr(self, '_is_closed', False):
                return

            try:
                if hasattr(self, '_db_conn') and self._db_conn:
                    self._db_conn.close()
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self._is_closed = True

            self.net_exists.cache_clear()
            self.find_matches.cache_clear()
            self.find_net_instance_names.cache_clear()
            self.resolve_to_canonical_ids.cache_clear()
            self._resolve_canonical_net_name.cache_clear()
            self._resolve_tpl_net_to_top_ids.cache_clear()
    
    def __del__(self):
        """Close database connection on cleanup."""
        self._cleanup_database()
