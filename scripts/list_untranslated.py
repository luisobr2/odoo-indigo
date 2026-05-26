"""List msgids without msgstr in en.po"""
import re

with open("addons/indigo_decors/i18n/en.po", encoding="utf-8") as f:
    content = f.read()

# Match: msgid "..."  followed by msgstr ""
pattern = re.compile(r'msgid "((?:[^"\\]|\\.)*)"\nmsgstr ""', re.MULTILINE)
matches = pattern.findall(content)
matches = [s for s in matches if s.strip()]
print("Untranslated count:", len(matches))
for s in matches:
    print(repr(s))
