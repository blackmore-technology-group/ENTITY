//! C ABI for Swift, Windows and NDK host adapters.
//! Caller selects trusted paths, identity, public keys and clock independently.
//! FFI verification output is evidence, never an automatically granted OS right.
use crate::{formula, rights};
use crate::rights::GrantOptions;
use serde_json::{json, Value};
use std::ffi::{CStr, c_char};
use std::path::Path;
use std::panic::{catch_unwind,AssertUnwindSafe};

type R<T> = Result<T,String>;
const MAX_INPUT:usize=16384;
const MAX_OUTPUT:usize=16384;

fn cstr(ptr:*const c_char)->R<String> {
    if ptr.is_null(){return Err("null input".into())}
    // SAFETY: As with any C ABI, caller must pass valid NUL-terminated memory.
    let slice=unsafe { CStr::from_ptr(ptr) };
    let data=slice.to_bytes();
    if data.len()>MAX_INPUT {return Err("C input too large".into())}
    String::from_utf8(data.to_vec()).map_err(|_|"invalid UTF-8 input".into())
}
fn output(out:*mut c_char,capacity:usize,response:Value)->i32{
    if out.is_null() || capacity==0 || capacity>MAX_OUTPUT {return -1}
    let raw=match serde_json::to_vec(&response){Ok(v)=>v,Err(_)=>return -3};
    if raw.len()+1>capacity {return -2}
    // SAFETY: Caller owns writable buffer of at least 'capacity' bytes.
    unsafe {
        std::ptr::copy_nonoverlapping(raw.as_ptr(),out.cast::<u8>(),raw.len());
        *out.add(raw.len())=0;
    }
    0
}

fn invoke<F:FnOnce()->R<Value>>(out:*mut c_char,cap:usize,callback:F)->i32 {
    match catch_unwind(AssertUnwindSafe(callback)){
        Ok(Ok(value))=>output(out,cap,value),
        Ok(Err(_))=>-3, // do not expose sensitive path/key details across ABI
        Err(_)=>-4
    }
}

/// Returns 0 on validated integrity, -1 bad args, -2 small output buffer,
/// -3 verification failed, -4 unexpected panic. No plaintext export or code.
#[no_mangle]
pub extern "C" fn entity_edc_verify_formula_v1(
    filepath:*const c_char,
    response:*mut c_char,
    response_capacity:usize,
)->i32 {
    invoke(response,response_capacity,|| {
        let path=cstr(filepath)?;
        formula::verify_file(Path::new(&path))
    })
}

/// Request JSON must be authored by an independently authenticated native host.
/// Contains keys grant_path, revocation_path, rights_key_id, rights_public_hex,
/// status_key_id, status_public_hex, chip_id, trusted_subject, trusted_audience,
/// now (integer epoch seconds). Never source trust roots or user identity from EDC.
#[no_mangle]
pub extern "C" fn entity_edc_verify_delegation_v1(
    request_json:*const c_char,
    response:*mut c_char,
    response_capacity:usize,
)->i32 {
    invoke(response,response_capacity,||{
        let raw=cstr(request_json)?;
        let v:Value=serde_json::from_str(&raw).map_err(|_|"invalid request")?;
        let object=v.as_object().ok_or("request not object")?;
        let fields=["grant_path","revocation_path","rights_key_id",
                    "rights_public_hex","status_key_id","status_public_hex",
                    "chip_id","trusted_subject","trusted_audience","now"];
        if object.len()!=fields.len()||!fields.iter().all(|k|object.contains_key(*k)){
            return Err("request fields invalid".into())
        }
        let strval=|k:&str|->R<&str>{
            v.get(k).and_then(|x|x.as_str()).ok_or("invalid required request string".into())
        };
        let now=v.get("now").and_then(|x|x.as_u64()).ok_or("invalid time")?;
        rights::verify_grant(GrantOptions{
            grant:Path::new(strval("grant_path")?),
            revocations:Path::new(strval("revocation_path")?),
            rights_kid:strval("rights_key_id")?,
            rights_pubkey:strval("rights_public_hex")?,
            revocation_kid:strval("status_key_id")?,
            revocation_pubkey:strval("status_public_hex")?,
            chip_id:strval("chip_id")?,
            subject:strval("trusted_subject")?,
            audience:strval("trusted_audience")?,
            now,
        })
    })
}
