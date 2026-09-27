import io
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preflight import inspect_mzml


def fixture(modes, times=None, unit="UO:0000031", ref=False):
    times = times or list(range(1, len(modes) + 1))
    rows = []
    for mode, time in zip(modes, times):
        cv = '<cvParam accession="{}"/>'.format(mode) if mode else ''
        if ref:
            cv = '<referenceableParamGroupRef ref="g"/>'
        rows.append('<spectrum>{}<cvParam accession="MS:1000511" value="1"/>'
                    '<scanList><scan><cvParam accession="MS:1000016" value="{}" unitAccession="{}"/>'
                    '</scan></scanList><binaryDataArrayList><binaryDataArray><binary>AAA=</binary>'
                    '</binaryDataArray></binaryDataArrayList></spectrum>'.format(cv, time, unit))
    refs = '<referenceableParamGroup id="g"><cvParam accession="MS:1000128"/></referenceableParamGroup>' if ref else ''
    return io.BytesIO(('<mzML xmlns="http://psi.hupo.org/ms/mzml">{}<spectrumList count="{}">{}</spectrumList></mzML>'
                       .format(refs, len(rows), ''.join(rows))).encode())


class Tests(unittest.TestCase):
    def test_profile_minutes(self):
        r = inspect_mzml(fixture(["MS:1000128"] * 2), "test")
        self.assertTrue(r["profile_mode_gate"])
        self.assertTrue(r["metadata_integrity_gate"])
        self.assertEqual(r["rt_max_seconds"], 120)

    def test_centroid(self):
        r = inspect_mzml(fixture(["MS:1000127"]), "test")
        self.assertFalse(r["profile_mode_gate"])
        self.assertTrue(r["metadata_integrity_gate"])

    def test_mixed_unknown(self):
        for modes in [[None], ["MS:1000128", "MS:1000127"]]:
            self.assertFalse(inspect_mzml(fixture(modes), "test")["profile_mode_gate"])

    def test_unit_seconds(self):
        self.assertEqual(inspect_mzml(fixture(["MS:1000128"], unit="UO:0000010"), "test")["rt_max_seconds"], 1)

    def test_unknown_unit(self):
        self.assertFalse(inspect_mzml(fixture(["MS:1000128"], unit="unknown"), "test")["metadata_integrity_gate"])

    def test_time_order(self):
        self.assertFalse(inspect_mzml(fixture(["MS:1000128"] * 2, times=[2, 1]), "test")["metadata_integrity_gate"])

    def test_reference_group(self):
        self.assertTrue(inspect_mzml(fixture([None], ref=True), "test")["profile_mode_gate"])

    def test_invalid_xml(self):
        with self.assertRaises(Exception):
            inspect_mzml(io.BytesIO(b"<mzML>"), "bad")


if __name__ == "__main__":
    unittest.main()
