"""Generate deterministic cross-platform Blackmore Aurora design adapters.

Single source: design/blackmore-aurora.tokens.json. No credentials, network, code
execution or release semantics. --check fails on stale or manually drifted adapters.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"design"/"blackmore-aurora.tokens.json"
DEST=ROOT/"design"/"adapters"

def _hex_rgb(code):
    return [int(code[i:i+2],16) for i in (1,3,5)]

def outputs(document):
    if document.get("schema")!="blackmore-aurora-design-tokens-v1.0.0":
        raise ValueError("unsupported Aurora token schema")
    colors=document["colors"]
    if any(not isinstance(value,str) or len(value)!=7 or not value.startswith("#") for value in colors.values()):
        raise ValueError("invalid color schema")
    fields=sorted(colors)
    css = "/* Generated Blackmore Aurora v1.0 — never hand-edit. */\n:root {\n"
    css += "".join("  --blackmore-"+key.replace("_","-")+": "+colors[key]+";\n" for key in fields)
    css += "  --blackmore-focus-width: 3px;\n  --blackmore-min-touch: 44px;\n}\n"
    css += "@media (prefers-reduced-motion: reduce) { :root { scroll-behavior: auto; } }\n"

    ts="// Generated Blackmore Aurora tokens v1.0 — no executable privileges.\n"
    ts+="export const blackmoreAurora = Object.freeze({\n"
    ts+="  version: '1.0.0',\n  colors: Object.freeze({\n"
    ts+="".join("    "+key+": '"+colors[key]+"',\n" for key in fields)
    ts+="  }),\n  minTouchPx: 44,\n  focusRingPx: 3,\n} as const);\n"
    ts+="export type BlackmoreAuroraColor = keyof typeof blackmoreAurora.colors;\n"

    swift="// Generated Blackmore Aurora v1.0 — UI-only, no native privileges.\n"
    swift+="import SwiftUI\n\npublic enum BlackmoreAurora {\n"
    swift+="  public static let version = \"1.0.0\"\n"
    swift+="  public static let minTouchSize: CGFloat = 44\n"
    for key in fields:
        r,g,b=_hex_rgb(colors[key])
        swift+=f"  public static let {key} = Color(red: {r}/255.0, green: {g}/255.0, blue: {b}/255.0)\n"
    swift+="  // AI, rights and verification colors communicate status only; they do not grant authority.\n}\n"

    kotlin="// Generated Blackmore Aurora v1.0 — presentation only.\n"
    kotlin+="package com.blackmore.design\n\nimport androidx.compose.ui.graphics.Color\n\nobject BlackmoreAurora {\n"
    kotlin+="  const val version = \"1.0.0\"\n  const val minTouchDp = 44\n"
    for key in fields:
        kotlin+=f"  val {key} = Color(0xFF{colors[key][1:].upper()})\n"
    kotlin+="  // All execution, issuer and native-device permissions belong to the application host.\n}\n"

    csharp="// Generated Blackmore Aurora v1.0 — semantic colors for .NET hosts.\n"
    csharp+="namespace Blackmore.Design {\n  public static class BlackmoreAurora {\n"
    csharp+="    public const string Version = \"1.0.0\";\n    public const int MinTouchPixels = 44;\n"
    for key in fields:
        csharp+="    public const string "+key[0].upper()+key[1:]+" = \""+colors[key]+"\";\n"
    csharp+="  }\n}\n"

    return {
        "web/aurora-tokens.css": css,
        "web/aurora-tokens.ts": ts,
        "ios/BlackmoreAurora.swift": swift,
        "android/BlackmoreAurora.kt": kotlin,
        "dotnet/BlackmoreAurora.cs": csharp,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    files=outputs(json.loads(INPUT.read_text(encoding="utf-8")))
    errors=[]
    for relative,text in files.items():
        path=DEST/relative
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8")!=text:
                errors.append(relative)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding="utf-8")
    if errors:
        print("AURORA_ADAPTER_DRIFT",json.dumps(errors),file=sys.stderr)
        return 1
    print("AURORA_ADAPTERS",len(files),"CHECK" if args.check else "GENERATED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
