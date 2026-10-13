use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::Read;
use std::path::Path;
use zip::{CompressionMethod, ZipArchive};

type R<T> = Result<T, String>;
const MAX_OUTPUT: u64 = 64 * 1024 * 1024;
const MAX_MANIFEST: u64 = 2 * 1024 * 1024;
const MAX_ENTROPY: u64 = 1024 * 1024;
const MAX_NODES: usize = 8192;
const MAX_DEPTH: u64 = 64;

fn fail(msg: &str) -> String { msg.into() }
fn hash(data: &[u8]) -> String { hex::encode(Sha256::digest(data)) }
fn member<'a>(v: &'a Value, key: &str) -> R<&'a Value> {
    v.get(key).ok_or_else(|| format!("missing {key}"))
}
fn text<'a>(v: &'a Value, key: &str) -> R<&'a str> {
    member(v, key)?.as_str().ok_or_else(|| format!("invalid {key}"))
}
fn integer(v: &Value, max: u64) -> R<u64> {
    let n=v.as_u64().ok_or_else(|| fail("formula requires unsigned integer"))?;
    if n > max { Err(fail("integer exceeds formula cap")) } else {Ok(n)}
}
fn num(v: &Value, key: &str, max: u64) -> R<u64> {
    integer(member(v,key)?,max)
}
fn fields(v: &Value, expected: &[&str]) -> R<()> {
    let obj=v.as_object().ok_or_else(|| fail("expected object"))?;
    if obj.len()!=expected.len() || !expected.iter().all(|k| obj.contains_key(*k)) {
        return Err(fail("unexpected or missing schema fields"))
    }
    Ok(())
}
fn checked_hash(s: &str) -> R<()> {
    if s.len()!=64 || !s.as_bytes().iter().all(|x| x.is_ascii_hexdigit() && !x.is_ascii_uppercase()) {
        return Err(fail("invalid SHA-256"))
    }
    Ok(())
}

struct Formula {
    manifest: Value,
    bytes: Vec<u64>,
    root: usize,
    entropy: HashMap<String,u64>
}
fn validate(v: Value) -> R<Formula> {
    fields(&v,&["schema","chip_id","formula_object_ref","content_sha256",
                 "content_bytes","root","nodes"])?;
    if text(&v,"schema")? != "entity-datachip-formula-v0.2" {
        return Err(fail("unknown formula schema"));
    }
    checked_hash(text(&v,"content_sha256")?)?;
    let content_bytes=num(&v,"content_bytes",MAX_OUTPUT)?;
    if !member(&v,"formula_object_ref")?.is_null() {
        let s=text(&v,"formula_object_ref")?;
        if s.is_empty() || s.len()>300 {return Err(fail("bad source reference"))}
    }
    let list=member(&v,"nodes")?.as_array().ok_or_else(||fail("invalid formula nodes"))?;
    if list.is_empty() || list.len()>MAX_NODES {return Err(fail("node limit"))}
    let root=integer(member(&v,"root")?,(list.len()-1) as u64)? as usize;
    let mut sizes:Vec<u64>=Vec::with_capacity(list.len());
    let mut depths:Vec<u64>=Vec::with_capacity(list.len());
    let mut entropy=HashMap::new();
    for (idx,node) in list.iter().enumerate() {
        let op=text(node,"op")?;
        let sz=num(node,"bytes",MAX_OUTPUT)?;
        let mut deps=Vec::new();
        match op {
          "ATOM" => {
            fields(node,&["op","bytes","atom"])?;
            if sz!=1 {return Err(fail("atom must be one byte"))}
            num(node,"atom",255)?;
          }
          "ENTROPY" => {
            fields(node,&["op","bytes","sha256"])?;
            if sz==0 || sz>MAX_ENTROPY {return Err(fail("entropy size"))}
            let digest=text(node,"sha256")?;
            checked_hash(digest)?;
            if let Some(existing)=entropy.insert(digest.to_string(),sz) {
                if existing!=sz {return Err(fail("conflicting entropy lengths"))}
            }
          }
          "CONCAT" => {
            fields(node,&["op","bytes","children"])?;
            let ids=member(node,"children")?.as_array().ok_or_else(||fail("invalid concat"))?;
            if ids.len()>2048 {return Err(fail("too many children"))}
            let mut sum=0u64;
            for id in ids {
                if idx==0 {return Err(fail("forward node reference"))}
                let dep=integer(id,(idx-1) as u64)? as usize;
                deps.push(dep);
                sum=sum.checked_add(sizes[dep]).ok_or_else(||fail("concat overflow"))?;
            }
            if sum!=sz {return Err(fail("concat byte count mismatch"))}
          }
          "REPEAT" => {
            fields(node,&["op","bytes","child","count"])?;
            if idx==0 {return Err(fail("repeat forward ref"))}
            let dep=num(node,"child",(idx-1) as u64)? as usize;
            let count=num(node,"count",MAX_OUTPUT)?;
            if count==0 || sizes[dep]==0 || sizes[dep]>MAX_ENTROPY ||
                    sizes[dep].checked_mul(count)!=Some(sz) {
                return Err(fail("unsafe repeat"))
            }
            deps.push(dep);
          }
          "SLICE" => {
            fields(node,&["op","bytes","child","offset"])?;
            if idx==0 {return Err(fail("slice forward ref"))}
            let dep=num(node,"child",(idx-1) as u64)? as usize;
            let offset=num(node,"offset",MAX_OUTPUT)?;
            if sizes[dep]>MAX_ENTROPY ||
                 offset.checked_add(sz).is_none_or(|v|v>sizes[dep]) {
                return Err(fail("unsafe slice"))
            }
            deps.push(dep);
          }
          _=>return Err(fail("unknown formula opcode"))
        }
        let depth=deps.iter().map(|i| depths[*i]).max().unwrap_or(0)+1;
        if depth>MAX_DEPTH {return Err(fail("formula depth exceeded"))}
        sizes.push(sz);
        depths.push(depth);
    }
    if sizes[root]!=content_bytes {return Err(fail("root size mismatch"))}
    let id=text(&v,"chip_id")?;
    let mut body=v.clone();
    body.as_object_mut().ok_or_else(||fail("invalid body"))?.remove("chip_id");
    let canonical=serde_json::to_vec(&body).map_err(|e|e.to_string())?;
    if id!=format!("edc:formula:sha256:{}",hash(&canonical)) {
        return Err(fail("manifest digest mismatch"))
    }
    Ok(Formula{manifest:v,bytes:sizes,root,entropy})
}

