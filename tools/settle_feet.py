"""Re-seat the hamster's feet on top of the wheel ring in assets/props.json (no sheets needed).
Usage: python tools/settle_feet.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from make_props import settle_feet  # noqa: E402

path = Path(__file__).resolve().parent.parent / "assets" / "props.json"
d = json.loads(path.read_text())
settle_feet(d["wheel"])
path.write_text(json.dumps(d))
print("feet settled on the wheel ring")
