#!/usr/bin/env python3
# coding: utf-8

#https://misc.flogisoft.com/bash/tip_colors_and_formatting

import argparse
from datetime import datetime
import os
import sys

# gen_prompt_text [T|F] $? GREEN,BOLD BLUE,UNDER origin/master 

#esc_format = '\\[\\033[{}m\\]'
#esc_format = '\[\033[{}m\]'
#esc_format = '\033[{}m'
#esc_format = '\\033[{}m'
#esc_format = '[{}]'

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

in_color = sys.argv[1] == 'T'
previous_retval = sys.argv[2]
no_error_format = sys.argv[3]
error_format = sys.argv[4]

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
        if 'BOLD' in fmt:
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
    emit_branch = 'GIT_BRANCH' in os.environ and os.environ['GIT_BRANCH']
    emit_robot = (
            'ANKI_ROBOT_ALIAS' in os.environ and
            'ANKI_ROBOT_COLOR' in os.environ and
            os.environ['ANKI_ROBOT_ALIAS'])
    if emit_branch or emit_robot:
        concat('(')
        if emit_branch:
            concat(os.environ['GIT_BRANCH'])
        if emit_robot:
            if emit_branch:
                space()
            push_state_from_string(os.environ['ANKI_ROBOT_COLOR'])
            concat(os.environ['ANKI_ROBOT_ALIAS'])
            pop_state()
        concat(')')
        space()

clock = datetime.now().strftime('%H:%M')
pwd = os.environ['PWD']
if len(pwd) > 37:
    pwd = '...' + pwd[-35:]

bashrc_xtras_path = os.path.join(os.environ['HOME'], '.bashrc_xtras')
stale_xtras_file = False
if 'BASHRC_XTRAS_TIMESTAMP' in os.environ:
    stale_xtras_file = os.stat(bashrc_xtras_path)[8] > int(os.environ['BASHRC_XTRAS_TIMESTAMP'])
stale_xtras_warning = (esc_format(codes['INVERT'], codes['RED']) + '⚙!' +
        esc_format(codes['NO_INVERT'], codes['WHITE']))

concat('\[', True)
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
concat('\]', True)

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

if in_color:
    esc_format('0')

filename = (os.environ['HOME'] + '/tmp/prompt_' +
        str(os.getppid()) + '.sh')
with open(filename, 'w') as fd:
    fd.write(u'export PROMPT_COL="' + prompt_col + u'"' + u'\n')
    fd.write('export PROMPT_BNW="' + prompt_bnw + '"' + '\n')
