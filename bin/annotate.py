#!/usr/bin/env python3

#TODO:
# if no args, process stdin
# if getting from stdin, -- shouldn't be required
# You can't print red for both stdout and stderr
#   either -- or a non-hyphen-ending arg should end args
# add a quiet option, so it'll only print tags and no lines

from collections import defaultdict

from datetime import datetime
import os
import re
import selectors
import subprocess
import sys
import time

command_name = sys.argv.pop(0) # the command name

def usage():
    print(command_name, ' [-e x.y] [-c x.y] [-s sleep_time] [-a] [--] command arg arg arg')
    print('\t-e change elapsed-time formatting to printf-style floats. (%8.2f => "-s 8.2")')
    print('\t-c change current-time formatting to printf-style floats. (%8.2f => "-s 8.2")')
    print('\t-s resolution of the timer & update rate (a positive float.)')
    print('\t-a change current-time formatting to 24-hr time.')
    print('\t-- end of args. If your command begins w/ "-", ' + command_name + ' will mistake')
    print('\t   it for one of its own arguments, so -- terminates this exe\'s args.')
    exit(0)

time_per_line = False
timer_resolution = 0.1
default_elapsed_format = '{:6.2f}'
tag_order = []
while sys.argv:
    arg = sys.argv[0]
    if arg[0] != '-':
        break
    else:
        sys.argv.pop(0)
        if arg == '--':
            break
        elif arg == '-E':
            elapsed_format = '{:' + sys.argv.pop(0) + 'f}'
            tag_order.append(lambda d: elapsed_format.format(d['elapsed']))
        elif arg == '-I':
            elapsed_format = '{:' + sys.argv.pop(0) + 'f}'
            tag_order.append(lambda d: elapsed_format.format(d['incremental']))
        elif arg == '-s':
            timer_resolution = float(sys.argv.pop(0))
        elif arg.startswith('-'):
            for subarg in arg[1:]:
                if subarg == 'a':
                    tag_order.append(lambda _: datetime.now().strftime('%H:%M:%S'))
                elif subarg == 'l':
                    tag_order.append(lambda d: '{:6d}'.format(d['lines']))
                elif subarg == 'w':
                    tag_order.append(lambda d: '{:6d}'.format(d['words']))
                elif subarg == 'c':
                    tag_order.append(lambda d: '{:6d}'.format(d['chars']))
                elif subarg == 'e':
                    tag_order.append(lambda d: default_elapsed_format.format(d['elapsed']))
                elif subarg == 'i':
                    tag_order.append(lambda d: default_elapsed_format.format(d['incremental']))
                else:
                    usage()
        else:
            usage()

if tag_order == []:
    tag_order.append(lambda d: default_elapsed_format.format(d['elapsed']))
    tag_order.append(lambda d: default_elapsed_format.format(d['incremental']))

buffers = defaultdict(lambda: '')

proc = subprocess.Popen(sys.argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)

outfiles = {proc.stdout: sys.stdout, proc.stderr: sys.stderr}

sel = selectors.DefaultSelector()
sel.register(proc.stdout, selectors.EVENT_READ)
sel.register(proc.stderr, selectors.EVENT_READ)

start_time = time.time()
last_line_end_time = start_time
next_update_time = start_time

def annotations(annotation_dict, red=False):
    retval = ''
    if red:
        retval += '\033[31m'
    for tag in tag_order:
        retval += tag(annotation_dict) + ' '
    if red:
        retval += '\033[0m'

    return retval

words_regexp = re.compile(r'(\S+)')

annotations_dict = {
  'chars': 0,
  'words': 0,
  'lines': 0,
}
done = False
while not done:
  active_buffs = 0
  active_fds = sel.select(timeout=0)
  now = time.time()
  annotations_dict['elapsed'] = now - start_time
  annotations_dict['incremental'] = now - last_line_end_time
  if active_fds:
    for key, _ in active_fds:
      data = key.fileobj.read1(1).decode()
      annotations_dict['chars'] += 1
      if data != '':
        active_buffs += 1
        buffers[key.fileobj] += data
      if data == '\n':
        annotations_dict['lines'] += 1
        annotations_dict['words'] += len(re.findall(words_regexp, buffers[key.fileobj]))
        print('\r' + annotations(annotations_dict, key.fileobj == proc.stderr) + ' ' +
              buffers[key.fileobj], end="", file=outfiles[key.fileobj])
        last_line_end_time = now
        buffers[key.fileobj] = ''
  else:
    if now > next_update_time:
      next_update_time = now + timer_resolution
      print ('\r' + annotations(annotations_dict, True), end='', file=sys.stderr, flush=True)
      print ('\r' + annotations(annotations_dict), end='', file=sys.stdout, flush=True)
      time.sleep(timer_resolution/4.0)

  done = proc.poll() is not None and active_buffs == 0 and active_fds

for fileobj, buffer in buffers.items():
  if buffer == '':
    continue
  now = time.time()
  last_line_end_time = now
  print('\r' + annotations(annotations_dict, fileobj == proc.stderr) + ' ' + buffers[fileobj],
        file=outfiles[fileobj])
