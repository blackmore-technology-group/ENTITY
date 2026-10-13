use entity_datachip_native::{formula, rights};

use std::env;
use std::path::Path;
use rights::GrantOptions;

fn dispatch(args:&[String])->Result<serde_json::Value,String> {
    if args.len()==3 && args[1]=="verify-formula" {
        return formula::verify_file(Path::new(&args[2]));
    }
    if args.len()==12 && args[1]=="verify-delegated-grant" {
        let now=args[11].parse::<u64>().map_err(|_|"invalid timestamp")?;
        return rights::verify_grant(GrantOptions{
            grant:Path::new(&args[2]),revocations:Path::new(&args[3]),
            rights_kid:&args[4],rights_pubkey:&args[5],
            revocation_kid:&args[6],revocation_pubkey:&args[7],
            chip_id:&args[8],subject:&args[9],audience:&args[10],
            now,
        });
    }
    Err("Usage: entity-datachip-verify verify-formula FILE.edcf\n   or: entity-datachip-verify verify-delegated-grant GRANT.json STATUS.json RIGHTS_KEY_ID RIGHTS_PUBLIC_KEY_HEX REVOCATION_KEY_ID REVOCATION_PUBLIC_KEY_HEX CHIP_ID TRUSTED_SUBJECT TRUSTED_APP NOW_UNIX".into())
}

fn main() {
    let args:Vec<String>=env::args().collect();
    match dispatch(&args) {
        Ok(result)=>println!("{}",result),
        Err(e)=>{
            eprintln!("ENTITY DATACHIP verification failed: {e}");
            std::process::exit(2)
        }
    }
}
