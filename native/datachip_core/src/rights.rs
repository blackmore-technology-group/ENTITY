use ed25519_dalek::{Signature, VerifyingKey};
use serde_json::{json,Value};
use std::fs::File;
use std::io::Read;
use std::path::Path;

type R<T> = Result<T,String>;
const GRANT_PREFIX:&[u8]=b"ENTITY:EDC:GRANT:v0.2\0";
const REVOCATION_PREFIX:&[u8]=b"ENTITY:EDC:REVOKE:v0.2\0";
const AGE:u64=86400;
const GRANT_LIFETIME:u64=30*86400;

fn field<'a>(v:&'a Value,k:&str) -> R<&'a Value> {
    v.get(k).ok_or_else(||format!("missing {k}"))
}
fn string<'a>(v:&'a Value,k:&str)->R<&'a str> {
    field(v,k)?.as_str().ok_or_else(||format!("invalid {k}"))
}
fn time(v:&Value,k:&str)->R<u64> {
    let n=field(v,k)?.as_u64().ok_or_else(||format!("invalid timestamp {k}"))?;
    if n>4102444800 {return Err(format!("timestamp out of range {k}"))}
    Ok(n)
}
fn id(s:&str)->R<()> {
    if s.is_empty()||s.len()>200||!s.bytes().all(|b|
        b.is_ascii_alphanumeric() || b":_./@-".contains(&b)) {
        return Err("invalid signed identity".into())
    }
    Ok(())
}
fn exact(v:&Value,fields:&[&str])->R<()> {
    let o=v.as_object().ok_or("signed record is not object")?;
    if o.len()!=fields.len()||!fields.iter().all(|x|o.contains_key(*x)){
        return Err("signed record has unexpected fields".into())
    }
    Ok(())
}
fn read(path:&Path)->R<Value> {
    let mut file=File::open(path).map_err(|e|e.to_string())?;
    if file.metadata().map_err(|e|e.to_string())?.len()>4*1024*1024 {
        return Err("signed proof too large".into())
    }
    let mut raw=Vec::new();
    file.read_to_end(&mut raw).map_err(|e|e.to_string())?;
    let v:Value=serde_json::from_slice(&raw).map_err(|e|e.to_string())?;
    // Disk JSON does not need canonical whitespace, but signatures bind the
    // canonical body. Duplicate/odd input members must not be silently accepted.
    if !v.is_object(){return Err("signed proof not an object".into())}
    Ok(v)
}
fn verify_signature<'a>(record:&'a Value,prefix:&[u8],pubhex:&str)->R<&'a Value> {
    exact(record,&["body","signature"])?;
    let body=field(record,"body")?;
    let raw=serde_json::to_vec(body).map_err(|e|e.to_string())?;
    let mut bytes=Vec::with_capacity(prefix.len()+raw.len());
    bytes.extend_from_slice(prefix);
    bytes.extend_from_slice(&raw);
    let pk_bytes=hex::decode(pubhex).map_err(|_|"bad pinned public key")?;
    let pk:[u8;32]=pk_bytes.as_slice().try_into().map_err(|_|"expected pinned 32-byte key")?;
    let key=VerifyingKey::from_bytes(&pk).map_err(|e|e.to_string())?;
    let signature_bytes=hex::decode(string(record,"signature")?).map_err(|_|"bad signature hex")?;
    let signature=Signature::from_slice(&signature_bytes).map_err(|e|e.to_string())?;
    key.verify_strict(&bytes,&signature).map_err(|_|"signature invalid")?;
    Ok(body)
}
fn list(v:&Value,key:&str,cap:usize)->R<Vec<String>> {
    let array=field(v,key)?.as_array().ok_or("invalid revocation list")?;
    if array.len()>cap{return Err("revocation list cap".into())}
    let mut out=Vec::new();
    for value in array {
        let strval=value.as_str().ok_or("invalid revocation item")?;
        id(strval)?;
        out.push(strval.to_string());
    }
    let mut sorted=out.clone();
    sorted.sort();
    sorted.dedup();
    if sorted!=out {return Err("noncanonical revocation records".into())}
    Ok(out)
}

