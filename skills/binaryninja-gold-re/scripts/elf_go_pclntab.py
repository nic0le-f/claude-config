#!/usr/bin/env python3
"""Recover Go function names, source files and CU mapping from .gopclntab.

For stripped, statically linked Go ELF binaries where `.gosymtab` is empty and
no DWARF is present, `.gopclntab` is the only remaining name source. This parser
is deliberately magic-agnostic: it validates the header structurally (ptrSize,
minLC, textStart against the real .text VA, and offset monotonicity) rather than
trusting the 4-byte magic, because malware routinely overwrites that magic to
break tools which fingerprint it.

Static-only. Reads the file from disk; never loads or executes the sample.

Usage:
    elf_go_pclntab.py CASE_DIR [--section .gopclntab]
    elf_go_pclntab.py --file SAMPLE --out-dir DIR

Writes:
    evidence/go_pclntab.json        header, functions, files, CU list
    evidence/go_functions.txt       "0xVA<TAB>size<TAB>name" per function
    evidence/go_files.txt           every source path in the filetab
    evidence/app_symbols.txt        application-owned functions only
    recovered_tree/source_tree.md   package/source tree reconstruction
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

KNOWN_MAGICS = {
    0xFFFFFFFB: "go1.2",
    0xFFFFFFFA: "go1.16",
    0xFFFFFFF0: "go1.18",
    0xFFFFFFF1: "go1.20+",
}

# Import-path roots that belong to the toolchain, stdlib or well-known third
# parties. Anything outside these is a candidate application package.
STDLIB_ROOTS = {
    "archive", "arena", "bufio", "builtin", "bytes", "cmp", "compress",
    "container", "context", "crypto", "database", "debug", "embed", "encoding",
    "errors", "expvar", "flag", "fmt", "go", "hash", "html", "image", "index",
    "internal", "io", "iter", "log", "maps", "math", "mime", "net", "os",
    "path", "plugin", "reflect", "regexp", "runtime", "slices", "sort",
    "strconv", "strings", "structs", "sync", "syscall", "testing", "text",
    "time", "unicode", "unique", "unsafe", "weak", "vendor", "cmd",
}

RUNTIME_PREFIXES = ("type:", "type..", "go:", "gogo", "_cgo", "crosscall", "x_cgo")

THIRD_PARTY_HOSTS = (
    "github.com", "gitlab.com", "gitee.com", "gitea.com", "bitbucket.org",
    "golang.org", "google.golang.org", "gopkg.in", "go.uber.org", "go.etcd.io",
    "cloud.google.com", "k8s.io", "sigs.k8s.io", "go.opentelemetry.io",
    "modernc.org", "lukechampine.com", "filippo.io", "rsc.io", "mvdan.cc",
    "howett.net", "gvisor.dev", "go.mongodb.org", "goftp.io", "nhooyr.io",
    "gioui.org", "fyne.io", "honnef.co", "git.sr.ht", "codeberg.org",
)


class Reader:
    def __init__(self, data: bytes, ptr_size: int = 8) -> None:
        self.d = data
        self.ptr = ptr_size

    def u8(self, off: int) -> int:
        return self.d[off]

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.d, off)[0]

    def i32(self, off: int) -> int:
        return struct.unpack_from("<i", self.d, off)[0]

    def uptr(self, off: int) -> int:
        if self.ptr == 8:
            return struct.unpack_from("<Q", self.d, off)[0]
        return struct.unpack_from("<I", self.d, off)[0]

    def cstr(self, off: int, limit: int = 4096) -> str:
        end = self.d.find(b"\x00", off, off + limit)
        if end == -1:
            end = min(off + limit, len(self.d))
        return self.d[off:end].decode("utf-8", "replace")


def elf_sections(path: Path) -> dict[str, dict[str, int]]:
    """Parse the ELF section header table directly, no external tools."""
    d = path.read_bytes()
    if d[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if d[4] != 2:
        raise ValueError("only ELF64 supported")
    e_shoff = struct.unpack_from("<Q", d, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", d, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", d, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", d, 0x3E)[0]
    if e_shoff == 0 or e_shnum == 0:
        raise ValueError("no section header table (packed or stripped of sections)")
    base = e_shoff + e_shstrndx * e_shentsize
    str_off = struct.unpack_from("<Q", d, base + 0x18)[0]
    out: dict[str, dict[str, int]] = {}
    for i in range(e_shnum):
        sh = e_shoff + i * e_shentsize
        name_idx = struct.unpack_from("<I", d, sh + 0x00)[0]
        end = d.find(b"\x00", str_off + name_idx)
        name = d[str_off + name_idx:end].decode("utf-8", "replace")
        out[name] = {
            "addr": struct.unpack_from("<Q", d, sh + 0x10)[0],
            "offset": struct.unpack_from("<Q", d, sh + 0x18)[0],
            "size": struct.unpack_from("<Q", d, sh + 0x20)[0],
        }
    return out


def parse_header(r: Reader, text_va: int) -> dict[str, Any]:
    magic = r.u32(0)
    pad1, pad2 = r.u8(4), r.u8(5)
    min_lc, ptr_size = r.u8(6), r.u8(7)
    if ptr_size not in (4, 8):
        raise ValueError(f"implausible ptrSize {ptr_size}")
    if pad1 != 0 or pad2 != 0:
        raise ValueError(f"non-zero header padding {pad1:#x} {pad2:#x}")
    r.ptr = ptr_size
    hdr = {
        "magic": magic,
        "magic_hex": f"{magic:#010x}",
        "magic_known": KNOWN_MAGICS.get(magic),
        "magic_tampered": magic not in KNOWN_MAGICS,
        "min_lc": min_lc,
        "ptr_size": ptr_size,
        "nfunc": r.uptr(8),
        "nfiles": r.uptr(8 + ptr_size),
        "text_start": r.uptr(8 + 2 * ptr_size),
        "funcname_off": r.uptr(8 + 3 * ptr_size),
        "cu_off": r.uptr(8 + 4 * ptr_size),
        "filetab_off": r.uptr(8 + 5 * ptr_size),
        "pctab_off": r.uptr(8 + 6 * ptr_size),
        "pcln_off": r.uptr(8 + 7 * ptr_size),
    }
    # Structural validation in place of the magic check.
    problems = []
    if hdr["text_start"] != text_va:
        problems.append(f"textStart {hdr['text_start']:#x} != .text VA {text_va:#x}")
    offs = [hdr["funcname_off"], hdr["cu_off"], hdr["filetab_off"],
            hdr["pctab_off"], hdr["pcln_off"]]
    if offs != sorted(offs):
        problems.append("section offsets not monotonically increasing")
    if any(o >= len(r.d) for o in offs):
        problems.append("an offset lies past the end of .gopclntab")
    if not (0 < hdr["nfunc"] < 2_000_000):
        problems.append(f"implausible nfunc {hdr['nfunc']}")
    hdr["structural_problems"] = problems
    hdr["structurally_valid"] = not problems
    return hdr


def parse_functions(r: Reader, hdr: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk functab, then each _func struct, resolving name and source file."""
    ptr = hdr["ptr_size"]
    nfunc = hdr["nfunc"]
    text = hdr["text_start"]
    pcln = hdr["pcln_off"]
    funcname = hdr["funcname_off"]
    filetab = hdr["filetab_off"]
    cutab = hdr["cu_off"]

    # go1.18+ functab: (nfunc+1) pairs of uint32 offsets relative to textStart.
    ent_size = 8
    funcs: list[dict[str, Any]] = []
    for i in range(nfunc):
        e = pcln + i * ent_size
        entry_off = r.u32(e)
        func_off = r.u32(e + 4)
        f = pcln + func_off
        if f + 40 > len(r.d):
            continue
        # _func layout (go1.20+): entryOff 0, nameOff 4, args 8, deferreturn 12,
        # pcsp 16, pcfile 20, pcln 24, npcdata 28, cuOffset 32, startLine 36,
        # funcID 40, flag 41, pad 42, nfuncdata 43.
        name_off = r.i32(f + 4)
        npcdata = r.u32(f + 28)
        cu_offset = r.u32(f + 32)
        start_line = r.i32(f + 36)
        func_id = r.u8(f + 40)
        flag = r.u8(f + 41)
        nfuncdata = r.u8(f + 43)
        va = text + entry_off
        # Next entry's entryOff bounds this function.
        nxt = r.u32(pcln + (i + 1) * ent_size) if i + 1 <= nfunc else entry_off
        name = r.cstr(funcname + name_off) if 0 <= name_off < len(r.d) else ""
        pcfile = r.u32(f + 20)
        funcs.append({
            "va": va,
            "va_hex": hex(va),
            "size": max(0, nxt - entry_off),
            "name": name,
            "cu_offset": cu_offset,
            "start_line": start_line,
            "func_id": func_id,
            "flag": flag,
            "nfuncdata": nfuncdata,
            "npcdata": npcdata,
            "pcfile": pcfile,
            "name_off": name_off,
        })

    # Resolve source file per function via cutab[cuOffset + fileIndex].
    # The first pcvalue in the pcfile table gives the file at function entry.
    pctab = hdr["pctab_off"]
    for fn in funcs:
        fn["file"] = ""
        if fn["pcfile"] == 0 or fn["cu_offset"] == 0xFFFFFFFF:
            continue
        try:
            file_idx = first_pcvalue(r, pctab + fn["pcfile"])
        except Exception:
            continue
        if file_idx is None or file_idx < 0:
            continue
        ct = cutab + (fn["cu_offset"] + file_idx) * 4
        if ct + 4 > len(r.d):
            continue
        name_off = r.u32(ct)
        if name_off == 0xFFFFFFFF:
            continue
        fn["file"] = r.cstr(filetab + name_off)
    return funcs


