import re


def unindent(multiline: str):
    "Unindents the first encountered indent in the string. Only triggers when the first character is '\\n'"
    if any(multiline) and multiline[0] == '\n':
        multiline = multiline.strip('\n')
        match = re.match(r'(\s\s)+\s*', multiline)
        if match:
            indent = match[0]
            multiline = multiline.replace(indent, '')
    return multiline
