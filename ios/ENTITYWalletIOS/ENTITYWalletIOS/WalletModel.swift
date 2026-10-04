import Foundation

struct WalletSnapshot: Decodable {
    let walletLineage: String?
    let issuerNamespace: String?
    let marketRegistryVersion: String?
    let assets: [WalletAsset]
    let instruments: [WalletInstrument]

    enum CodingKeys: String, CodingKey {
        case walletLineage = "wallet_lineage"
        case issuerNamespace = "issuer_namespace"
        case marketRegistryVersion = "market_registry_version"
        case assets
        case instruments
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        walletLineage = try c.decodeIfPresent(String.self, forKey: .walletLineage)
        issuerNamespace = try c.decodeIfPresent(String.self, forKey: .issuerNamespace)
        marketRegistryVersion = try c.decodeIfPresent(String.self, forKey: .marketRegistryVersion)
        assets = (try? c.decode([WalletAsset].self, forKey: .assets)) ?? []
        instruments = (try? c.decode([WalletInstrument].self, forKey: .instruments)) ?? []
    }
}

struct WalletAsset: Decodable, Identifiable {
    let objectId: String
    let title: String
    let assetCode: String?
    let domain: String
    let rightsActions: [String]

    var id: String { objectId }

    enum CodingKeys: String, CodingKey {
        case objectId = "object_id"
        case title
        case assetCode = "asset_code"
        case domain
        case rightsActions = "rights_actions"
        case lineage
        case rightsPassport = "rights_passport"
    }

    private struct Lineage: Decodable {
        let protocolLineage: ProtocolLineage?
        enum CodingKeys: String, CodingKey { case protocolLineage = "protocol_lineage" }
    }

    private struct ProtocolLineage: Decodable {
        let primaryDomainProfile: String?
        enum CodingKeys: String, CodingKey { case primaryDomainProfile = "primary_domain_profile" }
    }

    private struct RightsPassport: Decodable {
        let rights: [RightRule]?
    }

    private struct RightRule: Decodable {
        let effect: String?
        let actions: [String]?
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        objectId = (try? c.decode(String.self, forKey: .objectId)) ?? UUID().uuidString
        title = (try? c.decode(String.self, forKey: .title)) ?? objectId
        assetCode = try? c.decodeIfPresent(String.self, forKey: .assetCode)
        let directDomain = (try? c.decodeIfPresent(String.self, forKey: .domain)) ?? nil
        let lineage = (try? c.decodeIfPresent(Lineage.self, forKey: .lineage)) ?? nil
        domain = directDomain ?? lineage?.protocolLineage?.primaryDomainProfile ?? "Unspecified"

        if let direct = (try? c.decodeIfPresent([String].self, forKey: .rightsActions)) ?? nil {
            rightsActions = direct.sorted()
        } else if let passport = (try? c.decodeIfPresent(RightsPassport.self, forKey: .rightsPassport)) ?? nil,
                  let rules = passport.rights {
            rightsActions = rules
                .filter { ($0.effect ?? "").uppercased() == "ALLOW" }
                .flatMap { $0.actions ?? [] }
                .reduce(into: Set<String>()) { $0.insert($1) }
                .sorted()
        } else {
            rightsActions = []
        }
    }
}

struct WalletInstrument: Decodable, Identifiable {
    let instrumentId: String
    let marketIdentifier: String
    let rightsClass: String?
    let actions: [String]

    var id: String { instrumentId }

    enum CodingKeys: String, CodingKey {
        case instrumentId = "instrument_id"
        case marketIdentifier = "market_identifier"
        case displaySymbol = "display_symbol"
        case rightsClass = "rights_class"
        case actions
        case rights
    }

    private struct Rights: Decodable {
        let actions: [String]?
        let rightsClass: String?
        let marketIdentifier: String?

        enum CodingKeys: String, CodingKey {
            case actions
            case rightsClass = "rights_class"
            case marketIdentifier = "market_identifier"
        }
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        instrumentId = (try? c.decode(String.self, forKey: .instrumentId)) ?? UUID().uuidString
        let rights = (try? c.decodeIfPresent(Rights.self, forKey: .rights)) ?? nil
        let symbol = (try? c.decodeIfPresent(String.self, forKey: .displaySymbol)) ?? nil
        marketIdentifier =
            ((try? c.decodeIfPresent(String.self, forKey: .marketIdentifier)) ?? nil) ??
            rights?.marketIdentifier ??
            symbol ??
            "NO TICKER"
        rightsClass =
            ((try? c.decodeIfPresent(String.self, forKey: .rightsClass)) ?? nil) ??
            rights?.rightsClass
        actions =
            ((try? c.decodeIfPresent([String].self, forKey: .actions)) ?? nil) ??
            rights?.actions ??
            []
    }
}
