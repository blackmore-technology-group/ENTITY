use crate::error::{KernelError, Result};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum CanonicalValue {
    Null,
    Bool(bool),
    Int(i64),
    UInt(u64),
    Float(f64),
    String(String),
    Binary(Vec<u8>),
    Array(Vec<Self>),
    Map(BTreeMap<String, Self>),
}

impl CanonicalValue {
    pub fn from_json(value: &Value) -> Result<Self> {
        match value {
            Value::Null => Ok(Self::Null),
            Value::Bool(v) => Ok(Self::Bool(*v)),
            Value::Number(v) => {
                if let Some(n) = v.as_i64() {
                    Ok(Self::Int(n))
                } else if let Some(n) = v.as_u64() {
                    Ok(Self::UInt(n))
                } else if let Some(n) = v.as_f64() {
                    if !n.is_finite() {
                        return Err(KernelError::Canonical("non-finite float".into()));
                    }
                    Ok(Self::Float(n))
                } else {
                    Err(KernelError::Canonical("unsupported JSON number".into()))
                }
            }
            Value::String(v) => Ok(Self::String(v.clone())),
            Value::Array(values) => values
                .iter()
                .map(Self::from_json)
                .collect::<Result<Vec<_>>>()
                .map(Self::Array),
            Value::Object(values) => values
                .iter()
                .map(|(key, value)| Ok((key.clone(), Self::from_json(value)?)))
                .collect::<Result<BTreeMap<_, _>>>()
                .map(Self::Map),
        }
    }

    pub fn map(entries: impl IntoIterator<Item = (impl Into<String>, Self)>) -> Self {
        Self::Map(entries.into_iter().map(|(key, value)| (key.into(), value)).collect())
    }
}

fn write_len(out: &mut Vec<u8>, len: usize, fix_base: u8, fix_max: usize, code16: u8, code32: u8) -> Result<()> {
    if len <= fix_max {
        out.push(fix_base | u8::try_from(len).map_err(|_| KernelError::Canonical("length overflow".into()))?);
    } else if u16::try_from(len).is_ok() {
        out.push(code16);
        out.extend_from_slice(&(len as u16).to_be_bytes());
    } else if u32::try_from(len).is_ok() {
        out.push(code32);
        out.extend_from_slice(&(len as u32).to_be_bytes());
    } else {
        return Err(KernelError::Canonical("container too large".into()));
    }
    Ok(())
}

fn write_string(out: &mut Vec<u8>, value: &str) -> Result<()> {
    let bytes = value.as_bytes();
    if bytes.len() <= 31 {
        out.push(0xa0 | u8::try_from(bytes.len()).map_err(|_| KernelError::Canonical("string length overflow".into()))?);
    } else if u8::try_from(bytes.len()).is_ok() {
        out.push(0xd9);
        out.push(bytes.len() as u8);
    } else if u16::try_from(bytes.len()).is_ok() {
        out.push(0xda);
        out.extend_from_slice(&(bytes.len() as u16).to_be_bytes());
    } else if u32::try_from(bytes.len()).is_ok() {
        out.push(0xdb);
        out.extend_from_slice(&(bytes.len() as u32).to_be_bytes());
    } else {
        return Err(KernelError::Canonical("string too large".into()));
    }
    out.extend_from_slice(bytes);
    Ok(())
}

fn write_binary(out: &mut Vec<u8>, value: &[u8]) -> Result<()> {
    if u8::try_from(value.len()).is_ok() {
        out.push(0xc4);
        out.push(value.len() as u8);
    } else if u16::try_from(value.len()).is_ok() {
        out.push(0xc5);
        out.extend_from_slice(&(value.len() as u16).to_be_bytes());
    } else if u32::try_from(value.len()).is_ok() {
        out.push(0xc6);
        out.extend_from_slice(&(value.len() as u32).to_be_bytes());
    } else {
        return Err(KernelError::Canonical("binary value too large".into()));
    }
    out.extend_from_slice(value);
    Ok(())
}

