# Based on https://github.com/1j01/jspaint/blob/4a9163fb6dbb321ef07ed85bb5d5ce980e1a4866/localization/parse-rc-file.js
# Originally based on https://github.com/evernote/serge/blob/master/lib/Serge/Engine/Plugin/parse_rc.pm

import re

def parse_rc_file(rc_file_text: str) -> list[str]:
    """
    Parses a Windows RC file and returns a list of strings.
    """
    strings = []
    menu = dialog = stringtable = False
    block_level = 0
    id_str = dialog_id = hint = orig_str = None

    for line in rc_file_text.splitlines():
        norm_line = re.sub(r'[\t ]+', ' ', line.strip())
        norm_line = re.sub(r'\/\/.*$', '', norm_line)

        if norm_line.endswith(' MENU'):
            menu = True

        dialog_match = re.match(r'^(\w+) (DIALOG|DIALOGEX) ', norm_line)
        if dialog_match:
            dialog_id = dialog_match.group(1)
            dialog = True

        if norm_line == 'STRINGTABLE':
            stringtable = True

        if norm_line == 'BEGIN':
            block_level += 1

        if norm_line == 'END':
            block_level -= 1
            if block_level == 0:
                menu = dialog = dialog_id = stringtable = None

        if dialog and not block_level:
            match = re.match(r'^[\t ]*(CAPTION)[\t ]+(L?"(.*?("")*)*?")', line)
            if match:
                id_str = f"{dialog_id}:{match.group(1)}"
                hint = f"{dialog_id} {match.group(1)}"
                orig_str = match.group(2)

        elif (menu or dialog) and block_level:
            match = re.match(r'^[\t ]*(\w+)[\t ]+(L?"([^"]*?("")*)*?")(,[\t ]*(\w+)){0,1}', line)
            if match:
                id_str = match.group(6)
                hint = f"{match.group(1)} {match.group(6)}" if match.group(6) else match.group(1)
                orig_str = match.group(2)

        else:
            match = re.search(r'(L?"(.*)")', line)
            if match:
                orig_str = match.group(0)
            else:
                match = re.match(r'^[\t ]*(\w+)[\t ]*(\/\/.*)*$', line)
                if match:
                    id_str = match.group(1)
                else:
                    match = re.match(r'^[\t ]*(L?"(.*)")', line)
                    if id_str and match:
                        hint = id_str
                        orig_str = match.group(1)
                    else:
                        id_str = None

        if orig_str:
            str = orig_str

            wide = str.startswith('L')
            str = re.sub(r'^L?"(.*)"$', r'\1', str)
            str = str.replace(r'\r', '\r').replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\\"', '"')
            if wide:
                str = re.sub(r'\\x([0-9a-fA-F]{4})', lambda match: chr(int(match.group(1), 16)), str)

            strings.append(str)

            id_str = hint = orig_str = None

    return strings