pub struct GrantOptions<'a> {
    pub grant:&'a Path, pub revocations:&'a Path,
    pub rights_kid:&'a str, pub rights_pubkey:&'a str,
    pub revocation_kid:&'a str, pub revocation_pubkey:&'a str,
    pub chip_id:&'a str, pub subject:&'a str, pub audience:&'a str,
    pub now:u64
}
pub fn verify_grant(o:GrantOptions<'_>)->R<Value> {
    id(o.rights_kid)?;
    id(o.revocation_kid)?;
    id(o.chip_id)?;
    id(o.subject)?;
    id(o.audience)?;
    if o.now>4102444800 {return Err("invalid clock".into())}
    let signed=read(o.grant)?;
    let snapshot=read(o.revocations)?;
    let grant=verify_signature(&signed,GRANT_PREFIX,o.rights_pubkey)?;
    let status=verify_signature(&snapshot,REVOCATION_PREFIX,o.revocation_pubkey)?;
    exact(grant,&["schema","authority_key_id","grant_id","chip_id","subject",
                  "audience","action","rights_passport_ref","not_before","expires_at"])?;
    exact(status,&["schema","authority_key_id","issued_at","valid_until",
                   "revoked_grant_ids","revoked_rights_keys","covered_rights_keys"])?;
    if string(grant,"schema")?!="entity-edc-signed-rights-grant-v0.2"
       ||string(status,"schema")?!="entity-edc-signed-revocations-v0.2" {
       return Err("unsupported grants".into())
    }
    let kid=string(grant,"authority_key_id")?;
    let grant_id=string(grant,"grant_id")?;
    let passport=string(grant,"rights_passport_ref")?;
    for item in [kid,grant_id,passport,string(status,"authority_key_id")?] {
        id(item)?;
    }
    if kid!=o.rights_kid ||string(status,"authority_key_id")?!=o.revocation_kid {
        return Err("trusted signer/key binding mismatch".into())
    }
    if string(grant,"chip_id")?!=o.chip_id ||
       string(grant,"subject")?!=o.subject ||
       string(grant,"audience")?!=o.audience ||
       string(grant,"action")?!="dataplane:export" {
        return Err("grant scope/action mismatch".into())
    }
    let begins=time(grant,"not_before")?;
    let ends=time(grant,"expires_at")?;
    if ends<=begins || ends-begins>GRANT_LIFETIME ||
       o.now<begins || o.now>=ends {return Err("grant time invalid".into())}
    let issued=time(status,"issued_at")?;
    let valid_until=time(status,"valid_until")?;
    if valid_until<=issued || valid_until-issued>AGE ||
       o.now<issued || o.now>=valid_until || o.now-issued>AGE {
        return Err("status proof missing/stale".into())
    }
    let covered=list(status,"covered_rights_keys",1024)?;
    let revoked_issuers=list(status,"revoked_rights_keys",1024)?;
    let revoked_grants=list(status,"revoked_grant_ids",4096)?;
    if !covered.iter().any(|k|k==kid) ||
       revoked_issuers.iter().any(|k|k==kid) ||
       revoked_grants.iter().any(|g|g==grant_id) {
        return Err("issuer not covered or delegation revoked".into())
    }
    Ok(json!({"schema":"entity-edc-native-delegation-verification-v0.1",
              "issuer_signature_valid":true,
              "revocation_signature_valid":true,
              "grant_id":grant_id,"chip_id":o.chip_id,
              "subject":o.subject,"audience":o.audience,
              "rights_passport_ref":passport,
              "valid_until":ends.min(valid_until),
              "full_entity_rights_passport_state_verified":false,
              "delegated_claim_verified":true}))
}