fn write_int(out: &mut Vec<u8>, value: i64) {
    if value >= 0 {
        write_uint(out, value as u64);
    } else if value >= -32 {
        out.push(value as i8 as u8);
    } else if value >= i8::MIN as i64 {
        out.push(0xd0);
        out.push(value as i8 as u8);
    } else if value >= i16::MIN as i64 {
        out.push(0xd1);
        out.extend_from_slice(&(value as i16).to_be_bytes());
    } else if value >= i32::MIN as i64 {
        out.push(0xd2);
        out.extend_from_slice(&(value as i32).to_be_bytes());
    } else {
        out.push(0xd3);
        out.extend_from_slice(&value.to_be_bytes());
    }
}

fn write_uint(out: &mut Vec<u8>, value: u64) {
    if value <= 0x7f {
        out.push(value as u8);
    } else if u8::try_from(value).is_ok() {
        out.push(0xcc);
        out.push(value as u8);
    } else if u16::try_from(value).is_ok() {
        out.push(0xcd);
        out.extend_from_slice(&(value as u16).to_be_bytes());
    } else if u32::try_from(value).is_ok() {
        out.push(0xce);
        out.extend_from_slice(&(value as u32).to_be_bytes());
    } else {
        out.push(0xcf);
        out.extend_from_slice(&value.to_be_bytes());
    }
}

fn encode_into(value: &CanonicalValue, out: &mut Vec<u8>) -> Result<()> {
    match value {
        CanonicalValue::Null => out.push(0xc0),
        CanonicalValue::Bool(false) => out.push(0xc2),
        CanonicalValue::Bool(true) => out.push(0xc3),
        CanonicalValue::Int(v) => write_int(out, *v),
        CanonicalValue::UInt(v) => write_uint(out, *v),
        CanonicalValue::Float(v) => {
            if !v.is_finite() {
                return Err(KernelError::Canonical("non-finite float".into()));
            }
            out.push(0xcb);
            out.extend_from_slice(&v.to_bits().to_be_bytes());
        }
        CanonicalValue::String(v) => write_string(out, v)?,
        CanonicalValue::Binary(v) => write_binary(out, v)?,
        CanonicalValue::Array(values) => {
            write_len(out, values.len(), 0x90, 15, 0xdc, 0xdd)?;
            for value in values {
                encode_into(value, out)?;
            }
        }
        CanonicalValue::Map(values) => {
            write_len(out, values.len(), 0x80, 15, 0xde, 0xdf)?;
            for (key, value) in values {
                write_string(out, key)?;
                encode_into(value, out)?;
            }
        }
    }
    Ok(())
}


const MAX_CANONICAL_BYTES: usize = 64 * 1024 * 1024;
const MAX_CANONICAL_DEPTH: usize = 128;
const MAX_CANONICAL_ITEMS: usize = 1_000_000;

struct Decoder<'a> {
    data: &'a [u8],
    offset: usize,
    items: usize,
}

impl<'a> Decoder<'a> {
    fn new(data: &'a [u8]) -> Result<Self> {
        if data.len() > MAX_CANONICAL_BYTES {
            return Err(KernelError::Canonical("canonical input exceeds size limit".into()));
        }
        Ok(Self { data, offset: 0, items: 0 })
    }

