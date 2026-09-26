# ENTITY Sovereign Domain — External Clean-Room Interoperability Kit

This kit is for an implementation developed independently of BTG runtime source code.
The implementation may use only the published protocol/SERS, public cryptographic standards, and the vectors in this kit.

## Qualification requirements

1. Do not import, link, copy, translate, or execute BTG canonical runtime modules.
2. Parse and validate every vector in `valid_vectors` as acceptable according to its vector type.
3. Reject every vector in `invalid_vectors` for the security reason represented by that vector.
4. Independently verify a BTG-generated `entity-domain-export-package-v1` package.
5. Generate a fresh compatible domain export using the external implementation.
6. The BTG standalone verifier must validate that externally generated package without modification.
7. Preserve the same Entity-root / Domain-ID binding through export/import round trip.
8. Do not require DNS, BTG hosting, a registrar, blockchain, or a proprietary BTG database for interpretation.
9. Provide source/build hashes, language/toolchain, and an independence attestation.
10. Provide raw execution logs and machine-readable results; screenshots alone are insufficient.

## Submission

Place the external implementation result in `submissions/EXTERNAL_SUBMISSION.json` and its generated export in the same submission directory.
Run `verify_external_submission.py` from the kit directory. A local BTG-generated implementation does not satisfy the independence requirement even if it passes all vectors.
