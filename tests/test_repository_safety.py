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
FORBIDDEN_LIVE_JSON_NAMES = {"credentials.json", "secrets.json", "auth.json", "cookies.json"}
FORBIDDEN_LIVE_JSON_SUFFIXES = ("_principal_binding.json", "_device_binding.json")
PRIVATE_KEY_MARKERS = tuple(
    "-----BEGIN " + kind + "PRIVATE KEY-----"
    for kind in ("", "RSA ", "EC ", "OPENSSH ")
)


def cp1252_byte(ch):
    try:
        encoded = ch.encode("cp1252")
        if len(encoded) == 1:
            return encoded[0]
    except UnicodeEncodeError:
        pass
    codepoint = ord(ch)
    if 0x80 <= codepoint <= 0x9F:
        return codepoint
    if codepoint <= 0xFF:
        return codepoint
    return None


def reconstructable_mojibake_count(text):
    count = 0
    i = 0
    while i < len(text):
        lead = cp1252_byte(text[i])
        length = 0
        if lead is not None:
            if 0xC2 <= lead <= 0xDF:
                length = 2
            elif 0xE0 <= lead <= 0xEF:
                length = 3
            elif 0xF0 <= lead <= 0xF4:
                length = 4
        if length and i + length <= len(text):
            values = [cp1252_byte(ch) for ch in text[i:i + length]]
            if None not in values and all(0x80 <= value <= 0xBF for value in values[1:]):
                try:
                    bytes(values).decode("utf-8")
                except UnicodeDecodeError:
                    pass
                else:
                    count += 1
                    i += length
                    continue
        i += 1
    return count


class RepositorySafetyTests(unittest.TestCase):
    def tracked_candidate_files(self):
        for path in REPO.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                yield path

    def test_no_forbidden_operational_artifacts(self):
        bad = []
        for path in self.tracked_candidate_files():
            name = path.name.lower()
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                bad.append(str(path.relative_to(REPO)))
            elif name in FORBIDDEN_LIVE_JSON_NAMES or name.endswith(FORBIDDEN_LIVE_JSON_SUFFIXES):
                bad.append(str(path.relative_to(REPO)))
        self.assertEqual(bad, [], f"forbidden operational artifacts: {bad}")


    def test_all_public_text_is_clean_utf8(self):
        findings = []
        for path in self.tracked_candidate_files():
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
                "README.md", "CHANGELOG.md", "NOTICE", "LICENSE", ".gitignore", ".gitattributes"
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as exc:
                findings.append(f"{path.relative_to(REPO)}: invalid UTF-8: {exc}")
                continue
            if "\ufffd" in text:
                findings.append(f"{path.relative_to(REPO)}: Unicode replacement character")
            count = reconstructable_mojibake_count(text)
            if count:
                findings.append(f"{path.relative_to(REPO)}: {count} reconstructable mojibake sequence(s)")
        self.assertEqual(findings, [], "\n".join(findings))

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
