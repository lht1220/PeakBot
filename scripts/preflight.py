"""Stdlib-only raw mzML/source qualification. No labels, inference or metrics.

ZIP/directory mode reads ALL raw sample XML metadata (not validation-only).
Encoded intensity arrays are streamed as XML bytes, never decoded as signals.
Centroid input fails the native profile-mode preprocessing gate.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODES = {"MS:1000128": "profile", "MS:1000127": "centroid"}
UNITS = {"UO:0000031": 60.0, "UO:0000010": 1.0}
SOURCES = {"PeakBot": "c5df4f0d12db5165cd8714bebbe8941cc4c8bfc5",
           "PeakBot_Example": "24ff3e2561018a2a71584c2cccbb42a154188012"}
WEIGHTS = {
    "MTBLS1358": "61c4ffa18e839ff37a2664052f23ee751608e61ca00d9e6f484b94fcdb15170d",
    "MTBLS797": "d3410aa1ef92e1b552130035c44a2bd705ce68610ae22ac1aac9c37fbf19ddbc",
    "MTBLS868": "b09207a98b5b7fcc9c650748cd54a1181c76cfc95190be7caffce350f84602ae",
    "PHM": "d54faa80649cb5d10dc1f387c886cccd36993fb7cc19511d2413410fe4881659",
    "WheatEar": "b209fb06133d61d618280194967662e4452d61a1d1ea2e4df69b7e268188a684"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tag(elem):
    return elem.tag.rsplit("}", 1)[-1]


class HashedReader:
    def __init__(self, stream):
        self.stream, self.hash = stream, hashlib.sha256()

    def read(self, size=-1):
        b = self.stream.read(size)
        self.hash.update(b)
        return b


def inspect_mzml(stream, name):
    reader = HashedReader(stream)
    modes, levels, units = Counter(), Counter(), Counter()
    groups, stack = {}, []
    parsed = invalid_level = missing_time = nonmonotonic = picking = 0
    declared = rt_min = rt_max = previous = None
    for event, elem in ET.iterparse(reader, events=("start", "end")):
        t = tag(elem)
        if event == "start":
            stack.append(elem)
            if t == "spectrumList":
                declared = int(elem.attrib["count"]) if "count" in elem.attrib else None
            continue
        if t == "referenceableParamGroup":
            groups[elem.attrib.get("id")] = [dict(x.attrib) for x in elem if tag(x) == "cvParam"]
        elif t == "processingMethod":
            picking += sum(x.attrib.get("accession") == "MS:1000035" for x in elem.iter())
        elif t == "binary":
            elem.clear()
        elif t == "spectrum":
            parsed += 1
            cvs = [dict(x.attrib) for x in elem if tag(x) == "cvParam"]
            for x in elem:
                if tag(x) == "referenceableParamGroupRef":
                    cvs.extend(groups.get(x.attrib.get("ref"), []))
            ms = [x.get("value") for x in cvs if x.get("accession") == "MS:1000511"]
            try:
                level = int(ms[0]) if len(ms) == 1 else None
            except (TypeError, ValueError):
                level = None
            if level is None:
                invalid_level += 1
            else:
                levels[str(level)] += 1
            if level == 1:
                found = {MODES[x["accession"]] for x in cvs if x.get("accession") in MODES}
                modes[next(iter(found)) if len(found) == 1 else ("conflicting" if found else "unknown")] += 1
                times = [x.attrib for x in elem.iter() if x.attrib.get("accession") == "MS:1000016"]
                rt = None
                if len(times) == 1:
                    unit = times[0].get("unitAccession", "missing")
                    units[unit] += 1
                    try:
                        rt = float(times[0]["value"]) * UNITS[unit]
                        if not math.isfinite(rt) or rt < 0:
                            rt = None
                    except (KeyError, ValueError, TypeError):
                        pass
                if rt is None:
                    missing_time += 1
                else:
                    rt_min = rt if rt_min is None else min(rt_min, rt)
                    rt_max = rt if rt_max is None else max(rt_max, rt)
                    if previous is not None and rt <= previous:
                        nonmonotonic += 1
                    previous = rt
            elem.clear()
            stack[-2].remove(elem)
        stack.pop()
    ms1 = levels.get("1", 0)
    return {"name": name, "sha256": reader.hash.hexdigest(), "declared_spectra": declared,
            "parsed_spectra": parsed, "ms_level_counts": dict(levels),
            "unknown_ms_level_count": invalid_level, "ms1_spectrum_mode_counts": dict(modes),
            "ms1_time_unit_counts": dict(units), "ms1_missing_or_invalid_time_count": missing_time,
            "ms1_non_increasing_time_count": nonmonotonic, "rt_min_seconds": rt_min,
            "rt_max_seconds": rt_max, "peak_picking_processing_steps": picking,
            "profile_mode_gate": ms1 > 0 and modes.get("profile", 0) == ms1,
            "metadata_integrity_gate": declared is not None and declared == parsed and ms1 > 0
                                       and invalid_level == missing_time == nonmonotonic == 0}


def repository_check():
    rows = []
    for name, expected in SOURCES.items():
        folder = ROOT / "source" / name
        commit, dirty = None, None
        try:
            top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=str(folder),
                                          universal_newlines=True, encoding="utf-8", stderr=subprocess.PIPE).strip()
            if Path(top).resolve() == folder.resolve():
                commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(folder),
                                                 universal_newlines=True, encoding="utf-8").strip()
                dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=str(folder),
                                                     universal_newlines=True, encoding="utf-8").strip())
        except (OSError, subprocess.CalledProcessError):
            pass
        rows.append({"source": name, "commit": commit, "expected_commit": expected, "dirty": dirty,
                     "passed": commit == expected and dirty is False and (folder / "README.md").is_file()})
    weights = []
    for name, expected in WEIGHTS.items():
        p = ROOT / "source/PeakBot_Example/PreTrainedModels" / ("PBmodel_" + name + ".model.h5")
        actual = digest(p) if p.is_file() else None
        weights.append({"name": name, "sha256": actual, "expected_sha256": expected,
                        "passed": actual == expected})
    return {"sources": rows, "weights": weights, "passed": all(x["passed"] for x in rows + weights)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--mzml", type=Path)
    group.add_argument("--zip", dest="archive", type=Path)
    group.add_argument("--mzml-dir", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    if (args.out_dir / "report.json").exists():
        ap.error("report.json exists; choose a new out-dir to preserve history")
    repo = repository_check()
    files, errors = [], []
    archive_id = None

    def audit(stream, name):
        try:
            r = inspect_mzml(stream, name)
            files.append(r)
            print("{}: modes={}".format(name, r["ms1_spectrum_mode_counts"]), flush=True)
        except (ET.ParseError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            errors.append({"name": name, "error": str(exc)})

    if args.archive:
        archive_id = {"path": str(args.archive.resolve()), "size_bytes": args.archive.stat().st_size,
                      "sha256": digest(args.archive)}
        with zipfile.ZipFile(args.archive) as z:
            for member in sorted(z.infolist(), key=lambda x: x.filename):
                if member.filename.lower().endswith(".mzml"):
                    with z.open(member) as stream:
                        audit(stream, member.filename)
    else:
        paths = [args.mzml] if args.mzml else sorted(p for p in args.mzml_dir.rglob("*")
                                                   if p.is_file() and p.suffix.lower() == ".mzml")
        for path in paths:
            with path.open("rb") as stream:
                audit(stream, str(path.resolve()))
    metadata_ok = bool(files) and not errors and all(x["metadata_integrity_gate"] for x in files)
    profile_ok = bool(files) and not errors and all(x["profile_mode_gate"] for x in files)
    ready = repo["passed"] and metadata_ok and profile_ok
    reasons = []
    if not repo["passed"]:
        reasons.append("source checkout/commits or pretrained weights not qualified")
    if not metadata_ok:
        reasons.append("missing/invalid metadata, RT units, scan counts or ordering")
    if not profile_ok:
        reasons.append("not exclusively MS1 profile spectra; native PeakBot benchmark blocked")
    summary = {"status": "PASS" if ready else "BLOCKED", "file_count": len(files),
               "profile_file_count": sum(x["profile_mode_gate"] for x in files),
               "centroid_file_count": sum(x["ms1_spectrum_mode_counts"].get("centroid", 0) > 0 for x in files),
               "metadata_integrity_passed": metadata_ok, "native_peakbot_inference_allowed": ready,
               "blocking_reasons": reasons}
    report = {"protocol": "peakbot-raw-input-qualification-v1",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "raw XML metadata; ZIP/directory scans ALL supplied sample metadata",
              "labels_read": False, "split_files_read": False, "intensity_arrays_decoded": False,
              "model_inference_run": False, "test_metrics_computed": False,
              "archive_identity": archive_id, "repository": repo, "files": files, "errors": errors,
              "summary": summary, "script_sha256": digest(Path(__file__)),
              "notes": ["Parser/dummy smoke is not native profile-pipeline qualification.",
                        "Stored spectrum CVs override historical vendor filter strings.",
                        "Centroid interpolation cannot recover measured profile spectra.",
                        "Metadata PASS does not qualify label mapping or performance claims."]}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.out_dir / "report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print("wrote {}".format(output.resolve()), flush=True)
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
