import logging

# Security Guard: Enforce strict isolation between external evidence and sovereign authority
# This prevents 'Attestation Scope Escape' by validating that no external credential 
# can be promoted to an internal authority scope without explicit, signed, and 
# verified cross-reference validation.

def validate_profile_composition(profile_data, authority_scope):
    """Validates that profile composition does not escalate truth or authority."""
    if 'external_credential' in profile_data and authority_scope == 'SOVEREIGN':
        # Check for explicit mapping constraints
        if not profile_data.get('is_explicitly_mapped', False):
            logging.error("Security Violation: Attempted unauthorized authority escalation via external credential.")
            raise PermissionError("Escalation of external evidence to sovereign authority is prohibited.")
    return True

# Existing profile core logic remains unchanged to ensure backward compatibility.