fn emit<F>(zip:&mut ZipArchive<File>, nodes:&[Value], index:usize,
           out:&mut F) -> R<()>
where F:FnMut(&[u8])->R<()> {
    let node=&nodes[index];
    match text(node,"op")? {
      "ATOM" => {
        let byte=num(node,"atom",255)? as u8;
        out(&[byte])
      }
      "ENTROPY" => {
        let digest=text(node,"sha256")?;
        let entry=format!("entropy/{digest}.bin");
        let mut item=zip.by_name(&entry).map_err(|e|e.to_string())?;
        let size=num(node,"bytes",MAX_ENTROPY)? as usize;
        let mut buf=Vec::with_capacity(size);
        item.read_to_end(&mut buf).map_err(|e|e.to_string())?;
        if buf.len()!=size || hash(&buf)!=digest {return Err(fail("entropy tampered"))}
        out(&buf)
      }
      "CONCAT" => {
        let deps=member(node,"children")?.as_array().ok_or_else(||fail("children"))?;
        for child in deps {
            emit(zip,nodes,child.as_u64().ok_or_else(||fail("child index"))? as usize,out)?;
        }
        Ok(())
      }
      "REPEAT" => {
        let child=num(node,"child",(nodes.len()-1) as u64)? as usize;
        let count=num(node,"count",MAX_OUTPUT)?;
        let mut basis=Vec::new();
        emit(zip,nodes,child,&mut |b:&[u8]|{
            if basis.len()+b.len() > MAX_ENTROPY as usize {return Err(fail("basis cap"))}
            basis.extend_from_slice(b);
            Ok(())
        })?;
        if basis.is_empty(){return Err(fail("empty repeat basis"))}
        let per=(MAX_ENTROPY as usize/basis.len()).max(1) as u64;
        let mut remain=count;
        while remain>0 {
            let copies=remain.min(per);
            out(&basis.repeat(copies as usize))?;
            remain-=copies;
        }
        Ok(())
      }
      "SLICE" => {
        let child=num(node,"child",(nodes.len()-1) as u64)? as usize;
        let mut basis=Vec::new();
        emit(zip,nodes,child,&mut |b:&[u8]|{
            if basis.len()+b.len() > MAX_ENTROPY as usize {return Err(fail("slice basis cap"))}
            basis.extend_from_slice(b);
            Ok(())
        })?;
        let start=num(node,"offset",MAX_OUTPUT)? as usize;
        let size=num(node,"bytes",MAX_OUTPUT)? as usize;
        if start.checked_add(size).is_none_or(|v|v>basis.len()) {
            return Err(fail("invalid runtime slice"))
        }
        out(&basis[start..start+size])
      }
      _=>Err(fail("invalid opcode"))
    }
}

