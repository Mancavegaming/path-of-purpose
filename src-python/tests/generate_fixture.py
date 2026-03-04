"""One-time script to generate the Base64+zlib PoB export code from sample XML."""

import base64
import zlib
from pathlib import Path

fixture_dir = Path(__file__).parent / "fixtures"
xml_path = fixture_dir / "sample_build.xml"
code_path = fixture_dir / "sample_build_code.txt"

xml_bytes = xml_path.read_bytes()
compressed = zlib.compress(xml_bytes)
code = base64.urlsafe_b64encode(compressed).decode("ascii")

code_path.write_text(code)
print(f"Generated export code ({len(code)} chars) → {code_path}")
print(f"First 80 chars: {code[:80]}...")
