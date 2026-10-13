import Foundation

// EXPERIMENTAL Swift host adapter to signed Rust/C DataChip verification.
// Requires the target platform's signed libentity_datachip_native artifact.
//
// The native verifier never requests camera, GPS, ARKit, Metal, Wallet keys,
// arbitrary code loading, or OS privileges. Publisher/issuer public keys and
// the authenticated user context must come from the native host, not a chip.

@_silgen_name("entity_edc_verify_formula_v1")
private func edcVerifyFormula(
    _ path: UnsafePointer<CChar>?,
    _ jsonResponse: UnsafeMutablePointer<CChar>?,
    _ responseCapacity: Int
) -> Int32

@_silgen_name("entity_edc_verify_delegation_v1")
private func edcVerifyDelegation(
    _ requestJSON: UnsafePointer<CChar>?,
    _ jsonResponse: UnsafeMutablePointer<CChar>?,
    _ responseCapacity: Int
) -> Int32

public enum DataChipNativeError: Error, Equatable {
    case invalidInput
    case insufficientResponseBuffer
    case verificationRejected
    case internalFailure
    case invalidOutput
}

public struct DataChipNativeVerifier {
    private static let responseCapacity = 16_384

    private static func decodeStatus(_ code: Int32) throws {
        switch code {
        case 0: return
        case -1: throw DataChipNativeError.invalidInput
        case -2: throw DataChipNativeError.insufficientResponseBuffer
        case -3: throw DataChipNativeError.verificationRejected
        default: throw DataChipNativeError.internalFailure
        }
    }

    private static func parseResult(_ buffer: [CChar]) throws -> [String: Any] {
        let bytes = buffer.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }
        let decoded = try JSONSerialization.jsonObject(with: Data(bytes))
        guard let result = decoded as? [String: Any] else {
            throw DataChipNativeError.invalidOutput
        }
        return result
    }

    public static func verifyFormula(fileURL: URL) throws -> [String: Any] {
        guard fileURL.isFileURL else { throw DataChipNativeError.invalidInput }
        var buffer = [CChar](repeating: 0, count: responseCapacity)
        let status: Int32 = fileURL.path.withCString { path in
            buffer.withUnsafeMutableBufferPointer { region in
                edcVerifyFormula(path, region.baseAddress, region.count)
            }
        }
        try decodeStatus(status)
        let response = try parseResult(buffer)
        guard response["integrity_verified"] as? Bool == true,
              response["rights_authorized"] as? Bool == false else {
            throw DataChipNativeError.invalidOutput
        }
        return response
    }

    /// The request JSON must be assembled by a separately authenticated
    /// native host with pre-enrolled public keys, trusted principal/app,
    /// secure time and externally controlled grant/status files.
    public static func verifyDelegation(requestJSON: Data) throws -> [String: Any] {
        guard requestJSON.count <= responseCapacity,
              let utf8 = String(data: requestJSON, encoding: .utf8) else {
            throw DataChipNativeError.invalidInput
        }
        var buffer = [CChar](repeating: 0, count: responseCapacity)
        let status: Int32 = utf8.withCString { bytes in
            buffer.withUnsafeMutableBufferPointer { region in
                edcVerifyDelegation(bytes, region.baseAddress, region.count)
            }
        }
        try decodeStatus(status)
        let response = try parseResult(buffer)
        guard response["delegated_claim_verified"] as? Bool == true,
              response["full_entity_rights_passport_state_verified"] as? Bool == false else {
            throw DataChipNativeError.invalidOutput
        }
        return response
    }
}
