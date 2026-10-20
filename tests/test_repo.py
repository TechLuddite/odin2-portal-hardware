import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def files():
    return [p for p in ROOT.rglob("*") if p.is_file() and not any(
        part in {".git", "private", "previews", "__pycache__"} for part in p.relative_to(ROOT).parts)]


class RepositoryTests(unittest.TestCase):
    def test_manifest_entry_points(self):
        m = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(m["id"], "io.github.techluddite.odin2-portal-hardware")
        self.assertEqual(m["schemaVersion"], 1)
        self.assertEqual(set(m["kinds"]), {"service", "bar-widget"})
        for path in m["entryPoints"].values():
            self.assertNotIn("..", path)
            self.assertTrue((ROOT / path).is_file())

    def test_no_symlinks_or_agent_instructions_in_distribution(self):
        for p in files():
            self.assertFalse(p.is_symlink(), str(p))
            self.assertNotIn(p.name.upper(), {"AGENTS.MD", "CLAUDE.MD", "GEMINI.MD"})

    def test_source_has_no_hidden_bidi_controls(self):
        banned = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
        for p in files():
            if p.suffix in {".png", ".gif", ".webp"}:
                continue
            self.assertFalse(any(ord(c) in banned for c in p.read_text()), str(p))

    def test_qml_text_is_plain(self):
        for p in ROOT.glob("*.qml"):
            for text in re.findall(r"\bText\s*\{([^{}]*)\}", p.read_text(), re.S):
                self.assertIn("textFormat: Text.PlainText", text, str(p))

    def test_backend_has_no_write_or_process_api(self):
        source = (ROOT / "backend/portal.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, {"write_text", "write_bytes", "unlink", "chmod", "mkdir", "replace"})
        self.assertNotIn("import subprocess", source)
        self.assertIn("stream.read(4097)", source)

    def test_reader_boundary_and_no_install_hooks(self):
        qml = (ROOT / "Service.qml").read_text()
        self.assertIn('"/usr/bin/python3", "-I", "-B"', qml)
        self.assertIn("text.length > 65536", qml)
        self.assertIn("interval: 5000", qml)
        self.assertFalse((ROOT / "install.sh").exists())
        self.assertFalse((ROOT / "requirements.txt").exists())

    def test_ci_permissions_and_pins(self):
        source = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("contents: read", source)
        self.assertNotIn("pull_request_target", source)
        for use in re.findall(r"uses:\s*(\S+)", source):
            self.assertRegex(use, r"@[0-9a-f]{40}$")
        self.assertIn("SCOUT_SHA: d484fb96482e74681adcc42d22b88fb6db26920f", source)
        self.assertIn("MARKETPLACE_SHA: fd5874893f5f4690570d2d88e8bcfb6df9f30184", source)

    def test_documentation_links(self):
        for p in files():
            if p.suffix != ".md":
                continue
            for target in re.findall(r"\]\(([^)]+)\)", p.read_text()):
                target = target.split("#")[0]
                if target and "://" not in target:
                    self.assertTrue((p.parent / target).exists(), (p, target))

    def test_distribution_file_limits(self):
        for p in files():
            self.assertLess(p.stat().st_size, 5 * 1024 * 1024, str(p))


if __name__ == "__main__":
    unittest.main()