    fn take(&mut self, length: usize) -> Result<&'a [u8]> {
        let end = self
            .offset
            .checked_add(length)
            .ok_or_else(|| KernelError::Canonical("canonical length overflow".into()))?;
        if end > self.data.len() {
            return Err(KernelError::Canonical("truncated canonical value".into()));
        }
        let result = &self.data[self.offset..end];
        self.offset = end;
        Ok(result)
    }

    fn byte(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }

    fn length(&mut self, bytes: usize) -> Result<usize> {
        let raw = self.take(bytes)?;
        let value = match bytes {
            1 => u64::from(raw[0]),
            2 => u64::from(u16::from_be_bytes([raw[0], raw[1]])),
            4 => u64::from(u32::from_be_bytes([raw[0], raw[1], raw[2], raw[3]])),
            _ => return Err(KernelError::Canonical("unsupported length width".into())),
        };
        usize::try_from(value)
            .map_err(|_| KernelError::Canonical("canonical length does not fit platform".into()))
    }

    fn count_item(&mut self) -> Result<()> {
        self.items = self
            .items
            .checked_add(1)
            .ok_or_else(|| KernelError::Canonical("canonical item count overflow".into()))?;
        if self.items > MAX_CANONICAL_ITEMS {
            return Err(KernelError::Canonical("canonical item count exceeds limit".into()));
        }
        Ok(())
    }

    fn string(&mut self, length: usize) -> Result<String> {
        let bytes = self.take(length)?;
        std::str::from_utf8(bytes)
            .map(str::to_owned)
            .map_err(|_| KernelError::Canonical("canonical string is not UTF-8".into()))
    }

    fn array(&mut self, length: usize, depth: usize) -> Result<CanonicalValue> {
        let mut values = Vec::with_capacity(length.min(4096));
        for _ in 0..length {
            values.push(self.value(depth + 1)?);
        }
        Ok(CanonicalValue::Array(values))
    }

    fn map(&mut self, length: usize, depth: usize) -> Result<CanonicalValue> {
        let mut values = BTreeMap::new();
        let mut previous: Option<String> = None;
        for _ in 0..length {
            let key = match self.value(depth + 1)? {
                CanonicalValue::String(value) => value,
                _ => return Err(KernelError::Canonical("canonical map key must be a string".into())),
            };
            if previous.as_ref().is_some_and(|prior| prior >= &key) {
                return Err(KernelError::Canonical(
                    "canonical map keys must be unique and strictly sorted".into(),
                ));
            }
            previous = Some(key.clone());
            let value = self.value(depth + 1)?;
            values.insert(key, value);
        }
        Ok(CanonicalValue::Map(values))
    }

    fn value(&mut self, depth: usize) -> Result<CanonicalValue> {
        if depth > MAX_CANONICAL_DEPTH {
            return Err(KernelError::Canonical("canonical nesting exceeds limit".into()));
        }
        self.count_item()?;
        let marker = self.byte()?;
        match marker {
            0x00..=0x7f => Ok(CanonicalValue::Int(i64::from(marker))),
            0x80..=0x8f => self.map(usize::from(marker & 0x0f), depth),
            0x90..=0x9f => self.array(usize::from(marker & 0x0f), depth),
            0xa0..=0xbf => Ok(CanonicalValue::String(self.string(usize::from(marker & 0x1f))?)),
            0xc0 => Ok(CanonicalValue::Null),
            0xc2 => Ok(CanonicalValue::Bool(false)),
            0xc3 => Ok(CanonicalValue::Bool(true)),
            0xc4 => {
                let length = self.length(1)?;
                Ok(CanonicalValue::Binary(self.take(length)?.to_vec()))
            }
            0xc5 => {
                let length = self.length(2)?;
                Ok(CanonicalValue::Binary(self.take(length)?.to_vec()))
            }
            0xc6 => {
                let length = self.length(4)?;
                Ok(CanonicalValue::Binary(self.take(length)?.to_vec()))
            }
            0xcb => {
                let raw: [u8; 8] = self
                    .take(8)?
                    .try_into()
                    .map_err(|_| KernelError::Canonical("truncated float".into()))?;
                let value = f64::from_bits(u64::from_be_bytes(raw));
                if !value.is_finite() {
                    return Err(KernelError::Canonical("non-finite float".into()));
                }
                Ok(CanonicalValue::Float(value))
            }
            0xcc => Ok(CanonicalValue::Int(i64::from(self.byte()?))),
            0xcd => {
                let raw: [u8; 2] = self.take(2)?.try_into().map_err(|_| KernelError::Canonical("truncated uint16".into()))?;
                Ok(CanonicalValue::Int(i64::from(u16::from_be_bytes(raw))))
            }
            0xce => {
                let raw: [u8; 4] = self.take(4)?.try_into().map_err(|_| KernelError::Canonical("truncated uint32".into()))?;
                Ok(CanonicalValue::Int(i64::from(u32::from_be_bytes(raw))))
            }
            0xcf => {
                let raw: [u8; 8] = self.take(8)?.try_into().map_err(|_| KernelError::Canonical("truncated uint64".into()))?;
                let value = u64::from_be_bytes(raw);
                if value <= i64::MAX as u64 {
                    Ok(CanonicalValue::Int(value as i64))
                } else {
                    Ok(CanonicalValue::UInt(value))
                }
            }
            0xd0 => Ok(CanonicalValue::Int(i64::from(self.byte()? as i8))),
            0xd1 => {
                let raw: [u8; 2] = self.take(2)?.try_into().map_err(|_| KernelError::Canonical("truncated int16".into()))?;
                Ok(CanonicalValue::Int(i64::from(i16::from_be_bytes(raw))))
            }
            0xd2 => {
                let raw: [u8; 4] = self.take(4)?.try_into().map_err(|_| KernelError::Canonical("truncated int32".into()))?;
                Ok(CanonicalValue::Int(i64::from(i32::from_be_bytes(raw))))
            }
            0xd3 => {
                let raw: [u8; 8] = self.take(8)?.try_into().map_err(|_| KernelError::Canonical("truncated int64".into()))?;
                Ok(CanonicalValue::Int(i64::from_be_bytes(raw)))
            }
            0xd9 => {
                let length = self.length(1)?;
                Ok(CanonicalValue::String(self.string(length)?))
            }
            0xda => {
                let length = self.length(2)?;
                Ok(CanonicalValue::String(self.string(length)?))
            }
            0xdb => {
                let length = self.length(4)?;
                Ok(CanonicalValue::String(self.string(length)?))
            }
            0xdc => {
                let length = self.length(2)?;
                self.array(length, depth)
            }
            0xdd => {
                let length = self.length(4)?;
                self.array(length, depth)
            }
            0xde => {
                let length = self.length(2)?;
                self.map(length, depth)
            }
            0xdf => {
                let length = self.length(4)?;
                self.map(length, depth)
            }
            0xe0..=0xff => Ok(CanonicalValue::Int(i64::from(marker as i8))),
            _ => Err(KernelError::Canonical(format!(
                "unsupported MessagePack marker 0x{marker:02x}"
            ))),
        }
    }
}