pub fn verify_file(path:&Path) -> R<Value> {
    let file=File::open(path).map_err(|e|e.to_string())?;
    let size=file.metadata().map_err(|e|e.to_string())?.len();
    if size>MAX_OUTPUT+MAX_MANIFEST+MAX_NODES as u64*200 {
        return Err(fail("physical archive exceeds limit"))
    }
    let mut zip=ZipArchive::new(file).map_err(|e|e.to_string())?;
    if zip.len()>MAX_NODES+1 {return Err(fail("zip member count"))}
    let mut filenames=HashSet::new();
    for index in 0..zip.len() {
        let item=zip.by_index(index).map_err(|e|e.to_string())?;
        let name=item.name().to_owned();
        if !filenames.insert(name.clone()) {return Err(fail("duplicate ZIP name"))}
        if item.compression()!=CompressionMethod::Stored {
            return Err(fail("compressed member not supported"));
        }
        if item.size()>MAX_ENTROPY && name!="manifest.json" {
            return Err(fail("stored entropy chunk too large"))
        }
        if let Some(mode)=item.unix_mode() {
            let kind=mode & 0o170000;
            if kind!=0 && kind!=0o100000 {return Err(fail("archive symlink/device"))}
        }
    }
    let raw={
        let mut item=zip.by_name("manifest.json").map_err(|e|e.to_string())?;
        if item.size()>MAX_MANIFEST {return Err(fail("manifest too big"))}
        let mut raw=Vec::with_capacity(item.size() as usize);
        item.read_to_end(&mut raw).map_err(|e|e.to_string())?;
        raw
    };
    let document:Value=serde_json::from_slice(&raw).map_err(|e|e.to_string())?;
    if serde_json::to_vec(&document).map_err(|e|e.to_string())?!=raw {
        return Err(fail("noncanonical or duplicate-key manifest"))
    }
    let parsed=validate(document)?;
    let required:HashSet<String>=
        std::iter::once("manifest.json".to_string()).chain(
            parsed.entropy.keys().map(|x|format!("entropy/{x}.bin"))).collect();
    if required!=filenames {return Err(fail("missing or extraneous ZIP member"))}
    for (digest,length) in &parsed.entropy {
        let item=zip.by_name(&format!("entropy/{digest}.bin")).map_err(|e|e.to_string())?;
        if item.size()!=*length {return Err(fail("entropy length mismatch"))}
    }
    let nodes=member(&parsed.manifest,"nodes")?.as_array().ok_or_else(||fail("nodes"))?;
    let mut hashctx=Sha256::new();
    let mut actual=0u64;
    emit(&mut zip,nodes,parsed.root,&mut |bytes| {
        actual=actual.checked_add(bytes.len() as u64).ok_or_else(||fail("overflow"))?;
        if actual>MAX_OUTPUT {return Err(fail("reconstruction expansion limit"))}
        hashctx.update(bytes);
        Ok(())
    })?;
    let actual_hash=hex::encode(hashctx.finalize());
    if actual!=num(&parsed.manifest,"content_bytes",MAX_OUTPUT)?
        || actual_hash!=text(&parsed.manifest,"content_sha256")? {
        return Err(fail("reconstructed payload mismatch"))
    }
    Ok(json!({"schema":"edc-native-formula-verification-v0.1",
              "chip_id":text(&parsed.manifest,"chip_id")?,
              "content_bytes":actual,"content_sha256":actual_hash,
              "integrity_verified":true,
              "issuer_authenticated":false,"rights_authorized":false,
              "native_rust_verifier":true}))
}
