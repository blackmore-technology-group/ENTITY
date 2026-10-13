#ifndef ENTITY_DATACHIP_NATIVE_H
#define ENTITY_DATACHIP_NATIVE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Status: 0 success, -1 invalid FFI arguments, -2 insufficient output
 * buffer, -3 content/signature verification failure, -4 internal panic.
 * Outputs are NUL-terminated JSON on success only.
 *
 * Experimental: no issuer root provisioning, wallet authority or
 * OS privilege changes are performed by these functions.
 */
int entity_edc_verify_formula_v1(
    const char *filepath_utf8,
    char *json_response,
    size_t response_capacity);

/* request_json_utf8 must originate from an authenticated host and contain:
 * grant_path, revocation_path, rights_key_id, rights_public_hex,
 * status_key_id, status_public_hex, chip_id,
 * trusted_subject, trusted_audience, now (Unix epoch seconds).
 * Caller MUST pin trust roots separately, enforce secure time, and
 * re-check current ENTITY Rights Passport rules for live deployment.
 */
int entity_edc_verify_delegation_v1(
    const char *request_json_utf8,
    char *json_response,
    size_t response_capacity);

#ifdef __cplusplus
}
#endif
#endif