pub fn unpack(data: &[u8]) -> Result<CanonicalValue> {
    let mut decoder = Decoder::new(data)?;
    let value = decoder.value(0)?;
    if decoder.offset != data.len() {
        return Err(KernelError::Canonical("trailing bytes after canonical value".into()));
    }
    if pack(&value)? != data {
        return Err(KernelError::Canonical("non-canonical MessagePack representation".into()));
    }
    Ok(value)
}

pub fn pack(value: &CanonicalValue) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    encode_into(value, &mut out)?;
    Ok(out)
}

pub fn digest(domain: &str, value: &CanonicalValue) -> Result<String> {
    let mut hasher = Sha256::new();
    hasher.update(domain.as_bytes());
    hasher.update([0]);
    hasher.update(pack(value)?);
    Ok(hex::encode(hasher.finalize()))
}

pub fn sha256(data: &[u8]) -> String {
    hex::encode(Sha256::digest(data))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn integer_boundaries_match_messagepack() {
        assert_eq!(pack(&CanonicalValue::Int(127)).unwrap(), vec![0x7f]);
        assert_eq!(pack(&CanonicalValue::Int(128)).unwrap(), vec![0xcc, 0x80]);
        assert_eq!(pack(&CanonicalValue::Int(-32)).unwrap(), vec![0xe0]);
        assert_eq!(pack(&CanonicalValue::Int(-33)).unwrap(), vec![0xd0, 0xdf]);
    }

    #[test]
    fn canonical_decoder_rejects_noncanonical_or_trailing_input() {
        assert_eq!(unpack(&[0x7f]).unwrap(), CanonicalValue::Int(127));
        assert!(unpack(&[0xcc, 0x7f]).is_err());
        assert!(unpack(&[0x7f, 0x00]).is_err());
        assert!(unpack(&[0x82, 0xa1, b'z', 0x01, 0xa1, b'a', 0x02]).is_err());
    }

    #[test]
    fn maps_are_key_sorted() {
        let value = CanonicalValue::map([
            ("z", CanonicalValue::Int(1)),
            ("a", CanonicalValue::Int(2)),
        ]);
        assert_eq!(hex::encode(pack(&value).unwrap()), "82a16102a17a01");
    }
}
