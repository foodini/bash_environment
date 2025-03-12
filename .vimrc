"There's something in the google.vim that screws up pasting.  If I
"try to paste in python code, the indenting gets fubarfed.
"source /usr/share/vim/google/google.vim

"I haven't looked at what this does, but it does change the scroll wheel
"behavior so that it keeps the cursor in place (as much as possible) and
"scrolls the text instead of just scrolling the cursor.  Keep in mind that
"if you're going to select text in vim with the mouse, you'll now have to
"hold down shift while you do it.

set mouse=a
set cursorline

set ai tabstop=2 nu shiftwidth=2 backspace=eol,indent,start expandtab softtabstop=2 hlsearch incsearch noic
:syntax on
:noremap <F2> :set ic! ic?<CR>
:noremap <F3> :set nu! nu?<CR>
:noremap <F4> :set ai! ai?<CR>
:noremap <F5> :set hls! hls?<CR>
:noremap <F6> 10<C-w>-
:noremap <F7> 10<C-w>+
:noremap <F8> :1,$s/\s\s*$//g<CR>


let tabsize=2
:noremap H :let tabsize=(tabsize-2)<CR>:execute "set tabstop=".tabsize." shiftwidth=".tabsize." softtabstop=".tabsize<CR>:echo "tabsize=".tabsize<CR>
:noremap T :let tabsize=(tabsize+2)<CR>:execute "set tabstop=".tabsize." shiftwidth=".tabsize." softtabstop=".tabsize<CR>:echo "tabsize=".tabsize<CR>

if exists('+colorcolumn')
  :set colorcolumn=81,101
  :highlight ColorColumn ctermbg=darkgrey guibg=darkgrey
endif

:highlight ExtraWhitespace ctermbg=red guibg=red
:match ExtraWhitespace /\s\+$/

if has("autocmd")
  " I don't remember for the life of me what this line is for. I'll have to work it out later:
  au BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g'\"" | endif
endif
