"""
Shared AF line validation logic.

Used by:
- LineModel (document viewer — display coloring)
- Session.validate()
- Controller.validate()

Layer 2 (domain) is always run. Layer 3 (netlist) is run only when
an INetlistQueryService is provided.
"""
from typing import Optional, TYPE_CHECKING

from doc_types.af.line_data import AfLineData
from core.validation_result import ValidationResult

if TYPE_CHECKING:
    from core.interfaces import INetlistQueryService


def validate_af(
    data: AfLineData,
    nqs: Optional["INetlistQueryService"] = None,
) -> ValidationResult:
    """
    Validate an AF line's data.

    Args:
        data: The typed AF line data to validate.
        nqs:  Optional netlist query service. When provided, netlist-level
              warnings (template/net existence, canonical names, bus width)
              are appended.

    Returns:
        ValidationResult with errors and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ---- Layer 2: domain (pure, no service) ----

    if not data.net:
        errors.append("Net name cannot be empty.")

    if not (0 <= data.af_value <= 1):
        errors.append("AF value must be between 0 and 1.")

    if not data.is_em_enabled and not data.is_sh_enabled:
        errors.append("At least one of EM or SH must be enabled.")

    # Stop here if domain errors exist or no service available
    if errors or nqs is None:
        return ValidationResult(errors=errors, warnings=warnings)

    # ---- Layer 3: netlist (service-dependent warnings) ----

    if not data.net:
        return ValidationResult(errors=errors, warnings=warnings)

    # Template existence check
    if data.template is not None:
        templates = nqs.get_matching_templates(data.template, data.is_template_regex)
        if not templates:
            msg = (
                f"No matching templates found for pattern '{data.template}'."
                if data.is_template_regex
                else f"Template '{data.template}' does not exist in the netlist."
            )
            warnings.append(msg)
            return ValidationResult(errors=errors, warnings=warnings)
    
    nets, _ = nqs.find_matches(
        data.template, data.net, data.is_template_regex, data.is_net_regex,
    )

    # Net match check
    if not nets:
        warnings.append(f"No matches found for pattern '{data.net}'.")
        return ValidationResult(errors=errors, warnings=warnings)

    # Canonical name suggestion (non-regex, non-bus only)
    if not data.is_net_regex and not nqs.has_bus_notation(data.net):
        canonical = nqs.get_canonical_net_name(data.net, data.template)
        if canonical and canonical != data.net:
            warnings.append(
                f"Provided net name '{data.net}' is not canonical, "
                f"please use '{canonical}' instead."
            )

    # Bus width check (non-regex only)
    if not data.is_net_regex and nqs.has_bus_notation(data.net):
        expanded = nqs.expand_bus_notation(data.net)
        if expanded and len(nets) < len(expanded):
            warnings.append(
                f"Bus notation '{data.net}' is larger than existing nets ({len(nets)}) in the netlist."
            )

    return ValidationResult(errors=errors, warnings=warnings)