def read_varint(d: bytes, off: int) -> tuple[int, int]:
    v = 0
    shift = 0
    while True:
        b = d[off]
        off += 1
        v |= (b & 0x7F) << shift
        if b < 0x80:
            break
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")
    return v, off


def first_pcvalue(r: Reader, off: int) -> int | None:
    """Decode the first value of a pcvalue table (zig-zag delta from -1)."""
    d = r.d
    if off >= len(d) or d[off] == 0:
        return None
    raw, _ = read_varint(d, off)
    delta = (-(raw >> 1) - 1) if (raw & 1) else (raw >> 1)
    return -1 + delta


def package_of(name: str) -> str:
    """Best-effort Go import path for a symbol name."""
    if not name or name.startswith(RUNTIME_PREFIXES):
        return ""
    # Strip a receiver in parentheses: pkg.(*T).Method
    n = re.sub(r"\.\(\*?[^)]*\)", "", name)
    # The package path is everything before the last '.' that follows the final '/'
    slash = n.rfind("/")
    tail = n[slash + 1:]
    if "." not in tail:
        return ""
    pkg_tail = tail.split(".", 1)[0]
    return (n[:slash + 1] + pkg_tail) if slash != -1 else pkg_tail


def classify(pkg: str) -> str:
    if not pkg:
        return "runtime_artifact"
    root = pkg.split("/", 1)[0]
    if root in STDLIB_ROOTS:
        return "stdlib"
    if root.startswith(THIRD_PARTY_HOSTS) or any(
        pkg.startswith(h + "/") for h in THIRD_PARTY_HOSTS
    ):
        return "third_party"
    if "." in root:
        return "third_party"
    return "application"


