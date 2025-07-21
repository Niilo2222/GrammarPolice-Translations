import os
import xml.etree.ElementTree as ET
from pathlib import Path
from string import Template
import re

LANGUAGE_ROOT = Path("grammar")
OUTPUT_ROOT = Path("guides")

NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}

INLINE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <title>${LANG} Phrase Guide</title>
    <style>
        body {
            font-family: sans-serif;
            background-color: #1e1e1e;
            color: #eee;
            padding: 2em;
        }
        .action {
            background-color: #007acc;
            color: white;
            padding: 0.75em 1em;
            margin: 0.5em 0;
            cursor: pointer;
            font-weight: bold;
            border-radius: 5px;
        }
        .phrases {
            display: none;
            background-color: #2e2e2e;
            padding: 0.5em 1em;
            border-left: 3px solid #007acc;
            border-radius: 0 0 5px 5px;
        }
        .phrases.visible {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 0.25em 1em;
        }
        .phrase {
            color: #ffffff;
            margin: 0.25em 0;
        }
    </style>
</head>
<body>
    <h1>${LANG} Command Phrase Guide</h1>
    <div id=\"actions\">
        ${ACTIONS}
    </div>
    <script>
        document.querySelectorAll('.action').forEach(header => {
            header.addEventListener('click', () => {
                const next = header.nextElementSibling;
                next.classList.toggle('visible');
            });
        });
    </script>
</body>
</html>""")

def parse_command_file(command_path):
    tree = ET.parse(command_path)
    root = tree.getroot()
    name = root.findtext("Name")
    phrases = [el.text for el in root.find("Phrases") or []]
    return name, phrases

def parse_action_file(action_path):
    tree = ET.parse(action_path)
    root = tree.getroot()
    name = root.findtext("Name")
    command = root.find("Commands")
    command_name = command[0].text if command is not None and len(command) > 0 else None
    phrases = [el.text for el in root.find("Phrases") or []]
    target = root.findtext("Target")
    return name, command_name, phrases, target

def build_language_model(lang_path):
    command_phrases = {}
    action_lookup = {}
    commands_dir = lang_path / "default/commands"
    actions_dir = lang_path / "default/actions"

    for f in commands_dir.glob("*.xml"):
        cmd_name, phrases = parse_command_file(f)
        command_phrases[cmd_name] = phrases

    for f in actions_dir.glob("*.xml"):
        act_name, cmd_name, act_phrases, target = parse_action_file(f)
        if not cmd_name and act_name in command_phrases:
            cmd_name = act_name
        if act_name not in action_lookup:
            action_lookup[act_name] = {
                "name": act_name,
                "command": cmd_name,
                "target": target,
                "action_phrases": act_phrases,
                "command_phrases": command_phrases.get(cmd_name, [])
            }

    return action_lookup

def extract_numeric(word_list):
    total = 0
    for word in word_list:
        if word not in NUM_WORDS:
            return None
        val = NUM_WORDS[word]
        if val >= 20 and total % 10 != 0:
            return None
        total += val
    return total

def find_ten_codes(phrases):
    matches = set()
    for p in phrases:
        words = p.lower().split()
        for i in range(len(words) - 1):
            if words[i] in ("ten", "eleven"):
                candidate = extract_numeric(words[i + 1:i + 3])
                if candidate is not None:
                    prefix = "10" if words[i] == "ten" else "11"
                    matches.add(f"{prefix}-{candidate}")
    return sorted(matches)

def generate_html(lang_code, action_map):
    blocks = []
    for act in sorted(action_map.values(), key=lambda x: x["name"]):
        full_phrases = []
        if act["action_phrases"]:
            for cp in act["command_phrases"]:
                for ap in act["action_phrases"]:
                    full_phrases.append(f"{cp} {ap}")
        else:
            full_phrases.extend(act["command_phrases"])

        aliases = find_ten_codes(full_phrases)
        label = act["name"].upper()
        if aliases:
            label += f" ({', '.join(aliases)})"

        phrases_html = "\n".join(f"<div class='phrase'>{p}</div>" for p in full_phrases)

        blocks.append(f"""
            <div class='action'>{label}</div>
            <div class='phrases'>
                {phrases_html}
            </div>
        """)

    return INLINE_TEMPLATE.substitute(LANG=lang_code, ACTIONS="\n".join(blocks))

def generate_all():
    for lang_dir in LANGUAGE_ROOT.iterdir():
        if not lang_dir.is_dir():
            continue
        actions = build_language_model(lang_dir)
        html = generate_html(lang_dir.name, actions)
        output_path = OUTPUT_ROOT / f"{lang_dir.name}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

if __name__ == "__main__":
    generate_all()
