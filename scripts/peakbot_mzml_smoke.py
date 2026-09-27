"""Minimal PeakBot smoke test; inspects one raw mzML and runs one dummy patch.

This is an interface/runtime check only. It does not read labels, choose
parameters, score detections, or inspect any test split.
"""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
import pymzml
from peakbot.Chromatogram import Chromatogram
from peakbot.peakbot import loadModelFile


def install_scan_time_compatibility_shim():
    """Bridge PeakBot's legacy `scan time` key to the mzML-standard key.

    The mzML source declares scan start time in minutes. PeakBot's parser
    multiplies its `scan time` value by 60, so this alias preserves seconds.
    The upstream checkout itself is not modified.
    """
    spectrum_class = pymzml.spec.Spectrum
    original_getitem = spectrum_class.__getitem__

    def compatible_getitem(self, key):
        if key == "scan time":
            value = original_getitem(self, key)
            if value is None:
                return original_getitem(self, "scan start time")
            return value
        return original_getitem(self, key)

    spectrum_class.__getitem__ = compatible_getitem


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mzml", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    install_scan_time_compatibility_shim()
    chromatogram = Chromatogram()
    chromatogram.parse_file(str(args.mzml))
    scans = chromatogram.MS1_list
    if not scans:
        raise RuntimeError("PeakBot parser returned no MS1 scans")

    model = loadModelFile(str(args.checkpoint))
    outputs = model.predict(np.zeros((1, 32, 128, 1), dtype=np.float32), verbose=0)
    shapes = [list(output.shape) for output in outputs]
    finite = [bool(np.isfinite(output).all()) for output in outputs]
    if shapes != [[1, 6], [1, 2], [1, 4]] or not all(finite):
        raise RuntimeError("Unexpected/non-finite model outputs: {} {}".format(shapes, finite))

    report = {
        "protocol": "peakbot-mzml-runtime-smoke-v1",
        "scope": "one raw mzML parser check plus one dummy tensor inference; no labels or metrics",
        "python": os.sys.version.split()[0],
        "tensorflow": tf.__version__,
        "mzml": str(args.mzml.resolve()),
        "checkpoint": str(args.checkpoint.resolve()),
        "ms1_scan_count": len(scans),
        "rt_min_seconds": float(min(scan.retention_time for scan in scans)),
        "rt_max_seconds": float(max(scan.retention_time for scan in scans)),
        "first_scan_peak_count": int(len(scans[0].mz_list)),
        "mzml_compatibility_shim": "map pymzml 'scan time' lookup to mzML 'scan start time'; source is minutes and upstream parser converts to seconds",
        "dummy_input_shape": [1, 32, 128, 1],
        "output_shapes": shapes,
        "outputs_finite": finite,
        "labels_read": False,
        "validation_metrics_computed": False,
        "test_data_read": False,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
        print("wrote {}".format(args.out.resolve()))


if __name__ == "__main__":
    main()
