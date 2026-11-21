"""Offline regression checks for the Python decoder embedded in ext-tools.aardio.

Run with a Python environment containing zxing-cpp and Pillow. Test images stay
inside the ignored scripts/_qr-read-check directory; no RPC service is started.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "projects/00-rpc-server/ext-tools.aardio",
    ROOT / "projects/00-rpc-server/dist/ext-tools.aardio",
    ROOT / "tools/00-ext-tools.aardio",
]
SOURCE = SOURCES[0].read_text(encoding="utf-8-sig")
HANDLER = SOURCE.split('api["/api/qr/read"] = ', 1)[1].split(
    "// ========== 3.", 1
)[0]
DECODER = HANDLER.split("var decoder = /******\n", 1)[1].split("\n******/;", 1)[0]
ARTIFACTS = ROOT / "scripts/_qr-read-check"

try:
    from PIL import Image
    import zxingcpp
except ImportError:
    Image = zxingcpp = None


def decode(path, without_site=False):
    args = [sys.executable, "-I", "-X", "utf8"]
    if without_site:
        args.append("-S")
    result = subprocess.run(
        args + ["-c", DECODER],
        input=json.dumps({"path": str(path)}, ensure_ascii=False) + "\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def barcode_image(text, format=None):
    barcode = zxingcpp.create_barcode(text, format or zxingcpp.BarcodeFormat.QRCode)
    bitmap = zxingcpp.write_barcode_to_image(barcode, scale=6)
    pixels = memoryview(bitmap)
    return Image.frombytes("L", (pixels.shape[1], pixels.shape[0]), pixels.tobytes())


class DecoderContractTests(unittest.TestCase):
    def test_mirrors_and_encoding(self):
        original = SOURCES[0].read_bytes()
        self.assertTrue(original.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(original.count(b"\n"), original.count(b"\r\n"))
        for path in SOURCES[1:]:
            self.assertEqual(original, path.read_bytes(), str(path))

    def test_handler_has_no_remote_fallback(self):
        for forbidden in ("inet.http", "fileurl", "read-qr-code", "process.execute"):
            self.assertNotIn(forbidden, HANDLER)
        self.assertIn('io.joinpath(io._exedir, ".venv\\Scripts\\python.exe")', HANDLER)
        self.assertIn('p.write(JSON.stringify({path=path}) ++ string.char(10))', HANDLER)
        compile(DECODER, "embedded-qr-decoder", "exec")

    def test_missing_dependencies(self):
        self.assertEqual(
            decode(ARTIFACTS / "not-needed.png", without_site=True)["error"],
            "decoder_unavailable",
        )
        self.assertFalse(decode(ARTIFACTS / "not-needed.png", without_site=True)["ok"])


@unittest.skipUnless(Image and zxingcpp, "Install zxing-cpp and Pillow to test real decoding")
class LocalDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        cls.text = "Local QR / 本地二维码\nquote ' & % ! 😀"
        cls.path = ARTIFACTS / "中文 ' & % ! ;.png"
        image = barcode_image(cls.text)
        image.save(cls.path)
        cls.rotated = ARTIFACTS / "rotated.png"
        image.rotate(90, expand=True).save(cls.rotated)
        cls.blank = ARTIFACTS / "blank.png"
        Image.new("RGB", (400, 400), "white").save(cls.blank)
        cls.invalid = ARTIFACTS / "invalid.png"
        cls.invalid.write_text("This is not an image.", encoding="utf-8")
        cls.linear = ARTIFACTS / "linear.png"
        barcode_image("not-a-qr", zxingcpp.BarcodeFormat.Code128).save(cls.linear)
        cls.multi = ARTIFACTS / "multi.png"
        other = barcode_image("second QR")
        canvas = Image.new("L", (image.width + other.width + 60, max(image.height, other.height) + 40), "white")
        canvas.paste(image, (10, 20))
        canvas.paste(other, (image.width + 50, 20))
        canvas.save(cls.multi)

    def assert_failure(self, path, error):
        result = decode(path)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], error)

    def test_unicode_path_and_exact_text(self):
        result = decode(self.path)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["path"], str(self.path))
        self.assertEqual(result["text"], self.text)
        self.assertEqual(result["texts"], [self.text])

    def test_rotated_qr(self):
        self.assertEqual(decode(self.rotated)["text"], self.text)

    def test_multiple_qr_codes(self):
        result = decode(self.multi)
        self.assertTrue(result["ok"], result)
        self.assertCountEqual(result["texts"], [self.text, "second QR"])

    def test_blank_image(self):
        self.assert_failure(self.blank, "qr_not_found")

    def test_non_qr_barcode(self):
        self.assert_failure(self.linear, "qr_not_found")

    def test_invalid_image(self):
        self.assert_failure(self.invalid, "invalid_image")

    def test_missing_image(self):
        self.assert_failure(ARTIFACTS / "missing-image.png", "file_not_found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
