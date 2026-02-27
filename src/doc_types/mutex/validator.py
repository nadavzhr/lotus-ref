"""
Shared Mutex line validation logic.

Used by:
- LineModel (document viewer — display coloring)
- Session.validate()
- Controller.validate()

Layer 2 (domain) is always run. Layer 3 (netlist) is run only when
an INetlistQueryService is provided.
"""
from typing import Optional, TYPE_CHECKING

from doc_types.mutex.line_data import MutexLineData
from core.validation_result import ValidationResult

if TYPE_CHECKING:
    from core.interfaces import INetlistQueryService


def validate(
    data: MutexLineData,
    nqs: Optional["INetlistQueryService"] = None,
) -> ValidationResult:
    """
    Validate a Mutex line's data.

    Args:
        data: The typed Mutex line data to validate.
        nqs:  Optional netlist query service.

    Returns:
        ValidationResult with errors and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ---- Layer 2: domain (pure, no service) ----

    if not data.mutexed_nets:
        errors.append("No mutexed nets specified.")

    if data.active_nets and data.num_active != len(data.active_nets):
        errors.append(
            f"Number of active nets ({len(data.active_nets)}) "
            f"does not match specified active count ({data.num_active})."
        )

    # Stop here if domain errors exist or no service available
    if errors or nqs is None:
        return ValidationResult(errors=errors, warnings=warnings)

    # ---- Layer 3: netlist (service-dependent warnings) ----

    template = data.template

    # Template existence
    if template is not None and not nqs.template_exists(template):
        warnings.append(
            f"Template '{template}' does not exist in the netlist."
        )
        return ValidationResult(errors=errors, warnings=warnings)

    # Resolve all mutexed nets and count total matches
    all_matched_nets: set[str] = set()
    for net in data.mutexed_nets:
        if data.is_regexp:
            nets, _ = nqs.find_matches(template, net, False, True)
            if not nets:
                warnings.append(
                    f"No matches found for regex pattern '{net}'."
                )
            all_matched_nets.update(nets)
        elif nqs.has_bus_notation(net):
            expanded = nqs.expand_bus_notation(net)
            existing = [n for n in expanded if nqs.net_exists(n, template)]
            if not existing:
                warnings.append(
                    f"Bus pattern '{net}' does not expand to any existing nets."
                )
            if len(existing) < len(expanded):
                warnings.append(
                    f"Bus notation '{net}' is larger than existing nets ({len(existing)}) in the netlist."
                )
            all_matched_nets.update(existing)
        else:
            canonical = nqs.get_canonical_net_name(net, template)
            if canonical:
                all_matched_nets.add(canonical)
                if canonical != net:
                    warnings.append(
                        f"Provided net name '{net}' is not canonical, "
                        f"please use '{canonical}' instead."
                    )
            else:
                warnings.append(
                    f"Mutexed net '{net}' does not exist in the netlist."
                )

    # Not enough matched nets
    if len(all_matched_nets) < 2:
        warnings.append(
            f"At least 2 mutexed nets are required, found {len(all_matched_nets)}."
        )

    if len(all_matched_nets) < data.num_active:
        warnings.append(
            f"Number of matched nets ({len(all_matched_nets)}) "
            f"is less than specified active count ({data.num_active})."
        )

    # Validate active nets
    for net in data.active_nets:
        canonical = nqs.get_canonical_net_name(net, template)
        if not canonical:
            warnings.append(
                f"Active net '{net}' does not exist in the netlist."
            )
        elif canonical != net:
            warnings.append(
                f"Active net '{net}' is not canonical, "
                f"please use '{canonical}' instead."
            )
        # check if its in matched nets, an active net must also be mutexed!
        if canonical and canonical not in all_matched_nets:
            errors.append(
                f"Active net '{net}' is not in the set of mutexed nets."
            )

    return ValidationResult(errors=errors, warnings=warnings)