def build_source_tree(funcs: list[dict[str, Any]], files: list[str]) -> str:
    by_pkg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fn in funcs:
        pkg = package_of(fn["name"])
        if pkg:
            by_pkg[pkg].append(fn)

    buckets: dict[str, list[str]] = defaultdict(list)
    for pkg in by_pkg:
        buckets[classify(pkg)].append(pkg)

    lines = ["# Recovered Go Source Tree", "",
             "Evidence source: `.gopclntab` funcnametab / filetab / cutab "
             "(`elf_go_pclntab.py`). No DWARF and no `.gosymtab` in this binary.", ""]
    for label, title in (
        ("application", "Application-owned packages"),
        ("third_party", "Third-party dependencies"),
        ("stdlib", "Go standard library"),
    ):
        pkgs = sorted(buckets.get(label, []))
        lines.append(f"## {title} ({len(pkgs)})")
        lines.append("")
        if not pkgs:
            lines.append("_none recovered_")
            lines.append("")
            continue
        for pkg in pkgs:
            fns = by_pkg[pkg]
            srcs = sorted({f["file"] for f in fns if f["file"]})
            lines.append(f"- `{pkg}` — {len(fns)} function(s)")
            for s in srcs:
                lines.append(f"  - `{s}`")
        lines.append("")

    lines.append(f"## filetab source paths ({len(files)})")
    lines.append("")
    for f in sorted(files):
        lines.append(f"- `{f}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case_dir", nargs="?")
    ap.add_argument("--file", help="analyse a bare sample instead of a case dir")
    ap.add_argument("--out-dir")
    ap.add_argument("--section", default=".gopclntab")
    args = ap.parse_args()

    if args.file:
        sample = Path(args.file).expanduser().resolve()
        out_root = Path(args.out_dir or sample.parent).expanduser().resolve()
        ev_dir = out_root
        tree_dir = out_root
    else:
        if not args.case_dir:
            ap.error("CASE_DIR or --file is required")
        case_dir = Path(args.case_dir).expanduser().resolve()
        case = json.loads((case_dir / "case.json").read_text())
        sample = case_dir / case.get("analysis_target", "sample/original.bin")
        ev_dir = case_dir / "evidence"
        tree_dir = case_dir / "recovered_tree"
    ev_dir.mkdir(parents=True, exist_ok=True)
    tree_dir.mkdir(parents=True, exist_ok=True)

    secs = elf_sections(sample)
    if args.section not in secs:
        print(f"error: no {args.section} section; not a Go binary?")
        return 1
    pcln_sec = secs[args.section]
    text_va = secs[".text"]["addr"]
    blob = sample.read_bytes()[pcln_sec["offset"]:pcln_sec["offset"] + pcln_sec["size"]]

    r = Reader(blob)
    hdr = parse_header(r, text_va)
    hdr["section_va"] = hex(pcln_sec["addr"])
    hdr["section_size"] = pcln_sec["size"]
    hdr["text_va"] = hex(text_va)

    funcs = parse_functions(r, hdr)

    files = []
    off = hdr["filetab_off"]
    end = hdr["pctab_off"]
    while off < end:
        s = r.cstr(off)
        if s:
            files.append(s)
        off += len(s.encode("utf-8", "replace")) + 1
    files = [f for f in files if f]

    by_class: Counter[str] = Counter()
    pkg_counts: Counter[str] = Counter()
    for fn in funcs:
        pkg = package_of(fn["name"])
        fn["package"] = pkg
        fn["class"] = classify(pkg)
        by_class[fn["class"]] += 1
        if pkg:
            pkg_counts[pkg] += 1

    result = {
        "sample": str(sample),
        "header": hdr,
        "function_count": len(funcs),
        "class_counts": dict(by_class),
        "package_count": len(pkg_counts),
        "packages": {p: c for p, c in pkg_counts.most_common()},
        "files": files,
        "functions": funcs,
    }
    (ev_dir / "go_pclntab.json").write_text(
        json.dumps(result, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    with (ev_dir / "go_functions.txt").open("w", encoding="utf-8") as fh:
        for fn in sorted(funcs, key=lambda x: x["va"]):
            fh.write(f"{fn['va_hex']}\t{fn['size']}\t{fn['name']}\n")

    (ev_dir / "go_files.txt").write_text(
        "\n".join(sorted(files)) + "\n", encoding="utf-8")

    app = [fn for fn in funcs if fn["class"] == "application"]
    with (ev_dir / "app_symbols.txt").open("w", encoding="utf-8") as fh:
        for fn in sorted(app, key=lambda x: x["va"]):
            fh.write(f"{fn['va_hex']}\t{fn['size']}\t{fn['name']}\t{fn['file']}\n")

    (tree_dir / "source_tree.md").write_text(
        build_source_tree(funcs, files), encoding="utf-8")

    print(f"magic       : {hdr['magic_hex']} "
          f"({hdr['magic_known'] or 'UNKNOWN / TAMPERED'})")
    print(f"structural  : {'valid' if hdr['structurally_valid'] else hdr['structural_problems']}")
    print(f"nfunc/nfiles: {hdr['nfunc']} / {hdr['nfiles']}")
    print(f"parsed      : {len(funcs)} functions, {len(files)} files")
    print(f"classes     : {dict(by_class)}")
    print(f"packages    : {len(pkg_counts)}")
    print(ev_dir / "go_pclntab.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
