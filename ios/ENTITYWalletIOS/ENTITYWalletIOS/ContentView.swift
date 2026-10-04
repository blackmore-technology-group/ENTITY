import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @State private var snapshot: WalletSnapshot?
    @State private var showingImporter = false
    @State private var importError: String?

    var body: some View {
        TabView {
            NavigationStack {
                List {
                    Section("Wallet") {
                        LabeledContent("Lineage", value: snapshot?.walletLineage ?? "No snapshot imported")
                        LabeledContent("Issuer namespace", value: snapshot?.issuerNamespace ?? "—")
                        LabeledContent("Market registry", value: snapshot?.marketRegistryVersion ?? "—")
                        LabeledContent("Assets", value: "\(snapshot?.assets.count ?? 0)")
                        LabeledContent("Instruments", value: "\(snapshot?.instruments.count ?? 0)")
                    }

                    Section("Reference build") {
                        LabeledContent("ENTITY runtime", value: "v3.4.3")
                        LabeledContent("Desktop qualification", value: "91/91 PASS")
                        LabeledContent("Issuance policy", value: "Rights-Passport-driven")
                        Text("The reference BTG production snapshot used for qualification resolved 12 current assets to explicit domains: 10 Software Engineering and 2 Robotics.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }

                    Section {
                        Button {
                            showingImporter = true
                        } label: {
                            Label("Import wallet snapshot", systemImage: "square.and.arrow.down")
                        }
                    } footer: {
                        Text("The iOS client imports portable JSON snapshots. It does not silently create identities from device metadata and it does not expand Rights Passport authority.")
                    }

                    Section("Write boundary") {
                        Text("Canonical identity creation, device-bound signing, DCO registration, economic-instrument issuance, listing and order submission remain authoritative ENTITY runtime operations. This iOS simulator build is a portable wallet inspection client, not a replacement authority engine.")
                            .font(.footnote)
                    }
                }
                .navigationTitle("ENTITY Wallet")
            }
            .tabItem { Label("Overview", systemImage: "wallet.pass") }

            NavigationStack {
                Group {
                    if let assets = snapshot?.assets, !assets.isEmpty {
                        List(assets) { asset in
                            NavigationLink {
                                AssetDetail(asset: asset)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(asset.title).font(.headline)
                                    Text(asset.domain).font(.subheadline).foregroundStyle(.secondary)
                                    Text(asset.assetCode ?? asset.objectId)
                                        .font(.caption.monospaced())
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    } else {
                        ContentUnavailableView(
                            "No Assets",
                            systemImage: "shippingbox",
                            description: Text("Import a portable wallet snapshot to inspect DCO assets and domain lineage.")
                        )
                    }
                }
                .navigationTitle("Digital Assets")
            }
            .tabItem { Label("Assets", systemImage: "shippingbox") }

            NavigationStack {
                Group {
                    if let instruments = snapshot?.instruments, !instruments.isEmpty {
                        List(instruments) { instrument in
                            VStack(alignment: .leading, spacing: 5) {
                                Text(instrument.marketIdentifier).font(.headline.monospaced())
                                Text(instrument.rightsClass ?? "Unclassified rights")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                if !instrument.actions.isEmpty {
                                    Text(instrument.actions.joined(separator: " · "))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    } else {
                        ContentUnavailableView(
                            "No Instruments",
                            systemImage: "chart.bar.doc.horizontal",
                            description: Text("A DCO may legitimately have no ticker. Import a wallet snapshot to inspect issued economic instruments.")
                        )
                    }
                }
                .navigationTitle("Instruments")
            }
            .tabItem { Label("Instruments", systemImage: "chart.bar.doc.horizontal") }
        }
        .fileImporter(
            isPresented: $showingImporter,
            allowedContentTypes: [.json],
            allowsMultipleSelection: false
        ) { result in
            do {
                let url = try result.get().first!
                let scoped = url.startAccessingSecurityScopedResource()
                defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                let data = try Data(contentsOf: url)
                snapshot = try JSONDecoder().decode(WalletSnapshot.self, from: data)
            } catch {
                importError = error.localizedDescription
            }
        }
        .alert("Snapshot import failed", isPresented: Binding(
            get: { importError != nil },
            set: { if !$0 { importError = nil } }
        )) {
            Button("OK", role: .cancel) { importError = nil }
        } message: {
            Text(importError ?? "Unknown error")
        }
    }
}

private struct AssetDetail: View {
    let asset: WalletAsset

    var body: some View {
        List {
            Section("Asset") {
                LabeledContent("Title", value: asset.title)
                LabeledContent("Domain", value: asset.domain)
                if let code = asset.assetCode {
                    LabeledContent("Asset code", value: code)
                }
                Text(asset.objectId)
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
            }

            Section("Issuable Rights Passport actions") {
                if asset.rightsActions.isEmpty {
                    Text("No directly issuable ALLOW actions were present in the imported snapshot.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(asset.rightsActions, id: \.self) { action in
                        Label(action, systemImage: "checkmark.shield")
                    }
                }
            } footer: {
                Text("Economic instruments may select only a subset of actions already authorized by the active Rights Passport. The mobile client does not create new authority.")
            }
        }
        .navigationTitle("Asset")
        .navigationBarTitleDisplayMode(.inline)
    }
}
