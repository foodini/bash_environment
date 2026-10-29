#!/usr/bin/env python3
# coding: utf-8

#https://misc.flogisoft.com/bash/tip_colors_and_formatting

# usage: gen_prompt_text.py $? NO_ERROR_FORMAT ERROR_FORMAT
#
# A format is a comma-separated list of names from `codes` below and/or a
# 256-color number (0-255), e.g. "GREEN,BOLD" or "114" or "114,UNDER".
#
# Prints shell assignments for PROMPT_COL (the colored prompt, suitable for
# PS1) and PROMPT_BNW (the same text without color, used for the window
# title). The caller is expected to eval the output.

from datetime import datetime
import os
import sys

def esc_format(*args):
    return '\\033[{}m'.format(';'.join(args))

codes = {
    'RESET':       '0',
    'BLACK':       '30',
    'RED':         '31',
    'GREEN':       '32',
    'BROWN':       '33',
    'BLUE':        '34',
    'PURPLE':      '35',
    'CYAN':        '36',
    'WHITE':       '37',
    'UNDER':       '4',
    'NO_UNDER':    '24',
    'BOLD':        '1',
    'NO_BOLD':     '21',
    'DARK':        '2',
    'NO_DARK':     '22',
    'INVERT':      '7',
    'NO_INVERT':   '27'
}

previous_retval = sys.argv[1]
no_error_format = sys.argv[2]
error_format = sys.argv[3]

stack = [
    {'color': codes['WHITE'], 'bold': codes['NO_BOLD'],
    'dark': codes['NO_DARK'], 'under': codes['NO_UNDER']}
]

prompt_col = ''
prompt_bnw = ''
def concat(str, color_only=False):
    global prompt_col
    global prompt_bnw
    prompt_col += str
    if not color_only:
        prompt_bnw += str

def top_of_stack_to_result():
    e = stack[-1]
    # There's an ugly issue with some terminals, where they won't properly disable
    # bold. On Ubuntu, you'll likely see a double-underline when you send the
    # escape(21). I feel like doing a full reset at the beginning of EVERY output
    # might be sensible...
    if('bold' in e and e['bold'] == codes['NO_BOLD']):
        concat(esc_format(codes['RESET'], e['color'], e['dark'], e['under']), True)
    else:
        #The order the're written seems to matter. Bold won't work
        #unless at the end.
        concat(esc_format(e['color'], e['dark'], e['under'], e['bold']), True)

def push_state(**kwargs):
    entry = stack[-1].copy()
    entry.update(kwargs)
    stack.append(entry)
    top_of_stack_to_result()

def push_state_from_string(str):
    args = {}
    for fmt in str.split(','):
        if fmt.isdigit() and 0 <= int(fmt) <= 255:
            args['color'] = '38;5;' + fmt
        elif 'BOLD' in fmt:
            args['bold'] = codes[fmt]
        elif 'UNDER' in fmt:
            args['under'] = codes[fmt]
        elif 'DARK' in fmt:
            args['dark'] = codes[fmt]
        elif fmt in codes:
            args['color'] = codes[fmt]
    push_state(**args)

def pop_state():
    stack.pop()
    top_of_stack_to_result()

#I don't like underlined spaces, so this is an easy way to write
#one without the underline.
def space():
    push_state(under='24')
    concat(' ')
    pop_state()

def context():
    space()
    branch = os.environ.get('GIT_BRANCH', '')
    if branch:
        concat('(')
        concat(branch)
        concat(')')
        space()

def shell_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"

clock = datetime.now().strftime('%H:%M')
pwd = os.environ['PWD']
if len(pwd) > 37:
    pwd = '...' + pwd[-35:]

stale_xtras_file = False
env_dir = os.environ.get('BASH_ENVIRONMENT_DIR', '')
timestamp = os.environ.get('BASHRC_XTRAS_TIMESTAMP', '')
if env_dir and timestamp:
    try:
        bashrc_xtras_path = os.path.join(env_dir, 'bashrc_xtras')
        stale_xtras_file = int(os.stat(bashrc_xtras_path).st_mtime) > int(timestamp)
    except (OSError, ValueError):
        pass
stale_xtras_warning = (esc_format(codes['INVERT'], codes['RED']) + '⚙!' +
        esc_format(codes['NO_INVERT'], codes['WHITE']))

concat('\\[', True)
if stale_xtras_file:
    concat('{}╓'.format(stale_xtras_warning), True)
else:
    concat('╓', True)

if previous_retval == '0':
    push_state_from_string(no_error_format)
else:
    push_state_from_string(error_format)

concat(clock, True)
context()
concat(pwd)
pop_state()
concat('\\]', True)

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Everything enclosed in \[ & \] is ignored in computing the width of the prompt, for the sake of
# proper command wrapping. To this end, I closed out the stack BEFORE writing the second line:
# If you want any escape characters in the last line, enclose each in \[ & \].
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
top_of_stack_to_result()
if stale_xtras_file:
    concat('\\n{}╙'.format(stale_xtras_warning), True)
else:
    concat('\\n╙', True)

print('PROMPT_COL=' + shell_quote(prompt_col))
print('PROMPT_BNW=' + shell_quote(prompt_bnw))
