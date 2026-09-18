import pathlib
import re
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".key", ".p12", ".pfx", ".jks", ".keystore",
    ".sqlite", ".sqlite3", ".db", ".entitybackup",
    ".exe", ".dll", ".ipa", ".apk", ".aab",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".cfg", ".yml", ".yaml"}
PRIVATE_KEY_MARKERS = tuple(
    "-----BEGIN " + kind + "PRIVATE KEY-----"
    for kind in ("", "RSA ", "EC ", "OPENSSH ")
)


class RepositorySafetyTests(unittest.TestCase):
    def tracked_candidate_files(self):
        for path in REPO.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                yield path

    def test_no_forbidden_operational_artifacts(self):
        bad = []
        for path in self.tracked_candidate_files():
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                bad.append(str(path.relative_to(REPO)))
        self.assertEqual(bad, [], f"forbidden operational artifacts: {bad}")

    def test_no_private_key_blocks_or_btg_absolute_paths(self):
        findings = []
        drive_pattern = re.compile(r"(?i)\b[A-Z]:\\")
        for path in self.tracked_candidate_files():
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if any(marker in text for marker in PRIVATE_KEY_MARKERS):
                findings.append(f"{path.relative_to(REPO)}: private-key block")
            if drive_pattern.search(text):
                findings.append(f"{path.relative_to(REPO)}: absolute Windows path")
        self.assertEqual(findings, [], "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
