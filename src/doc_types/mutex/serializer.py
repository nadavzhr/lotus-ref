"""
Serializer for Mutex configuration lines.

Converts MutexLineData back to config file text format.
"""
from doc_types.mutex.line_data import MutexLineData, FEVMode


def serialize(data: MutexLineData) -> str:
    """Serialize a MutexLineData into a single config line string."""
    parts = [f"mutex{data.num_active}"]

    # FEV suffix (_low, _high, _ignore, or empty)
    fev_suffix = data.fev.value
    parts.append(f"_{fev_suffix}" if fev_suffix != FEVMode.EMPTY.value else "")

    # Type: template or regexp/regular
    if data.template is not None:
        parts.append(f" template {data.template}")
    else:
        parts.append(f" {'regexp' if data.is_regexp else 'regular'}")

    # Mutexed nets (space-separated)
    parts.append(" " + " ".join(data.mutexed_nets))

    # Active nets (comma-separated with on=)
    if data.active_nets:
        parts.append(f" on={','.join(data.active_nets)}")

    return "".join(parts)
