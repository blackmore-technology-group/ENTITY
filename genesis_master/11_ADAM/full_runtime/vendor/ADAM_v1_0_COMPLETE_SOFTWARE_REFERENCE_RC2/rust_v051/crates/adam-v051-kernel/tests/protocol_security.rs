use adam_v051_kernel::{
    ApplicationManifest, AuthorityAtom, FileEd25519Signer, InferenceAuthorizationRequest,
    NoveltyClosureEnvelope, QuorumCertificate, SignatureProvider, SignedVote,
    SignedWitnessStatement, VoteStatement, WitnessChain, WitnessStatement,
};
use serde_json::json;
use std::collections::BTreeMap;
use tempfile::tempdir;

fn root(seed: char) -> String {
    seed.to_string().repeat(64)
}

#[test]
fn atom_identity_and_protocol_bounds_are_enforced() {
    let mut atom = AuthorityAtom {
        atom_id: String::new(),
        atom_type: "PROJECT".into(),
        value: json!({"name": "P204"}),
        authority: "OPS".into(),
        provenance: vec![root('a')],
        security_scope: "PRIVATE".into(),
        chemistry_version: "v51.1".into(),
    };
    atom.atom_id = atom.calculated_id().unwrap();
    atom.validate().unwrap();
    atom.value = json!({"name": "P205"});
    assert!(atom.validate().is_err());

    let manifest = ApplicationManifest {
        format: "ADAM-v0.51-application-manifest".into(),
        version: 1,
        application_id: "OPERATIONS_ONE".into(),
        identity_namespace: "O1".into(),
        observable_entity_types: vec!["EQUIPMENT".into(), "PROJECT".into()],
        permitted_reactions: vec!["ASSIGN_EQUIPMENT".into()],
        constructible_representations: vec!["JSON".into(), "SQL_VIEW".into()],
        evidence_types: vec!["APPLICATION_EVENT".into()],
        authority_scope: "OPS".into(),
        security_scope: "PRIVATE".into(),
        maximum_event_bytes: 1024,
    };
    manifest.validate().unwrap();

    let authorization = InferenceAuthorizationRequest {
        format: "ADAM-v0.51-inference-authorization".into(),
        version: 1,
        actor: "SHAWN".into(),
        purpose: "OPERATIONS".into(),
        requested_roots: vec![root('1')],
        dependency_closure: vec![root('1'), root('2')],
        capabilities: vec!["READ_PROJECT".into()],
        issued_at: 1,
        expires_at: 2,
    };
    authorization.validate().unwrap();

    let closure = NoveltyClosureEnvelope {
        format: "ADAM-v0.51-novelty-closure".into(),
        version: 1,
        source_universe_root: root('1'),
        destination_prior_root: root('2'),
        destination_result_root: root('3'),
        dictionary_root: root('4'),
        epoch: 1,
        atom_ids: vec![root('5')],
        bond_ids: vec![root('6')],
        compound_ids: vec![root('7')],
        recipe_ids: vec![root('8')],
        metadata: BTreeMap::new(),
    };
    closure.validate().unwrap();
}

#[test]
fn quorum_and_witness_evidence_is_membership_bound() {
    let directory = tempdir().unwrap();
    let signer_a = FileEd25519Signer::load_or_create(directory.path().join("a.key")).unwrap();
    let signer_b = FileEd25519Signer::load_or_create(directory.path().join("b.key")).unwrap();
    let signer_c = FileEd25519Signer::load_or_create(directory.path().join("c.key")).unwrap();
    let previous_root = root('a');
    let next_root = root('b');
    let reaction_id = root('c');
    let signers = [("A", &signer_a), ("B", &signer_b), ("C", &signer_c)];
    let mut membership = BTreeMap::new();
    let mut votes = Vec::new();
    for (node_id, signer) in signers {
        membership.insert(node_id.to_owned(), signer.key_id());
        if node_id != "C" {
            let statement = VoteStatement {
                format: "ADAM-v0.51-authority-vote".into(),
                version: 1,
                node_id: node_id.into(),
                epoch: 1,
                sequence: 1,
                previous_root: previous_root.clone(),
                root: next_root.clone(),
                reaction_id: reaction_id.clone(),
            };
            votes.push(SignedVote {
                signature: signer.sign(&serde_json::to_vec(&statement).unwrap()).unwrap(),
                statement,
            });
        }
    }
    let certificate = QuorumCertificate {
        format: "ADAM-v0.51-quorum-certificate".into(),
        version: 1,
        epoch: 1,
        sequence: 1,
        previous_root,
        root: next_root.clone(),
        reaction_id,
        membership,
        quorum: 2,
        votes,
    };
    certificate.verify().unwrap();
    let mut forged = certificate.clone();
    forged.votes[0].statement.root = root('d');
    assert!(forged.verify().is_err());

    let statement = WitnessStatement {
        format: "ADAM-v0.51-witness-statement".into(),
        version: 1,
        witness_id: "A".into(),
        sequence: 1,
        root: next_root,
        previous_statement_id: None,
    };
    let signed = SignedWitnessStatement {
        signature: signer_a.sign(&serde_json::to_vec(&statement).unwrap()).unwrap(),
        statement,
    };
    let chain = WitnessChain {
        format: "ADAM-v0.51-witness-chain".into(),
        version: 1,
        membership: BTreeMap::from([("A".into(), signer_a.key_id())]),
        statements: vec![signed],
    };
    assert!(chain.verify().unwrap().is_some());
}
