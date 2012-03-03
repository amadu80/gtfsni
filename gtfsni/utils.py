
import re

rx_strip = re.compile(r'[^-\w\s,()/]').sub
rx_hyphenate = re.compile(r'[-\s,()/]+').sub

def slugify(s):
    return rx_hyphenate('-', rx_strip('', s.lower()).strip()).strip('-')
