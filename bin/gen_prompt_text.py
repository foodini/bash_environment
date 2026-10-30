#!/usr/bin/env python3
# coding: utf-8

# usage: gen_prompt_text.py LAST_EXIT_CODE PROMPT_STYLE ERROR_STYLE
#
# A style is a 256-color number (0-255), optionally followed by attributes,
# separated by commas: e.g. "114" or "196,bold,underline". The attributes are
# bold, dim, italic, underline and inverse. An empty style means the terminal's
# default. PROMPT_STYLE is used when LAST_EXIT_CODE is 0, ERROR_STYLE otherwise.
# ERROR_STYLE must include a color; without one, the prompt complains.
# Anything unrecognized in a style is reported (on stderr, so at every prompt)
# and otherwise ignored.
#
# Prints shell assignments for the caller to eval:
#   PROMPT_COL  the prompt, with color, ready for PS1
#   PROMPT_BNW  the same text without color or decoration, for the window title
#
# How styling works:
#   Styles nest with `with`, e.g.
#       with color(114), bold(True):
#           text('hello')
#   Entering a block pushes a modified copy of the current style; leaving it
#   pops back to the previous one. Nothing is sent to the terminal until text
#   is written. At that point, only the attributes that differ from what the
#   terminal already has are sent.
#
#   The prompt starts and ends with a full reset, so it never inherits colors
#   left behind by the previous command, and the text typed after it is in the
#   terminal's default color.
#
# TODO: The Mac is still on python 3.9. Python 3.10 allows a parenthesized
#       `with (a, b, c):` that can span lines. Until every machine runs 3.10+,
#       long `with` lists have to be written as nested `with` blocks instead.
#       Once they all do, nested `with`s can be collapsed.

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import os
import sys

# Bash's PS1 decodes \033 to ESC. Every escape sequence must be wrapped in \[ \]
# so readline knows it takes no space on screen; nothing else may be.
ESC = r'\033['
NONPRINTING_START = r'\['
NONPRINTING_END = r'\]'


@dataclass(frozen=True)
class Style:
  color: int = None    # 256-color number; None means the terminal's default
  bold: bool = False
  dim: bool = False
  italic: bool = False
  underline: bool = False
  inverse: bool = False


DEFAULT = Style()

style_stack = [DEFAULT]    # the style text would be written in
sent_style = DEFAULT     # the style the terminal is actually in
prompt_col = ''
prompt_bnw = ''


# sgr = "Select Graphic Rendition," a subset of ANSI escape sequences that formats
#     and colors text on terminals and terminal emulators.
def sgr(codes):
  """An escape sequence that sets the given SGR codes, hidden from readline."""
  return NONPRINTING_START + ESC + ';'.join(codes) + 'm' + NONPRINTING_END


def changes_needed(old, new):
  """The SGR codes that take the terminal from style `old` to style `new`."""
  codes = []
  # Bold and dim share one "off" code, 22, which turns off both. (Code 21
  # looks like "bold off" but many terminals treat it as double underline.)
  # So if either has to go off, send 22 and turn back on whichever stays.
  if (old.bold and not new.bold) or (old.dim and not new.dim):
    codes.append('22')
    old = replace(old, bold=False, dim=False)
  if new.bold and not old.bold:
    codes.append('1')
  if new.dim and not old.dim:
    codes.append('2')
  if new.italic != old.italic:
    codes.append('3' if new.italic else '23')
  if new.underline != old.underline:
    codes.append('4' if new.underline else '24')
  if new.inverse != old.inverse:
    codes.append('7' if new.inverse else '27')
  if new.color != old.color:
    codes.append('39' if new.color is None else '38;5;{}'.format(new.color))
  return codes


def text(s, title=True):
  """Writes s in the current style. title=False leaves it out of PROMPT_BNW."""
  global prompt_col, prompt_bnw, sent_style
  codes = changes_needed(sent_style, style_stack[-1])
  if codes:
    prompt_col += sgr(codes)
    sent_style = style_stack[-1]
  prompt_col += s
  if title:
    prompt_bnw += s


def reset():
  """Puts the terminal back in its default state, whatever it was in."""
  global prompt_col, sent_style
  prompt_col += sgr(['0'])
  sent_style = DEFAULT


def newline():
  global prompt_col
  prompt_col += r'\n'


@contextmanager
def styled(**changes):
  style_stack.append(replace(style_stack[-1], **changes))
  try:
    yield
  finally:
    style_stack.pop()


def color(number):
  return styled(color=number)

def bold(on):
  return styled(bold=on)

def dim(on):
  return styled(dim=on)

def italic(on):
  return styled(italic=on)

def underline(on):
  return styled(underline=on)

def inverse(on):
  return styled(inverse=on)


def space():
  # I don't like underlined spaces.
  with underline(False):
    text(' ')


ATTRIBUTES = ('bold', 'dim', 'italic', 'underline', 'inverse')


def parse_style(spec, description):
  """The style changes a spec like "196,bold,underline" asks for, as a dict
  for styled(). Complains on stderr about anything it doesn't understand."""
  changes = {}
  for word in spec.split(','):
    word = word.strip().lower()
    if not word:
      continue
    if word.isdigit() and 0 <= int(word) <= 255:
      changes['color'] = int(word)
    elif word in ATTRIBUTES:
      changes[word] = True
    else:
      sys.stderr.write('gen_prompt_text: {} "{}": don\'t know "{}" (expected a color '
                       '0-255 or one of: {})\n'.format(
                           description, spec, word, ', '.join(ATTRIBUTES)))
  return changes


def xtras_is_stale():
  """True if bashrc_xtras changed since this shell loaded it."""
  env_dir = os.environ.get('BASH_ENVIRONMENT_DIR', '')
  loaded_at = os.environ.get('BASHRC_XTRAS_TIMESTAMP', '')
  if not env_dir or not loaded_at:
    return False
  try:
    modified_at = int(os.stat(os.path.join(env_dir, 'bashrc_xtras')).st_mtime)
    return modified_at > int(loaded_at)
  except (OSError, ValueError):
    return False


last_exit_code = sys.argv[1]
normal_prompt_style = parse_style(sys.argv[2], 'prompt style')
error_prompt_style = parse_style(sys.argv[3], 'error style')
if 'color' not in error_prompt_style:
  sys.stderr.write('gen_prompt_text: no error color set, so failed commands won\'t '
                   'show. Set PROMPT_ERROR_COLOR in ~/.bashrc (e.g. 196), or rerun '
                   'install.\n')

if last_exit_code == '0':
  line_style = normal_prompt_style
else:
  line_style = error_prompt_style

clock = datetime.now().strftime('%H:%M')
branch = os.environ.get('GIT_BRANCH', '')
pwd = os.environ['PWD']
if len(pwd) > 37:
  pwd = '...' + pwd[-35:]
stale = xtras_is_stale()


def stale_warning():
  if stale:
    # Only the error style's color: its other attributes would make this odd.
    with color(error_prompt_style.get('color')), inverse(True):
      # I used to use ⚙, but it's too wide to render properly.
      text('!', title=False)


reset()

# First line: ╓HH:MM (branch) /current/dir
stale_warning()
text('╓', title=False)
with styled(**line_style):
  text(clock, title=False)
  space()
  if branch:
    text('(' + branch + ')')
    space()
  text(pwd)
newline()

# Second line: ╙ and the cursor
stale_warning()
text('╙', title=False)
reset()


def shell_quote(s):
  return "'" + s.replace("'", "'\\''") + "'"

print('PROMPT_COL=' + shell_quote(prompt_col))
print('PROMPT_BNW=' + shell_quote(prompt_bnw.strip()))
