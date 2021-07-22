import inspect
import re

from functools import wraps
from typing import Literal, Dict, Type, Union, Any

from manuals.common.types import ManFn
from manuals.formatting import h1, h2, h3, h4, h5, b, c, i, black, bg
from pygments.lexer import Lexer
from pygments import highlight as pyglight
# noinspection PyUnresolvedReferences
from pygments.formatters import TerminalTrueColorFormatter
# noinspection PyUnresolvedReferences
from pygments.lexers import (get_lexer_by_name,
                             AutohotkeyLexer,
                             BashLexer,
                             CssLexer,
                             DockerLexer,
                             IniLexer,
                             JavascriptLexer,
                             JsonLexer,
                             MySqlLexer,
                             PythonLexer,
                             SassLexer,
                             TypeScriptLexer
                             )
import logging
linebreak = r'\n'
backslash = '\\'
# color = '\x1b['
# https://help.farbox.com/pygments.html     ← previews of all styles
Style = Literal['default', 'fruity', 'friendly', 'native', 'algol_nu', 'solarized-dark', 'inkpot', 'monokai']
Language = Literal['mysql', 'python', 'bash', 'ipython', 'ini', 'json', 'js', 'ts', 'css', 'sass', 'docker', 'ahk']
langs = Language.__args__
HIGHLIGHT_START_RE = re.compile(fr'%({"|".join(langs)}) ?(\d|{"|".join(Style.__args__)})?')
HIGHLIGHT_END_RE = re.compile(fr'/%({"|".join(langs)})')
formatters: Dict[Style, TerminalTrueColorFormatter] = dict.fromkeys(Style.__args__)
lexers: Dict[Language, Lexer] = dict.fromkeys(langs)


# *** Helper Functions

def _get_lexer_ctor(lang: Language) -> Type[Lexer]:
    if lang == 'ahk':
        return AutohotkeyLexer
    if lang == 'bash':
        return BashLexer
    if lang == 'css':
        return CssLexer
    if lang == 'docker':
        return DockerLexer
    if lang == 'ini':
        return IniLexer
    if lang == 'ipython':
        return lambda o=lang: get_lexer_by_name('ipython')
    if lang == 'js':
        return JavascriptLexer
    if lang == 'json':
        return JsonLexer
    if lang == 'mysql':
        return MySqlLexer
    if lang == 'python':
        return PythonLexer
    if lang == 'sass':
        return SassLexer
    if lang == 'ts':
        return TypeScriptLexer
    raise ValueError(f"_get_lexer_ctor({repr(lang)})")


def _get_lexer(lang: Language):
    global lexers
    lexer = lexers.get(lang)
    if lexer is None:
        ctor = _get_lexer_ctor(lang)
        lexer = ctor()
        lexers[lang] = lexer
    return lexers[lang]


def _get_color_formatter(style: Style = None):
    # default
    # friendly (less bright than native. ipython default)
    # native (like defualt with dark bg)
    # algol_nu (b&w)
    # solarized-dark (weird for python)
    # inkpot
    # monokai (good for ts)
    # fruity
    if style is None:
        style = 'native'
    global formatters
    formatter = formatters.get(style)
    if formatter is None:
        formatter = TerminalTrueColorFormatter(style=style)
        formatters[style] = formatter
        return formatter
    return formatter


def _highlight(text: str, lang: Language, style: Style = None) -> str:
    lexer = _get_lexer(lang)
    if style is None:
        if lang == 'ipython':
            style = 'friendly'
        elif lang == 'js' or lang == 'json':
            style = 'default'
        elif lang == 'ts' or lang == 'bash':
            style = 'monokai'
    formatter = _get_color_formatter(style)
    highlighted = pyglight(text, lexer, formatter)
    return highlighted

# *** Decorators
def alias(_alias: str):
    def wrap(fn):
        fn.alias = _alias
        return fn

    return wrap


def syntax(_fn_or_style: Union[ManFn, Style] = None, **default_styles):
    """Possible forms:
    ::
        @syntax
        def foo(): ...

        @syntax('friendly')
        def foo(): ...

        @syntax(python='friendly', bash='inkpot')
        def foo(): ...

    Inline `%python native` takes precedence over decorator args.
    """
    default_style = None

    def wrap(fn):
        @wraps(fn)  # necessary for str() to display wrapped fn and not syntax()
        def morewrap(subject=None):

            try:
                ret = fn(subject)
            except TypeError as te:
                if te.args and re.search(r'takes \d+ positional arguments but \d+ was given', te.args[0]):
                    ret = fn()
                    
                    logging.warning('syntax() | ignored TypeError not enough pos arguments given')
                else:
                    raise

            lines = ret.splitlines()
            highlighted_strs = []
            idx = 0

            while True:
                try:
                    line = lines[idx]
                except IndexError as e:
                    break
                if match := HIGHLIGHT_START_RE.fullmatch(line.strip()):
                    # TODO: support %python friendly 2
                    lang, second_arg = match.groups()

                    j = idx + 1
                    if isinstance(second_arg, str) and second_arg.isdigit():
                        # e.g.: `%mysql 1`
                        if lang in default_styles:
                            # precedence to `@syntax(python='friendly')` over `@syntax('friendly')`
                            style = default_styles.get(lang)
                        else:
                            style = default_style  # may be None
                        lines_to_highlight = int(second_arg)
                        for k in range(lines_to_highlight):
                            text = lines[idx + 1]
                            highlighted = _highlight(text, lang, style)
                            highlighted_strs.append(highlighted)
                            idx += 1
                        else:
                            idx += 1
                            continue  # big while

                    # e.g.: either `%mysql` (second_arg is None) or `%mysql friendly`
                    if second_arg:
                        # give precedence to `%mysql friendly` over `**default_styles` or `@syntax('friendly')`
                        style = second_arg
                    else:
                        if lang in default_styles:
                            # precedence to `@syntax(python='friendly')` over `@syntax('friendly')`
                            style = default_styles.get(lang)
                        else:
                            style = default_style  # may be None

                    while True:
                        try:
                            nextline = lines[j]
                        except IndexError as e:
                            # no closing tag → _highlight only first line
                            # TODO: in setuppy, under setup(), first line not closing %bash doesnt work
                            #  Consider highlighting until end of string (better behavior and maybe solves this bug?)
                            text = lines[idx + 1]
                            highlighted = _highlight(text, lang, style)
                            highlighted_strs.append(highlighted)
                            idx = j
                            break
                        else:
                            if HIGHLIGHT_END_RE.fullmatch(nextline.strip()):
                                text = '\n'.join(lines[idx + 1:j])

                                highlighted = _highlight(text, lang, style)
                                highlighted_strs.append(highlighted)
                                idx = j
                                break
                            j += 1
                else:
                    highlighted_strs.append(line + '\n')
                idx += 1
            stripped = ''.join(highlighted_strs).strip()
            return stripped

        return morewrap

    if _fn_or_style is not None:
        if callable(_fn_or_style):
            # e.g. naked `@syntax`
            return wrap(_fn_or_style)
        # e.g. `@syntax(python='friendly')`
        default_style = _fn_or_style
        return wrap

    # e.g. `@syntax(python='friendly')` → **default_styles has value
    return wrap

def rich(_manualfn_or_whatever: Union[ManFn, Any] = None, *dec_args, **dec_kwargs):
    def wrap(fn:ManFn, *args, **kwargs):
        return fn(*args, **kwargs)
    
    if _manualfn_or_whatever is not None:
        if callable(_manualfn_or_whatever):
            # e.g. naked `@rich`
            return wrap(_manualfn_or_whatever)
        # e.g. `@rich(python='friendly')`
        raise NotImplementedError("manuals.py rich decorator was called with parens (). only bare @rich supported")
        default_style = _manualfn_or_whatever
        return wrap
    raise NotImplementedError("manuals.py rich decorator was called with parens (). only bare @rich supported")
    # e.g. `@rich(python='friendly')` → **dec_kwargs has value
    return wrap

# *** Manuals

@syntax(python='friendly')
def altair(subject=None):
    _CHART = f"""
  {h2('Chart')}
    %python 1
    chart = alt.Chart(cars)
    {c('or:')}
    %python
    chart = alt.Chart('https://.../cars.json')

    chart.to_dict()

    chart.mark_[point|circle|square|line|area|bar|tick|rect|rules](
        opacity? = 0.3,
        size? = 100     # at least for circle() and rules()
    )
    /%python
    """
    _ENCODE = f"""
  {h2('Chart.encode()')} {c('→ Chart')}

    Q   {c('Quantitative: numerical quantity (real-valued)')}
    N   {c('Nominal: Name / unordered categorical')}
    O   {c('Ordinal: Ordered categorial')}
    T   {c('Temporal: date/time')}

    %python
    interval = alt.selection_interval(encoding=['x', 'y'])
    interval = alt.selection_interval(encoding=['x'])
    bind = alt.selection_interval(bind='scales')

    single = alt.selection_single(on='mouseover', nearest=True, empty='none' encoding=['x', 'y'])

    multi = alt.selection_multi()
    /%python

    {h3('base = mark_...().encode(')}
        x = 'Year:T'
        x = 'Miles_per_Gallon:Q'
        x = 'mean(Miles_per_Gallon):N'
        x = alt.X('Miles_per_Gallon', bin=True)
        x = alt.X('Miles_per_Gallon', bin=alt.Bin(maxbins=20))
        x = alt.X('count()', stack='normalize')
        x = alt.X('date:T', timeUnit='month')
        x = alt.X('date:T', scale=alt.Scale(domain=interval.ref()))

        x = alt.X('date:O', timeUnit='date'),
        y = alt.Y('date:O', timeUnit='month') {c('"hours"')}

        y = 'Origin:O'

        y = 'ci0(Miles_per_Gallon)',
        y2 = 'ci1(Miles_per_Gallon)'

        color = 'Origin'
        color = 'Cylinders:N'
        color = alt.Color('Miles_per_Gallon', bin=True)
        color = alt.Color('Origin')
        color = alt.condition(interval, 'Origin', alt.value('lightgray'))

        opacity = alt.condition(single, 'Origin', alt.value('lightgray'))
        opacity = alt.condition(single, alt.value(1.0), alt.value(0.0))

        shape

        size

        row  {c('row within a grid of facet plots')}

        column  {c('column within a grid of facet plots')}

        tooltip = 'Name'
    {h3(')')}

    {h4('base.transform_filter(')}
        interval
    {h4(')')}

    {h4('chart = base.properties(')}
        width=800,
        height=300
    {h4(').encode(')}
        x=alt.X('date:T', scale=alt.Scale(domain=interval.ref()))
    {h4(')')}

    {h4('view = chart.properties(')}
        width=800,
        height=50
        selection=interval,

        selection=single
        selection=multi
        selection=bind
    {h4(')')}

    {h3('view.interactive()')}

    """

    _MISC = f"""
  {h2('Miscellaneous')}
    %python
    # side-by-side
    chart | chart.encode(x='Acceleration')
    (chart | chart.encode(x='Acceleration')).save('mychart.html')

    # +, -, |, & are supported
    chart.mark_area(opacity=0.3).encode(
        x='Year:T',
        color='Origin',
        y='ci0(Horsepower)',
        y2='ci1(Horsepower)'
    ) + chart.mark_area(opacity=0.3).encode(
        x='Year:T',
        color='Origin',
        y='ci0(Miles_per_Gallon)',
        y2='ci1(Miles_per_Gallon)'
    )

    # best performance; automatically save data to disk and load it
    alt.data_transformers.enable('json')
    /%python
  """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('altair')}
    {_CHART}
    {_ENCODE}
    {_MISC}
    """

def anxiety(subject=None):
    return f"""{h1('Anxiety')}
    {h2('Mark Manson: 5 Quick Ways to Get Rid of Anxiety')}
      {c('https://www.youtube.com/watch?v=m6rcjY8YHJc')}
      Emotions are expressed in body and bad feelz can become habits.
      {h3('1. Breath')}: diaphragm, belly, maybe hold
      {h3('2. Meditate')}
      {h3('3. Talk to someone')}: repeated thoughts in head amplify. Sharing stops repetition.  
      {h3('4. Negative Visualization')} (worst case + imagine how I'd handle, prob ok. stoicism?)  
    """

@syntax
def apt(subject=None):
    _LIST = f"""{h2('list')} [GLOB]                        {c('list packages based on package names')}
    {c('Without subcommand, lists all known packages')}
    --installed
    --upgradeable
    --all-versions
    """
    _INSTALL = f"""{h2('install')} <PKG>
    {h3('Examples')}
      %bash
      # Install from web
      install <REGEX, GLOB, EXACT>
      install <REGEX, GLOB, EXACT>/<stable | testing | unstable | buster | bullseye | sid ...>
      install <REGEX, GLOB, EXACT>=

      # Install from file
      install /path/to/pkg.deb
      /%bash

    {h3('options')}
      --no-install-recommends          {c('dont install extra recommended packages')}
      --only-upgrade                   {c('upgrade only specific')}
      -d, --download-only
      -f, --fix-broken
      -s, --simulate, --dry-run
      -V, --verbose-versions
      --reinstall                      {c('Upgrade already-installed pkgs to newest')}
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('apt')}
  {_LIST}
  {h2('search')} REGEX                       

  {h2('show')} NAME

  {h2('update')}                             {c('download package information (avail versions)')}

  {h2('upgrade')}                            {c('does not remove existing packages')}
    {h3('full-upgrade')}                     {c('removes existing packages')}

  {_INSTALL}
  {h2('reinstall')} <REGEX, GLOB, EXACT>       {c('maybe supports file?')}

  {h2('purge')} <REGEX, GLOB, EXACT>           {c('clean the config remove left behind')}
                                       {c('does not remove files in home dir')}

  {h2('remove')} <REGEX, GLOB, EXACT>
    -f, --fixed-broken

  {h2('autoremove')}                           {c('remove dependencies of removed packages')}
                                       {c(f'apt-mark deps you like')}
    
  {h2('misc')}
    dist-upgrade                {c('Smart handle changing deps with new versions of packages. Addition to "upgrade"')}
    ppa-purge <ppa>
    source <pkg>                {c('Fetch the source for the specified package')}
    build-dep <source_pkg>
    apt-file update             {c('Generates or updates the apt-file package database')}
    apt-file search --regexp
    apt-cache [options] command
        showsrc         {c('Show source records')}
        search          {c('Search the package list for a regex pattern')}
        depends         {c('Show raw dependency information for a package')}
        rdepends        {c('Show reverse dependency information for a package')}
        show            {c('Show a readable record for the package')}
        pkgnames        {c('List the names of all packages in the system')}
        policy          {c('Show policy settings')}    
    apt-cache [options] show pkg...
  """


@syntax('friendly')
@alias('aio')
def asyncio(subject=None):
    _TASK = f"""{h2('Tasks')}
    {c('https://docs.python.org/3/library/asyncio-api-index.html#tasks')}

    Utilities to run asyncio programs, create Tasks, and await on multiple things with timeouts.

    {h3('aio.run(coro, debug=False)')}
      {c('Create event loop, run a coroutine, close the loop, return the result.')}

      Cannot be called when another asyncio event loop is running in the same thread.
      Always creates a new event loop and closes it at the end.
      Should ideally only be called once.

    {h3('aio.create_task(coro, name=None)')} {c('→ Task')}
      {c('Wrap the coroutine into a Task and schedule its execution.')}

       The task is executed in the loop returned by get_running_loop().

    {c('await')} {h3('aio.sleep(delay, result=None)')}
      {c('Suspends the current task, allowing other tasks to run.')}

    {c('await')} {h3('aio.gather(*coro_or_future, loop=None, return_exceptions=False)')}
        {c('Schedule and wait for things concurrently.')}

        {h4('Examples')}
          %python
          async def foo():
              await aio.sleep(1)

          async def main():
              # Run concurrently
              await aio.gather(foo(), foo(), foo())

          aio.run(main())
          /%python


    {c('await')} {h3('aio.wait_for()')}
      {c('Run with a timeout.')}

    {c('await')} {h3('aio.shield()')}
      {c('Shield from cancellation.')}

    {c('await')} {h3('aio.wait()')}
      {c('Monitor for completion.')}

    {h3('Misc')}
      aio.current_task() {c('→ Task')}
      aio.all_tasks()                 {c('Return all tasks for an event loop.')}
      aio.Task
      aio.run_coroutine_threadsafe()  {c('Schedule a coroutine from another OS thread.')}
      {c('for in')} aio.as_completed()       {c('Monitor for completion with a for loop.')}

    """
    _SUBPROCESSES = f"""{h2('Subprocesses')}
    {c('https://docs.python.org/3/library/asyncio-api-index.html#subprocesses')}

    Utilities to spawn subprocesses and run shell commands.

    {c('await')} create_subprocess_exec()      {c('Create a subprocess.')}
    {c('await')} create_subprocess_shell()     {c('Run a shell command.')}

    """
    # _SUBPROCESS = _SUBPROCESSES
    _LOOP = f"""{h2('Event Loop')}
    {c('https://docs.python.org/3/library/asyncio-eventloop.html#running-and-stopping-the-loop')}

    {h3('aio.get_running_loop()')} {c('→ AbstractEventLoop')}
      {c('Return the running event loop in the current OS thread.')}

      Can only be called from a coroutine or a callback.

      {h4('Examples')}
        %python 2
        loop = get_running_loop()
        end_time = loop.time() + 5.0

    {h3('aio.get_event_loop()')} {c('→ AbstractEventLoop')}
      {c('Get the current event loop (use get_running_loop() when possible).')}

      If there is no current event loop set in the current OS thread, the OS thread is main,
      and set_event_loop() has not yet been called, asyncio will create a new event loop and set it as the current one.

    {h3('aio.set_event_loop(loop)')}
      {c('Set loop as a current event loop for the current OS thread.')}

    {h3('aio.new_event_loop()')} {c('→ AbstractEventLoop')}
      {c('Create a new event loop object.')}
    """
    _STREAMS = f"""{h2('Streams')}
    {c('https://docs.python.org/3/library/asyncio-stream.html#streams')}

    {c('coroutine')} {h3('aio.open_connection(host=None, port=None, **kwargs)')} {c('→ (StreamReader, StreamWriter)')}
      **kwargs are passed to loop.create_connection() (besides protocol_factory), so:

          ssl {c('= None')}
          family {c('= 0')}
          proto {c('= 0')}
          flags {c('= 0')}
          sock {c('= None')}
          local_addr {c('= None')}
          server_hostname {c('= None')}
          ssl_handshake_timeout {c('= None')}
          happy_eyeballs_delay {c('= None')}
          interleave {c('= None')}

    {c('coroutine')} {h3(f'aio.start_server(client_connected_cb, host=None, port=None, **kwargs)')}

      client_connected_cb{c('(StreamReader, StreamWriter)     plain callable or coroutine. if coroutine, it is scheduled as Task.')}
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('asyncio')}

  {_TASK}
  {_STREAMS}
  {_SUBPROCESSES}
  {_LOOP}
    """

@syntax
@alias('ahk')
def autohotkey(subject=None):
    _SYNTAX = f"""{h2('Syntax')}
    %ahk
    if WinActive("ahk_class Notepad") or WinActive("ahk_class" ClassName)
        WinClose ; Use the window found by WinActive.
        
    if (Color = "Blue" or Color = "White")
    /%ahk
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('autohotkey')}
  {_SYNTAX}
  {h2('Examples')}
  %ahk
  ActiveHwnd := WinExist("A")
  /%ahk
  
  {c('Parse web page:')}
  https://www.autohotkey.com/boards/viewtopic.php?t=66376
  """

@syntax(bash='friendly')
def bash(subject=None):
    # 	_strings(){
    # 		printf "$(_h1 'Strings')
    #
    #   stringZ=abcABC123ABCabc;
    #
    #   $(_h2 '6. Substring Removal')
    #     $(_white '6.0. Strip out from front of string')
    #       $(_white '6.0.0 Shortest match')
    #         \${stringZ#a*C}                         $(_# '123ABCabc')
    #
    #       $(_white '6.0.1 Longest match')
    #         \${stringZ##a*C}                        $(_# 'abc')
    #
    #       $(_white '6.0.2 Parameterize the substrings')
    #         X='a*C';
    #         \${stringZ#\$X}                         $(_# '123ABCabc')
    #         \${stringZ##\$X}                        $(_# 'abc')
    #
    #     $(_white '6.1. Strip out from the back of string')
    #       $(_white '6.1.0 Shortest match')
    #         \${stringZ%%A*c}                        $(_# 'abcABC123')
    #
    #       $(_white '6.1.1 Longest match')
    #         \${stringZ%%%%A*c}                       $(_# 'abc')
    #
    #   $(_h2 '7. Substring Replacement')
    #     $(_white '7.0 Replace first match')
    #         \${stringZ/abc/xyz}                     $(_# 'xyzABC123ABCabc')
    #
    #     $(_white '7.1 Replace all matches')
    #         \${stringZ//abc/xyz}                    $(_# 'xyzABC123ABCxyz')
    #
    #     $(_white '7.2 Replace with nothing')
    #         \${stringZ/abc}                         $(_# 'ABC123ABCabc')
    #         \${stringZ//abc}                        $(_# 'ABC123ABC"')
    #

    # TODO: git diff -w "$@" | view -
    __ARGUMENTS = __ARGS = f"""{h2('Arguments')}
    
    {h3('getopts')}
      %bash
      while getopts :d:no: OPT; do
        case $OPT in
          d) day="$OPTARG" ;;
          n) DRY_RUN=1 ;;
          o) OFFSET="$OPTARG" ;;
          *)
	        echo "Usage: ${{0##*/}} [-n] [-d day] [-o offset] ARGS..."
	        exit 2
        esac
      done
      shift $(( OPTIND - 1 ))
      OPTIND=1
      /%bash
    
    {h3('getopt')}
      %bash 1
      getopt [-u, --unquoted] --long difftool: -- "$@"    # supports --difftool=foo and --difftool foo
    
    {h3('Parse args / kwargs')}
      %bash
      POSITIONAL=()
      while [[ $# -gt 0 ]]; do
        case "$1" in
          -f|--flag)
          echo flag: $1
          shift # shift once since flags have no values
          ;;
          --switch=[a-zA-Z0-9]*)
          # '--switch=foo'
          val="${{1#*=}}"
          echo kwarg $1 with val $val
          shift
          ;;
          -s|--switch)
          # '-s foo' or '--switch foo'
          echo switch $1 with value: $2
          shift 2 # shift twice to bypass switch and its value
          ;;
          *) # unknown flag/switch
          POSITIONAL+=("$1")
          echo "added '$1' to POSITIONAL"
          shift
          ;;
        esac
      done
      set -- "${{POSITIONAL[@]}}" # restore positional params
      /%bash
    
    {h3('Get by index')}
      ${{#}}                  {c('get number of args (myfn "hello world" indeed → 2)')}
      ${{*:2}} {c('or')} ${{@:2}}      {c('2nd and following pos args')}
      ${{*:2:3}}              {c('three pos args, starting from 2nd')}
      ${{2}}                  {c('2nd arg exactly')}
      
      {h4('second-to-last, like sys.argv[-2]')}
        %bash 1
        ${{*:$((${{#}} - 1)):1}}  
        {c('or')}
        %bash 1
        $@[$(($# - 1))]
        {c('or')}
        %bash 1
        $*[$(($# - 1))]
      
      {h4('last arg')}
        %bash 1
        $@[$#]
    
    {h3('${*} vs $@')}
      {h4('Basically:')}
        "$*" concats all args within one string (like " ".join(args))
        "$@" keeps them separate
      
      {h4('Example:')}
        %bash
        function echo_1st_arg() {{ echo "$1" }}
        function pass_at() {{ echo_1st_arg "$@" }}
        function pass_star() {{ echo_1st_arg "$*" }}
        $ pass_at foo bar     
        # foo
        $ pass_star foo bar   
        # foo bar 
        /%bash
      
      {h4('Example:')}
        %bash
        function star() {{ printf "args: '%s'{linebreak}" "${{*}}" }}  # $* same
        $ star hello world    
        # args: 'hello world'
    
        function at() {{ printf "args: '%s'{linebreak}" "$@" }}  # ${{@}} same
        $ at hello world
        # args: 'hello'
        # args: 'world'
        /%bash
      
      {h4('Example:')}
        %bash
        function star() {{ echo "${{*:2}}" }}
        $ star hello world    
        # llo world
      
        function at() {{ echo "${{@:2}}" }}
        $ at hello world      
        # world
        /%bash
        
    """

    __ARRAY = rf"""{h3("Array")}
    %bash
    # Build array from multiline string
    arr=( $(echo ${{lines//" "/$'\n'}}) )
      # These also worked?
      arr=( $(echo ${{lines// /}}) ) 
      arr=( $(echo $lines) )
    
    # indexed array
      declare -a arr=([0]="mars" [2]="pluto")
    
    # initialize with values
      foo_arr=('foo'
      'bar')

    # length
      ${{#arr[0]}}       #4 (len of 0th item)
      ${{#arr}}          #4
      ${{#arr[*]}}       #6 (num of items)
      ${{#arr:[@]}}      #6
    
    # iterate over indexed array indices (keys; not necessarily continuous)
      for i in "${{!arr[@]}}"
    
    # append
      arr+=("six")
    
    # delete
      arr=("${{arr[@]/pluto}}")      # removes matching prefixes, not whole items
      unset 'arr[2]'               # only from assoc arr?
    
    # concatenate two arrays
      array=(${{array_1[@]}} ${{array_2[@]}})
      # also (echo looks ok):
      array+=${{other[@]}}
  
    # last item
      ${{array[${{#array}}]}}
    
    # get
      #TODO: this is all wrong?
      ${{arr[0]}}        # zero
      ${{arr:0}}         # zero
      ${{arr[1]}}        # one
      ${{arr:1}}         # ero
    /%bash
    
    {h3('Associative array')}
      %bash
      # Printing:
      for x in "${{!array[@]}}"; do printf "[%q]=%q\n" "$x" "${{array[$x]}}" ; done
      
      # Bash:
      echo ${{!arr[@]}}      # keys
      echo ${{arr[@]}}      # values
      
      # Zsh:
      echo ${{(t)array}}
      echo ${{(k)array}}
      echo ${{(kv)array}}
      
      # Tricks:
      # Copy arr to a new one:
      delcare -A LISA=([url]=www.google.com)
      tmp=$(declare -p LISA)        # tmp now holds 'declare -A LISA=([url]="www.google.com")'
      eval "declare -A lisa=${{tmp#*=}}"
      echo ${{lisa[url]}}   # www.google.com
      
      # Another way:
      declare -A FOO
      for k in ${{!LISA[@]}}; do eval "FOO[$k]=${{LISA[$k]}}"; done
      /%bash
      
      {h4('See "declare"')}
    """

    __CASE = f"""{h3('case')}
    %bash
    case $1 in
        verbose)    echo 'verbose';;
        false)   echo 'is false';;
        [Yy][Ee][Ss])   echo 'some regex'; break;;
        *)   echo 'none of the above';;
    esac
    /%bash
    """
    __DECLARE = f"""{h3('declare')} [-aAfFgilnrtux] [-p] [name[=value] ...]
    Without NAME, display all attributes/values of all variables.
    
    {h4('Options')}
      -g	{c('Makes variables global when inside function')}
      -f	{c('Print functions including content')}
      -F	{c('Print function names')}
      -p	{c('Print attributes/values of each NAME')}
    
    {h4('Options which set attributes')}
      -a	{c("Indexed arrays (if supported)")}
      -A	{c("Associative arrays (if supported)")}
      -i	{c("NAMEs are integers")}
      -l	{c("Convert NAMEs to lowercase")}
      -n	{c("NAMEs are refs to matching vars")}
      -r	{c("NAMEs are readonly")}
      -t	{c("NAMEs have 'trace' attribute")}
      -u	{c("Convert NAMEs to uppercase")}
      -x	{c("NAMEs are exported")}
    """
    __EXEC = __EVAL = f"""{h3('exec, eval and $(...)')}
    %bash 2
    if ! $(git checkout "$@"); then     # executes what's inside $()
    if ! git checkout "$@"; then        # doesn't execute
    """
    __IF = f"""{h3('if')}
    %bash
    # substring
    if [[ ${{var}} == *"My long"* ]]
  
    # newline exists?
    if [[ ${{var}} =~ $'{linebreak}' ]]
    
    if {{ [[ "$1" = ".*" * | | "$1" = *".*"]]; }}; then
    
    if [[ "$processes" != *"winactivate"*"$1"* ]] && ! bool "$last_proc"; then
    
    if ! is_num $2 || [ $2 -lt 1 ]; then
    
    if ! is_num "$1" || ! is_num "$2"; then
    
    # not sure it works?
    if [[ "$1" == d || "$1" == diff ]] && [[ -z $(gd) ]]; then
    
    /%bash
    """
    __TEST = __FILES = f"""{h3('test')}
    test <FLAG> <FILE>
    FLAG:
      -b  {c('block special')}
      -c  {c('character special')}
      -d  {c('directory')}
      -e  {c('exists')}
      -f  {c('regular file')}
      -g  {c('set-group-ID')}
      -h  {c('symbolic link (same as -L)')}
      -k  {c('has its sticky bit set')}
      -p  {c('a named pipe')}
      -r  {c('read permission is granted')}
      -s  {c('has a size greater than zero')}
      -t  {c('True if FD is opened on a terminal.')}
          {c('when not piped, -t 1 is True (?)')}
      -u  {c('its set-user-ID bit is set')}
      -w  {c('write permission is granted')}
      -x  {c('execute (or search) permission is granted')}
    """

    __FOR = rf"""{h3('for')}
    %bash
    # Example 1:
    for reqsubstr in 'o' 'M' 'alt' 'str';
    
    # Example 2:
    for l in $(git diff --summary gilad | grep -o -P "(?<=\d{{6}}\s).*");
    
    # Example 3:
    n=$((5));
    for ((i=0; i<n; i++));
    for i in {{1..$n}};   # Problematic: SC2051
    /%bash
    """
    __NUMBER = __INT = f"""{h3('numbers')}
    %bash 3
    count=$((0))
    count=$((0+1))
    count=$((count+1))
    ((count++))
    """
    __RETURN = f"""{h3('return value from functions')}
    %bash
    function myfunc() {{
        local  __resultvar=$1
        local myresult = 'some value'
        if [["$__resultvar"]]; then
            eval $__resultvar = "'$myresult'"
        else
            echo "$myresult"
        fi
    }}

    myfunc result
    echo $result    # 'some value'
    result2=$(myfunc)
    echo $result2   # 'some value'
    /%bash
    """
    
    __SET = f"""{h3('set')} {c('[-abefhkmnptuvxBCHP] [-o [OPTION]] [--] [arg ...]')}
    Using + rather than - causes these flags to be turned off.
    The current set of flags may be found in $-.

    -o                        {c('bare "o" displays a list of all options and their values')}
    -a, -o allexport          {c('Mark variables which are modified or created for export.')}
    -e, -o errexit            {c('Exit immediately if a command exits with a non-zero status.')}
    -n, -o noexec             {c('Read commands but do not execute them.')}
    -u                        {c('Treat unset variables as an error when substituting.')}
    -v, -o verbose            {c('Print shell input lines as they are read.')}
    -x, -o xtrace             {c('Print commands and their arguments as they are executed.')}
    -o interactive-comments   {c('allow comments to appear in interactive commands')}
    -T, -o functrace          {c('DEBUG and RETURN traps are inherited by shell functions.')}
    -E, -o errtrace           {c('ERR trap is inherited by shell functions.')}
    --                        {c('Assign any remaining arguments to the positional parameters.')}
                              {c('  If there are no remaining arguments, the positional parameters are unset.')}
    -                         {c('Assign any remaining arguments to the positional parameters.')}
                              {c('  The -x and -v options are turned off.')}

      """
    __STRING = rf"""{h3('strings')}
    https://linux.die.net/man/1/zshexpn
    mystr=abcABC123ABCabc

    {h4('Index and length')}
      %bash
      # length:
      echo ${{#mystr}}                   # length: 15

      # length of match:
      expr "$mystr" : 'abc[A-Z]*'      # 6
      expr match "$mystr" 'abc[A-Z]*'  # 6

      # index of match:
      expr index "$mystr" 'A'          # 4
      expr index "$mystr" '1c'         # 3 ("c" matches before "1")
      /%bash
    
    {h4('Substring')}
      %bash
      # 0-based index
      echo -e -n ${{mystr:4}}                  # BC123ABCabc
      echo -e -n ${{mystr:0:4}}                # abcA
      echo -e -n ${{mystr: -1}}                # c
      echo -e -n ${{mystr:(-1)}}               # c

      # 1-based index (either double quote or no quote!)
      expr substr "$mystr" 1 1         # a
      expr substr "$mystr" 2 2         # bc

      # removal (note the parens and actual escapes)
      expr match "$mystr" '\([a-z]*[A-Z]\)'    # abcA
      expr match "$mystr" '\(\{{4\}}\)'          # abcA
      echo "$foo" | tr -d ' \n'                # removes both whitespace and newline
      
      # to lowercase (^ for upper)
      var="AmazinG GracE"
      echo "${{var,}}"           # amazinG GracE
      echo "${{var,,}}"          # amazing grace
      echo "${{var,[AAEIUO]}}"   # amazinG GracE
      echo "${{var,,[AAEIUO]}}"  # amazinG Grace
      /%bash

    {h4('Manipulation')}
      %bash
      # Delete from end
      ${{string%substring}}                       # Deletes *shortest* match of $substring from *end* of $string.
        echo "${{SHELL%/*}}"                      # /usr/bin
        
      ${{string%%substring}}                      # Deletes *longest* match of $substring from *end* of $string.
      
      # Delete from start
      ${{string#substring}}                       # Deletes *shortest* match of $substring from *start* of $string.

      ${{string##substring}}                      # Deletes *longest* match of $substring from *start* of $string.
        echo "${{SHELL##*/}}"                     # zsh
        # gets value of --difftool=val and --difftool val:
        argstr="$*"; difftool="${{argstr##*difftool[= ]}}"
        
      
      # Replacement
      ${{string/substring/replacement}}    # Replace *first* match of $substring with $replacement.

      ${{string/%substring/replacement}}   # If *end* matches $substring, substitute $replacement for $substring.

      ${{string/#substring/replacement}}   # If *start* matches $substring, substitute $replacement for $substring.

      ${{string//substring/replacement}}   # Replace *all* matches of $substring with $replacement.
      /%bash

    {h4('Contacenating')}
    %bash
    mystr+="u"
    /%bash
    """
    __TYPE = f"""{h3('type')} [-afptP] name [name ...]
    Display information about command type.
    
    no flag       {c("print type and content of would be used.")}
                  {c("  type -f cd → cd is a function; cd () {{...}}")} 
    -t            {c("output alias, keyword, function, builtin, file, or nothing (1)")}
    -a            {c("display all locations, including content.")}
                  {c("  type -f cd → cd is a function; cd () {{...}}; cd is a shell builtin")}  
    -f            {c("suppress custom function lookup")}
                  {c("  type -f cd → cd is a shell builtin")}  
                  {c("  type -f log → not found (1)")}
    -P            {c("search PATH, output disk file")}
                  {c("  type -P ls → /bin/ls (even if overridden or aliased)")}
    -p            {c("output disk file, restricted to -t → 'function'")}
    
    see {bg('declare')}
    """
    __VARIABLES = __VARS = f"""{h3('Variables')}
    %bash 2
    ${{var:?}}          # fail if the variable is unset (or empty)
    : "${{var:=5}}"     # initialize it to a default value (5) if uninitialized
    """
    __QUOTES = f"""{h3('Quotes and var expansion')}
  {h4('simple')}
    %bash 2
    $ VAR='hi "everyone"'
    $ echo $VAR
    {i('hi "everyone"')}

    %bash 1
    $ echo "$VAR"
    {i('hi "everyone"')}

    %bash 1
    $ echo '$VAR'
    {i('$VAR')}

    %bash 1
    $ echo VAR
    {i('VAR')}

    %bash 1
    $ echo 'VAR'
    {i('VAR')}

  {h4('advanced')}
    %bash 2
    # '$(...)' captures the output
    $ VAR="command: $(echo hi)"
    $ echo $VAR
    {i('command: hi')}

    %bash 1
    $ echo $VAR
    {i('command: hi')}

    %bash 2
    $ VAR="command: '$(echo hi)'"
    $ echo $VAR
    {i("command: 'hi'")}

    %bash 2
    $ VAR="command: "$(echo hi)""
    $ echo $VAR
    {i("command: hi")}    {c('(why?)')}

    %bash 2
    $ VAR='command: $(echo hi)'
    $ echo $VAR
    {i("command: $(echo hi)")}

    %bash 2
    $ VAR='command: "$(echo hi)"'
    $ echo $VAR
    {i('command: "$(echo hi)"')}
    """

    __WHILE = f"""{h3('while')}
    %bash
    x=1
    while [[ ${{x}} -le 5 ]]; do
      echo "Welcome $x times"
      x=$((x + 1))
    done
    /%bash
    """
    __PIPE = __PROCESSES = __FILEDESCRIPTORS = __BG = __FG = __REDIRECTION = __JOB = f"""{h2('Pipe, Processes, File Descriptors, Background, Foreground, Redirection, >, >>, <, <<, <<<')}
    {c('https://stackoverflow.com/questions/35116699/piping-not-working-with-echo-command')}
    {c('http://tiswww.case.edu/php/chet/bash/bashref.html#Job-Control')}
    %bash
    nohup CMD &>/dev/null &
    CMD 2>&1

    echo "echo lol" | $SHELL  # lol
    
    echo "$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS" 2>bad.log
    /%bash

    {h3('?')}
      %bash
      # status of last command
      wait $pid
      echo Job 1 exited with status $?
      /%bash
    
    {h3('!')}
      %bash
      # process id of last command
      sleep 20 &
      pid=$!
      kill $pid
      wait $pid
      echo "$pid was terminated"
      /%bash
    
    {h3('&')}
      %bash
      # immediately displays '[1] 21415'
      # then after 3 seconds: '[1]  + 21415 done       sleep 3'
      sleep 3 &
      /%bash
    
    {h3('fg')}
        %bash
      # immediately displays:
      # [1] 21415
      # [1]  + 22039 running    sleep 3
      # and terminal is frozen for 3 seconds
      sleep 3 & fg
      /%bash
    
    {h3('bg, ctrl+z')}
        %bash
      # ctrl+z to send a foreground process to sleep background
      # process will be paused until next signal
      # running 'bg' to resume in background
      sleep 10
      ^Z
      # [1]  + 22523 suspended  sleep 10
      bg
      # [1]  + 22523 continued  sleep 10
      # ...then after 10s have finished
      # [1]  + 22523 done       sleep 10
      /%bash

    {h3('>, >>, <, <<, <<<')}    
      {c('http://zsh.sourceforge.net/Guide/zshguide03.html#l60')}
      >       {c('output to file')}
      >>      {c('append to file')}
      <       {c('read input from file')}
      <<      {c('heredoc')}
        {c('https://linuxize.com/post/bash-heredoc/')}
        [COMMAND] <<[-] 'DELIMITER'
          HERE-DOCUMENT
        DELIMITER
        
        - COMMAND is file descriptor, defaults to stdin (0)
        - '-' after '<<' to remove leading <tab> chars
        - Quote "EOF" to disable parameter expansion 
        
        %bash
        # Assign multi-line string to a shell variable
        sql=$(cat <<EOF
        SELECT foo, bar FROM db
        WHERE foo='baz'
        EOF
        )
        
        # Pass multi-line string to a file in Bash
        cat <<EOF > print.sh
        #!/bin/bash
        echo \\$PWD
        echo $PWD
        EOF
        
        # Pass multi-line string to a pipe in Bash
        cat <<EOF | grep 'b' | tee b.txt
        foo
        bar
        baz
        EOF
        # b.txt now contains bar and baz lines. Same output is also printed to stdout.


        # Load stdin into a variable
        stdin=$(cat<&0)

        # Send stdin from a pipe
        echo script.sh | sh /dev/stdin dest=/some/other/location
        
        /%bash
      
      <<<     {c('reverse pipe')}
        %bash
        # The following are the same:
        echo "hi" | cut -c 1
        cut -c 1 <<< "hi"
        /%bash    
    """
    _BASENAME = _DIRNAME = _REALPATH = f"""{h2('basename / dirname / realpath')}
    %bash
    realpath nav.sh  # /home/gilad/Code/bashscripts/nav.sh
    basename /home/gilad/Code/bashscripts/nav.sh  # nav.sh
    basename nav.sh .sh # nav
    dirname /home/gilad/Code/bashscripts/nav.sh  # /home/gilad/Code/bashscripts
    /%bash
    """
    _CHMOD = _CHOWN = f"""{h2('chown / chmod')}
    {h3('OPTION')} applies to either
      -v        
      -c          {c('like verbose but show only changes')}
      -R
  
    {h3('chmod')} {c('[OPTION]... MODE[,MODE]... FILE...')}
      recursively: chmod 777 */*.py
      {h4('MODE')}
        ugo   {c('user, group, other')}
        4     {c('read')}
        2     {c('write')}
        1     {c('execute')}
  
        chmod 756 → [rwx][r-x][rw-]
                    user  grp  othr
  
    {h3('chown')} {c('[OPTION]... [OWNER][:GROUP] FILE...')}
      chown gilad:gilad -R .git
      -h          {c('affect symbolic links instead of referenced file (default is affect the file)')}
      -H          {c('if arg is symlink to dir, traverse it')}
      -L          {c('when encountering a symlink to dir, traverse it (default is not to traverse)')}
    """
    _COMPLETE = _COMPGEN = f"""{h2('complete')} [FLAGS] [OPTS] [name ...]
    {c('https://www.gnu.org/software/bash/manual/html_node/Programmable-Completion-Builtins.html')}
    {c('https://www.gnu.org/software/bash/manual/html_node/Programmable-Completion-Builtins.html')}
    {h3('Flags')}
      -abcdefgjksuv
    
    {h3('Options')}
      -A ⟨action⟩    {c('one of the following to generate a list of possible completions:')}
              {c('alias arrayvar binding builtin command directory disabled enabled')}
              {c('export file function group helptopic hostname job keyword running')}
              {c('service setopt shopt signal stopped user variable')} 
      -G globpat 
      -W wordlist 
      -F function 
      -C command 
      -X filterpat 
      -P prefix 
      -S suffix
      {h4('-o ⟨OPTION⟩')}
        -p    {c('print existing completion specifications in a reusable format')}
        -r    {c('remove a completion specification for each NAME, or, if no')}
              {c('  NAMEs are supplied, all completion specifications')}
        -D    {c('apply the completions and actions as the default for commands')}
              {c('  without any specific completion defined')}
        -E    {c('apply the completions and actions to "empty" commands --')}
              {c('  completion attempted on a blank line')}
        bashdefault
        default
        dirnames
        filenames
        noquote
        nosort
        nospace
        plusdirs    {c('attempt and add dir name completion after any matches')}
    
    {h3('Globals')}
      COMP_WORDS{c(': Numbered array (words in biffer)')}
      COMP_CWORD{c(': int (1-index of current word in COMP_WORDS)')}
      COMP_LINE{c(': str (the whole buffer)')}
      COMP_POINT{c(': int (1-index of current char)')}
      COMP_TYPE
      COMP_KEY
      BASH_REMATCH
      CURSOR
      COMPREPLY
      BUFFER
      PREBUFFER
      CUTBUFFER
      RBUFFER
      LBUFFER
    
    {h3('compgen')} [option] [word]
      %bash
      # Ex. 1
      current="${{COMP_WORDS[$COMP_CWORD]}}"
      prev="${{COMP_WORDS[$COMP_CWORD - 1]}}"
      possible_completions='
        help install
        alias unalias'
      COMPREPLY=($(compgen -W "$possible_completions" -- "${{current}}"))
      /%bash
    
    {h3('Examples')}
      %bash
      complete -o default -F __nvm nvm
      
      complete -o filenames -C '_z --complete "$COMP_LINE"' ${{_Z_CMD:-z}}
      complete -o default -C 'compgen -W "a b c d" -- "${{COMP_WORDS[COMP_CWORD]}}"' hfzf
      
      complete -o bashdefault -o default -o nospace -F _drush_completion d dr drush drush5 drush6 drush7 drush8 drush.php
      /%bash
    """
    _COMPDEF = _COMPCTL = f"""{h3('compdef')}
      %bash
      compadd -- $(COMP_CWORD=$((CURRENT-1)) \\
                   COMP_LINE=$BUFFER \\
                   COMP_POINT=0 \\
                   npm completion -- "${{words[@]}}" \\
                   2>/dev/null)
      /%bash
    
    {h3('compctl')}
      %bash
      local cword line point words si
      read -Ac words
      read -cn cword
      let cword-=1
      read -l line
      read -ln point
      si="$IFS"
      IFS=$'\\n' reply=($(COMP_CWORD="$cword" \\
                         COMP_LINE="$line" \\
                         COMP_POINT="$point" \\
                         npm completion -- "${{words[@]}}" \\
                         2>/dev/null)) || return $?
      IFS="$si"
      /%bash
    """


    _CP = f"""{h2('cp')}
    {h4('Examples')}
    Given:
    {i('''
    ./
      A/
        .idea/
              foo.txt
      B/
        .idea/
              bar.txt
    ''')}
    %bash 1
    cpx -r */.idea/* /__test/
   
    Creates:
    {i('''
    /__test/
            foo.txt
            bar.txt
    ''')}
  
    But:
    %bash 1
    cpx -r --parents */.idea/* /__test/
    
    Creates:
    {i('''
    /__test/
            A/
              .idea/
                    foo.txt
            B/
              .idea/
                    bar.txt
    ''')}
    """
    _CUT = f"""{h2('cut')}
    -b, -c and -f are mutually exclusive
  
    -b                {c('bytes')}
    -c                {c('characters')}
    -f                {c('fields')}
    -d                {c('delimiter')}
    -z                {c('zero delimited')}

    {h4('examples')}
      cut -c 2          {c('[1]')}
      cut -c 1-         {c('[0:]')}
      cut -c -1         {c('[:1]')}
      cut -c 1-1        {c('[1:2]')}
      cut -d'=' -f1     {c('x.partition("=")[0]')}
      cut -d'=' -f1-3   {c('x.split("=")[0:2] (joined)')}
      cut -d'=' -f1,3   {c('x.split("=")[0,2] (joined)')}
      cut -d$'{linebreak}' -f4   {c(f'x.split("{linebreak}")[4]')}
    """

    _DIFF = f"""{h2('diff')}
    {c('diff [OPTION]... FILES')}

    {h3('behavior')}
      -r, --recursive         {c('for subdirectories')}
      -d,  --minimal          {c('Try harder for smaller changes')}
      --suppress-common-lines
      -N,  --new-file         {c('Treat absent files as empty')}
      -s,  --report-identical-files
      -a, --text              {c('treat all files as text')}

    {h3('ignoring')}
      -w,  --ignore-all-space
      -i, --ignore-case       {c('for content')}
      --ignore-file-name-case
      -E,  --ignore-tab-expansion
      -b,  --ignore-space-change
      -B,  --ignore-blank-lines
      -I {i('RE')},  --ignore-matching-lines={i('RE')}
      --strip-trailing-cr
      -x {i('PATTERN')},  --exclude={i('PATTERN')}   {c('Exclude files matching PATTERN')}
      -X {i('FILE')},  --exclude-from={i('FILE')}

    {h3('output')}
      -c,  -C {i('NUM')},  --context[={i('NUM')}] {c('lines of copied context')}
      -u,  -u {i('NUM')},  --unified[={i('NUM')}] {c('lines of unified context')}
      -q,  --brief
      -n,  --rcs             {c('Output an RCS format diff')}
      -y,  --side-by-side
      -l,  --paginate       {c('splits to pages, i.e. "page 1" etc')}
      -W {i('NUM')},  --width={i('NUM')}     {c('default 130')}
    
    {h3('Examples')}
      diff config_dev.json ../reconciliation_engine/config.json -wBy --suppress-common-lines
      
      {h4('Comparing content of binary files')}
      diff <(xxd profile-icecream.JPG) <(xxd profile-icecream2.JPG)

      {h4('Comparing strings')}
      diff <(echo "foo") <(echo "fo0")
      """

    _DU = f"""{h2('du')} [options] [path]
    {h3('options')}
      -a                  {c('all files, not just dirs')}
      -c                  {c('grand total')}
      -d, --max-depth=DEPTH      {c(f'for each files and dirs in {i("DEPTH")}')}
      -h                  {c('human readable (good with du -ah | sort -h)')}
      -k                  {c('counts in 1024-byte (1-Kbyte) blocks (good with du -ak | sort -n)')}
      -s, --summarize     {c('display only a total for each argument')}
      --exclude=PATTERN          {c('exclude files that match PATTERN')}
      -x, --exclude-from=FILE    {c('exclude files that match any pattern in FILE')}
      -S, --separate-dirs        {c("don't include size of subdirectories for parent dirs")}

    {h3('examples')}
      du -a | sort -n
      du -ah | sort -h
      du -ah -d 1 | sort -h      {c('Show only of this level')}
      du -sh --exclude="*env*" video_motion_detection
    """

    _ECHO = f"""{h2('echo')}
    -n     do not output the trailing newline
    -e     enable interpretation of backslash escapes
    -E     disable interpretation of backslash escapes
    """

    _FIND = f"""{h2('find')}

    {h3('examples')}
    find . -path '*.py' -and -not -path '*playground*'
    find . -path '*.py' ! -path '*playground*'
    find -E . -type f -regex ".*b.*" -exec {i('rm')} "{{}}" ";"
    find . -maxdepth 1 -type d      {c('list dirs in current directory')}
    
    -E          {c('extended regex. takes effect only with "-[i]regex" (and "-[i]wholename"?)')}
    -X          {c('safe with xargs')}
    -depth      {c('depth-first')}
    -s          {c('lexicographical order (alphabetical within each dir)')}
    -empty
    -exec[dir] {i('UTIL [argument ...]')} "{{}}" "[;|+]"      {c(f'{{}} is replaced by file path (containing dir path with {i("execdir")}). ";" → for each, "+" → for as many (?)')}

    {h3('times')} {c('-a accessed, -c created, -m modified')}
      -[a|c|m]time {i('n[smhdw]')}     {c('-atime -1h30m')}
      -[a|c|m]min {i('n')}             {c('minutes')}
      -[a|c|m]newer {i('file')}

    -[i]path
    -[i]name
    -[i]regex
    -[i]wholename
    -[max|min]depth {i('n')}
    -size {i('n[ckMGTP]')}
    -type {i('t')}
        b       {c('block special')}
        c       {c('character special')}
        d       {c('directory')}
        f       {c('regular file')}
        l       {c('symbolic link')}
        p       {c('FIFO')}
        s       {c('socket')}
    -user {i('name')}

    {h3('quirks')}
      given: ./b.txt
                    b   b.txt   b.t*t   *b.txt  .*b.txt  *b*t
      -name         F   T       T       T       F        T
      -path         F   F       F       T       T        T
      -wholename    F   F       F       T       T        T
      -regex        F   F       F       F       T        F

        """

    _GREP = f"""{h2('grep')}
    {h4('grep')} [OPTION...] PATTERN [FILE...]
    {h4('grep')} [OPTION...] -e PATTERN... [FILE...]
    {h4('grep')} [OPTION...] -f PATTERN_FILE... [FILE...]
    
    {h3('options')}
      {h4('pattern syntax')}
        -E, --extended-regexp    {c('aka ERE')}
        -F, --fixed-strings      {c('take pattern literally, dont interpret regex chars')}
        -P, --perl-regexp        {c('aka PCRE. only linux?')}
      
      {h4('match control')}
        -e PATTERN [-e PATTERN...]    {c("to specify multiple patterns. alias: '--regexp=PATTERN'")}
        -i, --ignore-case 
        -v, --invert-match
        -w, --word-regexp             {c("show only lines containing matches that form whole words. '-x' disables")}
        -x, --line-regexp             {c("show only lines that match fully")}
      
      {h4('context')}
        -C NUM, -NUM, --context=NUM
        -A NUM, --after-context=NUM
        -B NUM, --before-context=NUM
        
      {h4('output')}
        -c, --count                   {c('how many lines had a match per file')}
        -L, --files-without-match     {c('print paths of files without matches')}
        -l, --files-with-matches      {c('print paths of files with matches')}
        -o, --only-matching           {c('show only the matched parts')}
        -q, --quiet, --silent         {c('exit code works')}
        -s, --no-messages             {c('suppress error messages about nonexistent / unreadable files')}
      
      {h4('line prefix')}
        -H, --with-filename
        -n, --line-number
        -T, --initial-tab             {c('pad line content with tab stop to align nicely')}
        -Z, --null                    {c('zero byte instead of normal character following file name')}
        
      {h4('file filter')}
        -a, --text                    {c('process bin files as if text')}
        --exclude=GLOB
        --exclude-dir=GLOB
        --exclude-from=FILE
        -I                            {c('ignore binary')}
        --include=GLOB                {c('only search files matching GLOB')}
        -r, --recursive
        -z, --null-data               {c('Treat input and output data as zero-byte terminated sequences of lines (instead of newline)')}

    {h3('Special Characters')}
      [[:alnum:]]       {c("Alphanumeric characters.")}
      [[:alpha:]]       {c("Alphabetic characters")}
      [[:blank:]]       {c("Blank characters: space and tab.")}
      [[:digit:]]       {c("Digits: ‘0 1 2 3 4 5 6 7 8 9’.")}
      [[:lower:]]       {c("Lower-case letters: ‘a b c d e f g h i j k l m n o p q r s t u v w x y z’.")}
      [[:space:]]       {c("Space characters: tab, newline, vertical tab, form feed, carriage return, and space.")}
      [[:upper:]]       {c("Upper-case letters: ‘A B C D E F G H I J K L M N O P Q R S T U V W X Y Z’.")}
      
    {h3('Examples')}
      grep '[:upper:]' filename
      grep -E '[[:upper:]]' filename
      grep -r -w --color 'HereB' .    {c('-recursive, -word')}
      grep -n [-C -A -B] 2 'Ace' .    {c('line num, 2 context lines')}
      grep --exclude-dir "*home/gilad/Downloads/ANGRYsearch*" --exclude "file.zip" -riPa "angrysearch"
      grep -nIrEH -C 1 --exclude="*.log" --exclude-dir="src" "[^def ]loadDataFromS3" .
        """
    _HEAD = _TAIL = f"""{h2('head, tail')} [OPTION]... [FILE]...
    -z      {c('zero terminated')}
    head -n, --lines=NUM      {c('[:NUM]    until NUM')}
                     -NUM     {c('[:-NUM]   until len-NUM')}
    tail -n, --lines=NUM      {c('[-NUM:]   from len-NUM')}
                     +NUM     {c('[NUM:]    from NUM')}
    
    {h3('examples')}
      %bash
      # Last 20 lines:
      tail -n 20 FILE
      # OR:
      tail -20 FILE
      # OR:
      tail -n -20 FILE
      
      # First 20 lines:
      head -n 20 FILE
      # OR:
      head -20 FILE
      # OR:
      head -n +20 FILE
      /%bash
    """
    _LESS = f"""{h2('less')}
    {h3('args')}
      -N          line numbers
      --pattern=  {i('PATTERN')}
      -s, --squeeze-blank-lines
      -S, --chop-long-lines   {c("default is to wrap")}
      -W, --HILITE-UNREAD

    {h3('navigation')}
      f         scroll down 1 window
      b         scroll up 1 window
      d         scroll down 0.5 screen
      u         scroll up 0.5 screen
      g

    {h3('search')}
      [/ ? &]{i('pattern')} forward, backward, display only match
        !                   not
        ^K                  highlight match but dont move to it
        ^R                  not regex (simply text)

    {h3('misc')}
      ! {i('shell-command')}
      s {i('filename')}     saves to file. works only if input is a pipe
    """
    _MAN = f"""{h2('man')}
  {h3('Usage')}
    man [man options] [[section] page ...] ...
    man -k|--apropos [apropos options] regexp ...
    man -K|--global-apropos [man options] [section] term ...
    man -f|--whatis [whatis options] page ...
    man -l|--local-file [man options] file ...
    man -w|--where|--path|--location [man options] page ...
    man -W|--where-cat|--location-cat [man options] page ...
  
  {h3('Finding manuals')}
    --regex or --wildcard     {c('Show all pages matching PAGE arg')}
  {h3('Controlling formatted output')}
    -P pager, --pager=pager
    """

    _MOUNT = _UMOUNT = f"""{h2('mount, umount')}
    {h3('mount')}
      mount [-fnrsvw] [-t fstype] [-o options] <device> <dir>
      mount [-fnrsvw] [-o options] <device>|<dir>

      {h4('flags')}
        --fake
        --move
        -o, --options <options>
        --options-mode <ignore | append | prepend | replace>    {c('default prepend')}
        -v, --verbose

      {h4('-o options')}
        ro              {c('readonly')}
        rw              {c('read-write')}
        remount         {c('an already-mounted filesystem')}
        
      {h4('Examples')}
        mount /dev/foo /dir                 {c('mount device foo at /dir')}
        mount <device>|<dir> -o <options>   {c('append to list of existing options. last opt wins')}

        mount --move <olddir> <newdir>
      

      {h4('Mounting an external USB:')}
        sudo mkdir /media/external2tb
        sudo mount /dev/sdb1 /media/external2tb
      
      {h4('Remounting with read-write permissions:')}
        sudo mount -o remount,rw /dev/sda1
  
      {h4('Listing devices')}
        lsblk [--fs]    {c('good')}
        fdisk -l        {c('also good')}
            {c('prints relevant info nicely:')}
            sudo fdisk -l | grep -A 7 -P "^Disk /dev/(?\\!loop)"
        findmnt [-A, --all] or [-l, --list]
        blkid -p <device>

    {h3('umount')} [-dflnrv] <directory>|<device>...
      --fake        {c('dry run')}
      -v, --verbose
    """

    _READ = rf"""{h2('/bin/bash -c "read"')}
    http://linuxcommand.org/lc3_man_pages/readh.html
    read [-ers] [-a array] [-d delim] [-i text] [-n nchars] [-N nchars] [-p prompt] [-t timeout] [-u fd] [name ...]
    -a array	    {c(f'assign words read to {i("ARRAY")} indices (0-indexed)')}
    -d {i('DELIM')}	    {c(f'continue until first char of {i("DELIM")} is read (not newline)')}
    -e              {c(f'use Readline to obtain the line in an interactive shell')}
    -i {i('TEXT')}	        {c(f'Use {i("TEXT")} as the initial text for Readline')}
    -n {i('NCHARS')}	    {c(f'return after reading {i("NCHARS")} (honors delimiter)')}
    -N {i('NCHARS')}	    {c(f'return after reading {i("NCHARS")} (ignores delimiter)')}
    -p {i('PROMPT')}	    {c(f'output {i("PROMPT")} without a trailing newline before reading')}
    -r              {c(f'do not allow backslashes to escape any characters')}
    -s              {c(f'do not echo input coming from a terminal')}
    -t {i('TIMEOUT')}      {c(f'fail if a line is not read within {i("TIMEOUT")} seconds. "0" means no timeout.')}

    {h4('Examples')}
      %bash
      # first example
      foo=$(/bin/bash -c 'read bar; echo $bar');
      
      # second example
      find . -type f -regex ".*/.*\.pdf" | while read file; do
        if pdftotext -layout "$file" - | grep -on "foo"; then
            echo "$file";
        fi;
      done 
      /%bash
    """

    _PS = _PKILL = _PGREP = _KILL = f"""{h2('Processes')}
    {h3('ps')}
      -A      All processes
      -f      Full format

    {h3('killall')} [options] NAME
      -e, --exact
      -g, --process-group     {c('Kill the process group to which the process belong')}
      -i, --interactive
      -r, --regexp            {c('POSIX extended regular expression')}
      -v, --verbose
      -I, --ignore-case

    {h3('pgrep')} [options] PATTERN
      PATTERN: Extended Regular Expression
      
      -f, --full         {c("Match full command line, not only proc name")}
          {c("note: looks like re.search() behavior, i.e. '.*' isn't needed")}
      -i, --ignore-case
      -x, --exact        {c('only match if name (or full if -f) matches PATTERN exactly')}
      -l, --list-name    {c("518197 python3.8")}
      -a, --list-full    {c("518197 python3.8 ./file.py")}
      -n, --newest       {c('Select only most recently started')}
      -o, --oldest       {c('Select only least recently started')}
    """

    _SED = f"""{h2('sed')}
  {h3('delete line from file')}
    sed 'Nd' file         {c("sed '1d' file | sed '1,3d' file")}
    sed '$d' file         {c('last line')}
    sed '2,4!d' file      {c('all except lines 2 to 4')}
    sed '2;4d' file       {c('only 2 and 4')}
    sed '/^$/d' file      {c('empty lines')}
    '/fedora/,$d'         {c('starting from a pattern till last line')}
    '${{/ubuntu/d;}}'     {c('last line only if it contains the pattern')}
    """

    _SYMLINK = _LN = _LINK = f"""{h2('ln - make links between files')}
  {c('Hard links by default')}

  {c(f'create link to {i("TARGET")} with the name {i("LINK_NAME")}:')}
  ln [OPTION]... [-T] {i('TARGET LINK_NAME')}
  {c(f'create link to {i("TARGET")} in current directory:')}
  ln [OPTION]... TARGET
  {c(f'create links to each {i("TARGET")} in {i("DIRECTORY")}:')}
  ln [OPTION]... TARGET [TARGET...] DIRECTORY

  {c(f'Note: {i("TARGET")} means the actual file path that is linked')}

  -s, --symbolic
  -i, --interactive   {c('prompt whether to remove destinations')}
  find . -type l ! -exec test -e {{}} \\; -print    {c('print empty symlinks')}
    """
    _SCP = f"""{h2('scp')} [options...] <SOURCE> ... <TARGET>
    SOURCE and TARGET may be: 
     - a local pathname (rel or abs)
     - a remote host with optional path (e.g [user@]host:[path])
     - URI e.g. scp://[user@]host[:port][/path]
    
    {h3('options')}
      -i <identity_file>
      -P <port>
      -o <ssh_option>
      -F <ssh_config>
      -p      {c('preserve attributes of original file (times, modes)')}
      -r      {c('recursively copy dirs. follows symlinks')}
      -v      {c('verbose')}
    
    {h3('scp examples')}
      %bash
      scp -i /Users/gilad/Code/rapyd/CD-COMMON.pem ./test29.json5 ubuntu@172.20.10.121:/home/rapusr/reconciliation-testing-tools/scenarios
      /%bash
  
    """

    _SORT = f"""{h2('sort')}
  sort -u   {c('unique')}
  sort -s   {c('stable. keeps orig order of same-key values')}
  sort -n   {c('numeric sort (good with du -ak | sort -n )')}
  sort -g   {c('general-numeric. like -n but handles floats')}
  sort -h   {c('human-numeric. handles SI suffix (good with du -ah | sort -h)')}
  sort -r   {c('reverse')}
  sort -V   {c('version sort.')}

  {h3('ignoring')}
    sort -b   {c('--ignore-leading-blanks')}
    sort -f   {c('--ignore-case')}
    sort -i   {c('--ignore-nonprinting')}
    sort -r   {c('--reverse')}

  history | grep -o "idea.*" | sort -u
      """
    _SPLIT = f"""{h2('split')}
  {h4('Examples')}
  %bash
  # outputs 'my_file_00', 'my_file_01', ...
  split -d --bytes 102300KB my_file.pdf my_file_
 
  # join back:
  cat my_file_* > joined.pdf
  /%bash
    """
    _STAT = f"""{h2('/bin/stat')} [OPTION...] FILE...
  stat -c, --format=FORMAT
  {h4('FORMAT')}
    %A    {c('Access rights in human format, i.e. "-rwxrwxrwx"')}
    %s    {c('Size in bytes, i.e. 22099')}

    %w    {c('creation time, human-readable')}
    %W    {c('creation time, epoch')}
    %x    {c('access time, human')}
    %X    {c('access time, epoch')}
    %y    {c('modification time, human')}
    %Y    {c('modification time, epoch')}
    %z    {c('status-change time, human')}
    %Z    {c('status-change time, epoch')}
    """
    _SUDO = _SU = f"""{h2('sudo, su')}
    {h3('sudo')}
      -u, --user=USER     {c('instead of usual default "root"')}
      -S, --stdin         {c('prompt to stderr, read pass from stdin')}
                            {c('echo mypass | sudo -S, or sudo -S <<< mypass')}
      -E, --preserve-env
      -g, --group=GROUP
      -H, --set-home
      -h, --host=HOST
      -i, --login         {c('read e.g .profile, .bash_profile or .login')}
      -P, --preserve-groups
      -s, --shell         {c('honor SHELL env var')}
    
    {h3('su')}
      -c, --command=CMD
      -g, --group=GROUP
      -, -i, --login      {c('Clear all env vars except TERM and --whitelist-environment')}
                            {c('Init HOME, SHELL, USER, LOGNAME, PATH, cd to HOME')}
      -m, -p, --preserve-environment
      -w, --whitelist-environment=FOO,BAR   {c('Ignores HOME, SHELL, USER, LOGNAME, PATH')}
    """
    _SYNTAX = rf"""{h2('Syntax')}
  {__ARGUMENTS}
  
  {__RETURN}
  
  {__ARRAY}
  
  {__CASE}
  
  {__TEST}
  
  {__FOR}
  
  {__WHILE}
  
  {__NUMBER}
  
  {__STRING}
  
  {__QUOTES}
  
  {__EXEC}
  
  {__SET}
  
  {__TYPE}
  
  {__VARIABLES}
      
  {__IF}
  
  {__FILEDESCRIPTORS}
    """

    _TR = rf"""{h2('tr')} {c('[OPTION]... SET1 [SET2]')}
  -c, -C, --complement      {c('use the complement of SET1')}
  -d, --delete              {c('delete characters in SET1, do not translate')}
  -t, --truncate-set1       {c('first truncate SET1 to length of SET2')}

  {h3('SET')}
    \NNN            {c('character with octal value NNN (1 to 3 octal digits)')}
    \\              {c('backslash')}
    \a              {c('audible BEL')}
    \b              {c('backspace')}
    \f              {c('form feed')}
    \n              {c('new line')}
    \r              {c('return')}
    \t              {c('horizontal tab')}
    \v              {c('vertical tab')}
    
    CHAR1-CHAR2     {c('all characters from CHAR1 to CHAR2 in ascending order')}
    [CHAR*]         {c('in SET2, copies of CHAR until length of SET1')}
    [CHAR*REPEAT]   {c('REPEAT copies of CHAR, REPEAT octal if starting with 0')}
    [:alnum:]       {c('all letters and digits')}
    [:alpha:]       {c('all letters')}
    [:blank:]       {c('all horizontal whitespace')}
    [:cntrl:]       {c('all control characters')}
    [:digit:]       {c('all digits')}
    [:graph:]       {c('all printable characters, not including space')}
    [:lower:]       {c('all lower case letters')}
    [:print:]       {c('all printable characters, including space')}
    [:punct:]       {c('all punctuation characters')}
    [:space:]       {c('all horizontal or vertical whitespace')}
    [:upper:]       {c('all upper case letters')}
    [:xdigit:]      {c('all hexadecimal digits')}
    [=CHAR=]        {c('all characters which are equivalent to CHAR')}

  {h3('Examples')}
    %bash
    # Replace substring:
    echo "AxxBC" | tr xyz _     # A__BC

    # To lowercase:
    echo "AbC" | tr '[:upper:]' '[:lower:]'     # abc
    
    # Delete substring:
    foo="\n hi\nbye\n "
    echo "$foo" | tr -d ' \n'           # hibye%
    echo "$foo" | tr -d '\n'            #  hibye %
    echo -n $(echo "$foo" | tr -d '\n') # hibye%
    echo -n $(echo "$foo" | tr -d ' ')  # hi bye%
    /%bash
    """

    _TRAP = f"""{h2('trap')} [-lp] [[ARG] SIGNAL ...]
    
    -l          {c('List signals and numbers')}
  
  {h3('ARG')}
    If '-' or unspecified, resets SIGNAL
  
  {h3('SIGNAL')}
    EXIT (0)    {c('Execute ARG on exit')}
    DEBUG       {c('Execute ARG on before every simple command')}
    RETURN      {c("Execute ARG after 'source' or '.' finishes")}
    ERR         {c("Execute ARG every time a command would fail on '-e' opt")}
  
  {h3('Examples')}
    %bash
    set -o errtrace
    trap 'function_name' ERR
    /%bash
  
  {h3('See also')}
    set
    """

    _WC = f"""{h2('wc')} {c('[OPTION]... [FILE]...')}
    -l, --lines     {c('newline count')}
    -w, --words     {c('word count')}
    -m, --chars     {c('character count')}
    -c, --bytes     {c('byte count')}
    
    apt list | wc -l
    wc -l data.json
    """
    _WHERE = _WHICH = _WHEREIS = _WHENCE = _WHATIS = _WHICHCOMMAND = f"""{h2('where / whereis / which / whence / whatis / which-command')}
    {h3('which')} [-a] filename ...
      -a     {c('print all matching pathnames of each argument (doesnt work?)')}
      exits 1 if one or more specified commands is nonexistent or not executable
      man which
    
    {h3('whereis')} [options] [-BMS directory... -f] name...
      man whereis
      
    {h3('whatis')} [-dlv?V] [-r|-w] [-s list] [-m system[,...]] [-M path] [-L locale] [-C file] name ...
      man whatis
    """
    _XARGS = f"""{h2('xargs')} [options] [command [initial-args]]
    {h3('Options')}
      -P <max-procs>, --max-procs=<max-procs>   {c('in Parallel')}
      -t, --verbose
      -L <max-lines>        {c('Use at most N nonblank input lines per command line. Implies -x')}
      -n <max-args>, --max-args=<max-args>      {c('Use at most max-args arguments per command line')}
      -I <replace-str>      {c('Implies -x and -L 1')}
      -p, --interactive     {c('Prompt before running each command. Implies -t')}
      -r, --no-run-if-empty
    
    {h3('Examples')}
      ls | xargs echo
      ls | xargs -L 1 echo            {c('max 1 lines')}
      xargs -0 -I % cp % ~/backups    
      -0 seems to keep line breaks?   {c("cat requirements.txt | cut -d'=' -f1 | xargs")}
      cat zooecho | vipe | xargs -I % $SHELL -c "%"
    """

    if subject:
        if subject.startswith('<') or subject.startswith('>') or subject in ('!', '?', '&', '|'):
            return __FILEDESCRIPTORS

        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('bash')}
  http://www.etalabs.net/sh_tricks.html
  {_BASENAME}
  {_CHMOD}
  {_COMPLETE}
  {_CUT}
  {_DIFF}
  {_DU}
  {_CP}
  {_ECHO}
  {_FIND}
  {_GREP}
  {_HEAD}
  {_LESS}
  {_MAN}
  {_MOUNT}
  {_PS}
  {_READ}
  {_SED}
  {_SORT}
  {_SPLIT}
  {_SCP}
  {_STAT}
  {_SUDO}
  {_SYMLINK}
  {_SYNTAX}
  {_TR}
  {_TRAP}
  {_WC}
  {_WHERE}
  {_XARGS}
  """


@syntax
def bat(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('bat')}
  bat *.sh    {c('mult files')}
  bat -n, --number, --style=numbers   {c('only line numbers, no other decors')}
  bat --paging=never
  bat -L, --list-languages
  bat -l <language>   {c('man log md')}
  bat -p    {c('plain')}
  bat -H, --highlight-line <N:M>  {c('40, 30:40, :40, 40:')}
  bat -r, --line-range <N:M>    {c('print only these lines')}
  bat --style <full|auto|plain|changes|header|grid|rule|numbers|snip>   {c('BAT_STYLE')}
  bat --list-themes   {c('BAT_THEME')}
  bat --theme
  bat --pager <command>   {c('bat --pager "less -RF"')}
  bat --wrap <auto|never|character>
  """


def brew(subject=None):
    return f"""{h1('Brew')}
    brew update && brew upgrade
      """


@syntax('monokai')
def click_(subject=None):
    _OPTION = f"""{h2('Options')}
    %python
    @click.option('-s', '--string-to-echo', 'variable_name',
                  metavar=None,                # How it's displayed 
                  required=False,
                  show_default=False,
                  type=(str, int)
                  # or:
                  type=click.types.ParamType,  # Choice, INT, ...
                  show_choices=False,          # if type is Choice
                  is_flag=False,
                  flag_value=False,
                  multiple=False,
                  count=False,                 # Increment and int
                  allow_from_autoenv=False,    # ?
                  show_envvar=False,
                  ...
                  )
    /%python

    {h3('Multi-value options')}         {c('Tuple')}
      %python
      @click.option('--pos', nargs=2)
      def findme(pos):
        click.echo('%s / %s' % pos)

      >>> findme --pos 2.0 3.0
      /%python

    {h3('Multiple options')}            {c('Tuple[T]')}
      %python
      @click.option('--message', '-m', multiple=True, type=T)
      def commit(message):
        click.echo('\\n'.join(message))

      >>> commit -m foo -m bar
      /%python

    {h3('Boolean Flags')}
      %python
      @click.option('--shout/--no-shout')
      def info(shout):  # Pass either

      @click.option('--shout', is_flag=True)
      def info(shout):  # --shout → True
      /%python

    {h3('Feature Switches')}            {c('Multiple options')}
      %python 2
      @click.option('--upper', 'transformation', flag_value='upper', default=True)
      @click.option('--lower', 'transformation', flag_value='lower')

    {h3('Prompt')}
      %python 1
      @click.option('--name', prompt='Your name please')

    {h3('Dynamic Defaults')}
      %python 3
      @click.option('--username', prompt=True,
              default=lambda: os.environ.get('USER', ''),
              show_default='current user')
    """
    _COMMAND = f"""{h2('Command')}
    %python
    @click.command(name,                   # Unless a group overrides
                   help=None,              # core.Context() args
                   short_help=None, 
                   epilog=None,            # shown at the end
                   context_settings=None,  # core.Context() args
                   callback=None,          # ?
                   options_metavar='[OPTIONS]',
                   ...
                   )
    /%python
    """
    _CONTEXT = f"""{h2('Context(')}
      %python
      command : Command cls,
      allow_extra_args : bool = None,
      
      # mixing arguments and options
      allow_interspersed_args : bool = None,  
      
      auto_envvar_prefix : str = None,
      color = None,
      context_settings=,
      default_map : {{ str : {{ str : any }} }} = {{ command : {{ option : value }} }},
      help_option_names : str[] = ['--help'],
      ignore_unknown_options : bool = None,
      info_name : str = None,
      max_content_width : int = 80, 
      
      # arbitrary user data
      obj = None,              
      
      parent : Context = None,
      resilient_parsing : bool = False,
      
      # overrides show_default=True for all following options
      show_default : bool = False,    
      
      terminal_width : int = None,
      token_normalize_func = None
      )
      /%python
    """
    _GROUP = f"""{h2('Group(MultiCommand)')}
    {c('https://click.palletsprojects.com/en/7.x/commands/')}
    
    {h3('@click.group(')}
        %python
        name = None,
        invoke_without_command : bool = False,
        no_args_is_help : bool = not invoke_without_command,
        subcommand_metavar : str = '', 
        chain : bool = False
        )
        /%python
          
    
    {h3('Basic')}
      %python
      @click.group()
      @click.option('--debug/--no-debug', default=False)
      def foo(debug): ...
      
      @foo.command()
      def sync(): ...
      /%python
      
      %bash 1
      $ tool.py --debug sync
        
    {h3('No Subcommand')}
      %python
      @click.group(invoke_without_command=True)
      @click.pass_context
      def foo(ctx):
          if ctx.invoked_subcommand is None: ...
      
      @foo.command()
      def sync(): ...
      /%python
      
      %bash 1
      $ tool.py
    
    {h3('Merging Multiple Groups')}
      %python
      @click.group()
      def foo(): ...
      
      @foo.command()
      def foo_cmd(): ...
      
      @click.group()
      def bar(): ...
      
      @bar.command()
      def bar_cmd(): ...
      
      cli = click.CommandCollection(sources=[foo, bar])
      
      if __name__ == '__main__':
          cli()    
      /%python

    {h3('Chaining Subcommands')}
      %python
      @click.group(chain=True)
      def main(): ...
      
      @main.command('foo')
      def foo(): ...
      
      @main.command('bar')
      def bar(): ...
      /%python
      
      %bash 1
      $ tool foo bar
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    return f"""{h1('Click')}
  {_CONTEXT}
  
  {_OPTION}
    
  {_COMMAND}
  
  {_GROUP}
    """


def clickup(subject=None):
    return f"""{h1('ClickUp')}

  {h2('Hierarchy')}
    Workspace: Facebook (business)
      Spaces: "Marketing" (departments)
        Folders: "Social Media Outreach", "Web Design" (workflows)
          Lists: "Facebook Ad Campaign", "About Page" (projects)
            Tasks: "Create a Facebook Event", "New Logo"
              Subtasks
                Checklist
    """


@syntax
def css(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('css')}
  {h2('Attribute Selectors')}
    [attr]            {c("element with attribute 'attr'")}
    [attr=VALUE]
    [attr~=VALUE]     {c("whitespace separated words, where one is exactly VALUE")}
    [attr|=VALUE]     {c("exactly VALUE or VALUE-foo")}
    [attr^=VALUE]     {c("VALUEfoo")}
    [attr$=VALUE]     {c("fooVALUE")}
    [attr*=VALUE]     {c("has VALUE substring")}
    [attr <operator> VALUE i]     {c("regards VALUE case-insensitively")}
    
    {h4('examples')}
      a[href^="https"][href$=".org"]    {c("starts with 'https', ends with '.org")}
      div:not([lang])                   {c("divs without 'lang' attribute")}
      div[lang|="zh"]                   {c("zh-CN or zh-TW")}
  
  {h2('Pseudo Classes')}
    {c('https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes')}
    %css
    /* any paragraph inside a header, main or footer, that is being hovered */
    :is(header, main, footer) p:hover {{ }}
    /* equivalent to: */
    header p:hover, main p:hover, footer p:hover {{ }}
    /%css
    
    {h4('User action')}
      :hover, :active, :focus, :focus-visible, :focus-within 
    
    {h4('Resource state')}
      :playing, :paused
    
    {h4('Input')}
      :enabled, :disabled, :read-only, :read-write, :placeholder-shown, 
      :default, :checked, :indeterminate, :blank, :valid, :invalid, 
      :in-range, :out-of-range, :required, :optional, :user-invalid
      
    {h4('Tree')}
      :root, :empty, :nth-child, :nth-last-child, :first-child,
      :last-child, :only-child, :nth-of-type, :nth-last-of-type,
      :first-of-type, :last-of-type, :only-of-type
    
  {h2('Pseudo Elements')}
    {c('https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-elements')}
    :after, :backdrop 📡, :before, :cue, :cue-region, 
    :first-letter, :first-line, :file-selector-button, 
    :grammar-error 📡, :marker 📡, :part 📡, :placeholder 📡, 
    :selection, :slotted, :spelling-error 📡
  
  {h2('Combinators')}
    {c('https://developer.mozilla.org/en-US/docs/Web/CSS/Adjacent_sibling_combinator')}
    img + p {{ }}   {c('Paragraphs that come immediately after any image')}
    img ~ p {{ }}   {c("p's that are siblings or children of img (any depth)")}
    img > p {{ }}   {c("direct children of img")}
    img   p {{ }}   {c("children of img (any depth)")}
  """


@syntax
def curl(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('curl')}
  -f, --fail        {c('(HTTP) Fail silently (no output at all) on server errors')}
  --fail-early      {c('return an error on the first transfer that fails')}
  --create-dirs
  -o, --output      {c('Write output to <file> instead of stdout')}
  -L, --location    {c('Follow redirects')}
        """


@syntax
def delta(subject=None):
    return f"""{h1('delta')} [FLAGS] [OPTIONS] [ARGS]
  www.github.com/dandavison/delta

  delta file_1 file_2
  diff -u file_1 file_2 | delta

  {h2('Flags')}
     -n, --line-numbers
     -s, --side-by-side
     --show-config
    
    """


@syntax
def django(subject=None):
    _MISC = f"""{h2('misc')}
    %bash
    # alongside .gitignore, creates a manage.py and <PROJ>/ dir with asgi.py, setting.py, urls.py, wsgi.py:
    django-admin startproject <PROJ> .

    # create <APP>/ dir with admin.py etc:
    python manage.py startapp <APP>
    
    # add to top of settings.INSTALLED_APPS string:
    <APP>.apps.<Class name>     # class from <APP>/apps.py.<Class name>
    
    # not sure?
    python manage.py createsuperuser
    /%bash

    File import order:
      PROJ/__init__.py
      PROJ/settings.py
      PROJ/__init__.py  {c('yeah, twice')}
      PROJ/settings.py
      {c('Watching for file changes with StatReloader, Performing system checks...')}
      PROJ/urls.py
      APP/__init__.py
      APP/urls.py
      APP/views.py
      {c('Starting development server at http://127.0.0.1:8000')}
      PROJ/wsgi.py
    """

    _UTILS = f"""{h2('django.utils')}
    timezone.now() {c('-> datetime.datetime(2020, 12, 19, 6, 12, 57, 938731, tzinfo=<UTC>)')}
    timezone.get_current_timezone() {c('-> pytz.UTC: <UTC>')}
    timezone.get_current_timezone_name() {c('-> str: "UTC"')}
    timezone.get_default_timezone() {c('-> pytz.UTC: <UTC>')}
    timezone.get_default_timezone_name() {c('-> str: "UTC"')}
    """

    _ADMIN = f"""{h2('django-admin')} <subcommand>
    check
    compilemessages
    createcachetable
    dbshell
    diffsettings
    dumpdata
    flush
    inspectdb
    loaddata
    makemessages
    
    {h3('makemigrations')} [option...] [app_label ...]
      {h4('positional')}
      app_label                      {c('app label(s) to create migrations for')}
      
      {h4('options')}
      -n NAME, --name NAME           {c('of migration file')}
      --check                        {c('exit non-zero if model changes are missing migrations')}
      --dry-run                      
    
    migrate
    runserver
    sendtestemail
    shell
    showmigrations
    sqlflush
    sqlmigrate
    sqlsequencereset
    squashmigrations
    startapp
    
    {h3('startproject')} [option...] <name> [directory]
      {h4('positional')}
      name                          {c('Name of the application or project.')}
      directory                     {c('Optional destination directory')}
      
      {h4('options')}
      -h, --help
      --template TEMPLATE           {c('The path or URL to load the template from.')}
      --extension EXTS, -e EXTS     {c('extension(s) to render (default: "py")')}
      --name FILES, -n FILES        {c('file name(s) to render')}
      -v {{0,1,2,3}}, --verbosity {{0,1,2,3}}
      --settings SETTINGS           {c('e.g. "myproject.settings.main". default: DJANGO_SETTINGS_MODULE')}
      --pythonpath PYTHONPATH       {c('dir to add to Python path, e.g. "/home/djangoprojects/myproject"')}
    
    test
    testserver

    """

    _MANAGE = _MANAGEPY = f"""{h2('manage.py')}
    {h3('runserver')}
      --no[threading reload static]
      --insecure      {c('serve static even if DEBUG is False')}
      --settings {i('myproject.settings.main')}   {c('python module path. default: DJANGO_SETTINGS_MODULE env var')}
      --pythonpath {i('PYTHONPATH')}
    
    {h3('shell')} OPTIONS
      -c, --command COMMAND     {c('no interactive, just run COMMAND and exit')}
      -i, --interface <ipython | bpython | python>
      --no-startup              {c('When plain Python, ignore PYTHONSTARTUP env var and ~/.pythonrc.py')}

    {h3('createsuperuser')}
    """

    _MODELS = f"""{h2('models')}
    ForeignKey: many-to-one     {c('class Car')}
                                    {c('manufacturer = ForeignKey(Manufacturer)')}
                                    {c(f'# Many cars for one manufacturer')}
                                    {c(f'# behind the scenes, a {i("manufacturer_id")} column is created')}

    ManyToManyField             {c('class Person')}
                                    {c('pass')}
                                {c('class Group')}
                                    {c('members = ManyToManyField(Person)')}
                                    {c(f'# A person can be in many groups, and a group can have many persons')}

    OneToOneField               {c('class MySpecialUser')}
                                    {c('user = OneToOneField(User)')}

    {h3('Interactive / testing')} {c('manage.py shell [OPTIONS]')}
      https://tutorial.djangogirls.org/en/django_orm/
      %ipython
      # Database models:
      from <APP>.models import <Model>
      <Model>.objects.all() # -> QuerySet
      <Model>.objects.create(...)

      # Pretend user login:
      from django.contrib.auth.models import User
      /%ipython
    """

    _TEMPLATES = f"""{h2('templates')}
    {{% autoescape %}}
    {{% block %}} {{% endblock %}}
    {{% comment %}} {{% endcomment %}}
    {{% csrf_token %}}
    {{% cycle %}}
    {{% debug %}}
    {{% extends "" %}}
    {{% filter %}} {{% endfilter %}}
    {{% firstof %}}
    {{% for in %}} {{% endfor %}}
    {{% for in %}} {{% empty %}} {{% endfor %}}
    {{% if %}} {{% endif %}}
    {{% if %}} {{% else %}} {{% endif %}}
    {{% ifchanged %}} {{% endifchanged %}}
    {{% ifequal %}} {{% endifequal %}}
    {{% ifnotequal %}} {{% endifnotequal %}}
    {{% include %}}
    {{% load %}}
    {{% now "" %}}
    {{% regroup by as %}}
    {{% spaceless %}} {{% endspaceless %}}
    {{% ssi %}}
    {{% static %}}
    {{% templatetag %}}
    {{% url %}}
    {{% verbatim %}} {{% endverbatim %}}
    {{% widthratio %}}
    {{% with as %}} {{% endwith %}}
    {{% trans %}}
    {{% blocktrans with as %}} {{% endblocktrans %}}

    """

    _DJANGO_EXTENSIONS = f"""{h2('django-extensions')}  {c('pip install django-extensions')}
    dumpscript
    graph_models
    show_urls
    shell_plus
    runserver_plus
    passwd <USER>  {c('change user password')}
    models.TimeStampedModel
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Django 3')}
  {c('https://cloud.google.com/python/django/appengine')}
  {_ADMIN}
  
  {_MODELS}
  
  {_TEMPLATES}

  {_UTILS}

  {_MISC}
  
  {_MANAGEPY}
"""


@syntax(bash='friendly')
def docker(subject=None):
    _DOCKERFILE = f"""{h2('Dockerfile')}
        {h3('examples')}
          {c('https://www.youtube.com/watch?v=i7ABlHngi1Q')}
          %docker
          FROM node:latest
          RUN mkdir -p /app/src
          WORKDIR /app/src
          COPY package.json .    // dot aka "here" is WORKDIR
          RUN npm install
          COPY . .    // copy everything from /app/src to /app/src (why?)
          EXPOSE 3000    // React port
          CMD ["npm", "start"]
          /%docker
          """
    # *** docker-compose
    # ** Listing
    __COMPOSE_IMAGES = f"""{h3('images')} [options] [--] [SERVICE...]
    {bg('List images used by the created containers.')}
      {c('           Container                                          Repository                                        Tag             Image Id       Size ')}
      {c('-----------------------------------------------------------------------------------------------------------------------------------------------------')}
      {c('allotsecure_accounts_1            artifactory.rdlab.local/microservices-docker-sandbox-local/accounts   latest                8a45be89039f   550.5 MB')}
      {c('allotsecure_jaeger-all-in-one_1   jaegertracing/all-in-one                                              1.16.0                fea586ade9d0   50.51 MB')}
    """
    __COMPOSE_PS = f"""{h3('ps')} [options]
    {bg('List containers')}
      {c('             Name                            Command                 State               Ports ')}
      {c('-------------------------------------------------------------------------------------------------------')}
      {c('allotsecure_accounts_1            /bin/sh                          Up           0.0.0.0:6066->5000/tcp')}
      
      -a, --all                          {c('Show also stopped containers')}
          --services
    """

    # ** Starting
    __COMPOSE_START = f"""{h3('start')} [SERVICE...]
    {bg('Start existing containers')}
    """
    __COMPOSE_RUN = f"""{h3('run')} [options] [--] SERVICE [COMMAND] [ARGS...]
    {bg('Run a one-off command on a service.')}
    {bg('Dependencies are started by default if not already running.')}

      -d, --detach
          --name NAME                    {c('Assign a name to the container')}
          --entrypoint CMD               {c('Override the entrypoint of the image.')}
      -e KEY=VAL                         {c("Set an environment variable (can be used multiple times)")}
      -l, --label KEY=VAL                {c("Add or override a label (can be used multiple times)")}
      -u, --user=""                      {c("Run as specified username or uid")}
      --no-deps                          {c("Don't start linked services.")}
      --rm                               {c("Remove container after run. Ignored in detached mode.")}
      -T                                 {c("Disable pseudo-tty allocation.")}
      -w, --workdir=""                   {c("Working directory inside the container")}
      -p, --publish=[]                   {c("Publish a container's port(s) to the host")}
    """
    __COMPOSE_UP = f"""{h3('up')} [options] [--scale SERVICE=NUM...] [--] [SERVICE...]
    {bg('Builds, (re)creates, starts, and attaches to containers for a service.')}
                                         {c('Starts any linked services if needed.')}
      -d, --detach                       {c('Run in background.')}
          --no-start                     {c("Don't start services after creating them")}
          --build                        {c("Built images before starting containers.")}
          --no-build                     {c("Don't build an image, even if it's missing.")}
          --no-recreate                  {c("If containers already exist, don't recreate them.")}
          --force-recreate               {c("Create containers even if their config and image haven't changed.")}
          --always-recreate-deps         {c("Recreate dependent containers.")}
          --no-deps                      {c("Don't start linked services.")}
    """
    # ** Stopping
    __COMPOSE_DOWN = f"""{h3('down')} [options]
    {bg('Stops containers and removes cont, net, vol, imgs created by `up` from Compose file.')}
      --rmi <all|local>                  {c('Remove images.')}
      -v, --volumes                      {c('Remove volumes declared in `volumes` of Compose file and anonymous volumes attached to containers')}
      --remove-orphans                   {c('Remove containers for services not defined in Compose file.')}
    """

    __COMPOSE_STOP = f"""{h3('stop')} [options] [--] [SERVICE...]
    {bg('Stop running containers without removing them. Can be started again with `up`')}
    {c('SERVICE is output of docker-compose ps --services')}
    %bash
    docker-compose stop mosquitto adminmongo
    /%bash
    """

    _COMPOSE = f"""{h2('docker-compose')}
  LISTING
    {__COMPOSE_IMAGES}
    {__COMPOSE_PS}
  STARTING
    {__COMPOSE_START}
    {__COMPOSE_RUN}
    {__COMPOSE_UP}
  STOPPING
    {__COMPOSE_DOWN}
    {__COMPOSE_STOP}
    """

    # *** docker
    # ** Listing
    __CLI_IMAGES = f"""{h3('images')} [OPTIONS] [REPOSITORY[:TAG]]
    {bg('List images')}
      {c('REPOSITORY                                                             TAG       IMAGE ID       CREATED        SIZE')}
      {c('artifactory.rdlab.local/microservices-docker-sandbox-local/accounts    latest    3b1418a4971e   20 hours ago   493MB')}
    
      -a, --all                          {c("Don't hide intermediate images")}
    """
    __CLI_PS = f"""{h3('ps')} [OPTIONS]
    {bg('List containers')}
      {c('CONTAINER ID   IMAGE                                                                        COMMAND      CREATED          STATUS          PORTS                     NAMES')}
      {c('6f1563558e8e   artifactory.rdlab.local/microservices-docker-sandbox-local/accounts:latest   "/bin/sh"    23 minutes ago   Up 23 minutes   0.0.0.0:6066->5000/tcp    allotsecure_accounts_1')}
      
      -a, --all
      -s, --size
    """
    __CLI_INSPECT = f"""{h3('inspect')} [OPTIONS] NAME|ID [NAME|ID...]
    {bg('Return low-level information on Docker objects')}
    """
    # ** Starting
    __CLI_RUN = f"""{h3('run')} [OPTIONS] IMAGE [COMMAND] [ARG...]
    {bg('Run a command in a new container')}
      --rm                               {c('Remove intermediate containers after a successful build')}
      --it                               {c('Interactive process (like a shell)')}
      -p <LOCAL PORT>:<INSIDE CONTAINER PORT>
      dozens of additional options
    """

    __CLI_BUILD = f"""{h3('build')} [OPTIONS] PATH | URL | -
    {bg('Build an image from a Dockerfile')}
      --rm                               {c('Remove intermediate containers after a successful build')}
      -f <DOCKERFILE PATH>               {c("default is PATH/Dockerfile")}
      --build-arg <key=value LIST>       {c("Set build-time variables")}
      -t, --tag <name:tag LIST>          {c("Name and optionally a tag in the 'name:tag' format")}

      {h4('examples')}
        %bash
        docker build . -t <TAGNAME>   # dot because Dockerfile in PWD
        /%bash
    """
    __CLI_RESTART = f"""{h3('restart')} [OPTIONS] CONTAINER [CONTAINER...]
    {bg('Restart one or more containers')}
    """
    # ** Stopping
    __CLI_RM = f"""{h3('rm')} [OPTIONS] CONTAINER [CONTAINER...]
    {bg('Remove one or more containers')}
      -f, --force                        {c('uses SIGKILL')}
    """

    __CLI_RMI = f"""{h3('rmi')} [OPTIONS] IMAGE [IMAGE...]
    {bg('Remove one or more images')}
      -f, --force                        {c('uses SIGKILL')}
    """

    __CLI_STOP = f"""{h3('stop')} [OPTIONS] CONTAINER_ID [CONTAINER_ID...]
    {bg('Stop one or more running containers')}
    {c('CONTAINER_ID is output of docker ps -q')}
    %bash
    docker stop 83a036c2fe15 16d0b2aa69a0
    /%bash
    """

    __CLI_KILL = f"""{h3('kill')} [OPTIONS] CONTAINER [CONTAINER...]
    {bg('Kill one or more running containers')}
      -s, --signal <STRING>              {c('default KILL')}
    """
    __CLI_SUBCOMMANDS = f"""{h3('subcommands')}
    app*        {c('Docker App (Docker Inc., v0.9.1-beta3)')}
    builder     {c('Manage builds')}
    buildx*     {c('Build with BuildKit (Docker Inc., v0.5.1-docker)')}
    config      {c('Manage Docker configs')}
    container   {c('Manage containers')}
    context     {c('Manage contexts')}
    image       {c('Manage images')}
    manifest    {c('Manage Docker image manifests and manifest lists')}
    network     {c('Manage networks')}
    node        {c('Manage Swarm nodes')}
    plugin      {c('Manage plugins')}
    secret      {c('Manage Docker secrets')}
    service     {c('Manage services')}
    stack       {c('Manage Docker stacks')}
    swarm       {c('Manage Swarm')}
    system      {c('Manage Docker')}
    trust       {c('Manage trust on Docker images')}
    volume      {c('Manage volumes')}
    """
    _CLI = f"""{h2('docker')}
  {__CLI_SUBCOMMANDS}
  LISTING
    {__CLI_IMAGES}
    {__CLI_PS}
    {__CLI_INSPECT}
  STARTING
    {__CLI_RUN}
    {__CLI_BUILD}
    {__CLI_RESTART}
  STOPPING
    {__CLI_RM}
    {__CLI_RMI}
    {__CLI_STOP}
    {__CLI_KILL}
    """

    # *** docker container
    # ** Listing
    __CONTAINER_LS = f"""{h3('ls')} [OPTIONS]
    {bg('List containers')}
    -a, --all
    """
    __CONTAINER_STATS = f"""{h3('stats')}
    """
    __CONTAINER_LOGS = f"""{h3('logs')} [OPTIONS] CONTAINER
    {bg('Fetch the logs of a container')}
        --details
    -t, --timestamp
        --since SINCE                    {c('2013-01-02T13:23:37Z | 42m | 42 minutes')}
        --until UNTIL                    {c('2013-01-02T13:23:37Z | 42m | 42 minutes')}
    """
    __CONTAINER_TOP = f"""{h3('top')} CONTAINER [ps OPTIONS]
    {bg('Display the running processes of a container')}
    """
    __CONTAINER_INSPECT = f"""{h3('inspect')}
    """
    __CONTAINER_DIFF = f"""{h3('diff')}
    """
    # ** Starting
    __CONTAINER_START = f"""{h3('start')}
    """
    __CONTAINER_RUN = f"""{h3('run')}
    """
    __CONTAINER_RESTART = f"""{h3('restart')}
    """
    __CONTAINER_EXEC = f"""{h3('exec')}
    """
    __CONTAINER_ATTACH = f"""{h3('attach')}
    """
    __CONTAINER_UNPAUSE = f"""{h3('unpause')}
    """
    __CONTAINER_UPDATE = f"""{h3('update')}
    """
    # ** Stopping
    __CONTAINER_STOP = f"""{h3('stop')}
    """
    __CONTAINER_KILL = f"""{h3('kill')}
    """
    __CONTAINER_RM = f"""{h3('rm')}
    """
    __CONTAINER_PAUSE = f"""{h3('pause')}
    """

    __CONTAINER_PRUNE = f"""{h3('prune')}
    """

    # ** Not sure
    __CONTAINER_WAIT = f"""{h3('wait')}
    """
    __CONTAINER_COMMIT = f"""{h3('commit')}
    """
    __CONTAINER_CP = f"""{h3('cp')}
    """
    __CONTAINER_CREATE = f"""{h3('create')}
    """
    __CONTAINER_EXPORT = f"""{h3('export')}
    """
    __CONTAINER_RENAME = f"""{h3('rename')}
    """
    __CONTAINER_PORT = f"""{h3('port')}
    """

    _CONTAINER = f"""{h2('docker container')}
  LISTING
    {__CONTAINER_LS}
    {__CONTAINER_STATS}
    {__CONTAINER_LOGS}
    {__CONTAINER_TOP}
    {__CONTAINER_INSPECT}
    {__CONTAINER_DIFF}
  STARTING
    {__CONTAINER_START}
    {__CONTAINER_RUN}
    {__CONTAINER_RESTART}
    {__CONTAINER_EXEC}
    {__CONTAINER_ATTACH}
    {__CONTAINER_UNPAUSE}
    {__CONTAINER_UPDATE}
  STOPPING
    {__CONTAINER_STOP}
    {__CONTAINER_KILL}
    {__CONTAINER_RM}
    {__CONTAINER_PAUSE}
    {__CONTAINER_PRUNE}
  NOT SURE
    {__CONTAINER_WAIT}
    {__CONTAINER_COMMIT}
    {__CONTAINER_CP}
    {__CONTAINER_CREATE}
    {__CONTAINER_EXPORT}
    {__CONTAINER_RENAME}
    {__CONTAINER_PORT}
    """

    # *** Collections
    _LISTING = f"""
{h2('docker-compose')}
  {__COMPOSE_IMAGES}
  {__COMPOSE_PS}
{h2('docker')}
  {__CLI_IMAGES}
  {__CLI_PS}
  {__CLI_INSPECT}
    """
    _STARTING = f"""
{h2('docker-compose')}
  {__COMPOSE_START}
  {__COMPOSE_RUN}
  {__COMPOSE_UP}
{h2('docker')}
  {__CLI_RUN}
  {__CLI_BUILD}
  {__CLI_RESTART}
    """
    _STOPPING = f"""
{h2('docker-compose')}
  {__COMPOSE_DOWN}
  {__COMPOSE_STOP}
{h2('docker')}
  {__CLI_RM}
  {__CLI_RMI}
  {__CLI_STOP}
  {__CLI_KILL}
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('docker')}
  {_DOCKERFILE}
  
  {_CONTAINER}
  
  {_COMPOSE}
  
  {_CLI}
  """

@syntax
def dpkg(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('dpkg')} [option...] <action>   {c('options first')}
    {h2('action')}
      -i, --install <package-file>...
      --unpack <package-file>...
      -r, --remove <package>...     {c('removes everything except conffiles and other data')}
      -P, --purge <package>...
    
    {h2('option')}
      --no-act, --dry-run, --simulate
      -G, --refuse-downgrade      {c('do nothing if newer is installed')}
      -E, --skip-same-version     {c('do nothing if same version is installed')}
      --log=<filename>            {c('instead of to /var/log/dpkg.log')}
    
    {h2('dpkg-query')}
      -l, --list <package-name-pattern>...    {c('list matching packages')}
      -s, --status <package-name>...
      -L, --listfiles <package-name-pattern>...    {c('list files from packages')}
      -S, --search <filename-name-pattern>...    
      -p, --print-avail <package-name>...     {c('display details')}

    {h2('trick')}
      If online it says a file is in pool/main/g/gcc-10/, then this works:
      http://ftp.fr.debian.org/debian/pool/main/g/gcc-10/
    """

def fasd(subject=None):
    return f"""{h1('fasd')}
  f(files), a(files/directories), s(show/search/select), d(directories)

  {h2('aliases')}
    a='fasd -a'             any (files and directories)
    d='fasd -d'             directory
    f='fasd -f'             file
    j=zz
    s='fasd -si'            show / search / select
    sd='fasd -sid'          interactive directory selection
    sf='fasd -sif'          interactive file selection
    z='fasd_cd -d'          cd, same functionality as j in autojump
    zz='fasd_cd -d -i'      cd with interactive selection

  {h2('options')}
    -s                      paths w/ scores
    -l                      paths w/o scores
    -i                      interactive
    -e {i('cmd')}                  cmd to exec on resulting file
    -a                      any (files and directories)
    -d                      dirs
    -f                      files
    -R                      reverse
    -A {i('paths...')}             add paths
    -D {i('paths...')}             delete paths

  {h2('examples')}
    f foo                   files matching foo
    a foo bar               files / dirs matching foo and bar
    j abc                   cd /hell/of/a/awkward/path/to/get/to/abcdef
    f js$                   files that end in js
    f -e vim foo            run vim on the most frecent file matching foo
    v eng paper             vim /you/dont/remember/where/english_paper.pdf
"""


def ffmpeg(subject=None):
    _CONVERT = f"""{h2('Convert')}
    {h3('between video formats')}
    ffmpeg -i vid.mkv -codec copy vid.mp4

    {h3('between audio formats')}
    ffmpeg -i song.m4a -acodec lame_enc -aq 2 song.mp3

    {h3('mp4 to gif')}
    ffmpeg -i vid.mp4 -f gif -s 960x540 -r 10 vid.gif
    ffmpeg -i vid.mp4 -filter_complex '[0:v] fps=30,scale=480:-1,split [a][b];[a] palettegen [p];[b][p] paletteuse' vid.gif
    """
    _SRT = _SUBS = f"""{h2('SRT')}
    {h3('embed srt')}
    ffmpeg -i vid.mp4 -c copy -filter:v subtitles=vid.srt vid_with_subs.mp4
    ffmpeg -i vid.mp4 -i vid.srt -map 0 -map 1 -c copy -metadata:s:s:0 language=eng -metadata:s:s:1 language=ipk vid_with_subs.mkv

    {h3('extract srt from mkv')}
    ffmpeg -i vid.mkv-map 0:s:0 vid.srt
    """
    _AUDIO = f"""{h2('Audio')}
    {h3('reduce filesize')}
    ffmpeg -i input.mp3 -map 0:a:0 -b:a 96k output.mp3

    {h3('compress')}
    ffmpeg -i input.mp3 -filter_complex 'compand=attacks=0:points=3/1' output.mp3

    {h3('remove audio track')}
    ffmpeg -i vid.mp4 -c:v copy -an vid-no-audio.mp4
    """
    __CONCAT = f"""{h3('Concat')}
      {c('Has to convert to .ts first')}
      ffmpeg -i vid1.mp4 -c copy -bsf:v h264_mp4toannexb -f mpegts tmp1.ts && \\
      ffmpeg -i vid2.mp4 -c copy -bsf:v h264_mp4toannexb -f mpegts tmp2.ts && \\
      ffmpeg -i "concat:tmp1.ts|tmp2.ts" -c copy -bsf:a aac_adtstoasc out.mp4 && \\
      rm tmp1.ts tmp2.ts
      
      {c('Picture overlay')}
      ffmpeg -i vid.mp4 -i pic.jpg  -filter_complex "[0:v][1:v] overlay=0:0:enable='between(t,26,32)'" -pix_fmt yuv420p out.mp4
    """
    __MERGE = f"""{h3('Merge (audio and video)')}
      ffmpeg -i video.mp4 -i audio.wav -c copy output.mkv
      {c('OR (replace existing audio)')}
      ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -strict experimental -map 0:v:0 -map 1:a:0 output.mp4
    """
    __TRIM = f"""{h3('Trim')}
      {c('starting from 00:32:44 and lasting 11m:')}
      ffmpeg -ss 00:32:44 -i full.mp4 [-t 00:11:00] [-c:v libx264] -async 1 -strict -2 trimmed.mp4
      
      {c('starting from 00:32:44 to 00:33:00:')}
      ffmpeg -ss 00:32:44 -i full.mp4 -to 00:33:00 [-c:v libx264] -async 1 -strict -2 trimmed.mp4
    """
    __CROP = f"""{h3('Crop')}
      -qp [0/lossless : 50/lossy]

      {c('for ancient devices')}
      -profile:v baseline -level 3.0

      {c('puts info at beginning of file, good for streaming (youtube)')}
      {c('https://trac.ffmpeg.org/wiki/Encode/H.264')}
      ffmpeg -i input.mp4 -filter:v "crop=w:h:x:y" -qp 12 -preset ultrafast -tune zerolatency -profile:v baseline -level 3.0 -movflags +faststart output.mp4
      ffmpeg -i input.mp4 -filter:v "crop=in_w/2:in_h/2:in_w/2:in_h/2" -c:a copy output.mp4
      ffmpeg -i input.mp4 -filter:v "crop=320/2:240/2:320/2:240/2" -c:a copy output.mp4
      ffmpeg -i input.mp4 -filter:v "crop=iw:ih-40" -c:a copy output.mp4
      
      {c('Preview')}
      ffplay -i input.mp4 -vf "crop=in_w:in_h-40"
    """
    __SIZE = f"""{h3('Reduce filesize')}
      {c('constant rate; higher = lower bitrate')}
      ffmpeg -i input.mp4 -vcodec [h264 / libx265] [-crf 20] [-acodec [mp3 / aac] -b:a 96k] output.mp4
        -vcodec libx265 -crf 20    {c('153kbps vid')}
        -vcodec h264 -crf 20       {c('137kbps vid')}
        -vcodec h264 -crf 30       {c('81kbps vid')}
    """
    __FRAMERATE = f"""{h3('Framerate')}
      ffmpeg -i input.avi -r 24 -b:v 1640k -bufsize 1640k output.avi

      {c('OR (with reencoding, takes time, much smaller filesize)')}
      {c('setpts=1.25*PTS makes it 1.25x SLOWER (30/1.25 = 24)')}
      ffmpeg -i input.mp4 -vf "setpts=1.25*PTS" -r 24 output.mp4
        -vf "setpts=1.25*PTS"   {c('makes it 1.25x slower')}
        -r 24                   {c('compensates')}

      {c('OR (without reencoding, takes some time, same filesize)')}
      ffmpeg -i input.mp4 -c copy -f h264 output.mp4
      ffmpeg -r 24 -i output.mp4 -c copy output.mp4
    """
    _VIDEO = f"""{h2('Video')}
    {__CONCAT}
    {__MERGE}
    {__TRIM}
    {__CROP}
    {__SIZE}
    {__FRAMERATE} """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('ffmpeg')}
  {_CONVERT}
  {_SRT}
  {_AUDIO}
  {_VIDEO}
  """


@syntax
def firestore(subject=None):
    _COLLECTION_REF = f"""{h2('CollectionReference')}
    cities_ref = db.collection('cities')

    {h3(f'document({c("document_id")})')} {c('→ DocumentReference')}

    {h3('add()')} {c('→ (Timestamp, DocumentReference)')}
      created, ref = cities_ref.add(city.to_dict())

    {h3('stream()')} {c('→ Generator[DocumentSnapshot]')}
      %python
      docs = cities_ref.stream()
      for doc in docs:
        ...
      /%python

    {h3(f'where({c("field_path, op_string, value")})')}
      %python
      cities_ref.where('capital', '==', True).stream()
      query = cities_ref.where('regions', 'array_contains', 'west_coast')
      /%python

      {h4('op_string')} : str
      less_than, less_than_or_equal, greater_than, greater_than_or_equal, equal,
      array_contains    {c(f'{i("field")} must be an array that contains given {i("value")}')}
      in    {c(f'{i("value")} must be an array, {i("field")} is equal to at least one value in given array')}
      array_contains_any    {c(f'{i("field")} and {i("value")} both must be an array')}

      {h4('can be compound')}
      %python
      cities_ref.where('state', '==', 'CA')
      cities_ref.where('population', '<', 1000000)
      cities_ref.where('name', '>=', 'San Francisco')
      /%python

      {h4('and chained')}
      {c('in place of sql AND. each where doesnt return a filtered result')}
      %python
      cities_ref.where('state', '>=', 'CA').where('state', '<=', 'IN')
      /%python

    {h3('order_by()')}
      %python
      cities_ref.order_by('name').limit(3).stream()
      cities_ref.order_by('name', direction=firestore.Query.DESCENDING).limit(3).stream()
      /%python

      {h4('chained')}
      %python
      cities_ref.order_by('state').order_by('population', direction=firestore.Query.DESCENDING)
      /%python
    """
    _COLL_REF = _COLLECTION_REF

    _DOCUMENT_REF = f"""{h2('DocumentReference')}        {c('CollectionReference.document(...)')}
    washington_ref = db.collection('cities').document('DC')
      .id {c(': str')}
      .parent {c(': CollectionReference')}

    {h3(f'get()')} {c('→ DocumentSnapshot')}
      {c("ok if doc doesn't exist (use snapshot.exists)")}

      doc = washington_ref.get()
      City.from_dict(doc.to_dict())
      {c('···')}
      washington_ref.get(transaction=trans)
        {c("only when trans in progress, and before write")}
      {c('···')}
      washington_ref.get('key.nested')

    {h3(f'create({c("doc_data : dict")})')} {c('→ WriteResult')}
      {c("if doc exists, raises AlreadyExists")}

    {h3(f'set({c("doc_data : dict")})')} {c('→ WriteResult')}
      {c("if doc exists, overwrites. if it doesn't, creates it")}
      {c("'doc.data' delimited doesn't work here")}

      washington_ref.set(city.to_dict())
      washington_ref.set(dict(..., merge=True))  {c('update or field or create if missing')}

    {h3(f'update({c("field_updates : dict")})')} {c('→ WriteResult')}
      {c("if doc doesn't exist, raises NotFound")}
      {c("if key doesn't exist, creates it")}

      washington_ref.update({{'capital': True}})
      {c('···')}
      washington_ref.update({{'key.nested': True}})
      {c('···')}
      washington_ref.update({{'key.nested': firestore.DELETE_FIELD}})
        {c('or firestore.SERVER_TIMESTAMP')}
    """
    _DOC_REF = _DOCUMENT_REF

    _DOCUMENT_SNAPSHOT = f"""{h2('DocumentSnapshot')}        {c('DocumentReference.get()')}
    snapshot = db.collection('cities').document('DC').get()
      .create_time {c(': Timestamp')}
      .exists {c(': bool')}
      .id {c(': str')}
      .read_time
      .update_time {c(': Timestamp')}
      .reference {c(': DocumentReference')}

    snapshot.to_dict()
    snapshot.get({c('field_path')}) {c("→ DocumentReference  (KeyError if doesn't exist)")}
    """
    _DOCUMENT_SNAP = _DOCUMENT_SNAPSHOT
    _DOC_SNAP = _DOCUMENT_SNAPSHOT

    _TIMESTAMP = f"""{h2('Timestamp')}
    ts.ToSeconds() {c(': int')}
    ts.ToDatetime() {c(': datetime.datetime')}
    ts.ToJsonString() {c(': 2020-04-15T15:31:17.554685Z')}
    """

    _TRANSACTION = f"""{h2('Transaction')}
    transaction = db.transaction()

    @firestore.transactional
    def update_in_transaction(trans, ref):
      snapshot = ref.get(transaction=trans)
      trans.update(ref, dict(population = snapshot.get('population') + 1)

    update_in_transaction(transaction, washington_ref)
    """

    _QUERY = f"""{h2('Query')}        {c("CollectionReference.where(...)")}
    stream() {c('→ Generator[DocumentSnapshot]')}
    select({c("field_paths")}) {c('→ Query')}
    where({c("field_path, op_string, value")}) {c('→ Query')}
    """

    _BATCH = f"""{h2('Batch')}
    batch = db.batch()
    batch.update(doc_ref, dict(...))
    batch.set(other_ref, dict(...))
    batch.delete(yet_other_ref)
    batch.commit()
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Firestore / Datastore')}
  https://googleapis.dev/python/firestore/latest/client.html

  {_COLLECTION_REF}

  {_DOCUMENT_REF}

  {_DOCUMENT_SNAPSHOT}

  {_TIMESTAMP}

  {_TRANSACTION}

  {_QUERY}

  {_BATCH}
    """

@syntax
def flask(subject=None):
  return f"""{h1('flask')}
  {h2('cmd args')}
  -h, --host TEXT                 {c('The interface to bind to.')}
  -p, --port INTEGER              {c('The port to bind to.')}
  --cert PATH                     {c('Specify a certificate file to use HTTPS.')}
  --key FILE                      {c('The key file to use when specifying a')}
                                  {c('certificate.')}
  --reload / --no-reload          {c('Enable or disable the reloader. By default')}
                                  {c('the reloader is active if debug is enabled.')}
  --debugger / --no-debugger      {c('Enable or disable the debugger. By default')}
                                  {c('the debugger is active if debug is enabled.')}
  --eager-loading / --lazy-loader
                                  {c('Enable or disable eager loading. By default')}
                                  {c('eager loading is enabled if the reloader is')}
                                  {c('disabled.')}
  --with-threads / --without-threads
                                  {c('Enable or disable multithreading.')}
  --extra-files PATH              {c('Extra files that trigger a reload on change.')}
                                  {c('Multiple paths are separated by ":".')}
  
  {h2('app.run() options')}
    host     {c('the hostname to listen on.')}
    port     {c('the port of the web server.')}
    debug    {c('if given, enable or disable debug mode.')}
    load_dotenv     {c('load the nearest .env and .flaskenv files to set environment variables.')}
    use_reloader    {c('should the server automatically restart the python process if modules were changed?')}
    use_debugger    {c('should the werkzeug debugging system be used?')}
    use_evalex      {c('should the exception evaluation feature be enabled?')}
    extra_files     {c('a list of files the reloader should watch additionally to the modules.')}
    reloader_interval     {c('the interval for the reloader in seconds.')}
    reloader_type         {c('the type of reloader to use.')}
    threaded       {c('should the process handle each request in a separate thread?')}
    processes      {c('if greater than 1 then handle each request in a new process up to this maximum number of concurrent processes.')}
    passthrough_errors    {c('set this to True to disable the error catching.')}
    ssl_context    {c('an SSL context for the connection.')}
  """

@syntax
def fzf(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('fzf')}
  https://www.youtube.com/watch?v=qgG5Jhi_Els
  https://github.com/junegunn/fzf#options
  
  FZF_DEFAULT_OPTS
  
  %bash
  # Aliases:
    alias fzfp="fzf --preview 'bat --style=numbers --color=always {{}}' --preview-window=right:60%"
    alias fzff="find . -type f | fzf"
    alias fzffp="find . -type f | fzfp"
    alias fzfd="find . -type d | fzf"
    alias fzfdp="find . -type d | fzfp"
  
  # Options:
    --height 40%
    --preview 'bat --style=numbers --color=always {{}}' --preview-window=right:60%
    --reverse         # first result from top
    --cycle           # allows scrolling down to top
    -0, --exit-0          # Exit immediately when there's no match
    -f, --filter=STR      # Filter mode. Do not start interactive finder.
    -1, --select-1        # Automatically select the only match
    -q, --query=STR       # Start the finder with the given query
    --ansi                # Enable processing of ANSI color codes
  
  # Usage examples:
    find . -type f | fzf
    find -- * -type f | fzf
  
    fzf -q "foo" < /path/to/file

  # fzf as the selector interface for ripgrep:
    sudo rg -l "$@" 2>/dev/null | fzfp
    
    # OR
    
    INITIAL_QUERY=""
    RG_PREFIX="rg --column --line-number --no-heading --color=always --smart-case "
    FZF_DEFAULT_COMMAND="$RG_PREFIX '$INITIAL_QUERY'" fzf --bind "change:reload:$RG_PREFIX {{q}} || true" --ansi --phony --query "$INITIAL_QUERY" --layout=reverse
  /%bash
  """

def gcloud(subject=None):
    _APP = f"""{h2('app')}
    {h3('create')}
      gcloud app create --project={i('PROJNAME')}

    {h3('deploy')}
      gcloud app deploy --project={i('PROJNAME')}
    """

    _CONFIG = f"""{h2('config')}
    gcloud config list
    gcloud config set core/project {i('PROJNAME')}
    gcloud auth activate-service-account --key-file="/home/gilad/application_default_credentials.json"
    """

    _PROJECTS = f"""{h2('projects')}
    gcloud projects list
    gcloud projects update {i('OLDNAME')} --name={i('NEWNAME')}
    gcloud projects describe {i('PROJ_ID')}
    """

    _AUTH = f"""{h2('auth')}
    gcloud auth list
    gcloud auth application-default login   {c('create new credentials')}
    """

    _SERVICES = f"""{h2('services')}
    gcloud services list
    """

    __ins = i('i17-03-2020')
    _SQL = f"""{h2('SQL')}
    {h3('connect locally')}
      {c(f"URL: console.cloud.google.com/sql/instances/{__ins}")}
      ./cloud_sql_proxy -instances={i('mi-mevi-ma:europe-west1:i17-03-2020')}=tcp:{i('3307')}
      mycli -u root --password={i('PASS')} --host 127.0.0.1 --port {i('3307')}  {c(f'{i("URL")}/users')}

    gcloud sql instances describe {__ins}    {c('also shows private certificate key')}

    {c('databases gcloud sql docs: https://cloud.google.com/sql/docs/mysql/create-manage-databases')}
    gcloud sql databases create [{i('DB_NAME')}] --instance={__ins} [--charset={i('CHARSET')}] [--collation={i('COLL')}]
    gcloud sql databases list --instance={__ins}
    gcloud sql databases delete [{i('DB_NAME')}] --instance={__ins}

    {c('users gcloud sql docs: https://cloud.google.com/sql/docs/mysql/create-manage-users')}
    gcloud sql users set-password root --host=% --instance={__ins} --prompt-for-password
    gcloud sql users create {i('[U_NAME]')} --host={i('[HOST]')} --instance=[{__ins}] --password={i('[PASS]')}
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('gcloud')}
  {_APP}

  {_CONFIG}

  {_PROJECTS}

  {_AUTH}

  {_SERVICES}

  {_SQL}
  """


@syntax
def gimp(subject=None):
    return f"""{h1('gimp')} [OPTION…] [FILE|URI...]
  {h2('cmd')}
    --verbose
    -a, --as-new            {c('Open images as new')}
    -i, --no-interface
    -s, --no-splash
    -f, --no-fonts
    -d, --no-data
    -b, --batch=<command>   {c("Multiple'able")}
    -c, --console-messages  {c('Send msgs to console, not dialog')}
    --pdb-compat-mode=<off|on|warn>
    --debug-handlers        {c('pdb even on non-fatal debugging signals')}
    
  {h2('GUI')}
    Help > Procedure Browser

  {h2('Examples')}
    gimp -s -c -d -f -b '(plug-in-screenshot 0 2 0 0 0 0 0)'
    """


@syntax
def git(subject=None):
    # TODO: git clean -dffx
    #  git diff --cached
    #  git diff-tree
    #  git update-index --assume-unchanged
    #  git ls-files -v | grep "^[[:lower:]]"
    #  git svn dcommit
    #  git read-tree -u -m <commit>
    _BLAME = f"""{h2('blame')}
    git blame <path> --since=3.days
    git blame -L 15,+5
    git blame -t <path>         {c('unix timestamps')}
    """
    _BRANCH = f"""{h2('branch')}
    {h3('Rename branch')}
      git branch -m {i('newname')}
      git push origin :{i('old-name newname')}
      git push origin -u {i('newname')}

    {h3(f"Create new branch off of main")}
      git checkout -b {i('newbranch main')}
      git push origin --set-upstream origin {i('newbranch')}

    {h3(f"Create new branch with only a specific uncommitted file")}
      git commit {i('path/to/file')} -m {i('commitmsg')}
      git checkout -b {i('newbranch')}
      git push --set-upstream origin {i('newbranch')}

    {h3(f"Force delete branch")}
      git branch -D {i('branch_to_delete')}
      git push origin --delete {i('branch_to_delete')}

    git branch [--all] --contains {i('SHA')}
        """

    _CLONE = f"""{h2('clone')}
    {h3(f"Clone branch")}
      git clone --branch {i('somebranch')} https://github.com/{i('owner')}/{i('repo')}.git {i('dir')}
    """

    _CHECKOUT = f"""{h2('checkout')}
    {h3('Checkout specific file')}
      git checkout {i('origin/somebranch')} -- {i('path/to/file')}

    {h3('Checkout specific patch')}
      git checkout -p {i('origin/somebranch')} -- {i('path/to/file')}

    {h3('Checkout specific file from specific commit')}
      git checkout {i('$SHA1')} -- {i('path/to/file')}
    """

    _COMMIT = f"""{h2('Commit')}
    {h3('commit specific file')}
      git commit {i('path/to/file')}
    """

    _COMPARE = f"""{h2('Compare')}
    {h3('Compare 2 commits / branches')}
      {c(f"[..] line:line, [...] commit:commit")}
      https://github.com/Talship/sport-bingo/compare/gilad-staging...main
      https://bitbucket.org/cashdash/reconciliation_engine/branches/compare/recon-engine-v2.4.1%0Drecon-engine-v2.4.0"""

    _CONFIG = f"""{h2('Config')}
    git config --global user.name giladbarnea
    git config --global user.email giladbrn@gmail.com
    
    cd ~/ && printf '.idea\\n.vscode\\n.directory' > .gitignore_global
    git config --global core.excludesfile ~/.gitignore_global

    {h3('credential')}
      {c('man gitcredentials')}
      git config --global credential.helper cache [9000]    {c('seconds')}
      git config --global credential.helper store [--file=<PATH>]   {c('default: ~/.git-credentials or ~/.config/git/credentials')}
      
    {c(f"Support non unicode in git status")}
    git config --global core.precomposeunicode true
    git config --global core.quotePath false

    {h3('diff')}
      context               {c('<n> lines instead of default 3. option: -U')}
      interHunkContext      {c('between diff hunks. option: --inter-hunk-context')}
      suppressBlankEmpty    {c('dont print a space before each empty line. Default false')}
      wordRegex             {c('POSIX Extended to determine what is a "word" when word-by-word diff')}
      algorithm             {c('default/myers | minimal | patience | histogram (like patience with rare common elements)')}
      colorMoved            {c('no/false | default/zebra | plain | blocks | dimmed-zebra')}
      colorMovedWS          {c('dictates how whitespace is ignored when move detection for --color-moved')}
           no                        {c('dont ignore whitespace when performing move detection')}
           ignore-space-at-eol
           ignore-space-change       {c('Instances of one or more whitespace chars are equivalent. Ignores ws at line end.')}
           ignore-all-space          {c('ignores differences even if one line has ws where the other has none')}
           allow-indentation-change  {c('incompatible with the other modes')}
    
    {h3('status')}
      branch
      showStash             {c('default false')}
      showUntrackedFiles    {c('option: -u|--untracked-files')}
            no
            normal          {c('default')}
            all
    """
    _DIFF = f"""{h2('Diff')}
    {h3('Options')}
      -R                          {c('swap inputs')}
      --patience
      --color-moved=zebra {c('or')} dimmed-zebra
      --find-copies-harder
      --inter-hunk-context=100    {c('default 0')}
      --function-context, -W      {c('Show whole surrounding functions of changes')}
      --exit-code                 {c('exit like unix diff; 1 if any differences else 0')}
      --quiet                     {c('no output. implies --exit-code')}
      -a, --textual               {c('Treat all files as text')}

    {h3('Examples')}
      1.0.3: local committed changes
      1.0.4: fetched origin is
      1.0.5: local uncommitted (newest) changes
      git diff == git diff HEAD     | 1.0.3 vs 1.0.5 (local committed vs local uncommitted)
      git diff origin/master        | 1.0.4 vs 1.0.5 (fetched vs local uncommitted)
      git diff origin/master HEAD   | 1.0.4 vs 1.0.3 (fetched vs local committed)
      git diff origin/master upstream/master | fetched vs forked
    
    {h3('Dots')}
      git diff topic..main      {c("same as 'git diff topic main'")}
      git diff topic...main     {c(f"Changes that occurred on {i('main')} since when {i('topic')} was started off it")}
    
    {h3('Summary')}
      --compact-summary           {c("path/to/file (new) |  17 ++")}
      --numstat                   {c("17  0   path/to/file")}
      --summary                   {c("create mode 100644 path/to/file")}
      --name-only
      --name-status               {c('only names and status')}

    {h3('Ignoring whitespace')}
      --ignore-cr-at-eol          {c('Ignore carriage-return at end of line when doing comparison')}
      --ignore-space-at-eol       {c('Ignore changes in whitespace at EOL')}
      --ignore-space-change, -b   {c('Ignore changes in amount of whitespace. Ignores whitespace at line end,')}
                                    {c('and considers all other sequences of one or more whitespace chars to be equivalent')}
      --ignore-all-space, -w      {c('Ignore whitespace when comparing lines')}
                                    {c('Ignores differences even if one line has whitespace where other line has none')}
      --ignore-blank-lines        {c('Ignore changes whose lines are all blank')}
      
      {h4('Example')}
        # git diff --ignore-cr-at-eol --ignore-space-at-eol -b -w --ignore-blank-lines
    
    {h3(f'Excluding / Including files')}
      git diff origin/master -- . ':(exclude)*.csv' ':(exclude)*.ipynb' ':(exclude)*.sql'
      git diff origin/master -- . ':!*.csv' ':!*.ipynb' ':!*.sql'
      git diff origin/master -- ':*.ts' ':!*.d.ts'
    
    {h3('--diff-filter')}
      git diff --diff-filter={i('[(A|C|D|M|R|T|U|X|B)...[*]]')}
      git diff --diff-filter={i('ad')}    {c('lowercase to exclude')}
        A added
        C copied
        D deleted
        M modified
        R renamed
        T file type changed (symlink, submodule...)
        U unmerged
        X unknown
        B pairing broken

    {h3(f'-G')} <regex>
      {c('https://stackoverflow.com/a/35301258/11842164')}
      Look for differences whose patch text contains added/removed lines that match <regex>
      
      · basic regular expression
      · supports grouping () and OR-ing groups with |
      · supports \s, \W, etc
      · does not support lookbehind/ahead
      · supports ^&
      
      --pickaxe-all   {c(f'show all changes in changeset, not just files with change in {i("<regex>")}')}
      
      {h4('Examples')}
        git diff -G "def*" --pickaxe-all
        git diff -w -G '(^[^\*# /])|(^#\w)|(^\s+[^\*#/])'
        
        {c('Only show file differences with at least one line that mentions foo:')}
        git diff -G 'foo'
        
        {c('Show file differences for everything except lines that start with a #:')}
        git diff -G '^[^\# ]+\w+$'
        
        {c('Show files that have differences mentioning FIXME or TODO:')}
        git diff -G '(FIXME)|(TODO)'

    """

    _IGNORE = f"""{h2('ignore')}
    {h3('Ignore everything in dir except specific path')}
      !/node_modules/
      /node_modules/*
      !/node_modules/pyano_local_modules/
    """

    _INIT = f"""{h2('init')}
    cd {{...}}
    git init
    git add .

    {c("Optional: after creating repo")}
    git remote add origin https://github.com/giladbarnea/bashscripts.git
    git push
        """
    _LS = f"""{h2('ls-remote')}
    git ls-remote [--heads] [origin]

    """
    _LOG = f"""{h2('log')}
    git log                     {c('shows commits')}
    git log --stat              {c('also show additions/deletions stats')}
    git log -p [-1]             {c('also show patch diff (can limit patches)')}
    git log --pretty=[oneline | short | medium | full | fuller | reference | email | raw]
    git log --oneline           {c('short SHAs; convenience for --pretty=oneline --abbrev-commit')}
    git log {i("origin/master")}       {c('show where HEAD and origin/master is')}
    git log {i("SHA")}                 {c('of commit / branch')}
    git log {i('my_branch')} --pretty=oneline --graph
    
    {h3('Formatting')}
      {c('Most options can have appended iso-local')}
      date=[relative | local | iso | iso-strict | rfc | short | raw | human | unix | format:... | default]

    {h3('pretty=')}
      online | short | medium | full | fuller | reference | email | raw | format:...
    
    {h3('Limiting')}
      {h4('amount')}
        git log -n {i('1')}            {c('limit')}
        git log --skip={i('n')}        {c('dont show first n')}

      {h4('when')}
        --[since until]={i('date')}

      {h4('who')}
        --author={i('pattern')}

      {h4('filtering')}
        --grep={i('pattern')}          {c('filter log message')}
        --all-match             {c('if mult greps, return only which matched all (not any)')}
        --invert-grep           {c('if mult greps, return only which matched all (not any)')}
        --i                     {c('ignore case')}
        --E                     {c('extended')}
        --[no]-merges           {c('only do [not] return commits with parents > 1')}
        --[branches tags remotes]={i('pattern')}
        --exclude={i('pattern')}

        """

    _MERGE = f"""{h2('merge')} [OPTIONS...] [-m MSG] [COMMIT...]
    {h3('examples')}
      $(master) git merge better_branch     {c('merge better_branch INTO master and commit')}

    {h3('options')}
      --no-commit            {c("merge but don't commit to allow tweaks before commtting")}

      -s <strategy>, --strategy=<strategy>      {c('Can supply more than one (order matters)')}
        ours                  {c("does not even look at what the other tree contains at all")}
        recursive -Xours      {c("conflicting hunks to be auto-resolved cleanly by favoring our version")}

        -X <option>, --strategy-option=<option>


    {h3('Force merge branches')}
      git push -f origin main

      {c(f"keep content of {i('better_branch')}, but record a merge")}
      git merge --strategy=ours main
      git checkout main

      {c(f"fast-forward main up to the me")}
      git merge better_branch

    {h3('Undo merge after conflict')}
      git merge --abort
        """

    _PRUNE = f"""{h2('prune')}
    {c(f"update local copies of remote branches")}
    git fetch --prune origin

    {c(f"remove info about removed remote branches")}
    git remote prune origin

    {c('?')}
    git gc
    """
    _PUSH = f"""{h2('push')}
    -f      {c('force')}
    """
    _PULL = f"""{h2('pull')}
    
    """

    _REBASE = f"""{h2('Rebase')}
    {h3('Rebase branch-to-update onto (on top) branch-with-changes.')}
      {c("This will apply changes from branch-with-changes to branch-to-update")}
      git checkout {i('branch-to-update')}
      git rebase [-i] {i('branch-with-changes')}

      {c("In short:")}
      git checkout {i('branch-to-update')} && git rebase {i('branch-with-changes')} && git push
      """

    _REMOTE = f"""{h2('remote')} [OPTIONS]
    
    {h3('options')}
      -v, --verbose     {c('prints 1 line for fetch and 1 for push sources,')}
                        {c('e.g. "origin https://... (fetch)"')}
      
      add [-t <BRANCH>] [-m <MASTER>] [-f] <NAME> <URL>
      rename <OLD> <NEW>
      remove <NAME>
      prune [-n | --dry-run] <NAME>
      get-url <NAME> [--all]
      set-url <NAME> <NEWURL> [<OLDURL>]
    
    {h3('Change remote origin after forking')}      {c('when origin is theirs')}
      git remote rename origin upstream     {c('origin was ORIG-DEV, set it as upstream')}
      git remote add origin https://github.com/giladbarnea/MY-FORK.git      {c('set my fork as origin')}
      git fetch origin && git push --set-upstream origin main

    {h3('Change remote upstream')}      {c('when origin is mine')}
      git remote add upstream git://github.com/ORIG-DEV/REPO-NAME.git
      git fetch upstream
      git pull upstream main    {c('merges forked local with pulled upstream')}
      
    
    """
    _RESET = f"""{h2('reset')}
    {h3('Usage')}
      git reset [-q | (--patch | -p)] [<tree-ish>] [--] [<pathspec>...]
      git reset [<mode>] [<commit>]

    {h3('Uncommit file')}
      git reset --soft HEAD^    {c('or HEAD~1 instead of HEAD^')}
      git reset HEAD {i('path/to/unwanted_file')}
      {c('# commit again now')}

    {h3(f"Reset to specific commit")}
      git reset --hard {i('$SHA1')}
      git reset --soft HEAD@{{1}}
      git commit -m "Reverting to the state of the project at ..."
      git push

    {h3(f"reset modes")}
      --soft    {c('changes head only, not index nor working tree')}
      --mixed   {c('the default: changes head and index, not working tree')}
      --hard    {c('changes head, index and working tree')}
    """

    _RM = f"""{h2('rm')}
    {h3('Remove file only from online repo')}
      {c(f"{i('cached')} means only in online repo")}
      git rm --cached {i('path/to/file')} && git commit -m "removed file from cache" && git push
    """

    _STASH = f"""{h2('stash')}
    git stash                  {c(f"convenience for {i('git stash push')}")}
    list [git log options]     {c('all stashed entries ever')}
    show [stash]               {c('diff. stash.showStat / stash.showPatch config')}
    drop [stash]               {c(f"removes {i('stash')}")}
    pop [--index] [stash]      {c(f"apply {i('stash')} and remove it")}
    apply [--index] [stash]    {c('load from stash')}
    branch <branchname> [stash]
    clear                      {c('remove all. will be pruned.')}
    create <message>
    store [-m|--mes_sage <message>] <commit>
    push [-p|--patch] [-k|--[no-]keep-index]
         [-u|--include-untracked]    {c("untracked are stashed then 'git clean'ed")} 
         [-a|--all]                  {c("untracked and ignored are stashed then 'git clean'ed")}
         [-m|--message <message>] [-- pathspec...]
    
    stash@{{0}}, stash@{{2.hours.ago}}
    
    {h3('Examples')}
      git stash list --source --name-status --pretty=full
    """

    _STATUS = f"""{h2('status')}
    -s, --short
    -b, --branch    {c('Show the branch and tracking info (even in short-format)')}
    --long          {c('This is the default behavior')}
    --show-stash    {c('Show the number of entries currently stashed away')}
    -v              {c('also show textual changes that are staged to be committed')}
    -u[<mode>], --untracked-files[=<mode>]
      no            {c('Show no untracked files')}
      normal        {c('default when unspecified. Shows untracked files and directories')}
      all           {c('like not specifying mode. shows individual files in untracked directories')}
    --ignored[=<mode>]
      traditional   {c('Shows ignored files and directories')}
      no            {c('Show no ignored files. This is the default.')}
      matching      {c('Shows ignored files and directories matching an ignore pattern')}
    
    {h3('short output')}
      ' '           {c('unmodified')}
      M             {c('modified')}
      A             {c('added')}
      D             {c('deleted')}
      R             {c('renamed')}
      C             {c('copied')}
      U             {c('updated but unmerged')}
      ??            {c('untracked')}
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('git')}

  {_BLAME}
  
  {_BRANCH}

  {_CHECKOUT}

  {_CLONE}

  {_COMMIT}

  {_COMPARE}

  {_CONFIG}

  {_DIFF}

  {_IGNORE}
  
  {_INIT}

  {_LS}

  {_LOG}

  {_MERGE}

  {_PRUNE}
  
  {_PUSH}
  
  {_PULL}

  {_REBASE}
  
  {_REMOTE}

  {_RESET}

  {_RM}

  {_STASH}
  
  {_STATUS}
    """


@syntax
def gitflow(subject=None):
    return f"""{h2('git-flow')}
  git flow init             {c('Initialize git-flow repository')}
  git checkout develop      {c('Check out develop branch')}
  git checkout hotfix       {c('Check out hotfix branch')}
  git checkout release      {c('Check out release branch')}
  git flow feature          {c('List existing feature branches')}
  git flow hotfix           {c('List existing hotfix branches')}
  git flow release          {c('List existing release branches')}
  git flow feature start    {c('Start a new feature: gflfs <name>')}
  git flow hotfix start     {c('Start a new hotfix: gflhs <version>')}
  git flow release start    {c('Start a new release: gflrs <version>')}
  git flow feature finish   {c('Finish feature: gflff <name>')}
  git flow feature publish  {c('Publish feature: gflfp <name>')}
  git flow hotfix finish    {c('Finish hotfix: gflhf <version>')}
  git flow release finish   {c('Finish release: gflrf <version>')}
  """


@syntax
@alias('gh')
def githubcli(subject=None):
    # Keep h3 indented with 6 spaces because lots of info
    _REPO = f"""{h2('repo')} <command> [flags]      {c('Work with GitHub repositories')}
      {h3('clone')}
    
      {h3('create')} <name> [flags]
        -y, --confirm
        -d, --description <string>
        --internal | --private | --public
    
      {h3('fork')}
    
      {h3('view')} [repo] [flags]
        With no args, displays current
      
        -b, --branch BRANCH
        -w, --web       {c('open web page, not in terminal')}
    
      {h3('Examples')}
        gh repo create REPO --public
        gh repo view heroku/python-getting-started
    """
    _RELEASE = f"""{h2('release')} <command> [flags]      {c('Manage GitHub releases')}
      {h4('flags')}
        -R, --repo [HOST/]OWNER/REPO
        
      {h3('create')}      {c('Create a new release')}
      
      {h3('delete')}      {c('Delete a release')}
      
      {h3('download')} [<tag>] [flags]    {c('Download release assets')}
        -D, --dir <PATH='.'>
        download v1.2.3
        download --pattern '*linux-amd64*'
        download -p '*.deb' -p '*.rpm'
      
      {h3('list')}        {c('List releases in a repository')}
      
      {h3('upload')}      {c('Upload assets to a release')}
      
      {h3('view')}        {c('View information about a release')}
      
      {h3('Examples')}
        gh release list -R flameshot-org/flameshot
    """
    _GIST = f"""{h2('gist')} <command> [flags]      {c('Work with Github Gists')}
      {c('A gist can be 5b0e0062eb8e9654adad7bb1d81cc75f or "https://gist.github.com/OWNER/5b0e0062eb8e9654adad7bb1d81cc75f"')}
      
      {h3('clone')} <gist> [<directory>] [-- <git clone flags>...]    {c('Clone a gist locally')}
      
      {h3('create')} [<filename>... | -] [flags]    {c('Create a new gist')}
        {c("'-' as filename means read from stdin")}
        -d, --desc <DESCRIPTION>     {c('A description for this gist')}
        -f, --filename <FILENAME>    {c('Provide a filename to be used when reading from STDIN')}
        -p, --public                 {c('Default is private')}
        -w, --web                    {c('Open browser with created gist')}
        
        {h4('Examples')}
          %bash
          gh gist create hello.py world.py cool.txt        
          gh gist create -      # from stdin
          cat cool.txt | gh gist create
          gh gist create hello.py -d "Some description"
          /%bash
      
      {h3('delete')}      {c('Delete a gist')}
      
      {h3('edit')} {{<gist ID> | <gist URL>}} [flags]    {c('Edit one of your gists')}
        -f, --filename <FILENAME>    {c('A specific file of the gist')}
      
      {h3('list')} [flags]        {c('List your gists')}
        -L, --limit <INT>            {c('Maximum number of gists to fetch (default 10)')}
            --public                 {c('Show only public gists')}
            --secret                 {c('Show only secret gists')}
      
      {h3('view')} {{<gist ID> | <gist URL>}} [flags]    {c('View a gist')}
        -f, --filename <FILENAME>    {c('Display a single file of the gist')}
        -r, --raw                    {c('Do not try and render markdown')}
        -w, --web                    {c('Open gist in browser')}
      

    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('gh')} <command> <subcommand> [flags]
  {c('https://cli.github.com/manual')}
  
  {_GIST}
  
  {h2('issue')}         {c('Manage issues')}
  
  {h2('pr')}            {c('Manage pull requests')}
  
  {_RELEASE}

  {_REPO}
  
  {h2('alias')}         {c('Create command shortcuts')}
  
  {h2('api')}           {c('Make an authenticated GitHub API request')}
  
  {h2('auth')}          {c('Login, logout, and refresh your authentication')}
  
  {h2('completion')}    {c('Generate shell completion scripts')}
  
  {h2('config')}        {c('Manage configuration for gh')}
  
  {h2('help')}          {c('Help about any command ')}
  """

@syntax
def gunicorn(subject=None):
    _APP = f"""{h2('app')}"""
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('gunicorn')}
  {h2('Signals')}
  """
  
  

@syntax('friendly')
def heroku(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('heroku')}
  {h2('install')}
    sudo snap install --classic heroku
    heroku login
  
  {h2('CLI plugins')}
    https://devcenter.heroku.com/articles/heroku-cli#useful-cli-plugins
    heroku-repo         {c('manipulate an app’s Heroku git repository')}
    api                 {c('ad-hoc API requests (such as heroku api GET /account)')}
    heroku-papertrail   {c('Display, tail, and search for logs with Papertrail')}

  {h2('Django')}
    {c('https://www.youtube.com/watch?v=ex7vAsmCk8o')}
    {h3('after startproject PROJ, startapp APP:')}
      %bash
      sudo apt install libpq-dev python3-dev gcc    # also e.g. python3.8-dev
      (env) pip install django-heroku psycopg2-binary psycopg2
      (env) pip freeze > requirements.txt
      echo Procfile > 'web: gunicorn PROJ.wsgi'
      # assuming already pushed to git
      heroku create PROJ-giladbarnea
      heroku config:set PROJ_SECRET_KEY="'$PROJ_SECRET_KEY'"
      git push heroku main
      (env) heroku run python manage.py migrate
      (env) heroku run python manage.py createsuperuser
      /%bash

    heroku run python manage.py shell
    
    {h3('PROJ/settings.py:')} 
      %python
      # top of file:
      import django_heroku
      
      # change SECRET_KEY line:
      SECRET_KEY = os.environ.get('PROJ_SECRET_KEY')
      
      # end of file:
      django_heroku.settings(locals())
      /%python
    
        """


def inspect_(subject=None):
    _FRAME = f"""{h2('frame')}    {c(f"inspect.currentframe(); FrameInfo.frame")}

      f.f_back{c(': frame')}
      f.f_builtins{c(': dict')}
      f.f_code{c(': code')}
      f.f_globals{c(': dict')}
      f.f_lasti{c(': int')}
      f.f_lineno{c(': int')}
      f.f_locals{c(': dict')}
      f.f_trace{c(': ???')}

      """
    _FRAME_INFO = f"""{h2('FrameInfo extends List')}    {c(f"inspect.getouterframes(frame)[n]")}

      finfo.code_context{c(': List[str]')}
      finfo.filename{c(': str')}
      finfo.frame{c(': frame')}
      finfo.function{c(': str')}
      finfo.index{c(': int')}
      finfo.lineno{c(': int')}

    """

    _CODE = f"""{h2('code')}    {c(f"frame.f_code, function.__code__")}
      {c('import gc; gc.get_referrers(code_obj)')}

      co_argcount{c(': int')}
      co_cellvars{c(': Tuple[?]')}
      co_code{c(': bytes')}
      co_consts{c(': Tuple[str] (literal lines of code)')}
      co_filename{c(': str')}
      co_firstlineno{c(': int')}
      co_flags{c(': int')}
      co_freevars{c(': Tuple[?]')}
      co_kwonlyargcount{c(': int')}
      co_lnotab{c(': bytes')}
      co_names{c(': Tuple[str]')}
      co_name{c(': str')}
      co_nlocals{c(': int')}
      co_stacksize{c(': int')}
      co_varnames{c(': Tuple[str] (actual names of local variables)')}

    """
    _FUNCTION = f"""{h2('function')}

      fn.__closure__{c(': Tuple[cell]')}
      fn.__code__{c(': code')}
      fn.__defaults__{c(': Tuple[?]')}
      fn.__globals__
      fn.__kwdefaults__
      fn.__module__{c(': str')}
      fn.__name__{c(': str')}
      fn.__qualname__{c(': str')}
    """

    _FULL_ARG_SPEC = f"""{h2('FullArgSpec')}    {c(f"inspect.getfullargspec(function)")}
      spec.args{c(': List[str]')}
      spec.defaults{c(': Tuple[str]')}
      spec.kwonlyargs{c(': List[???]')}
      spec.kwonlydefaults{c(': ???')}
      spec.varargs{c(': str')}
      spec.varkw{c(': str')}
      spec.annotations{c(': dict')}
    """

    _CLOSURE_VARS = f"""{h2('ClosureVars')}    {c(f"inspect.getclosurevars(function)")}
      ???
    """

    _SIGNATURE = f"""{h2('Signature')}    {c(f"inspect.signature(function, follow_wrapped=True)")}
      sig.parameters {c(': { "param" : Parameter }')}
      sig.return_annotation
      str(str)       {c('(app, *args, **kwargs)')}
    """

    _PARAMETER = f"""{h2('Parameter')}    {c(f"sig.parameters['myparam']")}
      p.annotation {c(': inspect._empty OR ???')}
      p.default
      p.kind {c(': ParameterKind')}
      p.name {c(': str')}

      {h3('ParameterKind')}{c(f"(Enum)")}
        KEYWORD_ONLY
        POSITIONAL_ONLY
        POSITIONAL_OR_KEYWORD
        VAR_KEYWORD
        VAR_POSITIONAL
    """

    _ARGUMENTS = f"""{h2('Arguments')}    {c(f"inspect.getargs(code)")}
      args.args{c(': List[str]    if passed fn.__code__, returns fn sig args')}
      args.varargs
      args.varkw
    """

    _ARG_INFO = f"""{h2('ArgInfo')}    {c(f"inspect.getargvalues(frame)")}
      ???
    """

    _MODULE = f"""{h2('module')}
      m.__name__ {c(": str ('mytool.myman.manuals')")}
      m.__package__ {c(": str ('mytool.myman')")}
      m.__loader__ {c(': SourceFileLoader')}
      m.__spec__ {c(': ModuleSpec')}
      m.__file__ {c(": str (absolute path)")}

      {h3('ModuleSpec')}
        spec.has_location {c(': bool')}
        spec.name {c(': str')}
        spec.origin {c(': str (absolute path)')}
        spec.submodule_search_locations
    """

    _INSPECT = f"""
    {c('https://docs.python.org/3/library/inspect.html')}
    inspect.getcurrentframe() {c('→ frame')}
    inspect.getargs(code{c(': code')}) {c('→ Arguments')}
    inspect.getfile(obj{c(': object')}) {c('→ Arguments')}
    inspect.getargvalues(frame{c(': frame')}) {c('→ ArgInfo')}
    inspect.getcallargs(function{c(': function')}) {c('→ dict')}
    inspect.getclosurevars(function{c(': function')}) {c('→ ClosureVars')}
    inspect.getframeinfo(frame{c(': frame')}, ctx) {c('→ Traceback    # like FrameInfo, no ".frame" attr')}
    inspect.getfullargspec(function{c(': function')}) {c('→ FullArgSpec')}
    inspect.getinnerframes(tb, ctx) {c('→ ???')}
    inspect.getlineno(frame) {c('→ ???')}
    inspect.getmembers(object) {c('→ List[Any]')}
    inspect.getmodulename(path{c(': str')}) {c('→ str')}
    inspect.getouterframes(frame{c(': frame')}, ctx) {c('→ List[FrameInfo]')}
    inspect.signature(function{c(': function')}) {c('→ Signature')}
    inspect.stack() {c('→ List[FrameInfo]')}
    """
    _TRACEBACK = f"""{h1('traceback')}
    {c('https://docs.python.org/3/library/traceback.html')}
    traceback.extract_stack(f=None, limit=None) {c('→ StackSummary')}
    """
    _STACK_SUMMARY = f"""{h2('StackSummary')} {c(': List[FrameSummary]    # traceback.extract_stack()')}
    ss.extract(frame_gen, *, limit=None, lookup_lines=True, capture_locals=False) {c('Create a StackSummary from a traceback or stack object.')}
    ss.format() {c('Format the stack ready for printing')}
    """
    _FRAME_SUMMARY = f"""{h2('FrameSummary')}    {c('# traceback.extract_stack()[0]')}
    fs.filename {c('→ str')}
    fs.line {c('→ str (e.g "stack=tb.extract_stack()")')}
    fs.lineno {c('→ int')}
    fs.locals {c('→ int')}
    fs.name {c('→ str (e.g "run_code")')}
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('inspect')}
    {_INSPECT}
    {_FRAME}
    {_FRAME_INFO}
    {_FUNCTION}
    {_CODE}
    {_FULL_ARG_SPEC}
    {_CLOSURE_VARS}
    {_SIGNATURE}
    {_PARAMETER}
    {_ARGUMENTS}
    {_ARG_INFO}
    {_MODULE}
    
    {_TRACEBACK}
    {_STACK_SUMMARY}
    {_FRAME_SUMMARY}
    """

traceback = inspect_

@syntax
def ipython(subject=None):
    _AUTORELOAD = f"""{h2('%autoreload')}       {c(f'{i("%load_ext")} first')}
    0               Disable
    1               Autoreload marked by {i('%aimport')}
    2               Autoreload all except {i('%aimport')}
    %aimport        List
    %aimport {i('[foo[, bar]]')}  Add to group 1
    %aimport {i('-foo')}   Remove from group 1
    """
    _ALIAS = f"""{h2('%alias')} <alias_name> <cmd>
    {h2('where <i>cmd</i> can include either:')}
      {h3('%l')}: The whole input line
        %ipython
        In [2]: alias bracket echo "Input in brackets: <%l>"
        In [3]: bracket hello world
        /%ipython
        i|Input in brackets: <hello world>|i

      {h3('%s')}: Positional
        %ipython
        In [1]: alias parts echo first %s second %s
        In [2]: %parts A B
        /%ipython
        i|first A second B|i

    {h3('Variable Expansion')}
      %ipython
      In [6]: alias show echo
      In [7]: PATH='A Python string'
      In [8]: show $PATH
      /%ipython
      A Python string
      %ipython
      In [9]: show $$PATH
      /%ipython
      /usr/local/lf9560/bin:/usr/local/intel/compiler70/ia32/bin:...

    {h3('Examples')}
      %ipython 1
      %alias copy echo '%l' | xclip -selection clipboard

    {h3('%unalias')} <alias_name>

  {h2('%alias_magic')}  [-l] [-c] [-p PARAMS] <name> <target>
    {c('for an existing line or cell magic')}
    %alias_magic t timeit
    %t -n1 pass
    """
    _CELLS = f"""{h2('%load_ext ipython_cells')}

    %ipython 1
    %load_file example.py

    {c('example.py')}
    %python 2
    # %% cell1
    print('hello')

    %ipython 2
    %cell_run cell1
    hello

    %ipython
    # from beginning of file to cell1 (inclusive):
    %cell_run ^cell1
    # from cell1 (inclusive) to end of file (inclusive):
    %cell_run cell1$

    %list_cells
    /%ipython
    """
    _CMD = _COMMANDLINE = f"""{h2('ipython')} [subcommand] [options] [-c cmd | -m mod | file] [--] [arg] ...
  ipython --help-all
  ipython {i('CMD')} -h
  ipython locate    {c('/home/gilad/.ipython')}
  ipython profile create    {c("creates '/home/gilad/.ipython/profile_default/ipython_config.py'")}

  {h3('subcommand')}
    profile             create / manage profiles
    history             manage history db

  {h3('options')}
    -i                  interactive after running script (instead of exiting)
    -c {i('CMD')}
    -m {i('MODULE')}

    --debug             set level to logging.DEBUG
    --quiet             set level to logging.CRITICAL
    --autoindent
    --[no-]automagic
    --[no-]pdb          [don't] call on exception
    --[no-]pprint
    --autocall=(0|1|2)  2: lone str → str(); 1: only if args (str 43 works, str doesnt call)

    """

    _CONFIG = f"""{h2('%config')} Class[.trait=value]
    """

    _DEBUG = f"""{h2('%debug')}
  {h4('Without args:')}
    Right after an exception, run '%debug' to ipdb to where exception occurred
  
  {h4('With args:')}
    %ipython 1
    %debug [--breakpoint FILE:LINE] [statement [statement ...]]
    
    ipdb will step through the code
  
  {h4('Notes')}
    Turning %pdb on is like calling %debug right after every exception.
    
    Also, seems to work better as cell magic:
    %ipython
    In [10]: %%debug
        ...: --breakpoint /path/to/file.py:77
        ...: prompt.action('What to do?')
    /%ipython
    
  {h4('See also: %tb')}  
    """

    _DISPLAY = f"""{h2('%display')}
    %python 2
    from IPython.display import Image
    Image(filename='my_screenshot.jpg')
    """

    _EDIT = f"""{h2('%edit')} [options] [args]
    {h3('options')}
      -n <NUM>       {c('open editor at a specified line number')}
      -p             {c('call editor with same data as the previous time')}
      -r             {c('raw input')}
      -x             {c('dont exec immediately upon exit')}

    {h3('arguments')}
      if a filename: will execute its contents with execfile() when you exit
      input history, e.g. “7 ~1/4-6”
      string variable: contents are loaded into the editor.
      name of an object: locate the file where it was defined and open the editor at the point where it is defined
    """

    _HIST = _HISTORY = f"""{h2('%hist[ory]')} [options] <VALUE>
    {h3("VALUE")}
      1                 Prints line 1 of current session
      ~2/5
      ~2/5-~1/4
      1-2
      1:3
    {h3("options")}
      -n                {c('Line numbers')}
      -o                {c('Output')}
      -p                {c('print ">>>" prompts before each input')}
      -f <FILE>         {c('Write to FILE')}
      -g <PATTERN>      {c('Search all history')}
      -u                {c('Unique')}
    """

    _MACRO = f"""{h2('%macro')} [options] <macro_name> <history_args>
    {c('re-execute those lines')}
    {h3('options')}
      -r              use ‘raw’ input
    
    %ipython 1
    %macro my_macro 44-47 49
    
    {h4('See also: %save, %store')}
    """

    _MAGIC = f"""{h2('IPython.core.magic')}
    {c('https://ipython.readthedocs.io/en/stable/config/custommagics.html')}
    %python
    @magics_class
    class MyMagics(Magics):
        @line_magic("st")
        def lmagic(self, line):
            "my line magic"
            print("Full access to the main IPython object:", self.shell)
            print("Variables in the user namespace:", list(self.shell.user_ns.keys()))
            return line
    def load_ipython_extension(ipython): ipython.register_magics(IGitMagics)
    /%python

    {h3('Magics class')}
      {h4('Properties')}
        config{c(': traitlets.config.loader.Config')}
        magics{c(': {"cell":dict, "line": {"st":<bound method...>}}')}
        options_table{c(': dict')}
        shell{c(': TerminalInteractiveShell')}
    """

    _KEYS = f"""{h2('keys')}
    F12             Open editor
    ctrl-a          beginning of line
    ctrl-e          end of line
    ctrl-k          Cut text from cursor to end of line
    ctrl-m          When the user presses return, insert a newline or execute the code
    ctrl-o          insert a newline after the cursor indented appropriately
    ctrl-r          Reverse-search through command history
    ctrl-t          Transpose (i.e., switch) previous two characters
    ctrl-u          Cut text from beginning of line to cursor
    ctrl-y          Yank (i.e. paste) text that was previously cut

    ctrl-b          Go back one char
    alt-b           Go back one word

    ctrl-f          Go forward one char
    alt-f           Go forward one word

    ctrl-d          Delete next character
    alt-d           Delete to end of word

    ctrl-d          Delete next character
    alt-d           Delete to end of word
    """

    _LOAD = f"""{h2('%load')} {i('FILE, URL, MACRO')}
    -r                      Range
    -s                      Symbol
    -n                      Include the user's namespace
    %ipython
    %load {i('myscript.py')}
    %load 7-27
    %load myMacro
    %load {i('http://.../myscript.py')}
    %load -r {i('5-10 myscript.py')}
    %load -r {i('5-10,40: myscript.py')}
    %load -s {i('MyClass,wonder_function myscript.py')}
    %load -n {i('MyClass')}
    %load -n {i('my_module.wonder_function')}
    /%ipython
    """

    _PRINT = f"""{h2('%p<foo>')}
    %pdef           Print call signature.
    %pdoc           Print docstring.
    %pfile          Print the file where object is defined.
    %psource        Print the source code for an object.
    """

    _SEARCH = _PSEARCH = f"""{h2('%psearch')} {c(f'[options]')} {i("PATTERN [OBJECT TYPE]")}
    {c('a*? and ?a* are equivalent to ‘%psearch a*’')}
    -a              Match underscored objs
    -i/-c           Case
    -e/-s           Exclude/search
    -l              List all available object types
    {h3('Examples')}
      %psearch -i a* function
      ?-i a* function
      %psearch -e builtin a*    objects NOT in the builtin space starting in a
      %psearch r*.* string      all strings in modules beginning with r
    
    {h4('See also: %who')}
    """

    _SHELL = _IP = f"""{h2('TerminalInteractiveShell')} {c('IPython.terminal.interactiveshell.TerminalInteractiveShell')}
      %python 2
      from IPython import get_ipython()
      ip = get_ipython()
      
      {h3('Properties')}
        ip.user_ns[_hidden]{c(': dict')}
        ip.user_global_ns{c(': dict')}
        ip.user_module{c(': module')}
        ip.editing_mode{c(': str')}
        ip.editor{c(': str')}
        ... and all configurable props
      
      {h3('Methods')}
        ip.define_macro()
        ip.enable_matplotlib()
        ip.get_local_scope(stack_depth: int) {c('→ dict')}
      
      {h3('Objects')}
        ip.extension_manager
        ip.magics_manager
    """

    _PROFILE = _PROFILER = _PRUN = _LPRUN = f"""{h2('%prun')} [options] <statement>
    {c('Profiler Run')}

    {h3('options')}
      -l {i('<limit>')}      {c('str (fn names), int (lines) or float (% of output). repeatable')}
      -s {i('<key>')}        {c('sort. repeatable.')}
          {c('calls cumulative file module pcalls line name nfl stdname time')}
      -r              {c('Return Stats obj')}
      -T {i('file')}         {c('Write stats to text file')}

    {h3('Examples')}
      stats = %prun -r -l 10 objs[0].get()

  {h2('%lprun')} <args>             {c('Line by line profiler')}
    {h3('install')}
      Requires pip installing line_profiler, and
      c.InteractiveShellApp.extensions = ['line_profiler']

    {h3('basic')}
      %ipython
      %lprun -f func1 [-f func2...] <statement>
      # and/or:
      %lprun -m module <statement>
      /%ipython

    {h3('options')}
      -r          {c('Return Stats obj')}
      -s          {c('Dont show lines that took 0 time')}
      -u <unit>   {c('specify time unit, e.g. 0.001 (default is 1e-06)')}
      -t <path>   {c('dump text results to file')}

    {h3('Examples')}
      %ipython
      prof = %lprun -u 0.001 -s -r -f winactivate.main -f getwid.main -m common winactivate.main('code')
      prof.print_stats()
      /%ipython

  {h4('See also: %run, %time')}
    """

    _REP = _RECALL = f"""{h2('%rep / %recall')}
    %recall (no arguments)      {c('Put editable last output in prompt')}
    %recall 45                  {c('Put hist line 45 in prompt')}
    %recall 1-4                 {c('Combine lines 1-4 to editable cell')}
    %recall var1+var2           {c('If vars exist, evaluated and placed in prompt.')}
                                  {c('Otherwise, history searched for lines with that substring')}
    """

    _RESET = f"""{h2('%reset')}
    -f                        {c('force reset without asking for confirmation.')}
    -s                        {c('Only clears your namespace, leaving history intact.')}

  {h2('%reset_selective')} {c(f"[-f]")} {i("REGEX")}
    %reset_selective -f b[2-3]m     {c("removes 'b2m' and 'b3m' from ns")}
    %reset_selective -f b           {c("removes 'b', 'b1m', 'b2s', 'b4m' from ns")}
    """

    _RERUN = f"""{h2('%rerun')}
    -l {i('<n>')}             {c('Repeat last <n> lines (excluding current)')}
    -g {i('<foo>')}           {c('Repeat most recent lines which contain <foo>')}
    
    {h4('See also: %run')}
    """

    _RUN = f"""{h2('%run')} {c(f"[options]")} {i('-m MOD | FILE')}
    -i {i('file')}                          {c('run the file in IPython’s namespace instead of an empty one.')}
    -e                               {c('ignore sys.exit() calls or SystemExit exceptions')}
    -t [-N{i('<N>')}]                       {c("print timing after run. '-N1' to run once (default)")}
    -d {i('[-b40]')} myscript               {c('with pdb')}
    -d {i('[-b otherfile:20]')} myscript    {c('specify bp in a different file')}
    -p {i('[prof options]')} myscript
    -m module
    
    {h4('See also: %rerun, %prun, %lprun')}
    """

    _ENV = _SET_ENV = f"""{h2('%set_env')}
    {i('%set_env KEY=VAL')}
    {i('%set_env KEY=$VAL')}
    """

    _SAVE = f"""{h2('%save')} [options] filename n1-n2 n3-n4 … n5 .. n6 …
    {c('Save a set of lines or a macro to a given filename.')}
    %history syntax
    {h3('options')}
      -r        raw
      -f        force overwrite
      -a        append to the file
    
    {h4('See also: %store, %macro')}
    """

    _STORE = f"""{h2('%store')}
    {i('%store')}                     Show list
    {i('%store foo bar')}
    {i('%store -d foo')}              Delete
    {i('%store -r foo')}              Refresh (just {i('-r')} to refresh all)
    {i('%store -z')}                  Remove all from storage
    
    {h4('See also: %macro, %save')}
    """

    _PASTE = f"""{h2('%paste')} also %cpaste
    """

    _TB = _TRACEBACK = f"""{h2('%tb')}
    {c('Print last traceback')}
    """

    _TIME = f"""{h2('%time')} Time execution of statement (once)

  {h2('%timeit')} [-n{i("<N>")} -r{i("<R>")} [-t|-c] -q -p{i("<P>")} -o] {i('statement')}
    {c('Repeated time execution of statement')}
    -n5             execute {i('statement')} 5 times per repeat
    -r10            do {i("<N>")} loops, 10 times (default: 7)
    -p5             5 digit precision in result (default: 3)
    -o              return TimeitResult
    -q              quiet, don't print result
    """

    _WHO = f"""{h2(f'%who[s] {i("[type [type ...]]")}')}
    {c('Session variables')}
    %who function str

  {h2('%who_ls')}
    {c('sorted list of all interactive variables.')}
    %who_ls int

  {h2('%whos')}
    {c('Like %who, but gives some extra information about each variable')}
    
  {h4('See also: %psearch')}  
    """

    _MISC = f"""{h2('Miscellaneous')}
  %python
  # dynamic ipython prompt:
  from IPython import start_ipython
  start_ipython(argv=[], user_ns={{**locals(), **globals()}})
  
  # load ipython_utils from python:
  with open('/home/gilad/.ipython/profile_default/startup/ipython_utils.py') as f:
      exec(f.read())
  /%python
  %ipython native
  # or from ipython:
  %run '/home/gilad/.ipython/profile_default/startup/ipython_utils.py'
  %run '/home/gilad/.ipython/profile_default/startup/extensions.ipy'
  %run '/home/gilad/.ipython/profile_default/startup/aliases.ipy'  
  /%ipython

    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('ipython')}
  https://ipython.readthedocs.io/en/stable/interactive/magics.html
  {_ALIAS}

  {_AUTORELOAD}

  {_CELLS}

  {_CMD}

  {_CONFIG}

  {_DEBUG}
  
  {_DISPLAY}

  {_EDIT}

  {_ENV}

  {_HIST}

  {_KEYS}

  {_LOAD}

  {_MACRO}

  {_MAGIC}

  {_MISC}

  {_PASTE}

  {_PRINT}

  {_PROFILE}

  {_REP}

  {_RERUN}

  {_RESET}

  {_RUN}

  {_SAVE}

  {_SEARCH}

  {_SHELL}

  {_STORE}

  {_TB}

  {_TIME}

  {_WHO}
  """


@syntax
def iwatch(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('iwatch')}
  {c('http://manpages.ubuntu.com/manpages/bionic/man1/iwatch.1.html')}
  iwatch -e close_write -t relations.md -c 'python3 -m mytool.to_math relations --out=.md -y --out=.html --css=markdown.css' relations
  """


@syntax
@alias('js')
def javascript(subject=None):
    _CALL = _APPLY = _BIND = f"""{h2('call / apply / bind')}
  %ts
  const obj = {{num: 2 }};
  const increase = function (extra: number, moreExtra: number): number {{
      return (this.num + 1) * extra * moreExtra;
  }};
  // call(thisArg, ...args): sets 'this' via first arg, then ...args
  const increased: number = increase.call(obj, 1, 1);
  console.log(increased); // (2+1) * 1 * 1 == 3
  
  // bind(thisArg): like python's partial. sets 'this' explicitly, returns a func that expects ...args
  const bound: (extra: number, moreExtra: number) => number = increase.bind(obj);
  console.dir(bound);
  console.log(bound(2, 100)); // (2+1) * 2 * 100 == 600
  
  // apply(thisArg, arguments): like 'call', only with [...args]
  const applied: number = increase.apply(obj, [3, 10]);
  console.log(applied); // (2+1) * 3 * 10 == 90
  /%ts
    
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('javascript')}
  {_CALL}
  """

@syntax
def jira(subject=None):
    _JQL=f"""{h2('JQL')}
    assignee = currentUser() AND resolution = Unresolved AND issueLinkType != "Child of"
    issue not in childIssuesOf("ASM-5277")
    """
    
    _REST=f"""{h2('REST v2')}
    %bash
    curl --request GET -s --user $JIRA_USER:$JIRA_PASS --header 'Accept: application/json' --header 'Content-Type: application/json' --data '{"fields":"parent"}' https://jira.allot.com/rest/api/2/issue/$ISSUE
    /%bash
    
    {h3('/issue/<ISSUE>')}
      {h3('/worklog')}
        /worklog?notifyUsers=false
        
        timeSpent
        started {c('h.000+m.000')}
        comment
    """
    
    _CLI=f"""{h2('jira-cli')}  
    {h3('view')}
      jira-cli view --search-jql='assignee=cr-gbarn-herolo\u0040allot.com'
      jira-cli view --search-jql='assignee=cr-gbarn-herolo\u0040allot.com AND parent=ASM-5293 ORDER BY status'
      jira-cli view --search-jql='assignee=cr-gbarn-herolo\u0040allot.com AND resolution = Unresolved AND issueLinkType not in ("Child of","is blocked by") ORDER BY status ASC'
    """
    
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return rf"""{h1('jira')}
  {_JQL}
    
  {_CLI}
  
  {_REST}
        """


@syntax(bash='friendly')
def jupyter(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('jupyter')} [options] [subcommand]
  {h2('subcommands')}
    bundlerextension 
    console 
    kernel 
    kernelspec 
    migrate 
    nbconvert
    nbextension 
    notebook 
    qtconsole 
    run 
    serverextension 
    troubleshoot
    trust
  
  {h2('options')}
    --paths
  
  {h2('jupyterlab')} [cmd] [options]
    %bash
    pip install jupyterlab [xeus-python for debugging]
    
    {h3('cmd')}
      build
      clean
      path  
      paths
      workspace
      workspaces
    
    {h3('Install virtualenv')}
      %bash 2
      . env/bin/activate
      (env) python -m ipykernel install --user --name <CUSTOM_ENV_NAME>
    
    {h3('config')}
      jupyter lab --generate-config
              
    {h3('labextension')}
      https://jupyterlab.readthedocs.io/en/stable/user/extensions.html
      npm search <NAME>
      jupyter labextension list, check
      jupyter labextension install|uninstall|update|enable|disable <NAME>

    {h3('nbextension')}
      https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/nbextensions.html
      pip install jupyter_contrib_nbextensions
      jupyter nbextension list
      jupyter nbextension install|uninstall|enable|disable [--py] <NAME>  {c('from a python package')}

    {h3('options')}
      --allow-root
      --autoreload    {c('on change in py src files or exts')}
      --core-mode
      --dev-mode
      --log-level=[0, 10, 20, 30, 40, 50, 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']   {c('default 30')}
      --port=[8888]
      --notebook-dir=<PATH>
      --app-dir=<PATH>
  """


@syntax
def loguru(subject=None):
    _RECORD = f"""{h2('record dict')}
    elapsed 
    exception 
    extra 
    file 
    function 
    level       
    line        
    message 
    module 
    name        {c('default: __name__')}
    process 
    thread 
    time        {c('datetime (record["time"].timestamp())')}
    """
    _ADD = fr"""{h2('add')}(sink,
    %python
      level="DEBUG",      # file-like object, str, pathlib.Path, callable, coroutine function or logging.Handler
      format=FORMAT,      # '<green>{{time:YYYY-MM-DD HH:mm:ss.SSS}}</green> | <level>{{level: <8}}</level> | {{message}}'
      filter=None,        # lambda rec: rec["extra"]["task"] == "A"
      colorize=None,      # default True if tty
      serialize=False,    # Convert record to JSON
      backtrace=True,     # Use better-exceptions 
      diagnose=True,      # Use variable values
      enqueue=False, 
      catch=True, 
      **kwargs            # Populate extra dict
      ) -> int (handler id to use with remove(hid))
    
      # Example 1: Formatting Traceback
      import stackprinter
      
      def format(record):
          format_ = "{{time}} {{message}}\n"
      
          if record["exception"] is not None:
              record["extra"]["stack"] = stackprinter.format(record["exception"])
              format_ += "{{extra[stack]}}\n"
      
          return format_
      
      logger.add(sys.stderr, format=format)
      
      # Example 2: Syntax Highlighting
      from pygments.formatters import TerminalTrueColorFormatter
      from pygments.lexers import PythonLexer
      from pygments import highlight
      
      def format(record):
          record["message"] = highlight(record["message"], PythonLexer(), TerminalTrueColorFormatter(style="monokai"))
          fmt = '[<level>{{level: <7}}</level>]\n{{message}}\n'
          return fmt
      
      logger.add(sys.stderr, format=format)    
    /%python
    
    """
    _FORMAT = rf"""{h2('Formatting')}
    format can be function that takes a 'record' dict and returns a str e.g
    "{{level}} | {{extra[foo]}} - {{message}}\n{{exception}}"
    
    {h3('Padding')}
      {{level: <8}}
      {{line: >3}}
      {{name: ^15}}
    """
    _PATCH = f"""{h2('patch')}(callable)
    logger.patch(lambda rec: rec["extra"].update(utc=datetime.utcnow())
    logger.patch(lambda rec: rec.update(function=func.__name__))
    
    {h3('Examples')}
      %python
      # Example 1
      import traceback
      
      def add_traceback(record):
          extra = record["extra"]
          if extra.get("with_traceback", False):
              extra["traceback"] = "{linebreak}" + "".join(traceback.format_stack())
          else:
              extra["traceback"] = ""
      
      logger = logger.patch(add_traceback)
      logger.add(sys.stderr, format="{{time}} - {{message}}{{extra[traceback]}}")
      
      logger.info("No traceback")
      logger.bind(with_traceback=True).info("With traceback")
      
      /%python
    """
    _BIND = f"""{h2('bind')}(**extra_kv)
    Sets record['extra'][key] = value.
    """

    _OPT = rf"""{h2('opt')}(*,
    %python
      exception=None,  # bool | tuple | Exception
      record=False,    # Use record dict e.g "Current line is: {{record[line]}}"
      lazy=False,      # .info("If sink <= DEBUG: {{x}}", x=lambda: math.factorial(2**5))
      colors=False,    # .info("We got a <red>BIG</red> problem")
      raw=False,       # Don't format sink e.g .info("No formatting\n")
      capture=True,    # If False, don't populate extra with **kwargs
      depth=0 
      )
      
    # To persist (because resets every call):
    logger.opt = partial(logger.opt, colors=True)
    /%python
    """
    _CONFIGURE = f"""{h2('configure')}(*,
    %python
      handlers=None,     # list[dict] (list of add() params) 
      levels=None,       # list[dict] (list of level() params)
      extra=None,        # dict (bind() params)
      patcher=None,      # callable
      activation=None,   # list[(logger_name : str, state : bool)]
      )
    /%python
    """
    _LEVEL = f"""{h2('level')}(name,
    %python
        no=None,     # int (severity)
        color=None,  # str, markup
        icon=None,   # str
        ) -> Level (namedtuple)
    /%python
    
    {h3('Examples')}
      %python
      logger.level("custom", no=15, color="<blue><bold>", icon="❌")
      logger.log("custom", "Logging...")
      
      # Convenience:
      logger.__class__.custom = partialmethod(logger.__class__.log, "custom")
      logger.custom("Logging...")
      /%python
    """
    _SNIPPETS = f"""{h2('Snippets')}
    %python
    # Monkeypatch all warnings
    import warnings
    from loguru import logger
    
    showwarning_ = warnings.showwarning
    
    def showwarning(message, *args, **kwargs):
        logger.warning(message)
        showwarning_(message, *args, **kwargs)
    
    warnings.showwarning = showwarning
    /%python
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('loguru')}
  {_CONFIGURE}  
  {_RECORD}  
  {_FORMAT}  
  {_ADD}  
  {_BIND}  
  {_PATCH}  
  {_OPT}  
  {_LEVEL}  
  {_SNIPPETS}  
  """



@syntax
@alias('md')
def markdown(subject=None):
    _LINKS = f"""{h2('links')}
    {c('url:')}
    [Foo](www.example.com)

    {c('file:')}
    ![](./relations2.gif)

    {c('inside ref:')}
    #### Total Order
    [total order](#total-order)
    """
    _HR = f"""{h2('horizontal line')}
    ---
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('markdown')}
  {_HR}
  {_LINKS}
  """


@syntax
def matplotlib(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('matplotlib')}
  %python 1
  from matplotlib import pyplot as plt

  {h2('plot(*args), scatter(*args)...')}
    plt.plot(nineties, apple_stocks)
    plt.plot(nineties, ms_stocks)

    {c('same as:')}
    plt.plot(nineties, apple_stocks, {c('["g", "--g", ":g"] for gr  een color and different line styles')}
             nineties, ms_stocks)

  {h2('axis(*args)')}
    {c('Defines the plot borders')}
    plt.axis([x_min, x_max, y_min, y_max])

  {h2('Examples')}
    %python
    lst1 = range(100)
    lst2 = range(120)
    plt.[plot | scatter](lst1, list(map(lambda n:n**0.5, lst1)))
    plt.[plot | scatter](lst2, list(map(lambda n:n**0.4+3, lst2)))
    plt.title('My Plot')
    plt.xlabel('A')
    plt.ylabel('B')
    /%python
    """


@syntax
def micro(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('micro')}
  {h2('Commands')}
    help [defaultkeys | keybindings | commands | options | plugins]
    cd <path>
    open <file>
    replace <search> <value> [-al]  {c("'a' replace all occurrences, 'l' literal searcn not regex")}
    {h4("shell")}
      run <sh-command>           {c('runs in the background')}
      textfilter <sh-command>    {c("applies <sh-command> to selection, e.g. 'textfilter sort -V'")}
    {h4("settings related")}
      bind <key> <action>        {c("modifies bindings.json. see 'help keybindings'")}
      showkey <binding>          {c("e.g. 'showkey Ctrl-c' shows 'Copy'")}
      set <option> <value>       {c("modifies settings.json. see 'help options'")}
      setlocal <option> <value>  {c("does not modify settings.json")}
      show <option>
      reset <option>
    {h4('tab control')}
      vsplit / hsplit <file>     
      tab <file>               {c('open in new tab')}
      tabmove [-+]<n>          {c('moves active tab to slot <n>, or relatively if either -|+')}
      tabswitch <n or tab name>
  
  {h2('bindings.json')}
    help defaultkeys
    %json
    "Alt-foo" : "None",              // disables
    "<Ctrl-x><Ctrl-c>" : "...",     // brackets for sequence
    "Alt-foo" : "command:pwd",
    "Mouse<Left | Middle | Right | Wheel<Up | Down | Left | Right>>": "Mouse<Press | MultiCursor>"
    /%json

  {h2('plugins')}
    {c('https://github.com/micro-editor/plugin-channel')}
    %bash 1
    micro -plugin install PLUGIN
    {h3('filemanager')}
      {c('https://github.com/NicolaiSoeborg/filemanager-plugin')}
      micro -plugin install filemanager
    
    {h3('manipulator')}
      {c('https://github.com/NicolaiSoeborg/manipulator-plugin')}
      Surround selection
      keybindings: "manipulator.lower"
      commands: curly, square, angle, dquote, squote, upper, lower, capital
    
    {h3('bounce')}
      {c('https://github.com/deusnefum/micro-bounce')}
      help bounce
      lua:bounce.smartHome
      lua:bounce.bounce         {c('matching bracket')}
      lua:bounce.keepLoc        {c('save cursor location')}
      lua:bounce.gotoStoredLoc  
    
    {h3('fmt')}
      {c('https://github.com/sum01/fmt-micro')}
      Settings: "fmt-onsave", "fmt|js": "prettier --write"
      commands: fmt [formatter | list]
  
  """


def moment(subject=None):
    return f"""{h1('moment')}
  {h2('moment')} {c('→ Moment')}

    m.date(*args)    {c("Moment ctor args")}
    m.now()
    m.utcnow()
    m.unix({i("timestamp")}, {i("utc=False")})
    m.utc({i("'Feb 15 2020'")})   {c("moment.unix(0, utc=True) == moment.utc('Jan 1 1970')")}

  {h2('Moment(date, formula=None)')}
    {h4('date')} can be datetime or str
    {h4('formula')} can be py "%d-%m-%Y" or js "DD-MM-YYYY"

    M.date  {c(f"→ datetime.datetime(1970, 1, 1, 0, 0, {i('[tzinfo=<UTC>]')})")}
    M.datetime  {c(f"→ datetime.datetime(1970, 1, 1, 0, 0, {i('[tzinfo=<UTC>]')})")}
    M.day, M.minute[s], M.month, M.second[s], M.year {c(f"→ int")}
    M.[add sub]({i('hours=5')}) {c(f"→ Moment (inplace)")}
    M.zero {c(f"→ Moment (inplace)")}
    M.epoch({i("rounding=True")}, {i("miliseconds=False")})  {c(f"→ int")}
    M.format({"'DD/MM/YY'"})  {c(f"→ '01/01/70'")}
    M.now()  {c(f"→ Moment")}
    M.replace({i("year=1980")})  {c(f"→ Moment (inplace)")}
        """

@syntax
def mongo(subject=None):
    _SHELL = f"""{h2('shell')}
    {c('https://docs.mongodb.com/manual/reference/mongo-shell/')}
    Shell vs JS table:
    https://docs.mongodb.com/manual/tutorial/write-scripts-for-the-mongo-shell/#differences-between-interactive-and-scripted-mongo 
    
    """
    _PYMONGO = f"""{h2('PyMongo')}
    {c('https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection')}

    """
    _CURSOR = f"""{h2('Cursor')}
    {c('https://docs.mongodb.com/manual/reference/method/db.collection.find/#std-label-find-cursor-methods')}
    addOption()             forEach()       min()
    allowDiskUse()          hasNext()       noCursorTimeout()
    allowPartialResults()   next()          objsLeftInBatch()
    batchSize()             hint()          pretty()
    close()                 isExhausted()   readConcern()
    isClosed()              itcount()       readPref()
    collation()             limit()         returnKey()
    comment()               map()           showRecordId()
    count()                 max()           size()
    explain()               maxTimeMS()     skip()
    tailable()              sort()          toArray()
    """
    _COLLECTION = f"""{h2('Collection')}
    {c('https://docs.mongodb.com/manual/reference/method/js-collection/')}
    insertOne()
    updateOne()
    findOne()
    """
    _GLOBAL = f"""{h2('Global namespace (Native)')}
    {c('https://docs.mongodb.com/manual/reference/method/#native')}
    cat()			    {c('Returns the contents of the specified file.')}
    cd()			    {c('Changes the current working directory to the specified path.')}
    copyDbpath()	    {c('Copies a local dbPath. For internal use.')}
    getHostName()	    {c('Returns the hostname of the system running the mongo shell.')}
    getMemInfo()	    {c('Returns a document that reports the amount of memory used by the shell.')}
    hostname()		    {c('Returns the hostname of the system running the shell.')}
    isInteractive()	    {c('Returns a boolean indicating whether the mongo shell is running in interactive or script mode.')}
    listFiles()		    {c('Returns an array of documents that give the name and size of each object in the directory.')}
    load()			    {c('Loads and runs a JavaScript file in the shell.')}
    ls()			    {c('Returns a list of the files in the current directory.')}
    md5sumFile()	    {c('The md5 hash of the specified file.')}
    mkdir()			    {c('Creates a directory at the specified path.')}
    pwd()			    {c('Returns the current directory.')}
    quit()			    {c('Exits the current shell session.')}
    removeFile()	    {c('Removes the specified file from the local file system.')}
    resetDbpath()	    {c('Removes a local dbPath. For internal use.')}
    sleep()			    {c('Suspends the mongo shell for a given period of time.')}
    setVerboseShell()	{c('Configures the mongo shell to report operation timing.')}
    version()		    {c('Returns the current version of the mongo shell instance.')}
    _isWindows()	    {c('Returns true if the shell runs on a Windows system; false if a Unix or Linux system.')}
    _rand()			    {c('Returns a random number between 0 and 1.')}
    """
    _DB = f"""{h2('db')}
    {c('https://docs.mongodb.com/manual/reference/method/js-database/')}
    getCollectionInfos(filter, nameOnly, authorizedCollections)
    getCollectionNames(){c(' → str[]')}
    getCollection(name){c(' → Collection')}
    """

    __QUERY = f"""{h3('Query Operators')}
    {c('https://docs.mongodb.com/manual/reference/operator/query/#std-label-query-selectors')}
    {h4('Comparison')}
      $nin, $in     [ 5, ObjectId("507c35dd8fada716c89d0013") ]
      $gt, $gte     new Date('1950-01-01')
      $lt, $lte
      $eq, $ne
      
      AND:
      $gt           new Date('1940-01-01'), $lt: new Date('1960-01-01') (exclusive)
      {{ 
          birth: {{ $gt: new Date('1920-01-01') }},
          death: {{ $exists: false }}
      }}
    
    {h5('Logical')}
      $and, $not, $nor, $or
    
    {h5('Element')}
      $exists, $type
    
    {h5('Evaluation')}
      $expr
      $jsonSchema
      $mod
      $regex        /^N/
      $text
      $where        {c('Javascript expression')}
    
    {h5('Geo')}
      $geoIntersects, $geoWithin, $near, $nearSphere
    
    {h5('Array')}
      $all          [ "ALGOL", "Lisp" ]
      $elemMatch  {{ <query1>, <query2>, ... }}   
          Array with at least 1 matching all queries
          No: $where, $text
      $size         4
    
    {h5('Bitwise')}
      $bitsAllClear, $bitsAllSet, $bitsAnyClear, $bitsAnySet
      """
    __PROJECTION = f"""{h3('Projection Operators')}
    {h3('Projection')}
      $             First item in arr that matches query
      $elemMatch
      $meta         Document's score assigned during $text operation
      $slice
    
    {h3('Misc')}
      $comment, $rand
    """
    __UPDATE = f"""{h3('Update Operators')}
    {c('https://docs.mongodb.com/manual/reference/operator/update/')}
    """
    _OPERATOR = f"""{h2('Operator')}
    {c('https://docs.mongodb.com/manual/reference/operator/')}
    {__QUERY}
    {__PROJECTION}
    {__UPDATE}
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('mongo')}
  {_SHELL}
  {_PYMONGO}
  {_GLOBAL}
  {_DB}
  {_COLLECTION}
  {_CURSOR}
  {_OPERATOR}
  """
@syntax
def mysql(subject=None):
    _CLI = f"""{h2('cli')}
    mysql -uroot
    %mysql
    > CREATE DATABASE db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci (or utf8mb4_general_ci?)
    > USE db_name
    /%mysql

    {h3('Load data')}
      {c('# 1')}
      mysql -uroot -p db_name < ./dump.sql

      {c('# 2')}
      mysql -uroot -p --default-character-set=utf8 db_name
      > SET names 'utf8'
      > SOURCE ./dump.sql

      {c('# 3')}
      mysql -e "source ./dump.sql" db_name

    {h3('mysqldump')}
      mysqldump [OPTIONS] {i('<database>')} [tables...]
      mysqldump {i('<database>')} > {i('<file>.sql')}
      mysqldump --opt {i('<database_to_dump>')} | mysql -h {i('<host>')} -C {i('<database_to_popuplate>')}
      -d, --no-data
      --add-locks=FALSE?
      --default-character-set=utf8mb4
      --extended-insert       {c('Write INSERT statements using multiple-rows with several VALUES lists. Smaller dump file, faster insert')}
      --single-transaction    {c('Creates a consistent snapshot by dumping all tables in a single transaction')}
      --skip-set-charset=TRUE?
      --tables                {c('Overrides option --databases (-B).')}
      --quote-names           {c('backticks')}

      {h4('example')}
      mysqldump \\
        -u admin \\
        -h cd-dev-db.cj5jj1dxmcgk.us-east-1.rds.amazonaws.com \\
        -P 3306 \\
        --add-drop-table=TRUE \\        # {c('Write a DROP TABLE statement before each CREATE TABLE statement.')}
        --column-statistics=FALSE \\
        --create-options=FALSE \\       # {c('default on; part of "--opt"; ""--skip-create-options" to disable')}
        --databases reconciliation_db \\
        --hex-blob=TRUE \\
        --no-create-info=FALSE \\       # {c('When false, create tables')}
        --routines=TRUE \\              # {c('Dump stored routines (functions and procedures).')}
        --set-gtid-purged=OFF \\
        --password="foo" \\
        -r ./reconciliation_db_dump.sql # {c('"r" for Result file')}


      NOTE:
      "--opt" is on by default, and is equivalent to:
      --add-drop-table --add-locks --create-options --quick --extended-insert --lock-tables --set-charset --disable-keys
      Disable with "--skip-opt"

    """
    _ALTER = f"""{h2('ALTER')}
    {c("https://dev.mysql.com/doc/refman/8.0/en/alter-table.html")}
    %mysql
    ALTER TABLE tbl ALTER COLUMN col SET DEFAULT 0;
    ALTER TABLE tbl MODIFY COLUMN col VARCHAR(255) NOT NULL DEFAULT 0;
    ALTER TABLE tbl CHANGE COLUMN col col VARCHAR(255) NOT NULL DEFAULT 0;
    /%mysql"""
    _CONCAT = f"""{h2('CONCAT')}
    %mysql
    SELECT
    CONCAT('TRUNCATE ', TABLE_NAME, ';')
    FROM
        information_schema.TABLES
    WHERE
        TABLE_SCHEMA = 'Employees'
    /%mysql
    """
    _CREATE = f"""{h2('CREATE')}
    %mysql 1
    CREATE USER 'UNAME'@'%' IDENTIFIED BY 'PASS';
    """
    _DATA_TYPES = f"""{h2('Data Types')}
    {c("https://www.w3schools.com/sql/sql_datatypes.asp")}
    from sqlalchemy.dialects.mysql.types import *
    """
    _DATE_TIME = f"""{h2('Date and Time')}
    YEAR(), MONTH(), DAY(),
    DAYOFMONTH(), DAYOFWEEK(), DAYOFYEAR(),
    WEEK(), HOUR(), MINUTE(), SECOND()

    {h3('Conversions')}
      {c("              varchar       varchar       date")}
      %mysql 1
      STR_TO_DATE('02-06-2020', '%d-%m-%Y') # 2020-06-02
      {c("                    date                   int")}
      %mysql 1
      UNIX_TIMESTAMP(CURRENT_DATE())        # 1592956800
      {c("                 int                       varchar?")}
      %mysql 1
      FROM_UNIXTIME(1591106400)             # 2020-06-02 14:00:00
      {c("            varchar                     int")}
      %mysql 1
      TIME_TO_SEC('01:00')                  # 3600
    """
    _DATE = _DATE_TIME
    _TIME = _DATE_TIME
    _DROP = f"""{h2('DROP')}
    %mysql 1
    DROP DATABASE DB;
    """
    _JOIN = f"""{h2('JOIN')}
    {h4('A')}
      {c('Id  Name')}
      0   Gilad
      1   Morki

    {h4('B')}
      {c('Id  Name')}
      0   Gilad
      2   Catta

    {h4('A LEFT JOIN B ON A.Id = B.Id')}
      Id  Name  Id   Name
      0   Gilad 0    Gilad
      1   Morki NULL NULL

    """
    _MISC = f"""{h2('misc')}
    systemctl status mysql.service
    sudo systemctl start mysql

    """
    _SELECT = f"""{h2('SELECT')}
    %mysql
    SELECT user, host FROM mysql.user;
    /%mysql
    """
    _SHOW = f"""{h2('SHOW')}
    %mysql
    SHOW DATABASES;
    /%mysql
    """
    _UNION = f"""{h2('UNION')}
    {h4('A')}
      {c('Id  Name')}
      0   Gilad
      1   Morki

    {h4('B')}
      {c('Id  Name')}
      0   Gilad
      2   Catta

    {h4('A UNION B')}
      {c('Id  Name')}
      0   Gilad
      1   Morki
      2   Catta

    {h4('A UNION ALL B')}
      {c('Id  Name')}
      0   Gilad
      1   Morki
      0   Gilad
      2   Catta
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('mysql')}
  {_CLI}

  {_ALTER}

  {_CONCAT}

  {_CREATE}

  {_DATA_TYPES}

  {_DATE_TIME}

  {_DROP}

  {_JOIN}

  {_MISC}

  {_SELECT}

  {_SHOW}

  {_UNION}
    """


@syntax
def node(subject=None):
    _MODULES = f"""{h2('ES6 Modules with Typescript')}
  {h3('Node')}
    node v12^
    node --experimental-modules --es-module-specifier-resolution=node .
      {c(f'{i("--experimental-modules")} allows for {i("import / export")} syntax.')}
      {c(f'{i("--es-module-specifier-resolution=node")} allows for %s (subdir. not name of module from {i("package.json")})' % i('import from "./giladbarnea"'))}
        {c(i('import from "./giladbarnea/index" is also possible'))}
      {c(f'the dot is dependent on "main" field in root {i("package.json")}')}
    import {{sayHi}} from "./giladbarnea";        {c(f'watch the relative {i("./")}')}
    {i('"type": "module"')} in {i("package.json")}

    {h4('Submodules')}
      Each subfolder's {i("package.json")} has to have a {i('"type": "module"')}
      Make sure {i('modules')} and {i('resolution')} flags are on

  {h3('Typescript')}
    {i('"module": "es2015"')} in {i("tsconfig.json")} (or later)
    {i('"target"')} doesn't seem to matter
    {i('"include"')} field has to have something

      node ./node_modules/.bin/electron .
    
  {h3('import / export syntax')}
    {c('mymodule.ts')}
    const obj = {{ foo: "bar" }};
    
    export default obj            require('mymodule').default     import mymodule from 'mymodule'
    export = obj                  require('mymodule')             import * as mymodule from 'mymodule'
    export {{ foo: "bar" }}         require('mymodule')             import * as mymodule from 'mymodule'
    """
    _ELECTRON = f"""
  {h3('Electron')}
    {h4('main.ts')}
      No {i("export / import")}, only {i("require")}
      {i("webPreferences.experimentalFeatures")} and {i("nodeIntegration")} don't seem to matter

    {h4('tsconfig.json')}
      "module": "es6"
      "outDir": "dist"
      "include": [ "src/**/*" ]
      "types": [ "./node_modules/electron" ]
      {c('Not sure if needed:')}
      "lib": [ "es6", "dom" ]
      "baseUrl": "."
      "paths": {{ "*" : [ "node_modules/*" ] }}
      "moduleResolution": "node"

    {h4('package.json')}
      "start": "electron ./dist/main.js"      {c(f'(or {i("electron .")} if "main" field directs to file)')}
      "dependencies": {{ "electron" : "7.1.0", "typescript" : "^3.7.0-beta" }}
      {c('Not sure if needed:')}
      "type": "module"

    {h4('index.html')}
      {c('Required for import/export:')}
      <script src="./dist/importfile.js" type="module"></script>
      <script src="./dist/exportfile.js" type="module"></script>

    {h4('renderer.ts')}
      if type="module" in index.html:
        use {i("require")} and {i("module.exports = ...")}
        to import: {i('require("./dist/renderer.js")')}
      else:
        vars / objs in this file are globally accessible

    {h4('Debugging')}
      https://github.com/microsoft/vscode-recipes/tree/master/Electron
      In tsconfig.json compilerOptions, "inlineSourceMap": true, and in DevTools add root dir to workspace and restart.
        Optional: "inlineSources" : true (dependent on either inlineSourceMap or sourceMap)

    {h4('Run with node')}
      
    {h4('Misc')}
      To check matching node version, run from project root:
      %bash 1
      grep -nrEHao "https://nodejs\.org/download/release/v[0-9]+\.[0-9]+\.[0-9]+" "./node_modules/electron/dist/electron"
    """

    _PACKAGING = f"""{h2('Packaging')}
  {c('Note: I managed to get it working only with 1 file')}

  {h3('No Webpack')}
    mkdir src && touch src/betterhtmlelement.ts
    echo "export function foo():void {{ }}" >> src/betterhtmlelement.ts
    touch .npmignore && echo "node_modules" >> .npmignore
    {h4('package.json')}
      %json
      "main": "dist/betterhtmlelement.js", (!)
      "module": "dist/betterhtmlelement.js", (?)
      "type": "module", (!)   // also in user's package.json
      "files": ["README.md","dist"] (?)
      /%json

    {h4('tsconfig.json')}
      %json
      "compilerOptions": {{
        "baseUrl": "./",
        "declaration": true,
        "keyofStringsOnly": true,
        "lib": [
            "ES2017",
            "dom"
        ],
        "module": "es6",
        "moduleResolution": "Node",
        "noImplicitAny": false,
        "outDir": "./dist",
        "removeComments": false,
        "sourceMap": true,
        "strict": false,
        "target": "ES2017"
      }},
      "include": [
          "./src"
      ]
      /%json

    {h4('Build')}
      tsc -p .

    {h4('Run (use)')}
      npm install betterhtmlelement@1.1.7

      {c('package.json')}
        "type": "module"

      {c('tsconfig.json')}
        "target": "ES2017",
        "moduleResolution": "Node",
        "outDir": "./dist/"

      tsc -p .
      node --experimental-modules --es-module-specifier-resolution=node dist/index.js

  {h3('With Webpack')} (not sure if works?)
    yarn add webpack webpack-cli --dev
    mkdir src && touch src/betterhtmlelement.ts && echo "console.log('hello world')" >> src/betterhtmlelement.ts
    {h4('package.json')}
      %json
      "main": "dist/betterhtmlelement.js", (!)
      "module": "dist/betterhtmlelement.js", (?)
      "type": "module", (!)
      "files": ["README.md","dist"], (?)
      "scripts": {{
          "build" : "webpack --mode production",
          "build:dev": "webpack --mode development"
      }},
      "devDependencies": {{
        "ts-loader": "^7.0.5",
        "typescript": "^3.9.5",
        "webpack": "^4.43.0",
        "webpack-cli": "^3.3.12"
      }}
      /%json
    {h4('tsconfig.json')}
      {c('try no webpack tsconfig if this doesnt work')}

      %json
      "compilerOptions": {{
        "declaration": true,
        "outDir": "./dist/",
        "allowJs": true, (!)
        "sourceMap": true,
        "allowSyntheticDefaultImports": true (needed?)
      }},
      "include": [ "src/**/*" ]
      /%json
    {h4('webpack.config.js')} {c('at root')}
      {c('try Piano.js webpack.config.js if doesnt work')}
      {c('https://github.com/tambien/Piano/blob/master/webpack.config.js')}

      %js
      const path = require('path');
      module.exports = {{
          entry: './src/index.ts',
          devtool: 'inline-source-map',
          module: {{
              rules: [
                  {{
                      test: /\.tsx?$/,
                      use: 'ts-loader',
                      exclude: /node_modules/,
                  }},
              ],
          }},
          resolve: {{
              extensions: [ '.tsx', '.ts', '.js' ],
          }},
          output: {{
              filename: 'index.js',
              path: path.resolve(__dirname, 'dist'),
          }},
      }};
      /%js
    {h4('build and run')}
      yarn build:dev
      node dist/index.js
    """
    _NPM = f"""{h2('npm')}
  {h3('list')}
    npm list --depth=0
  
  {h3('view / info / show')} <pkg>[@version]    {c('shows lots of info. version defaults to "latest"')}
    """

    _NVM = f"""{h2('nvm')}
  {h3('install')} [-s] <version>
    --lts[=<LTS NAME>]
    --latest-npm
  
  {h3('uninstall')} <version>
    --lts[=<LTS NAME>]

  {h3('ls')}
    ls [<version substring>]
    ls-remote [--lts[=<LTS NAME>]] [<version substring>]
  
  {h3('misc')}
    nvm [which] current
    nvm install-latest-npm
    nvm deactivate
    
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('node')}
  {_MODULES}

  {_ELECTRON}

  {_PACKAGING}

  {_NPM}
  
  {_NVM}
    """


def numbers(subject=None):
    return f"""{h1('Numbers')}
  Real ℝ = Rational ℚ + Irrational 𝕁
  Rational ℚ > Integers ℤ > Natural ℕ

  {h2('Natural ℕ')} or "Whole"?
    0?, 1, 2, 3, ...

  {h2('Integers ℤ')}
    A number that can be written without a fractional component.

    {h4('Examples')}
      21, 4, 0, −2048

  {h2('Rational ℚ')}
    Can be expressed as a fraction {i('p/q')} of two integers; a numerator {i('p')} and a non-zero denominator {i('q')}.

  {h2('Irrational 𝕁')}
    All the real numbers which are not rational numbers.

    {h4('Examples')}
      {i('√2')}, {i('π')}, Euler's {i('e')}, golden ratio {i('φ')}.

    {c('Trivia: all square roots of natural numbers, other than of perfect squares, are irrational.')}

  {h2('Real ℝ')}
    Represent a distance along a line.
    Include all rational numbers and irrational numbers.

  {h2('Imaginary 𝕀')}
    An imaginary number {i('bi')} can be added to a real number {i('a')} to form a complex number of the form {i('a + bi')}.

    The square of an imaginary number {i('bi')} is {i('−b^2')}.
    Zero is considered to be both real and imaginary.

    {h4('Examples')}
      {i('5i')} is an imaginary number, and its square is {i('−25')}.

  {h2('Complex ℂ')}
    Can be expressed in the form {i('a + bi')}, where {i('a')} and {i('b')} are real numbers,
    and {i('i')} is a solution of the equation {i('x^2 = −1.')}

    Because no real number satisfies {i('x^2 = −1')}, {b(i('i'))} is called an {b('imaginary')} number.
    For the complex number {i('a + bi')}, {b(i('a'))} is called the {b('real')} part, and {b(i('b'))} is called the {b('imaginary')} part.

    {h4('Examples')}
      (x+1)^2 = -9
  """


@syntax
def pandas(subject=None):
    _CONSTRUCTING = f"""
    {h3('Constructing')}
      %python 2
      data = {{'Col A': [10,20], 'Col B': [500,5000]}}
      pd.DataFrame(data)

         Col A  Col B
      0     10    500
      1     20   5000

      %python 1
      pd.DataFrame.from_dict(data, orient='index')

               0     1
      Col A   10    20
      Col B  500  5000


    """
    _DATAFRAME = _DF = _CONSTRUCTING
    _VIEWING = f"""
    {h3('Viewing')}
      df.head()
      df.tail(3)
      df.index
      df.columns            {c("Index(['id', 'gateway_name'], dtype='object')")}
      df.describe()         {c("A few samples")}
      df.info()             {c("quick stats")}
    """
    _SORTING = f"""
    {h3('Sorting')}
      df.sort_index(axis=1, ascending=False)
      df.sort_values(by='B')
    """
    _SELECTING = f"""
    {h3('Selecting')}
      {h4('DataFrame')}
        df[:1]                          {c("First 1 rows x all columns")}
        df.loc[:1]                      {c("First 2 rows x all columns")}
        df.iloc[:1]                     {c("First 1 row x all columns")}
        df.loc[:1, ['Name']]            {c("First 2 rows x 'Name' column")}
        df.iloc[:1, :2]                 {c("First 1 rows x 'Name', 'Grade' columns")}

      {h4('Series')}
        df.Name | df['Name']            {c('A series of Names column')}
        df[:2].Name                     {c('A series of Names column (only first 2)')}
        df.loc[0]                       {c('First object')}
        df.iloc[0]                      {c('First object')}
        df.loc[0, ['Name']]             {c('First object limited to only Name column')}
        df.iloc[0, :1]                  {c('First object limited to only Name column')}
        df.iloc[0, :2]                  {c('First object limited to Name and Grade columns')}
        df.loc[:1, 'Name']              {c('A series of Names column (only first 2)')}
        df.iloc[:2, 0]                  {c('A series of Names column (only first 2)')}

      {h4('Scalars / primitives')}
        df.Name[0] → str                 {c("'Gilad'")}
        df.loc[0].Name → str             {c("'Gilad'")}
        df.loc[0, 'Name'] → str          {c("'Gilad'")}
        df.iloc[0, 0] → str              {c("'Gilad'")}
        df.iloc[0, :1].Name → str        {c("'Gilad'")}
        df.columns[0] → str              {c("'Name'")}
        df.columns.format() → List[str]  {c("['Name', 'Grade', 'Courses']")}
    """
    _MANIPULATING = f"""
    {h3('Manipulating')}
      {h2('DataFrame')}
        df.agg(sum) → Series                 {c('df.agg((Series) → scalar))')}
        df.agg([sum, min]) → DataFrame
        df.agg({{'Grades': sum}}) → Series     {c('returns Series regardless of dict len')}
        df.agg(func, axis=[0|'index' or 1|'columns']) → Series   {c('0|index: vertical, 1|columns: horizontal (only single func)')}

        df.apply(sum, axis=0) → Series
        df.apply([sum, min], axis=0) → DataFrame
        {c('Compare with applymap, aggregate, transform')}

      {h2('Series')}
        series.agg(sum) → scalar             {c('agg((Series) → scalar)')}
        series.agg([sum, min]) → Series

        series.apply(lambda x:x**2) → Series   {c('apply((scalar) → scalar)')}
        series.apply(lambda x,y:x**y, y=100) → Series
        series.apply([lambda x:x**2]) → DataFrame
    """
    _FILTERING = f"""
    {h3('Filtering')}
      df[df.Courses=='Math']
      df[(df.Name == 'Gilad') & (df.Courses == 'Math')]
      df.query('Name == "Gilad" and Courses == "Math"')
      df.query('Grade in [92,100]')
      df.query('Grade == [92,100]')
      df[df.Name.isin(['Gilad'])]
      gw[gw.ID.str.startswith('2')]
    """

    _GROUPBY = f"""
    {h3('Group By')}
      df.groupby(by=['Name','Courses']).mean() / .max() / .min()
                                       .describe()
                                       .sum()
                                       .count()
                                       .first() / .last()
                                       .head() / .tail()
                                       .obj
    """
    _WHERE = f"""
    {h3('Where')}
      df.where(df.Courses=='Math')
    """
    _MISC = f"""
    {h3('Misc')}
      df.dropna(how='any')              {c('Drop missing data')}
      df.fillna(value=5)                {c('Fill missing data')}
      df.fillna(df.Courses)
      pd.isna(df1)                      {c('Map values to bool if nan')}
      df.drop_duplicates(inplace=True, keep=False)
      df.columns = df.columns.map(str.lower)    {c('Convert columns to lowercase')}

      df['avg'] = df.mean(axis=1)       {c('Calculate average across columns (horizontally)')}

      [df|series].mask(cond, other, inplace=False)      {c('Replace values where cond is True')}
        cond: (original_frame) → boolean NDFrame (same len)
        cond: boolean NDFrame (same len)
        other: (original_frame) → Union[NDFrame, scalar]
        other: NDFrame
        other: scalar

      [df|series].replace(Union[str, int, regex], Union[str, int, regex], inplace=False)    {c('if lists, then same len')}
      [df|series].replace(dict)
      [df|series].replace([None], float('nan'), inplace=True)   {c('replace all None with NaN')}
    """
    _SQL = f"""
    {h3('SQL')}
      {h4('Reading')}
        pd.read_sql('select * from db.table', con)
        pd.read_sql_table('table', con, schema='db')

      {h4('Writing')}
        df.to_sql(name, con, schema=None, if_exists='fail')   {c('writes to db')}

      {h4('Operating')}
        {c('LEFT JOIN')}
        joined = pd.merge(left, right,
                            how='left',
                            on=left['left_id'])
                            .drop(columns='key_0')    {c("Works even if right's ON is a different column (?)")}

        {c("Doesn't work?:")}
        joined = left.merge(right, how='left', on='Name')
                        left_on='Name1', right_on='Name3'
        joined = pd.merge(left, right, how='left', on='Name')

        {c("UNION")}
        union = pd.concat([tmp, tmp2], ignore_index=True)

        {c("2 DataFrames side-by-side:")}
        pd.concat([tmp, tmp2], axis=1)

    """
    _JSON = f"""
    {h3(f'read_json({c("**kwargs")})')}
      {h4('orient')}{c(': str = None')}
        |   value   |               json content structure
        |- - - - -  | - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        | 'split'   | {{index → [index], columns → [columns], data → [values]}}
        | 'records' | [{{column → value}}, ... , {{column → value}}]
        | 'index'   | {{index → {{column → value}}}}
        | 'columns' | {{column → {{index → value}}}}
        | 'values'  | just the values array. depends on the {i('typ')} kwarg.

      {h4('typ')}{c(': str = "frame"')}
        |   value   |               allowed orients
        |- - - - -  | - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        | 'series'  | 'split', 'records', 'index' (default).
        |           |  if 'index', series index must be unique
        | 'frame'   | 'split', 'records', 'index', 'values', 'table', 'columns' (default).
        |           | if 'index' or 'columns', DF index must be unique.
        |           | if 'index', 'columns' or 'records', DF columns must be unique.
    """
    _CASTING = f"""
    {h3('Casting')}
      df.to_[csv | dict | excel | json | string | timestamp]
    """
    __MOCK = f"""
{c('.')}       Name  Grade  Courses
    0  Gilad     90     Math
    1  Morki    100     Math
    2  Gilad     80  Drawing
    3  Morki     80  Drawing
    """
    if subject:
        frame = inspect.currentframe()
        return '\n' + __MOCK + frame.f_locals[subject]
    else:
        return f"""{h1('pandas')}
{__MOCK}
{_CONSTRUCTING}
{_VIEWING}
{_SORTING}
{_SELECTING}
{_MANIPULATING}
{_FILTERING}
{_GROUPBY}
{_WHERE}
{_MISC}
{_SQL}
{_JSON}
{_CASTING}
"""


@syntax
def pdb(subject=None):
    _ARGS = f"""{h2('a')}[rgs]
    Argument list of current function
    """

    _BREAK = f"""{h2('b')}[reak]
    List all breaks
    {h3('b ' + i('[filename:]lineno | function [, condition]'))}
      {i('break 15')}
      {i('break myfile:15')}
      {i('break add_numbers')}
    """

    _WHERE = f"""{h2('w[here] | bt')}
    Stack trace
    """

    _ALIAS = f"""{h2('alias / unalias')}
    {i('define:')}
    alias pi for k in %1.__dict__.keys(): print("%1.",k,"=",%1.__dict__[k])
    {i('usage:')}
    pi classInstance
    {i('nesting:')}
    alias ps pi self
    """

    _CONFIG = f"""{h2('Configuration')}
    Lowest priority first:
    setup.cfg or .ipdb in project working dir
    .ipdb in ~/
    IPDB_CONFIG env var
    """
    _CONTINUE = f"""{h2('c')}[ont[inue]]
    Stop at next bp
    """

    _CLEAR = f"""{h2('cl')}[ear]
    Clear all breakpoints (confirm first)
    {h3('clear ' + i('bpnumber [bpnumber...]'))}
      Space separated numbers
    {h3('clear ' + i('filename:lineno'))}
    Clearing cannot be undone, whereas disabling can
    """

    _DOWN = f"""{h2('d')}[own] {i('[count]')}
    Move down (newer) the stack trace (default 1)
    """

    _DISABLE = f"""{h2('disable / enable')} {i('bpnumber [bpnumber...]')}
    Can be re-enabled / re-disabled
    """
    _ENABLE = _DISABLE
    _DISPLAY = f"""{h2('display')}
        List all display expressions for the current frame
        {h3('display ' + i('expression'))}
          Display value of {i('expression')} each stop if it changed
    """
    _QUIT = f"""{h2('q')}[uit] {c('or')} exit
    Aborts
    """
    _EXIT = _QUIT
    _INTERACT = f"""{h2('interact')}
    Starts an interactive console
    """
    _JUMP = f"""{h2('j')}[ump] {i('[lineno]')}
    {c('Only in bottom-most frame')}
    Jump back / forth to {i('lineno')} (i.e re-execute or skip code).
    """
    _LIST = f"""{h2('l')}[ist]
    Continue "browsing" through the lines
    {h3('list ' + i('.'))}
      Show current += 5
    {h3('list ' + i('num'))}
      Show lineno {i('num')} += 5
    {h3('list ' + i('first,last'))}
      If {i('last')} > {i('first')}, show {i('first')} to {i('last')}.
      Else, show {i('first')} + {i('last')} lines.
    """
    _LONGLIST = f"""{h2('ll | longlist')}
    Show whole code for current function or frame
    """
    _LL = _LONGLIST
    _NEXT = f"""{h2('n')}[ext]
    Continue until next line or until return
    """
    _PRINT = f"""{h2('p')} {i('expression')}
    Print value of {i('expression')}
    """
    _PRETTYPRINT = f"""{h2('pp')} {i('expression')}
    Pretty-print value of {i('expression')}
    """
    _PP = _PRETTYPRINT
    _RETURN = f"""{h2('r')}[eturn]
    Continue until return
    """
    _RUN = f"""{h2('run | restart')}
    """
    _RESTART = _RUN
    _RETVAL = f"""{h2('rv | retval')}
    Print return value
    """
    _RV = _RETVAL
    _SOURCE = f"""{h2('source')} {i('expression')}
    {c(i('obj ') + 'is either module, class, method, function, traceback, frame, or code object')}
    Try to display source code for {i('obj')}.
    """
    _STEP = f"""{h2('s')}[tep]
    Into
    """
    _UP = f"""{h2('u')}[p] {i('steps')}
    Move up (older) the stack trace (default 1)
    """
    _TBREAK = f"""{h2('tbreak')}
    Same as b[reak] but cleared after hit
    """
    _CMD = f"""{h2('command line')}
  {c('Automatically enter pm if exists abnormally')}
  %bash
  python -m pdb script.py
  python -m pdb -m module
  python -m pdb -c continue script.py   # lets the program run normally
  /%bash
    """

    _MISC = f"""{h2('misc')}
    %python
    def execfile(fname, glob, loc=None, compiler=None):
        loc = loc if (loc is not None) else glob
        with open(fname, 'rb') as f:
            compiler = compiler or compile
            exec(compiler(f.read(), fname, 'exec'), glob, loc)
    /%python
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('pdb')}
  {_ARGS}
  {_BREAK}
  {_WHERE}
  {_ALIAS}
  {_CONFIG}
  {_CONTINUE}
  {_CLEAR}
  {_DOWN}
  {_DISABLE}
  {_DISPLAY}
  {_QUIT}
  {_INTERACT}
  {_JUMP}
  {_LIST}
  {_LONGLIST}
  {_NEXT}
  {_PRINT}
  {_PRETTYPRINT}
  {_RETURN}
  {_RUN}
  {_RETVAL}
  {_SOURCE}
  {_STEP}
  {_UP}
  {_TBREAK}
  {_CMD}
  {_MISC}
  """


@syntax('friendly')
def pdbpp(subject=None):
    _COMMANDS = f"""{h2('commands')}  
    sticky [START END]        {c('Inclusive')}
    interact                  {c('Starts and interactive interpreter')}
    track EXPRESSION          {c('Graph. requires pypy.')}
    [un]display EXPRESSION    {c('Evaluated each step, printed on change.')}
    edit EXPRESSION           {c('Open editor to the right.')}
    hf_...
       hf_list                {c('Prints a list of hidden frames')}
       hf_unhide              {c("Enables up and down through hidden frames")}
       hf_hide                {c('Disables')}
    """

    _CONFIG = f"""{h2('config')}  
    {c('.pdbrc.py in home dir')}
    %python
    import pdb
    class Config(pdb.DefaultConfig):
        sticky_by_default = True
        enable_hidden_frames = True
        use_pygments = None
        
        # e.g "pygments.formatters.TerminalTrueColorFormatter"
        # default to detect if $TERM contains "256color"
        pygments_formatter_class = None
        
        # e.g dict(style='default', bg=self.config.bg, colorscheme=self.config.colorscheme)
        pygments_formatter_kwargs = {{}}
        
        def setup(self, pdb): ...  # called on Pdb init
    /%python
    """

    _INLINE = f"""{h2('inline use')}
    {h3('programmatically')}
      pdb.xpm()               {c('Inside except, start from where exc happened')}
    
    {h3('decorators')}  
      %python
      @break_on_setattr('bar')
      class Foo(object):
          ...
      f = Foo()
      f.bar = 42  # breaks
      
      # Alternatively:
      def predicate(inst, attrval) -> bool:
          ...
      break_on_setattr('bar', condition=predicate)(Foo)
      /%python
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('pdbpp')}
  {_COMMANDS}
  {_CONFIG}
  {_INLINE}
  """


@syntax
def pudb(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('pudb')}

  """


def pip(subject=None):
    _INSTALL = f"""{h2('install')}
    {h3('options')}
      --no-deps
      --upgrade-strategy "only-if-needed"|"eager"   {c('default "only-if-needed"')}
      --force-reinstall                             {c('Reinstall all packages even if they are already up-to-date.')}
      -I, --ignore-installed                        {c('Overwrite installed')}
      --exists-action <action>                      {c('action when a path already exists: (s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort.')}

    {h3('From VCS')}
      {c('watch the slashes etc when pasting')}
      {c('bzr+http, bzr+https, bzr+ssh, bzr+sftp, bzr+ftp, bzr+lp, bzr+file, git+http, git+https, git+ssh, git+git,')}
      {c('git+file, hg+file, hg+http, hg+https, hg+ssh, hg+static-http, svn+ssh, svn+http, svn+https, svn+svn, svn+file')}
      pip install -e "git+ssh://git@bitbucket.org/cashdash/reconciliation_services.git@recon-services-v2.4.0#egg=reconciliation_services"
      pip install -e "git+ssh://git@github.com/giladbarnea/more_termcolor.git#egg=more_termcolor"

    {h3('From local dir')}
      {c('sudo chmod 777 target dir, and make sure no prompts in target setup.py')}
      (env) pip install --log ./PIP.log -v -e /home/gilad/Code/IGit

    --src {i('<dir>')}     {c('virenv default is "<venv path>/src", global default is "<current dir>/src"')}
    --root {i('<dir>')}    {c('Install everything relative to this alternate root directory')}
    --user                 {c('install to user dir (~/.local/ or %APPDATA%/Python)')}
    -t, --target {i('<dir>')}
    -e, --editable {i('<path/url>')}    {c('implies setuptool "develop" mode')}

    pip3 freeze | grep -v "^-e" | xargs pip3 uninstall -y    {c('uninstall all packages')}

    pip install ./pip-21.1.1.tar.gz --user --ignore-requires-python --no-build-isolation --no-clean --retries 1 --timeout 10 --disable-pip-version-check
    """

    _SEARCH = f"""{h2('search')}"""
    _DOWNLOAD = f"""{h2('download')} [options] [pkg]
    {h3('pkg')}
      <requirement specifier> [package-index-options] ...
      -r <requirements file> [package-index-options] ...
      <vcs project url> / <local project path> / <archive url/path> ...
    
    {h3('options')}
      --platform <platform>      {c('Default to running platform. Mulitplable.')}
                                   {c('macosx-10_10_x86_64, linux_x86_64, any, manylinux1_x86_64')}
      --python-version <ver>     {c('3, 3.7, 3.7.0, 37')}
      --implementation <impl>    {c('pp | jy | cp | ip | py')}
      --abi <abi>
    
      --no-binary=<FMT>          {c("Don't use specified binary. Can be multiple.")}
      --only-binary=<FMT>        {c("Don't use source pkgs. Can be multiple.")}
                                   {c(":all: | :none: | pkg names with commas")}
      --no-deps                  {c("Don't install deps")}
      --prefer-binary            {c("Older bin pkgs over newer source pkgs")}
      
      -i, --index-url <url>      {c("Default https://pypi.org/simple. Must PEP-503 compliant.")}
      --extra-index-url <url>
      --no-index                 {c("Only look at --find-links URLs")}
      -f, --find-links <url>     {c('VCS not supported')}
          URL / path to .html: parse archive links (.tar.gz, .whl) 
          Local path or file:// to dir: look for archives in dir
      
      --global-options <options>   {c("to setup.py")}
      --src <dir>                {c("defaults to <venv/src> or <pwd/src>")}
      -d, --dest <dir>           {c("Download into <dir>")}
      
      --no-build-isolation       {c("PEP-518 deps must already be installed")}
      --use-pep517, --no-use-pep517    {c("--no-use-pep517 to force legacy behavior")}
      --ignore-requires-python
      
      --no-clean                 {c("Don't clean build dirs")}
      
      --proxy <proxy>            {c('[user:passwd@]proxy.server:port')}
      --retries <N=5>
      --isolated                 {c('from env vars')}
      --timeout <SECS=15>
      --exists-action <action>   {c('When path exists: (s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort')}
      --no-cache-dir             {c('Disable cache')}
      --disable-pip-version-check
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('pip')}
  {_INSTALL}
  {_SEARCH}
  {_DOWNLOAD}
    """

@alias('poe')
@syntax
# @rich
def poetry(subject=None):  
  _NEW = f"""{h2('new project')}
    %bash
    # install:
    pip38 install --user poetry
  
    # new project (BEFORE mkdir and git init)
    cd ~/dev
    poetry new myproject    
    # creates:
    # ~/dev/myproject/
    #                /myproject/
    #                /tests/
    #                /README.rst
    #                /pyproject.toml
    cd myproject && git init && gh repo create
    /%bash
  """
  _ADD = f"""{h2('add')} [-D] [-E <...>] [--optional] [--python <...>] [--platform <...>] [--source <...>] [--allow-prereleases] [--dry-run] [--lock] <NAME>...
  """
  
  _BUILD = f"""{h2('build')} [-f wheel|sdist]
    %bash
    poetry build
    # creates a ./dist/ dir with PROJECT-0.1.0.tar.gz and -py3-none-any.whl
    # that can be pip install --user ./PROJECT-...whl
    # or pip install -e setup.py extracted from the .tar.gz
    /%bash
  """
  
  _ENV = f"""{h2('env')}
    %bash
    poetry env info [-p]
    poetry env list [--full-path]
    poetry env remove <python>
    poetry env use <python>
    
    # Examples
    poetry env use python3.8                [c]Creates a venv[/c]
    . "$(poetry env info -p)"/bin/activate     [c]activates venv[/c]
    /%bash
  """
  
  _INSTALL = f"""{h2('install')} [--no-dev] [--no-root] [--dry-run] [--remove-untracked] [-E <...>]
    Reads poetry.lock file from current dir, installs libs and deps from that file.
    Uses pyproject.toml if poetry.lock doesn't exist.
    --no-dev              {c("don't install dev dependencies")}
    --no-root             {c("don't install current package")}
    --remove-untracked    {c("remove pkgs not in lock file")}
  """

  _PUBLISH = f"""{h2('publish')}
    %bash
    poetry publish -u giladbarnea --build --dry-run
    /%bash
  """
  _UPDATE = f"""{h2('update')} [--no-dev] [--dry-run] [--lock] [package...]
  Resolve latest versions of deps and write exact versions to poetry.lock.
  """
  if subject:
      frame = inspect.currentframe()
      return frame.f_locals[subject]
  else:
      return f"""{h1('poetry')}
  {_NEW}
  {_ADD}
  {_ENV}
  {_INSTALL}
  {_BUILD}
  {_PUBLISH}
  {_UPDATE}
      """

@syntax
@alias('psql')
def postgres(subject=None):
    _COMMANDS = f"""{h2('commands')}
    pgcli / psql: \h
    +--------------------+-----------------------------+----------------------+----------------------------+---------------------------+--------------------------+
    | ABORT              | ALTER AGGREGATE             | ALTER COLLATION      | ALTER CONVERSION           | ALTER DATABASE            | ALTER DEFAULT PRIVILEGES |
    | ALTER DOMAIN       | ALTER EVENT TRIGGER         | ALTER EXTENSION      | ALTER FOREIGN DATA WRAPPER | ALTER FOREIGN TABLE       | ALTER FUNCTION           |
    | ALTER GROUP        | ALTER INDEX                 | ALTER LANGUAGE       | ALTER LARGE OBJECT         | ALTER MATERIALIZED VIEW   | ALTER OPCLASS            |
    | ALTER OPERATOR     | ALTER OPFAMILY              | ALTER POLICY         | ALTER ROLE                 | ALTER RULE                | ALTER SCHEMA             |
    | ALTER SEQUENCE     | ALTER SERVER                | ALTER SYSTEM         | ALTER TABLE                | ALTER TABLESPACE          | ALTER TRIGGER            |
    | ALTER TSCONFIG     | ALTER TSDICTIONARY          | ALTER TSPARSER       | ALTER TSTEMPLATE           | ALTER TYPE                | ALTER USER               |
    | ALTER USER MAPPING | ALTER VIEW                  | ANALYZE              | BEGIN                      | CHECKPOINT                | CLOSE                    |
    | CLUSTER            | COMMENT                     | COMMIT               | COMMIT PREPARED            | COPY                      | CREATE AGGREGATE         |
    | CREATE CAST        | CREATE COLLATION            | CREATE CONVERSION    | CREATE DATABASE            | CREATE DOMAIN             | CREATE EVENT TRIGGER     |
    | CREATE EXTENSION   | CREATE FOREIGN DATA WRAPPER | CREATE FOREIGN TABLE | CREATE FUNCTION            | CREATE GROUP              | CREATE INDEX             |
    | CREATE LANGUAGE    | CREATE MATERIALIZED VIEW    | CREATE OPCLASS       | CREATE OPERATOR            | CREATE OPFAMILY           | CREATE POLICY            |
    | CREATE ROLE        | CREATE RULE                 | CREATE SCHEMA        | CREATE SEQUENCE            | CREATE SERVER             | CREATE TABLE             |
    | CREATE TABLE AS    | CREATE TABLESPACE           | CREATE TRANSFORM     | CREATE TRIGGER             | CREATE TSCONFIG           | CREATE TSDICTIONARY      |
    | CREATE TSPARSER    | CREATE TSTEMPLATE           | CREATE TYPE          | CREATE USER                | CREATE USER MAPPING       | CREATE VIEW              |
    | DEALLOCATE         | DECLARE                     | DELETE               | DISCARD                    | DO                        | DROP AGGREGATE           |
    | DROP CAST          | DROP COLLATION              | DROP CONVERSION      | DROP DATABASE              | DROP DOMAIN               | DROP EVENT TRIGGER       |
    | DROP EXTENSION     | DROP FOREIGN DATA WRAPPER   | DROP FOREIGN TABLE   | DROP FUNCTION              | DROP GROUP                | DROP INDEX               |
    | DROP LANGUAGE      | DROP MATERIALIZED VIEW      | DROP OPCLASS         | DROP OPERATOR              | DROP OPFAMILY             | DROP OWNED               |
    | DROP POLICY        | DROP ROLE                   | DROP RULE            | DROP SCHEMA                | DROP SEQUENCE             | DROP SERVER              |
    | DROP TABLE         | DROP TABLESPACE             | DROP TRANSFORM       | DROP TRIGGER               | DROP TSCONFIG             | DROP TSDICTIONARY        |
    | DROP TSPARSER      | DROP TSTEMPLATE             | DROP TYPE            | DROP USER                  | DROP USER MAPPING         | DROP VIEW                |
    | END                | EXECUTE                     | EXPLAIN              | FETCH                      | GRANT                     | IMPORT FOREIGN SCHEMA    |
    | INSERT             | LISTEN                      | LOAD                 | LOCK                       | MOVE                      | NOTIFY                   |
    | PGBENCH            | PREPARE                     | PREPARE TRANSACTION  | REASSIGN OWNED             | REFRESH MATERIALIZED VIEW | REINDEX                  |
    | RELEASE SAVEPOINT  | RESET                       | REVOKE               | ROLLBACK                   | ROLLBACK PREPARED         | ROLLBACK TO              |
    | SAVEPOINT          | SECURITY LABEL              | SELECT               | SELECT INTO                | SET                       | SET CONSTRAINTS          |
    | SET ROLE           | SET SESSION AUTH            | SET TRANSACTION      | SHOW                       | START TRANSACTION         | TRUNCATE                 |
    | UNLISTEN           | UPDATE                      | VACUUM               | VALUES                     |                           |                          |
    +--------------------+-----------------------------+----------------------+----------------------------+---------------------------+--------------------------+
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('postgres')}
  {_COMMANDS}

  {h2('install')}
    {c('https://stackoverflow.com/questions/11919391/postgresql-error-fatal-role-username-does-not-exist')}
    %bash 3
    sudo apt-get install postgresql
    sudo -u postgres createuser -s $(whoami)
    sudo -u postgres createdb $(whoami)

  {h2('env vars')}
    PGHOST
    PGPORT
    PGUSER
    PGPASSWORD
    PGDATABASE
    
  {h2('pgAdmin')}
    https://www.pgadmin.org/download/pgadmin-4-apt/

  {h2('pgcli')} [OPTIONS] [DBNAME] [USERNAME]
    pip install -U pgcli
    pip install ipython-sql
    %load_ext pgcli.magic
    ~/.config/pgcli/config

    {h3('options')}
      -l, --list                {c('list available databases, then exit.')}'
      -h, --host TEXT           {c('Host address of the postgres database.')}'
      -d, --dbname TEXT         {c('database name to connect to.')}'
      -p, --port INTEGER        {c('Port number at which the postgres instance is listening.')}'
      -U|u, --user[name] TEXT   {c('Username to connect to the postgres database.')}'
      -W, --password            {c('Force password prompt.')}'
      -w, --no-password         {c('Never prompt for password.')}'
      -v, --version

    {h3('examples')}
      pgcli postgresql://[user[:password]@][netloc][:port][/dbname][?extra=value[&other=other-value]]
      pgcli local_database
      pgcli postgres://amjith:pa$$w0rd@example.com:5432/app_db?sslmode=verify-ca&sslrootcert=/myrootcert
      %pgcli postgres://someone@localhost:5432/world
  
      """


@syntax
def pytest(subject=None):
    return f"""{h1('pytest')} {c('[options] [file_or_dir] [file_or_dir...]')}

  {h2('Examples')}
    %bash
    pytest --disable-warnings -k MySQLSession -l -s
    pytest tests/python -l -vv -rA --disable-warnings
    pytest tests/python/test_Message.py -rA --maxfail=1 -l -k "create_tempo_shifted" | grep -P ".*{backslash}.py:{backslash}d*"
    python -m pytest -k "gito" --pdbcls="IPython.terminal.debugger:TerminalPdb" --pdb -s
    pytest test_mod.py::TestClass::test_method
    /%bash

  {h2('General')}
    -x {c('or --maxfail=1')}             stop after first failure
    -l                            show locals
    --tb=auto|long|short|line|native|no
    --full-trace                  longer than --tb=long
    --rootdir=ROOTDIR             define {i('ROOTDIR')} for tests
    --trace                       drop to pdb immediately at the start of each test
    --pdb [options]               drop to pdb after every failure (use with -x)
    --pdbcls=IPython.terminal.debugger:TerminalPdb  {c('must use -s')}
    -m MARKEXPR                   -m 'mark1 and not mark2'
    --disable-warnings
    -s                            disable capturing ie show prints
    -c more_termcolor/tests/pytest.ini

  {h2('Filtering')}
    -k KEYWORD                    only run tests matching {i('KEYWORD')}
    -k "not send_http"
    -k "http or quick"
    -k "MyClass and not method"
    -k "file_path and MyClass"    no file extension
    --lf                          run only last failed (all if none failed)
    --ff                          run all tests, but run the failed ones first
    --nf                          new first

  {h2('Reporting')}
    {h3('-r<flag>')}                      short test summary at the end of the test session
      {c('default: -rfE')}
      -rA                         (show summary of) all
      -ra                         all except passed
      -rf                         only failed
      -rE                         only errored
      -rp                         only passed
      -rP                         only passed with output
      -rs                         only skipped
      -rN                         nothing

    {h3('--doctest-')}
      --doctest-modules           run all
      --doctest-glob=GLOB         maybe together with --doctest-modules
    --durations=10                time of {i('10')} slowest tests

  {h2('Configuration')}
    {h3('conftest.py')}
      {h4('Custom function arguments')}
      %python
      import pytest
      def pytest_addoption(parser):
          parser.addoption('--myopt', ...)

      @pytest.fixture
      def myopt(request):
          return request.config.getoption("--myopt")
      /%python

    {h3('pytest.ini')}
      {c('https://docs.pytest.org/en/latest/reference.html#ini-options-ref')}
      %ini
      [pytest]
      addopts =
          --pdbcls=IPython.terminal.debugger:TerminalPdb
          --capture=no  # this is required with custom pdb!
          --disable-warnings
      doctest_optionflags= ELLIPSIS
      filterwarnings =
          error
          ignore::DeprecationWarning
          ignore:.*U.*mode is deprecated:DeprecationWarning
      python_classes = Test* [a-z]*
      python_files = test_*.py check_*.py example_*.py
      python_files =
        test_*.py
        check_*.py
        example_*.py
      python_functions = *_test
      /%ini

  """


@syntax
def python(subject=None):
    _ARGPARSE = f"""{h2('argparse')}
  {c('https://docs.python.org/3.8/library/argparse.html')}
  
  {h3('ArgumentParser(...)')}
    prog        {c('default: sys.argv[0]')}
    usage       {c('default: generated from args')}
    description
    epilog
    ...
    
    {h4('add_argument(...)')}
      *name_or_flags      {c("str               'bar' or ('-f', '--foo')")}
      action              {c("str | Action      'store' (default), 'store_const',")}
                                            {c("'store_true', 'store_false',")}
                                            {c("'append', 'append_const', 'count'")}
      choices             {c("list[str]")}
      const               
      default
      dest                {c("str; eventual VARIABLE name")}
      help                {c("str               '%(prog)s %(default)s'")}
      metavar             {c("str; how DISPLAYED in help")}
      nargs               {c("int | '?' | '*' | '+' | argparse.REMAINDER")}
      prog                {c("str")}
      required            {c("bool")}
      type
      ...
    
    {h4('parse_args(args: list[str] = None, namespace: Namespace = None)')}
      %python friendly
      # Examples
      >>> parser.parse_args(['--max-depth', 1])
      Namespace(max_depth=1)
      
      >>> parser.parse_args(['--max-depth=1'])
      Namespace(max_depth=1)
      
      >>> parser.parse_args(['-mr'])
      Namespace(mode='r')
      /%python
    """
    _BITWISE = f"""{h2('Bitwise')}
  &  |  0  1  F  T 10
  ---|---------------
  0  |  0  0  0  0  0
  1  |  0  1  0  1  0
  F  |  0  0  F  F  0
  T  |  0  1  F  T  0
  10 |  0  0  0  0 10

  ^  |  0  1  F  T 10
  ---|----------------
  0  |  0  1  0  1 10
  1  |  1  0  1  0 11
  F  |  0  1  F  T 10
  T  |  1  0  T  F 11
  10 | 10 11 10 11  0

  |  |  0  1  F  T 10
  ---|----------------
  0  |  0  1  0  1 10
  1  |  1  1  1  1 11
  F  |  0  1  F  T 10
  T  |  1  1  T  T 11
  10 | 10 11 10 11 10
    """
    _CMD = _COMMANDLINE = f"""{h2('python3 -c <command>')}
  {c("https://docs.python.org/3/using/cmdline.html")}

  {h3('-d')}  {c("Turn on parser debugging | PYTHONDEBUG")}
  {h3('-E')}  {c("Ignore PYTHON* env vars like PYTHONPATH and PYTHONHOME")}
  {h3('-i')}  {c("enter interactive mode after execution. PYTHONSTARTUP is not read | PYTHONINSPECT")}
  {h3('-I')}  {c("isolated mode: implies -E and -s. no: script dir, user site-packages, PYTHON* env vars")}
  {h3('-O')}  {c("remove assert statements and any code conditional on the value of __debug__ | PYTHONOPTIMIZE")}
  {h3('-OO')} {c("Do -O and also discard docstrings | PYTHONOPTIMIZE=2")}
  {h3('-q')}  {c("no copyright and version messages")}
  {h3('-s')}  {c("don't add user site-packages to sys.path")}
  {h3('-u')}  {c("Force stdout and stderr streams to be unbuffered. No effect on stdin stream. | PYTHONBUFFERED")}
  {h3('-v')}  {c("Print when a module is initialized | PYTHONVERBOSE")}
  {h3('-vv')} {c("Also on each file that's searched | PYTHONVERBOSE=2")}

  {h3('-W action:message:category:module:line')}
    {c('Can be specified multiple times | PYTHONWARNINGS')}
    {c('https://docs.python.org/3/using/cmdline.html#cmdoption-w')}
    {h4('action')}: ignore|default|all|module|once|error
      {c(f'module print only first time each module')}
      {c(f'once only first time per warning')}
    {h4('message')}: matches start of the warning. case-insensitive
    {h4('category')}: full warning (super) class name
    {h4('module')}: module name. case-sensitive.
    {h4('line')}: number. 0 matches all == unspecified

  {h3('-X importtime')}  {c("python3 -X importtime -c 'import asyncio' | PYTHONPROFILEIMPORTTIME")}

  {h4('See also')}
    mm python env
    """

    _DATE = _DATETIME = _TIME = _TZ = f"""{h2('date / datetime / time / timezone')}
  {h3('strftime')}(format)
    {c('now  = datetime.datetime(2020, 9, 2, 17, 37, 29, 960461)')}
    %a      Wed
    %b, %h  Sep
    %c      Wed Sep  2 00:00:00 2020
    %d      02
    %e       2
    %f      960461
    %g      20
    %k      17
    %l       5 (maybe time in PM?)
    %m      09
    %p      PM
    %r      05:37:29 PM
    %s      1599057449
    %x      09/02/20
    %y      20
    %A      Wednesday
    %B      September
    %C      20
    %D      09/02/20
    %F      2020-09-02
    %G      2020
    %H      17
    %I      05
    %M      37
    %P      pm
    %R      17:37
    %S      29
    %T      17:37:29
    %X      17:37:29
    %Y      2020
  
  {h3('pytz')}
    %python 1
    from pytz import all_timezones  # America/..., Israel, UTC, Etc/GMT+2, Etc/Universal, US/Centra

  {h3('time')}
    %python 1
    import time
    time.time() {c('→ 1600000000.8624794')}
    time.time_ns() {c('→ 1600000000670609665')}
    time.ctime([seconds since epoch]) {c("→ 'Sat Dec 19 20:10:39 2020'")}
    time.strftime(<format>)
    time.sleep(s)
    time.perf_counter() {c('→ 222349.809660548')}
    time.perf_counter_ns() {c('→ 222398727158532')}
    time.localtime([seconds since epoch]) {c('→ struct_time. If no `seconds` passed, do for current time')}

  {h3('datetime.date')}
    %python 1
    from datetime import date
    date(2020, 12, 19) {c('→ datetime.date(2020, 12, 19)')}
    
    {h4('Static Methods')}
      today = date.today() {c('→ date')}
      date.fromtimestamp(1600000000) {c('→ date')}
    
    {h4('Instance Methods / Attrs')}
      today.day, .month, .year {c('→ int')}
      today.ctime() {c('→ "Wed Sep  2 00:00:00 2020"')}
      today.isoformat() {c('→ "2020-12-30"')}
      today.strftime(format) {c('→ "2020-12-30"')}
  
  {h3('datetime.datetime')}
    %python 1
    from datetime import datetime as dt
    dt(2020, 12, 19) {c('→ datetime.datetime(2020, 12, 19, 0, 0)')}
    dt(2020, 12, 19{c('[, 23, 45, 10, 999999, tzinfo]')})

    now = dt.now() {c('→ datetime.datetime(2020, 12, 19, 6, 12, 57, 938731)')}
    
    {h4('Instance Methods / Attrs')}
      now.microsecond, .second, .minute, .hour, .day, .month, .year {c('→ int')}
      now.astimezone() {c('→ datetime')}
      now.isoformat() {c('→ "2020-09-02T17:37:29.960461"')}
      now.isoweekday() {c('→ int (Monday is 1)')}
      now.date() {c('→ date')}
      now.time() {c('→ datetime.time')}
      now.ctime() {c('→ "Wed Sep  2 17:37:29 2020"')}
      now.timestamp() {c('→ float (1599057449.960461)')}
      now.timetz() {c('→ datetime.time')}
    
    {h4('Static Methods')}
      utcnow = dt.utcnow() {c('→ datetime (utc)')}
      now = dt.now() {c('→ datetime (local)')}
      dt.fromtimestamp(1600000000) {c('→ datetime')}
  
    """
    _DECORATORS = f"""{h2('Decorators')}

  @naked_dec              {c('equiv:')}
  def foo(): ...          def foo(): ...
                          foo = naked_dec(foo)
  {c('This is why @naked_dec has to return a function')}

  @arg_dec(arg)           {c('equiv:')}
  def foo(): ...          def foo(): ...
                          foo = arg_dec(arg)(foo)
  {c(f'This is why @arg_dec has to return something that expects a function (liked naked_dec)')}

  @f1(arg)                {c('equiv:')}
  @f2                     class Foo: ...
  class Foo: ...          Foo = f1(arg)(f2(Foo))
    """
    _DIFFLIB = f"""{h2('difflib')}
  %ipython
  In [0]: for x in difflib.ndiff('abc','ac'):
     ...:    print(x)
    a
  - b
    c

  In [1]: for x in difflib.ndiff('ac','abc'):
     ...:    print(x)
    a
  + b
    c
  /%ipython
    """
    _DOCTEST = f"""{h2('doctest')}
  {h3('Programmatically')}
    {h4('Dynamically, so `python3 file.py` runs the doctests:')}
      %python
      if __name__ == "__main__":
          import doctest
          doctest.testmod()
      
      # OR (pytest):
      testres: TestResults = doctest.testmod(igit.expath, optionflags=doctest.ELLIPSIS)
      assert testres.failed == 0
      /%python

    {h4('Interactively:')}
      %python
      import doctest
      doctest.testfile("expath.py", package='igit') # optional raise_on_error=True
      # OR:
      doctest.testfile("igit/expath.py", module_relative=False)

      # alternatively:
      run_doctest = partial(doctest.run_docstring_examples, globs=globals())
      run_doctest(relate)
      /%python

  {h3('Exceptions')}
    %bash 1
    python -m doctest [-v] igit/util/path.py -o ELLIPSIS

    %python
    Traceback (most recent call last):
        ...
    TypeError
    /%python

  {h3('Options')} {c('-o <OPTION>[ -o <OPTION>...]')}
    DONT_ACCEPT_BLANKLINE {c('2')}
    ELLIPSIS {c('8')}
    FAIL_FAST, -f {c('1024')}
    IGNORE_EXCEPTION_DETAIL {c('32      expects same exception type, doesnt care about detail')}
    NORMALIZE_WHITESPACE {c('4          all sequences of whitespace (blanks and newlines) are treated as equal')}
    REPORT_ONLY_FIRST_FAILURE {c('512   suppresses output of following tests, but still counts them')}
    SKIP {c('16')}
    """
    _ENV = f"""{h2('Environment Variables')}
  {c('https://docs.python.org/3/using/cmdline.html#environment-variables')}

  PYTHONHOME
    Change the location of the standard Python libraries. By default, the libraries are searched in prefix/lib/pythonversion and exec_prefix/lib/pythonversion,
    where prefix and exec_prefix are installation-dependent directories, both defaulting to /usr/local.

  PYTHONPATH {c("/this/path:/other/path:...")}
    Augment the default search path for module files

  PYTHONSTARTUP {c('/path/to/file.py')}
    Executed before first prompt in interactive mode,
    in same namespace where interactive commands are executed.
    Can change sys.ps1 and sys.ps2 and sys.__interactivehook__ in this file.

  PYTHONBREAKPOINT {c('package.module.callable')}

  PYTHONNOUSERSITE
    Don't add the user site-packages directory to sys.path.
    {c('https://docs.python.org/3/library/site.html#site.USER_SITE')}

  PYTHONUSERBASE
    Defines the user base directory.
    {c('https://docs.python.org/3/library/site.html#site.USER_BASE')}
    Used to compute path of site-packages and installation paths for python setup.py install --user.

  PYTHONWARNINGS {c("action[,action,...]")}
    {c('https://docs.python.org/3/library/warnings.html#warning-filter')}
    ignore|default|all|module|once|error

  PYTHONPROFILEIMPORTTIME {c('like -X importtime')}
  
  PYTHONBUFFERED
    If a non-empty string, equivalent to specifying -u option.
    
  PYTHONINSPECT
    If a non-empty string, equivalent to specifying -i option.

  {h4('See also')}
    mm python cmd
    """

    __FORMATTER = f"""{h3('Formatter(')}
        %python
        fmt : str = None,
        datefmt: str = None,
        style: str = "%"
        )
        /%python
        
        formatter.formatException((etype, einst, tb))
        formatter.formatStack(stack_info)
        formatter.formatMessage(record)
        formatter.format(record)
    """
    __HANDLER = f"""{h3('Handler(level=NOTSET)')}
        handler.name    {c('Getter / setter to lock and release')}
        handler.format(record)
        handler.setFormatter(formatter : Formatter)
        handler.handlerError(record)
    """
    __LOGRECORD = f"""{h3('LogRecord(')}
        %python
        name : str, 
        
        # self.levelname = getLevelName(level)
        # 'INFO' → 20
        # 20 → 'INFO'
        # 'foo' → 'Level foo'
        level : str | int,
        
        pathname, 
        lineno,
        msg, 
        args, 
        exc_info, 
        func=None, 
        
        # stack info
        sinfo=None, 
        **kwargs
        )
        /%python
    
    {h4('Attributes')} {c('%(attr)[s f d]')}
      {c('https://docs.python.org/3/library/logging.html#logrecord-attributes')}
      asctime
      created           {c('when LogRecord was created. %(created)f')}
      exc_info          {c('Exception tuple (like sys.exc_info)')}
      exc_text
      filename
      funcName
      levelname
      levelno           {c('e.g 20')}
      lineno            {c('%(lineno)d')}
      message           {c('result of record.getMessage()')}
      module
      msecs             {c('%(msecs)d')}
      name              {c('logging.getLogger(name)')}
      pathname
      process           {c('process ID. %(process)d')}
      processName       {c('process name')}
      relativeCreated   {c('ms between logging module was loaded and LogRecord created. %(relativeCreated)d')}
      stack_info
      thread            {c('thread ID. %(thread)d')}
      threadName
    
    {h4('logging.setLogRecordFactory(factory : LogRecord)')}
      Sets global logging._logRecordFactory
    
    {h4('logging.getLogRecordFactory() -> LogRecord')}
      Returns global logging._logRecordFactory
    """
    _LOGGING = f"""{h2(f'logging')}
  {__HANDLER}
  {__LOGRECORD}
  {__FORMATTER}
  
  {h3('_loggerClass : Logger')}
    {c('Used by Logger.manager in Manager.getLogger(name)')}
    logging.setLoggerClass(cls : Logger)    {c('Sets global logging._loggerClass')}
    logging.getLoggerClass()    {c('Returns global logging._loggerClass')}
  
  {h3('basicConfig(')}
            %python
            filename,
            filemode = 'a',
            format,
            datefmt,
            style = '%',
            level,
            stream,
            handlers
            )
            /%python
            
    {h3('getLogger(name=None)')}
      {c('Returns Logger.manager.getLogger(name) if name else root')}
    """
    _OPEN = rf"""{h2(f'with open(path, mode="rt" {c("default")}, errors=None)')}
  {h2('mode')}
    w                   {c("truncate file first. doesn't raise")}
    x                   {c(f"create new file (implies 'w', raises FileExistsError if exists)")}
    a                   {c("append to end of file if exists. doesn't raise")}
    b                   {c("binary")}
    t                   {c("text")}
    +                   {c("open for updating (read and write)")}

  {h2('errors')}
    'strict'            {c("raise a ValueError error (or a subclass)")}
    'ignore'            {c("ignore the character and continue with the next")}
    'replace'           {c("with '?' on encoding, U+FFFD on decoding")}
    'backslashreplace'  {c("backslash escape the faulty chars")}
    'namereplace'       {c(f"Replace with {backslash}N{{...}} escape sequences (only for encoding).")}
    """
    _PATHLIB = f"""{h2('pathlib')}
  p = PosixPath('mytool/git/status/status.py')
  
  {h3('methods / properties')}
    Path.cwd()  {c("PosixPath('/media/gilad/Main_EXT4')")}
    p.name      {c('status.py')}
    p.stem      {c('status')}
    p.suffix    {c('.py')}
    p.suffixes  {c("['.py']")}
    p.parts     {c("('mytool', 'git', 'status', 'status.py')")}
    p.parent    {c("PosixPath('mytool/git/status')")}

  {h3('relation')}
    home = Path('/home')
    gilad = Path('/home/gilad')
    gilad.relative_to(home)       {c("PosixPath('gilad')")}
    home.relative_to(gilad)       {c("ValueError: '/home' does not start with '/home/gilad'")}
    home.relative_to(home)        {c("PosixPath('.')")}
      {h5('Note')}: same_content_different_name because PosixPath('.').samefile(cwd()) is always True regardless of actual cwd
  
  {h3('comparison')}
    Path.cwd() == Path('.')                   {c('False')}
    Path.cwd() == Path('.').absolute()        {c('True')}
    Path.cwd().samefile(Path('.'))            {c('True')}
    Path.cwd().samefile(Path('.').absolute()  {c('True')}
    """
    _REGEX = rf"""{h2('Regex')}

    {h3('Nuances')}
      re.match("([abc])+", "ab{b('c')}").groups() → ({b('"c"')},)
      re.match("([abc])?", "{b('a')}bc").groups() → ({b('"a"')},)
      re.match("([abc]+)", "{b('abc')}").groups() → ({b('"abc"')},)
      re.match("([abc]?)", "{b('a')}bc").groups() → ({b('"a"')},)

    {h3('Groups')}
      {c('Find doubled words')}
      >>> p = re.compile('\b(\w+)\s+\1\b')         {c('The')} \1 means "result of first group" {c('')}
      >>> p.search('Paris in the the spring').group()
      {c('the the')}

    {h3('Non-capturing groups')}
      {c('capturing:')}
      >>> m = re.match("([abc])+", "abc")
      >>> m.groups()
      {i(c("('c',)"))}

      {c('non-capturing:')}
      >>> m = re.match("(?:[abc])+", "abc")
      >>> m.groups()
      {i(c('()'))}

      >>> m = re.match("(?:abc)+(d)ef", "abcdef")
      >>> m.groups()
      {i(c("('d',)"))}
      >>> m.group()
      {i(c("'abcdef'"))}

    {h3('Named groups')}
      >>> re.compile(r'(?P<word>\\b\w+\\b)')
      >>> m.group('word')

      {h4('groupdict')}
      >>> re.match(r'(?P<first>\w+) (?P<last>\w+)', 'Jane Doe')
      >>> m.groupdict()
      {i(c("{'first': 'Jane', 'last': 'Doe'}"))}

    {h3('Look')}
      {h4('behind')}
        (?<!a)b
        (?<=a)b
        >>> re.match(r'((?<!notes).)*', 'hello-notes-hi')
        {i(c("hello-notes"))}
        >>> re.fullmatch(r'((?<!notes).)*', 'hello-notes-hi')
        {i(c("None"))}

      {h4('ahead')}
        q(?=u)
        q(?!u)
        >>> re.match(r'((?!notes).)*', 'hello-notes-hi')
        {i(c("hello-"))}
        >>> re.match(r'(.(?!notes))*', 'hello-notes-hi')
        {i(c("hello"))}

    """
    _SUBPROCESS = _POPEN = f"""{h2('subprocess')}

    {h3("fn                       returns             prints      out in ret      accepts     raises")}
    sp.run()                 CompletedProcess    yes         no              input
    
    sp.run(stdout=PIPE)      CompletedProcess    no          yes             input
    
    sp.run(capture_output=True)  
    
    sp.Popen()               Popen               yes         no
    
    sp.Popen(stdout=PIPE)    Popen               no          yes
    
    sp.check_output()        bytes               no          yes             input       on non-zero
      {c('Wraps run(*popenargs, stdout=PIPE, timeout=timeout, check=True, **kwargs).stdout')}
    
    sp.check_call([...])     0?                  yes         no                          on non-zero      
      {c('Wraps call(*args, **kwargs) for raising CalledProcessError if exitcode != 0')}
    
    sp.call([...])           exit code (int)     yes         no
      {c('Wraps Popen for timeout=')}
    
    sp.getoutput(cmd)        str                 no          yes
      {c('Wraps getstatusoutput(cmd)[1]')}
    
    sp.getstatusoutput(cmd)  (code, out)         no          yes
      {c('Wraps check_output(cmd, shell=True, text=True, stderr=STDOUT)')}

    {h3('Output')}
      {c("capture_output=True  <==>  stdout=sp.PIPE")}
      sp.getoutput('ls')
      sp.run(['ls'], stdout=sp.PIPE).stdout.decode().strip()
      sp.Popen(['ls'], stdout=sp.PIPE).stdout.read().decode().strip()
      sp.check_output(['ls']).decode().strip()

    {h3('Input')}
      p = sp.Popen(['sudo', '-S', 'ls'], stdin=sp.PIPE); p.communicate(input=b'...')
      sp.run(['sudo', '-S', 'ls'], input=b'...')

    {h3('Popen args')}
      shell = True              {c(f'pass a str {i("args")}. like running {i("/bin/sh -c ...")}')}
      executable = True         {c(f'replace program to exec instead of first arg. when {i("shell = True")}, replaces {i("/bin/sh")}')}
      cwd: str or pathlike      {c(f'executable (or first arg) is looked relative to {i("cwd")} if executable path is relative.')}
      env                       {c('env variables mapping for new process')}

    {h3('Examples')}
      try:
          sp.run(['python','-c','pass'], stdout=sp.PIPE, stderr=sp.PIPE, timeout=1)   {c('# 1s')}
      except sp.TimeoutExpired:
          ...

      {h4('Ignore errors')}
      sp.run(['./uninstall.py'], stdin=sp.PIPE, stdout=sp.DEVNULL, stderr=sp.STDOUT)

      {h4('output=$(mycmd myarg)')}
        output = sp.check_output(["mycmd", "myarg"]{c(", stderr=sp.STDOUT, input=b'this is passed to proc stdin'")})
        {c("also:")}
        p = sp.Popen('mycmd myarg'.split(), stdout=sp.PIPE)
        p.stdout.readlines()

      {h4('output=$(dmesg | grep hda)')}
        p1 = Popen(["dmesg"], stdout=PIPE)
        p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()    {c('Allow p1 to receive a SIGPIPE if p2 exits.')}
        output = p2.communicate()[0]
        {c("also:")}
        output=check_output("dmesg | grep hda", shell=True)

      {h4('a << "input data" | b > "outfile.txt"')}
        a = Popen(["a"], stdin=PIPE, stdout=PIPE)
        with a.stdin:
            with a.stdout, open("outfile.txt", "wb") as outfile:
                b = Popen(["b"], stdin=a.stdout, stdout=outfile)
            a.stdin.write(b"input data")
        statuses = [a.wait(), b.wait()] # both a.stdin/stdout are closed already
    """
    _VERSIONS = _CHANGELOG = f"""{h2('versions')}
    {h3('3.9')}
      {c('https://docs.python.org/3/whatsnew/3.9.html')}
      asyncio.to_thread()
      pathlib.Path.readlink()
      str.removeprefix, str.removesuffix
      
      {h4('PEP-584: Dict union operators')}
        %python
        d1 | d2     # {{**d1, **d2}}
        d1 |= d2    # d1.update(d2)
        d1 |= [('spam', 999)]
        /%python
      
      {h4('PEP-585: Type Hinting Generics')}
        def foo(bar: dict[str, list[int]]): ...
        {h5('available at runtime:')}
          >>> l = list[str]()
          []
          >>> list is list[str]
          False
      
      {h4('PEP-593: Flexible function and variable annotations')}
      
      {h4('Relaxed decorator syntax')}
        anything that's valid as a test in if, elif, and while blocks
        
        %python
        @buttons[0].clicked.connect
        def spam():
            ...
        /%python
      
      {h4('zoneinfo module')}
        %python 2
        from zoneinfo import ZoneInfo
        ZoneInfo("America/Vancouver")
    """

    if subject:
        # if subject == '_SUBPROCESS':
        #     from rich.table import Table
        #     from rich.console import Console
        #     con = Console()
        #     table = Table('Function', 'Returns', 'Prints', 'Out in ret?', 'Accepts', 'Raises')
        #     table.add_row('run()', 'Completed Process', 'yes', 'no', 'input')
        #     segments = con.render(table)
        #     return ''.join(seg.text for seg in segments)

        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Python')}
  {_BITWISE}

  {_CMD}

  {_DATE}
  
  {_DECORATORS}

  {_DIFFLIB}
  
  {_ARGPARSE}

  {_DOCTEST}

  {_ENV}

  {_LOGGING}

  {_OPEN}

  {_PATHLIB}

  {_REGEX}

  {_SUBPROCESS}
  
  {_VERSIONS}
        """


@alias('rst')
def restructured_text(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('reStructuredText')}
  {c('https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html')}
  {bg('tip:')} export jupyter notebook to .rst to learn syntax
  
  *emphasis*, **strong emphasis**, `interpreted text`, ``inline
  literals``, standalone hyperlinks (http://www.python.org),
  external hyperlinks (Python_), internal cross-references
  (example_), footnote references ([1]_), citation references
  ([CIT2002]_), substitution references (|example|), and _`inline
  internal targets`.

  {h2('function(arg)')}
    :param arg: description
    :type arg: description
    :return: description
    :rtype: type
    .. seealso:: text
    .. note:: text
    .. warning:: text
    .. todo:: text
    :Example:

    example text
  
  {h2('Examples')}
    {h3('highlighted code')}
    ::
        foo(42)
    
    {h3('click')}
      :class:`Option` or :class:`Argument`

    {h3('traitlets.config.configurable.Configurable')}
      Create a configurable given a config config.

      Parameters
      ----------
      config : Config
          If this is empty, default values are used. If config is a
          :class:`Config` instance, it will be used to configure the
          instance.
      parent : Configurable instance, optional
          The parent Configurable instance of this object.

      Notes
      -----
      Subclasses of Configurable must call the :meth:`__init__` method of
      :class:`Configurable` *before* doing anything else and using
      :func:`super`::

          class MyConfigurable(Configurable):
              def __init__(self, config=None):
                  super(MyConfigurable, self).__init__(config=config)
                  # Then any other code you need to finish initialization.

      This ensures that instances will be configured properly.
        """


@syntax(python='friendly')
def rich_(subject=None):
    _INSPECT = f"""{h3('inspect(')}
        %python
        obj, *,
        console = None,
        title: str = None,
        help: bool = False,    # Full-fledged docstring. `True` forces `docs = True`
        methods: bool = False,
        docs: bool = True,     # First line or two of docstring
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all: bool = False,
        value: bool = True     # Pretty print value
        /%python
    )"""

    _CONSOLE = f"""{h3('console.Console(')}
              %python
              highlight = True,
              log_time = True, 
              log_path = True,
              log_time_format = "[%X]", 
              width = None,
              height = None, 
              ...
              /%python
      )
      
      {h4('log(')}     {c('Prints and indents with [07.01.2021]. ~30ms')}
          %python
          *objs, 
          sep = ' ', end = '{linebreak}', 
          highlight: bool = None,
          justify: 'default' | 'left' | 'center' | 'right' | 'full' = None, 
          log_locals = False,   # ← not in console.print()
          _stack_offset = 1, ...
          /%python
      )
      
      {h4('print(')}   {c('Advanced form of rich.print(). ~15ms')}
          %python
          *objs, 
          sep = ' ', end = '{linebreak}', 
          highlight = None,   # ← not in rich.print()
          justify: 'default' | 'left' | 'center' | 'right' | 'full' = None, 
          overflow = 'fold', 'crop', 'ellipsis', 'ignore' = None,   # ← not in .log()
          no_wrap: bool = None,
          soft_wrap: bool = None,
          width = None,
          crop: bool = True, ...
          /%python
      )
    
      {h4('print_exception(')}   {c('Prints a rich render of the last exception and traceback. ')}
          %python
          width = 100,
          extra_lines = 3,  # Additional lines of code to render
          word_wrap = False, 
          show_locals = False
          /%python
      )

      {h4('save_text(')}      {c('Generate text from console contents and write to file (requires record=True in constructor)')}
          %python 2
          path: str,
          styles = False   # Whether to include ansi codes
      )
      
      {h4('export_text(')}    {c('Generate text from console contents (requires record=True in constructor)')}
          %python 2
          styles = False   # Whether to include ansi codes
      ) -> str
      
      {h4('save_html(')}      {c('Generate HTML from console contents and write to file (requires record=True in constructor)')}
          %python 2
          path: str,
          code_format='PREDEFINED FANCY HTML'
      )
      
      {h4('export_html(')}    {c('Generate HTML from console contents (requires record=True in constructor)')}
          %python 2
          code_format: str = None   # "{{foreground}} {{background}} {{code}}"
      ) -> str
      
      {h4('with capture() as capture:')}    {c('of print() or log()')}
          %python 2
          console.print('hi')
      return capture.get()
      
      {c('alternatively:')}
      
      {h4('begin_capture(); ...; .end_capture()')}
      
      {h4('input(')}
          %python 3
          prompt = '',
          password = False
      ) -> str"""
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('rich / pyinspect')}
  {h2('pyinspect')}
    {h3('pi.what(')}   {c('like rich.inspect(title=str(type(hi)), methods=True) but also displays source code')}
        %python 2
        var=None,   # without args, shows all locals
        **kwargs
    )
    
    {h3('pi.showme(func)')}   {c('Shows source code')}
    
    {h3('pi.search(')}
        %python
        obj,
        name = "",
        print_table = True,
        **kwargs
        /%python
    )
    
    {h3('pi.install_traceback(')}   {c('Syntax highlighting, formatting, expose local vars')}
        %python
        keep_frames=2,        # N last frames are presented in detail
        hide_locals=False, 
        all_locals=False,     # Expose everything, not just the local vars
        relevant_only=False,  # Expose only the vars that existed in the error line
        enable_prompt=False
        /%python
    )
  
  {h2('rich')}
    {_INSPECT}
    
    {h3('print()')}    {c('Syntax highlight; Same sig as builtin. ~15ms')}
    
    {_CONSOLE}
    
    {h3('rich.pretty')}
      {h4('pretty_repr(')}
          %python
          obj,
          /%python
      )
      .pretty_repr(obj, expand_all = False, max_length:int = None, max_string:int = None, indent_guides: bool = True)

      .prettyprint

      .print

      .install(expand_all = False, max_length:int = None, max_string:int = None)    {c('automatic pretty printing in Python REPL')}

    {h3('rich.logging')}
    
    {h3('rich.panel')}
    {h3('rich.table')}
    
    {h3('rich.traceback')}
      {c('https://rich.readthedocs.io/en/latest/reference/traceback.html')}
      .install(show_locals = True, word_wrap = False, show_locals = False)
      .Traceback(...)
      .extract(...)
      .from_exception(...)
    
        """


@alias('rg')
def ripgrep(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('ripgrep')}
  {h2('Exit Status')}
    0: found a match, no errors
    1: no match, no errors
    2: errors

  {h2('Usages')}
     rg [OPTIONS] [PATTERN] [PATH...]
     <command> | rg [OPTIONS] PATTERN

  $RIPGREP_CONFIG_PATH env var

  {h2('options')}
    {h3('file filter')}
      --unrestricted
        -u                        {c('like --no-ignore')}
        -uu                       {c('like --no-ignore and --hidden')}
        -uuu                      {c('like --no-ignore, --hidden and --binary')}
      --no-ignore                 {c('dont respect ignore files. off by default')}
      --hidden                    {c('search hidden files and dirs. off by default.')}
      --binary                    {c('dont exclude binary files from search. off by default')}
      --no-ignore-global          {c('like --no-ignore but for global files/settings')}
      --max-depth <N>             {c('0 only works for files. 1 searches direct children of dir')}
      -a, --text                  {c('treat binary as text (and search them)')}
      -z, --search-zip
      -g, --[i]glob <GLOB>        {c("filter paths. --glob '!*.py' to exclude")}
      --pre <COMMAND>             {c('search stdoud of COMMAND FILE. see "man rg" for example.')}
      --pre-glob <GLOB> ...       {c('apply "--pre" only on files matching GLOB(s)')}

    {h3('match control')}
      -s, --case-sensitive        {c('overrides -i/--ignore-case and -S/--smart-case')}
      -i, --ignore-case
      -S, --smart-case            {c('insensitive if all lowercase, sensitive otherwise')}
      -F, --fixed-strings         {c('treat PATTERN literally, so no need to escape regex chars')}
      -U, --multiline[-dotall]

    {h3('output')}
      -A, -B, -C                  {c('context')}
      -v                          {c('invert match')}
      --no-line-number, -N        {c('dont show line numbers')}
      --line-number, -n           {c('show line numbers (default)')}
      --only-matching, -o         {c('show only the matched parts')}
      --count, -c                 {c('how many lines had a match per file')}
      --count-matches             {c('how many matches per file')}
      --files                     {c('print files that would be searched (no actual search)')}
      --files-with-matches, -l    {c('print paths of files with matches')}
      --files-without-match       {c('print paths of files without matches')}
      --no-filename, -I
      --no-heading                {c('file path is prefixed left to result (no linebreak)')}
      -q, --quiet                 {c('dont print matches to stdout. exit code still works.')}
      --sort[r] <none | path | modified | accessed | created>   {c('"none" is multithreaded')}
      """

@syntax
def rsync(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('rsync')}
    -n, --dry-run
    -v, --verbose
    --info=FLAGS                {c('fine-grained informational verbosity')}
                                {c('--info=help    # view options')}
                                {c('--info=progress2')}
                                {c('--info=stats2,misc1,flist0')}
    -r, --recursive
    -u, --update                {c('skip files that are newer on the receiver')}
        --inplace               {c('update destination files in-place')}
        --super                 {c('receiver attempts super-user activities')}
        --fake-super            {c('store/recover privileged attrs using xattrs')}
    -p, --perms                 {c('preserve permissions')}
    -t, --times                 {c('preserve modification times')}
    -t, --times                 {c('preserve modification times')}
    -E, --executability         {c('preserve executability')}
        --chmod=CHMOD           {c('affect file and/or directory permissions')}
    -S, --sparse                {c('handle sparse files efficiently')}
        --preallocate           {c('allocate dest files before writing')}
    -e, --rsh=COMMAND           {c('specify the remote shell to use')}
        --ignore-errors         {c('delete even if there are I/O errors')}
        --force                 {c('force deletion of dirs even if not empty')}

        --max-size=SIZE         {c('dont transfer any file larger than SIZE')}
        --min-size=SIZE         {c('dont transfer any file smaller than SIZE')}
        --partial               {c('keep partially transferred files')}
        
    -m, --prune-empty-dirs      {c('prune empty directory chains from file-list')}
    -I, --ignore-times          {c('dont skip files that match size and time')}
        --size-only             {c('skip files that match in size')}
    -z, --compress              {c('compress file data during the transfer')}
        --compress-level=NUM    {c('explicitly set compression level')}

        --delete                {c('delete extraneous files from dest dirs')}
        --remove-source-files   {c('sender removes synchronized files (non-dir)')}'
        --existing              {c('skip creating new files on receiver')}
        --ignore-existing       {c('skip updating files that exist on receiver')}
    -C, --cvs-exclude           {c('auto-ignore files in the same way CVS does')}
    -f, --filter=RULE           {c('add a file-filtering RULE')}
        --exclude=PATTERN       {c('exclude files matching PATTERN')}
        --include=PATTERN       {c('dont exclude files matching PATTERN')}

        --stats                 {c('give some file-transfer stats')}
    -h, --human-readable        {c('output numbers in a human-readable format')}
        --progress              {c('show progress during transfer')}

    -P                          {c('same as --partial --progress')}
    -i, --itemize-changes       {c('output a change-summary for all updates')}

    {h2('Examples')}
      %bash
      # Identity file:
      -e "ssh -i $HOME/.ssh/somekey"
      
      # Whatever:
      exclude=()
      for x in '*.apk' '*.exe' '*.gif' '*.jpg' '*.mib' '*.png' \\
               '*.so*' '*.svg' '*.tar' '*.ttf' '*.zip' 'php' \\ 
               'frontend' 'site-packages' 'vagrant' 'tools' '*.whl' 
      do
        exclude+=(--exclude "$x")
      done
      rsync --ignore-existing -z --compress-level=9 -C -h --progress \\
        "${{exclude[@]}}" --recursive ./allotsecure root@10.111.242.38:/tmp/allotsecure
      /%bash
        """
def s3(subject=None):
    _BUCKET = f"""{h2('Bucket')}    {c(f"b = s3.Bucket('bucket')")}

    b.name
    b.download_file()
    b.download_fileobj()
    b.load()
    b.put_object(Body=...)
    b.upload_file()
    b.upload_fileobj()
    b.wait_until_exists()
    b.wait_until_not_exists()
    b.objects {c('→ s3.Bucket.objectsCollectionManager')}

    """
    _OBJECTS_COLLECTION = f"""{h2('s3.Bucket.objectsCollection')}    {c(f"b.objects.all()")}

      all() {c('→ s3.Bucket.objectsCollection')}
      delete()
      filter() {c('→ s3.Bucket.objectsCollection')}
      limit() {c('→ s3.Bucket.objectsCollection')}
      pages() {c('→ generator')}
      page_size() {c('→ s3.Bucket.objectsCollection')}
      list(objectsCollection) {c('→ List[s3.ObjectSummary]')}

    {h2('s3.Bucket.objectsCollectionManager extends s3.Bucket.objectsCollection')}    {c(f"b.objects")}

      iterator() {c('→ s3.Bucket.objectsCollection')}

    """
    _OBJECT_SUMMARY = f"""{h2('s3.ObjectSummary')}    {c(f"os = list(b.objects.all())[0]")}

      os.bucket_name
      os.key
      os.size
      os.copy_from()
      os.delete()
      os.get() {c('→ dict')}
        get()['Body'] {c('→ botocore.response.StreamingBody')}
      os.load()
      os.put()
      os.wait_until_exists()
      os.wait_until_not_exists()

    """
    _OBJECT = f"""{h2('s3.Object extends s3.ObjectSummary')}    {c(f"o = s3.Object('bucket', 'key')")}

      o.content_[encoding | length | type | disposition | language]
      o.copy()
      o.download_file()
      o.download_fileobj()
      o.upload_file()
      o.upload_fileobj()

    """

    _STREAMING_BODY = f"""{h2('botocore.response.StreamingBody')}    {c(f"body = o.get()['Body']")}

      body.close()
      body.iter_chunks() {c("→ Generator['bytes']")}
      body.iter_lines() {c("→ Generator['bytes']")}
      body.next() {c('→ bytes')}
      body.read() {c('→ bytes')}
      body.set_socket_timeout()

    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('s3')}
  {_BUCKET}
  {_OBJECTS_COLLECTION}
  {_OBJECT_SUMMARY}
  {_OBJECT}
  {_STREAMING_BODY}
  """


@syntax
def setuppy(subject=None):
    return f"""{h1(f'setup.py {i("[cmd] [subcmds] [--verbose, -v] [-dry-run, -n]")}')}
  https://setuptools.readthedocs.io/en/latest/setuptools.html#options
  {h2('install')}   {c('install everything from build directory')}
    --force (-f)    {c('overwrite any existing files')}
    --user          {c('install in user site-package (~/Library/Python/3.7/lib/python/site-packages)')}
    --root          {c('install everything relative to this alternate root directory')}

  {h2('develop')}   {c('install everything in development mode')}
    --editable (-e)         {c("Install specified packages in editable form")}
    --user                  {c('install in user site-package (~/Library/Python/3.7/lib/python/site-packages)')}
    --uninstall (-u)        {c('Uninstall this source package')}
    --upgrade (-U)          {c('force upgrade (searches PyPI for latest versions)')}
    --egg-path              {c('Set the path to be used in the .egg-link file')}
    --no-deps (-N)          {c("don't install dependencies")}
    --version               {c('Print version info and exit')}
    --site-dirs (-S)        {c('list of directories where .pth files work')}
    --build-directory (-b)  {c('download/extract/build in DIR; keep the results')}

    %bash
    # example:
    python3 setup.py develop --user --editable .
    # alternative:
    python3 -m pip install -e . --user
    /%bash

  {h2('setup()')}
    %bash
    export DISTUTILS_DEBUG=TRUE
    /%bash

    %python
    package_dir = {{'': 'lib'}}             # set 'lib' as source path. if packages = ['foo']
                                        # this promises lib/foo/__init__.py exists

    package_dir = {{'foo': 'lib'}}          # set 'lib' as source of 'foo' package. if packages = ['foo', 'foo.bar']
                                        # this promises lib/__init__.py and lib/bar/__init__.py exist

    py_modules = ['mod1', 'pkg.mod2']   # means the following exist: mod1.py, pkg/__init__.py, pkg/mod2.py

    # might need to have a release / tag in that name
    install_requires = [
      'more_termcolor @ https://github.com/giladbarnea/more_termcolor/archive/master.zip#egg=more_termcolor-1.0.0',
      'igit @ file:///home/gilad/Code/IGit#egg=igit',

      # https://stackoverflow.com/a/54794506/11842164:
      'ipdb @ git+ssh://git@github.com/giladbarnea/ipdb@v0.13.4#egg=ipdb',

      # from pdbpp source:
      "fancycompleter @ git+https://github.com/pdbpp/fancycompleter@master#egg=fancycompleter"
      ]

    # pip install -e .[dev], or pip install -e "/home/gilad/Code/MyTool[dev]", or
    # pip install -e "git+ssh://git@github.com/giladbarnea/pyinspect.git#egg=pyinspect"
    extras_require={{'dev': ['pytest', 'ipdb', 'IPython', 'semver'],

        # conditions:
        ':python_version == "2.7"': ['ipython >= 5.1.0, < 6.0.0'],
        ':python_version >= "3.4"': ['ipython >= 5.1.0'],
    
    }},

    tests_require = [ ... ]
    /%python

  {h2('Upload to pypi')}
    {c('https://switowski.com/blog/ipython-extensions-guide -> "Publishing extension on PyPI"')}
    {c('https://github.com/audreyfeldroy/cookiecutter-pypackage')}
    {c('https://github.com/cjolowicz/cookiecutter-hypermodern-python')}
    %bash
    # rm -rf dist build
    (env) pip install -U twine setuptools wheel
    (env) python setup.py sdist bdist_wheel
    (env) python -m twine upload dist/*
    /%bash
    """


@syntax
def shellcheck(subject=None):
    return f"""
  https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md#options
  
  -e CODE1[,CODE2...], --exclude=CODE1[,CODE2...]
  -s SHELL, --shell=SHELL
  -x, --external-sources
  -P, --source-path=SOURCEPATH1[:SOURCEPATH2...]      {c('paths to search for sourced files')}
  export SHELLCHECK_OPTS='--shell=bash --exclude=SC2016'
    """


@syntax
def ssh(subject=None):
    _SSH_KEYGEN = f"""{h2('ssh-keygen')} [options] [flags]
  {h3('options')}
    -l          {c('Show fingerprint of specified public key file. With -v, shows art')}
    -v[v[v]]    {c('verbose')}
    -f <filename>
    -r <hostname>       {c('Print SSHFP fingerprint resource record named hostname for specified public key file.')}
    -t <dsa | ecdsa | ecdsa-sk | ed25519 | ed25519-sk | rsa>  {c('key type to create')}
    
  {h3('ssh-keygen examples')}
    %bash
    # Create new ssh key:
    ssh-keygen
    
    # Check if ssh valid:
    ssh-keygen -l -f /Users/gilad/.ssh/id_rsa.pub
  
    # View fingerprint art to compare visually:
    ssh-keygen -lv -f ~/.ssh/known_hosts
    
    /%bash
    """
    _SSHD_CONFIG = f"""{h2('sshd_config')}
    AcceptEnv "NAME1 NAME2 NA*ME NA?ME"
    Compression[=delayed]         {c('yes | no | delayed')}
    DisableForwarding             {c('Overrides everything')}
    ExposeAuthInfo[=no]           {c('Writes temp file with auth methods and public creds (e.g. keyes)')}
    EnableSSHKeysign[=no]         {c('Enable ssh-keysign(8) during HostbasedAuthentication')}
    GatewayPorts[=no]             {c('Allow remote to connect to local forwarded ports')}
    HostbasedAuthentication[=no]  {c('Try rhosts based authentication with public key authentication')}
    PermitUserEnvironment[=no]    {c('yes | no | e.g. "LANG,LC_*". Process ~/.ssh/environment and environment= options in ~/.ssh/authorized_keys by sshd')}
    SetEnv                        {c('NAME=VALUE')}
    X11DisplayOffset[=10]         {c("Specify first display num available for sshd(8)'s X11 forwarding")}
    X11Forwarding[=no]
    X11UseLocalhost[=yes]         {c('Bind X11 forwarding server to the loopback address or to the wildcard address')}
    
    {h3('SSHD TOKEN')}
      %%    {c('A literal ‘%’.')}
      %D    {c('The routing domain in which the incoming connection was received.')}
      %F    {c('The fingerprint of the CA key.')}
      %f    {c('The fingerprint of the key or certificate.')}
      %h    {c('The home directory of the user.')}
      %i    {c('The key ID in the certificate.')}
      %K    {c('The base64-encoded CA key.')}
      %k    {c('The base64-encoded key or certificate for authentication.')}
      %s    {c('The serial number of the certificate.')}
      %T    {c('The type of the CA key.')}
      %t    {c('The key or certificate type.')}
      %U    {c('The numeric user ID of the target user.')}
      %u    {c('The username.')}
    """
    _TUNNEL = f"""{h2('Tunneling')}
    https://www.youtube.com/watch?v=N8f5zv9UUMI
    https://www.youtube.com/watch?v=aOmIqUs0fbY
    
    %bash
    # Tunnel IRC session from client to IRC server at “server.example.com”, 
    # join channel “#users”, nickname “pinky”, using the standard IRC port 6667
    ssh -f -L 6667:localhost:6667 server.example.com sleep 10
    irc -c '#users' pinky IRC/127.0.0.1
    /%bash
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('ssh')}
  {_SSH_KEYGEN}
  {_SSHD_CONFIG}
  {_TUNNEL}
  {h2('ssh')} [options...] destination [command]
    {h3('options')}
      -E <log_file>       {c('instead of to stderr')}
      -F <configfile>     {c('ignores /etc/ssh/ssh_config and defaults to ~/.ssh/config')}
      -T      {c('Disable pseudo-terminal allocation.')}
      -X      {c('ForwardX11')}
      -Y      {c('ForwardX11Trusted')}
      -R [bind_address:]port:host:hostport
      -R [bind_address:]port:local_socket
      -R remote_socket:host:hostport
      -R remote_socket:local_socket
      -R [bind_address:]port
      -t      {c('Force pseudo-terminal allocation. Can be used to execute arbitrary screen-based programs on remote machine.')}
      -g      {c('Allows remote hosts to connect to local forwarded ports.')}
      -i <identity_file>  {c('Multiple. defaults in ~/.ssh/: id_dsa, id_ecdsa, id_ecdsa_sk, id_ed25519, id_ed25519_sk and id_rsa.')}
      -l <login_name>
      -p <port>
      -f      {c('go to background just before command execution (after prompts)')}
      -n      {c('Redirects stdin from /dev/null (actually, prevents reading from stdin).')}
    
    {h3('-o OPTION')}
      {c('bind_address can also be * and localhost')}
      DynamicForward            {c('-D [bind_address:]port')}
      ForwardAgent[=no]         {c('-A | Forward connection to authentication agent (if any) to remote')}
      ForwardX11[=no]           {c('-X')}
      ForwardX11Trusted[=no]    {c('-Y | Redirect X11 connection and set DISPLAY')}
      GatewayPorts[=no]         {c('-g? | Allow remote to connect to local forwarded ports')}
      Host                      {c('Specifies real host name to log into')}
      HostKeyAlias              {c('Specifies alias instead of the real host name')}
      Hostname
      LocalForward [bind_address:]port    {c('Forward TCP port on local to specified host and port from remote')}
      LocalCommand              {c('Allow local command execution via the LocalCommand')}
      NoHostAuthenticationForLocalhost[=no]  {c('Disable host authentication for localhost (loopback addresses)')}
      PermitLocalCommand[=no]
      RemoteCommand             {c('execute on remote after connecting')}
      RemoteForward [bind_address:]port   {c('Requires GatewayPorts')}
      SendEnv                   {c('Refer to sshd_config AcceptEnv')}
      SetEnv
      VisualHostKey             {c('Show art')}
    
    {h3('SSH TOKENS')}
      %%    {c("A literal ‘%’.")}
      %C    {c("Hash of %l%h%p%r.")}
      %d    {c("Local user's home directory.")}
      %h    {c("The remote hostname.")}
      %i    {c("The local user ID.")}
      %k    {c("The host key alias if specified, otherwise the orignal remote hostname given on the command line.")}
      %L    {c("The local hostname.")}
      %l    {c("The local hostname, including the domain name.")}
      %n    {c("The original remote hostname, as given on the command line.")}
      %p    {c("The remote port.")}
      %r    {c("The remote username.")}
      %T    {c('The local tun(4) or tap(4) network interface assigned if tunnel forwarding was requested, or "NONE" otherwise.')}
      %u    {c("The local username.")}
  
    {h3('Network Information')}
      %bash
      # Public IP:
        # Windows:
        nslookup myip.opendns.com. resolver1.opendns.com
        # or: (PS)
          $wc = new-object System.Net.WebClient
          $wc.DownloadString("http://myexternalip.com/raw")
        
        # Linux:
        dig +short myip.opendns.com @resolver1.opendns.com
        # or:
          curl "http://myexternalip.com/raw"

      # Cool colors:
      ip -s -c -h a
      
      # Get originating IP inside remote:
      sudo netstat -taepn | grep -Po "\\b(\d|\.)+:22(?= .*ssh)"
        # or:
        ifconfig | awk '/inet addr/{{print substr($2,6)}}'
      
      # In host:
      ss -ant
      /%bash    

    {h3('Examples')}
      %bash
      # Create a key pair with a remote machine:
        ssh-keygen -f my_key -C "some comment"
        ssh-copy-id -i ./my_key.pub user@ip
      
      # Connect to a host on local network:
        ssh <username>@<computer-name>.local    # e.g. ssh gilad@gilad.local
        # or:
        ssh <name>@<local-port>    # e.g. ssh gilad@10.0.0.13
      
      # Scan local network for hosts: 
        # Scan .1 to .254 range:
        nmap -sn 192.168.2.1/24       # also e.g 192.168.1.0/24
        # Or:
        arp -a 
      
      # Check access to site:
        ssh -T git@bitbucket.org

      # Add ssh key:
        eval `ssh-agent`
        ssh-add -K ~/.ssh/<private_key_file>
      
      # ~/.ssh/config file:
        Host 10.100.200.6
        User root
        # Hostname example.com
        IdentityFile ~/.ssh/id_rsa_example
        IdentityFile ~/.ssh/id_rsa_example2
        IdentitiesOnly yes
      /%bash
  """


@syntax
def sshfs(subject=None):
  return f"""{h1('sshfs')}
  http://manpages.ubuntu.com/manpages/precise/man8/mount.fuse.8.html
  sudo sshfs -o allow_other,default_permissions admin@10.110.100.90:/ /mnt/u20_56
  
  {h3('default_permissions')}
    Enable permission checking, restricting access based on file mode. 
    Useful with allow_other.
  
  {h3('allow_other')}
    Don't restrict file access only to the user mounting the filesystem.
    
  {h3('allow_root')}
    File access is limited to the user mounting the filesystem and root.
    Mutually exclusive with allow_other.
  
  {h3('max_read=N')}
    Default infinite
  
  {h3('max_readahead=BYTES')}
    Default is determined by the kernel. Linux kernel <= 2.6.22 it's 131072 (128KB).
  
  {h3('max_write=BYTES')}
    In a single write operation. Default is 131072 (128KB).
  
  {h3('cache_timeout=SECONDS')}
    Default 20

  {h2('Examples')}
    %bash
    # https://superuser.com/questions/344255/faster-way-to-mount-a-remote-file-system-than-sshfs
    opts="allow_other,no_check_root,cache=yes,cache_timeout=115200,attr_timeout=115200,entry_timeout=1200,max_write=1310720,Ciphers=aes128-ctr,Compression=no"
    sudo sshfs -o "$opts" admin@10.110.100.90:/ /mnt/u20_56
    /%bash
  """
  
@syntax
def snap(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('snap')}
  {h2('help')}
    snap help <command>
    snap help --all
    
  {h2('start')} [options] <service>
    --enable      {c('set to also start at boot')}

  {h2('alias')}
    alias <existing_snap> <alias>     {c('then its available globally')}
    aliases                           {c('shows aliases')}

  {h2('run')} <pkg>

  {h2('find / search')} [options] <pkg>
    --private     {c('search private snaps')}
    --narrow      {c('only stable')}

  {h2('remove')} <pkg>    {c("keeps data. can be 'snap restore'ed")}
    --purge               {c('doesnt keep data')}

  {h2('forget')} <id> <pkg>    {c('deletes completely. cannot be undone')}

  {h2('info')} [--verbose] <pkg>

  {h2('install')} [options] <pkg>

  {h2('list')}            {c('list installed snaps')}

  {h2('refresh')} [options] <pkg>   {c('upgrades to latest ver.')}
    {c('if no pkg specified, upgrades all')}
    --channel=<channel>   {c('one of the channels below')}
    --edge
    --beta
    --candidate
    --stable
    --classic
        """


@syntax
def sqlalchemy(subject=None):
    _ENGINE = f"""{h2('engine')}
    {h3('eng.execute(object_, *multiparams, **params)')} {c('→ ResultProxy')}
      {h4('object_')} can be:
        str
        ClauseElement that's an .Executable
        FunctionElement
        .DDLElement
        .DefaultGenerator
        .Compiled

      {h4('examples')}
        %python
        conn.execute(
          table.insert(),
          {{"id":1, "value":"v1"}},
          {{"id":2, "value":"v2"}}
        )

        conn.execute(table.insert(), id=1, value="v1")

        conn.execute(
          "INSERT INTO table (id, value) VALUES (?, ?)",
          (1, "v1"), (2, "v2")
        )

        conn.execute(
          "INSERT INTO table (id, value) VALUES (?, ?)",
          1, "v1"
        )
        /%python

    eng.transaction(callable_, *args, **kwargs)
    """
    _RESULT_PROXY = f"""{h2('ResultProxy')}
    {h3('properties')}
      res.closed{c(': bool')}
      res.connection{c(': Connection')}
      res.cursor{c(': pymysql.cursors.Cursor')}
      res.is_insert{c(': bool')}
      res.lastrowid{c(': ?')}
      res.out_parameters{c(': ?')}
      res.returned_defaults{c(': ?')}
      res.returns_rows{c(': bool')}
      res.rowcount{c(': int')}

    {h3('methods')}
      res.close()
      res.fetchall() {c('→ List')}
      res.fetchmany(size=None)
      res.fetchone()
      res.first()
      res.keys() {c('→ List[str]')}
      res.last_inserted_params()
      res.last_updated_params()
      res.lastrow_has_defaults() {c('→ bool')}
      res.next()
      res.process_rows(rows)
      res.scalar()

    """
    _META = _METADATA = f"""{h2('MetaData')}
    meta = sqlalchemy.schema.MetaData()
    meta.reflect(bind=engine)
    meta.tables{c(': Dict[str, Table]')}
    """

    _TABLE = f"""{h2('Table')}
    {h3('properties')}
      t.columns{c(': Column[]')}
      t.comment{c(': str')}
      t.constraints{c(': Set[PrimaryKeyConstraint, ?]')}
      t.description{c(': str')}
      t.fullname{c(': str')}
      t.is_selectable{c(': bool')}
      t.key{c(': str')}
      t.name{c(': str')}
      t.primary_key{c(': PrimaryKeyConstraint')}
      t.selectable{c(': Table')}

    {h3('methods')}
      t.append_column(column{c(': Column')})
      t.compare(other)
      t.count(functions, whereclause=None, **params)
      t.create(bind=None, checkfirst=False)
      t.delete(dml, whereclause=None, **kwargs)
      t.drop(bind=None, checkfirst=False)
      t.exists(bind=None)
      t.get_children(column_collections=True, schema_visitor=False, **kw)
      t.insert(dml, values=None, inline=False, **kwargs) {c('→ dml.Insert')}
      t.join(right, onclause=None, isouter=False, full=False)
      t.lateral(name=None)
      t.outerjoin(right, onclause=None, full=False)
      t.select(whereclause=None, **params) {c('→ selectable.Select')}
      t.update(dml, whereclause=None, values=None, inline=False, **kwargs)
    """

    _COLUMN = f"""{h2('Column')}
    {h3('properties')}
      c.table{c(': Table')}
      c.type{c(': sqlalchemy.dialects.mysql.types.<FOO>')}
      c.description{c(': str')}
      c.foreign_keys{c(': Set')}
      c.is_clause_element{c(': bool')}
      c.is_selectable{c(': bool')}
      c.key{c(': str')}
      c.nullable{c(': bool')}
      c.primary_key{c(': bool')}
      c.supports_execution{c(': bool')}
      c.unique{c(': bool')}

    {h3('methods')}
      c.append_foreign_key(fk)
      c.asc()
      c.between(cleft, cright, symmetric=False)
      c.bool_op(opstring:str, precedence=0)
      c.cast(type_)
      c.collate(collation)
      c.compare(other, use_proxies=False, equivalents=None, **kw)
      c.concat(other)
      c.contains(other, **kwargs)
      c.copy(**kw)
      c.desc()
      c.distinct()
      c.endswith(other, **kwargs)
      c.get_children(schema_visitor=False, **kwargs)
      c.ilike(other, escape=None)
      c.in_(other)
      c.is_(other)
      c.is_distinct_from(other)
      c.isnot(other)
      c.isnot_distinct_from(other)
      c.like(other, escape=None)
      c.match(other, **kwargs)
      c.notilike(other, escape=None)
      c.notin_(other)
      c.notlike(other, escape=None)
      c.nullsfirst()
      c.nullslast()
      c.op(opstring:str, precedence=0, is_comparison=False, return_type=None)
      c.operate(op, other, **kwargs)
      c.startswith(other, **kwargs)
      c.unique_params(*optionaldict, **kwargs)

    """

    _PRIMARY_KEY_CONSTRAINT = f"""{h2('PrimaryKeyConstraint')}

    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('sqlalchemy')}
  {_ENGINE}
  {_RESULT_PROXY}
  {_META}
  {_TABLE}
  {_COLUMN}
    """

@syntax
def sphinx(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('sphinx')}
    {c('https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html')}
    {h2('Sections')}
      Args (alias of Parameters)
      Arguments (alias of Parameters)
      Attributes
      Example
      Examples
      Keyword Args (alias of Keyword Arguments)
      Keyword Arguments
      Methods
      Note
      Notes
      Other Parameters
      Parameters
      Return (alias of Returns)
      Returns
      Raises
      References
      See Also
      Todo
      Warning
      Warnings (alias of Warning)
      Warns
      Yield (alias of Yields)
      Yields        
    
    {h2('Examples')}
      `PEP 484`_ is a good link.
      
      Args:
          param1 (int): The first parameter.
          param2 (:obj:`str`, optional): The second parameter. Defaults to None.
              Second line of description should be indented.
          *args: Variable length argument list.
          **kwargs: Arbitrary keyword arguments.
  

      Other Parameters:
          param3 (int): description
          param4 (str): 
          ...
  

      Keyword Args:
          key1 (int): description 
          key2 (int): description


      Literal blocks::

          $ python example_google.py


      Returns:
          bool: True if successful, False otherwise.

          
      Todo:
          * For module TODOs
          * You have to also use ``sphinx.ext.todo`` extension


      .. _Google Python Style Guide:
          http://google.github.io/styleguide/pyguide.htm

      .. _PEP 484:
          https://www.python.org/dev/peps/pep-0484/         
        """
def tar(subject=None):
    return f"""{h1('tar')}
  -x        {c('extract')}
  -f --file={c('file')}
  -t        {c('list content of archive')}
  -v        {c('verbose')}
  -C <PATH> {c('different destination')}
    """

@syntax
def tree(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('tree')}
  {h2('filtering')}
    -P <PATTERN> {c('List only files that match pattern')}
      --ignore-case
      --matchdirs      {c('Include directory names in pattern matching')}
      --filelimit <N>  {c("Don't descend dirs with more than N files")}
    -I <PATTERN> {c('Do not list files that match pattern')}
    -a All files are listed (including hidden)
    -d dirs only
    -L descend only <level>
    -l Follow symbolic links like directories
    -R Rerun tree when max dir level reached ?

  {h2('output')}
    -h    {c('Human size')}
    -p Print the protections for each file
    
    {h3('sorting')}
    -v    {c('alphanumerically by version')}
    -t    {c('last modification time')}
    -c    {c('last status change time')}
    --dirsfirst
    --sort <name|version|size|mtime|ctime>
  """
@syntax
@alias('ts')
def typescript(subject=None):
    _SYNTAX = f"""{h1('syntax')}
    {h2('3.7')}
      {h3('Optional Chaining')}
        %ts
        let x = (foo === null || foo === undefined) ? undefined : foo.bar.baz();
        // is the same as:
        let x = foo?.bar.baz();
        
        if (json && json.address && json.address.country === 'US')
        // is the same as:
        if (json?.address?.country === 'US')
        
        // more examples:
        arr?.[0]
        log?.('Some log message');
        /%ts
    
      {h3('Nullish Coalescing')}
        %ts
        let x = foo ?? bar();
        // is the same as:
        let x = (foo !== null && foo !== undefined) ? foo : bar();
        /%ts

    {h2('3.8')}
      {h3('Type-only imports / exports')}
        %ts 2
        import type {{ SomeThing }} from "./some-module.js";
        export type {{ SomeThing }};
      
      {h3('"importsNotUsedAsValues" in tsconfig.json')}
        · "remove": default (like past behavior)
        · "preserve": don't remove
        · "error": don't remove, but error when a value import is only used as a type
      
      {h3('#hardPrivacy')}
        · uniquely scoped to containing class ("strong" this)
        · accessing on any other type then `this` throws a TypeError
        · inaccessible outside the class (new C().#foo → SyntaxError, new C()["#foo"] → undefined)
      
      {h3('export * as ns')}
        %ts
        // only if target is >= es2020
        export * as utilities from "./utilities.js";
        
        // is the same as:
        import * as utilities from "./utilities.js";
        export {{ utilities }};
        /%ts
      
      {h3('top level await')}
        · only works at top level of a module   {c('file must have import or export')}
        · target >= es2017
        · module is esnext or system
      
      {h3('"watchOptions" in tsconfig.json')}
      
      {h3('"assumeChangesOnlyAffectDirectDependencies" in tsconfig.json')}
        avoid rechecking/rebuilding all possibly-affected files, and only recheck/rebuild
        files that have changed as well as files that directly import them.
        
        Given import order:
        fileA.ts <- fileB.ts <- fileC.ts <- fileD.ts
      
        Change in fileA by default would re-check all files, new behavior re-checks only A and B
  
    {h2('3.9')}
      {h3('// @ts-expect-error')}
      
      {h3('CommonJS require() support')}
        https://github.com/microsoft/TypeScript/pull/37027
  
    {h2('4.0')}
      {h3('Variadic Tuple Types (solves "Death By a Thousand Overloads" issue')}
        https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-0.html#variadic-tuple-types
        %ts
        function tail<T extends any[]>(arr: readonly [any, ...T]) {{
            const [_ignored, ...rest] = arr;
            return rest; // const rest: [...T]
        }}

        // another example:
        type Arr = readonly any[];
        
        function concat<T extends Arr, U extends Arr>(arr1: T, arr2: U): [...T, ...U] {{
            return [...arr1, ...arr2];
        }}
        /%ts
    
      {h3('...rest anywhere in tuple')}
        %ts
        type Strings = [string, string];
        type Numbers = [number, number];
        
        // [string, string, number, number, boolean]
        type StrStrNumNumBool = [...Strings, ...Numbers, boolean];
        /%ts
      
      {h3('Labeled Tuple Elements')}
        %ts
        // Examples:
        type Range = [start: number, end: number];
        type Foo = [first: number, second?: string, ...rest: any[]];
        function foo(...args: [string, number]): void {{ }}
        /%ts
    
      {h3('catch(e: unknown) { ... }')}
  
    {h2('4.1')}
      {h3('Template Literal Types')}
        %ts
        // type Greeting = "hello world"
        type World = "world";
        type Greeting = `hello ${{World}}`;
        
        // type SeussFish = "one fish" | "two fish" | "red fish" | "blue fish"
        type Color = "red" | "blue";
        type Quantity = "one" | "two";
        type SeussFish = `${{Quantity | Color}} fish`;
        /%ts
      
        {h4('Dynamic Type Creation: example 1')}
        %ts
        type PropEventSource<T> = {{
            on(eventName: `${{string & keyof T}}Changed`, callback: () => void): void;
        }};
        declare function makeWatchedObject<T>(obj: T): T & PropEventSource<T>;
        
        let person = makeWatchedObject({{
            firstName: "Homer",
            age: 42, // give-or-take
            location: "Springfield",
        }});
        
        person.on("firstNameChanged", () => {{
            console.log(`firstName was changed!`);
        }});
        /%ts

        {h4('Dynamic Creation: example 2')}
        %ts
        type PropEventSource<T> = {{
            on<K extends string & keyof T>
                (eventName: `${{K}}Changed`, callback: (newValue: T[K]) => void): void;
        }};
        
        // newName: string (actually `typeof person.firstName`)
        person.on("firstNameChanged", newName => {{
            console.log(`new name is ${{newName.toUpperCase()}}`);
        }});
        
        // newAge: number (actually `typeof person.age`)
        person.on("ageChanged", newAge => {{
            if (newAge < 0)
                ...
        }})
        /%ts
      
      {h3('Uppercase, Lowercase, Capitalize, Uncapitalize')} Type Aliases

      {h3('Key Remapping in Mapped Types')}
        %ts
        type MappedTypeWithNewKeys<T> = {{
            [K in keyof T as NewKeyType]: T[K]
            
            // OR:
            
            [K in keyof T as `get${{Capitalize<string & K>}}`]: () => T[K]
        }}
        /%ts
      
      {h3('Recursive Conditional Types')}
        %ts
        type ElementType<T> = T extends ReadonlyArray<infer U> ? ElementType<U> : T;
      
        function deepFlatten<T extends readonly unknown[]>(x: T): ElementType<T>[]
        /%ts
      
    {h2('Misc')}
      %ts
      interface Person {{
          name: string;
          age: number;
      }}
      
      // {{ K:"K" for K in T }}
      type PropertiesAndTheirNames<T> = {{ [ K in keyof T ]: K }}
      PropertiesAndTheirNames<Person>  // {{ name: "name", age: "age" }}
      
      // [ K for K in T ]
      // More precisely:
      // [ {{ K:"K" }}[K] for K in T ]
      type PropertyNames<T> = {{ [K in keyof T]: K }}[keyof T];
      PropertyNames<Person>  // "name" | "age"
      
      // {{ K:"K" for K in T if T[K] extends number }}
      type NumberPropertiesAndTheirNames<T> = {{ [ K in keyof T ]: T[K] extends number ? K : never }}
      NumberPropertiesAndTheirNames<Person>  // {{ age: "age" }}
      
      // {{ K for K in T if T[K] extends number }}
      // More precisely:
      // [ {{ K:"K" }}[K] for K in T if T[K] extends number ]
      type NumberPropertyNames<T> = {{ [ K in keyof T ]: T[K] extends number ? K : never }}[keyof T]
      NumberPropertiesAndTheirNames<Person>  // "age"
      /%ts
    """
    _TSCONFIG = f"""{h2('tsconfig.json')}
    {h4('"files"')}
      List of rel / abs file paths
      Trumps "exclude" even if specified there

    {h4('"include"')}
      "files" specified → union of both.
      "outDir" is excluded as long as "exclude" is not specified
      Files in "include" can be filtered with "exclude".

    {h4('"exclude"')}
      When not specified, defaults to node_modules, bower_components, jspm_packages and <outDir>.
      If B.ts is references by A.ts, B.ts can't be excluded unless A.ts is also excluded.
      Compiler doesn't include possible outputs (eg index.d.ts / index.js).

    {h4('"types" / "typeRoots"')}
      By default all **/node_modules/@types are included, also recursively.
      A types package is a folder with a file called index.d.ts or a folder with a package.json that has a types field.
      Folders under "types" must exist under ./node_modules/@types. Disables recursive inclusion. Example: "types" : ["node"].
      "typeRoots" disables ./node_modules/@types. Good for local typing dirs. Example: "typeRoots" : ["./typings"]

    {h4('"module"')}
      If specified "outFile", only "AMD" and "System" allowed.
      "ES6" and "ES2015" allowed only when "target" : "ES5" or lower.

    {h4('"paths"')}
      Map paths to {i("baseUrl")}. (baseUrl: "." means where tsconfig.json is).
      The mapped path is appended to {i("baseUrl")} when it's a non-relative name.
        This means {i("folder1/file2")} → {i("baseUrl/folder1/file2")}
      Values in arrays are fallbacks; if file doesn't exist, move to next.
      Examples:
        "jquery" : ["node_modules/jquery/dist/jquery"]. This means importing "jquery" actually imports the long path.
        "*" : ["*"]   {i("<moduleName> → <baseUrl>/<moduleName>")}
        "*" : ["generated/*"]   {i("<moduleName> → <baseUrl>/generated/<moduleName>")}
    """
    _TYPES = f"""{h1('Utility Types')}
    {c('https://www.typescriptlang.org/docs/handbook/utility-types.html')}
    %ts 2
    interface MyI {{ a : "hello" , b : "goodbye" }}
    type MyT = "a" | "b"
  
    {h3('Diff< MyT, "a" | "c" | "f" >')} // "b"

    {h3('Filter< MyT, "a" | "c" | "f" >')} // "a"

    {h3("Omit, Pick")}
      %ts 2
      Omit< MyI, "a" > // {{ b : "goodbye" }}
      Pick< MyI, "a" > // {{ a : "hello" }}
  
    {h3("Exclude, Extract")}
      %ts 2
      Exclude< MyT, "a" > // "b"
      Extract< MyT, "a" > // "a"
  
    {h3("Record< MyT, MyI >")} // {{ a : MyI, b : MyI }}
    
    {h3('Examples')}
      %ts
      interface Part {{
          name: string;
          subparts: Part[];
          updatePart(newName: string): void;
      }}
      
      
      // The [keyof T] makes it a list of 
      // [ K for K in T.keys() if T[K] extends Function ]
      type FunctionPropertyNames<T> = {{ [ K in keyof T ]: T[K] extends Function ? K : never }}[ keyof T ];
      
      FunctionPropertyNames<Part> // "updatePart"
      
      // {{ K:V for K,V in T.items() if T[K] extends Function }}
      // More precisely:
      // {{ K:V for K,V in T.items() if K in [ K for K in T.keys() if T[K] extends Function ] }}
      type FunctionProperties<T> = Pick<T, FunctionPropertyNames<T>>;
      
      FunctionProperty<Part> // {{ updatePart: (newName: string) => void }}
      
      /%ts
    
    {h3('Parameters<some function>')}
    
    {h3('ConstructorParameters<ErrorConstructor>')}
      {c('maybe this is relevant?: type Constructor = new (...args: any[]) => {{}}')}
      {c('https://www.typescriptlang.org/docs/handbook/mixins.html#how-does-a-mixin-work')}
    
    {h3('ReturnType<some function>')}
    
    {h3('InstanceType<some class>')}
    
    {h3('ThisParameterType<some function>')}
      %ts
      // Extracts the type of the this parameter for a function type, or unknown if the function type has no this parameter.
      function toHex(this: Number) {{ return this.toString(16) }}
      function numberToString(n: ThisParameterType<typeof toHex>) {{ return toHex.apply(n) }}
      /%ts
      
    {h3('OmitThisParameterType<some function>')}
      %ts
      // In absence of this, returns the type of <some function>. Erased: Generics, and all overloads except last.
      function toHex(this: Number) {{ return this.toString(16) }}
      function numberToString(n: ThisParameterType<typeof toHex>) {{ return toHex.apply(n) }}
      /%ts
    
    {h3('ThisType<Type>')}
      %ts 1
      # Requires --noImplicitThis. Marker for a contextual this type
    
    {h3('infer')}
      %ts
      type ReturnType<T> = T extends (...args: any[]) => infer R ? R : any;
      
      type Unpacked<T> = T extends (infer U)[] ? U      // array of U? → U
        : T extends (...args: any[]) => infer U ? U     // function that returns U? → U
        : T extends Promise<infer U> ? U                // Promise of U? → U
        : T;                                            // None of the above? → as-is

      // mult. candidates for type in co-variant positions → union
      type CoVariant<T> = T extends {{ a: infer U; b: infer U }} ? U : never;
      CoVariant< {{ a: string; b: string }} >       // string
      CoVariant< {{ a: string; b: number }} >       // string | number
      
      // "" in contra-variant positions → intersection
      type ContraVariant<T> = T extends {{ a: (x: infer U) => void; b: (x: infer U) => void }} ? U : never;
      ContraVariant< {{ a: (x: string) => void; b: (x: string) => void }} >     // string
      ContraVariant< {{ a: (x: string) => void; b: (x: number) => void }} >     // never (string & number = never)
      /%ts
      
    """

    _IMPORT = _EXPORT = _MODULES = _NAMESPACES = f"""{h1('import / export / modules / namespaces')}
    {c('https://www.typescriptlang.org/docs/handbook/modules.html')}
    {c('https://www.typescriptlang.org/docs/handbook/namespaces.html')}
    {c('https://www.typescriptlang.org/docs/handbook/namespaces-and-modules.html')}
    {c('https://www.typescriptlang.org/docs/handbook/module-resolution.html')}
    
    {h3('namespace / module')}
      {h4('just namespace')}
        %ts
        // mammals.ts
        export namespace Mammals {{
          export class Dog {{ constructor(...args) {{ /* code */ }} }}
         }}
        // index.ts
        import {{ Mammals }} from "./mammals";
        let dog = new Mammals.Dog();
        /%ts
        
      {h4('module > namespace')}
        %ts
        // mammals.ts
        export module mammals_mod {{
          export namespace Mammals {{
            export class Dog {{ constructor(...args) {{ /* code */ }} }}
           }}
        }}
        // index.ts
        import {{ mammals_mod }} from "./mammals";
        let dog = new mammals_mod.Mammals.Dog();
        /%ts
      
    
    {h3('import / export')}
      {h4('standard export')}
        %ts
        // foo.ts
        export class Foo {{ }}
        // is the same as:
        class Foo {{ }}
        export {{ Foo }}
        
        // to import:
        import {{ Foo }} from "./foo"
        /%ts
      
      
      {h4('export default')}
        %ts
        // foo.ts
        export default class Foo {{ }}
        // is the same as:
        class Foo {{ }}
        export default Foo
        
        // to import:
        import Foo from "./foo"
        /%ts
      
      
      {h4('export =')}
        %ts
        // log.ts
        export = Logger
        // index.ts
        import Logger = require("./log")
        /%ts
    
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Typescript')}
  {_TSCONFIG}
  
  {_SYNTAX}
  
  {_TYPES}
  
  {_IMPORT}
  """


@syntax('friendly')
def vagrant(subject=None):
    _ENV = f"""{h2('Environment Variables')}
    {c('https://www.vagrantup.com/docs/other/environmental-variables')}
    VAGRANT_WSL_ENABLE_WINDOWS_ACCESS="1"    {c('Necessary in WSL')}
    VAGRANT_IS_HYPERV_ADMIN
    VAGRANT_VAGRANTFILE    {c('Specify to use a different file than default Vagrantfile')}
    """
    _CMD = f"""{h2('commands')}
    {h3('box')} <subcmd> [args]
      add
      list
      outdated
      prune
      remove
      repackage
      update
    {h3('destroy')} [-f]
    {h3('global-status')}
    {h3('halt')} [name|id]
       Shut down running machine Vagrant is managing.
       -f
    {h3('init')} [options] [name [url]]
    {h3('plugin')} <cmd> [args]
      expunge
      install
      license
      list
      repair
      uninstall
      update
    {h3('provision')}
    {h3('push')}
    {h3('rdp')}
    {h3('reload')} [name|id]
      The equivalent of running a halt followed by an up.
      -f
      --provision                   {c("Force the provisioners to run.")}
      --provision-with X[,Y[,Z]]    {c("Run only given provisioners. e.g, '--provision-with shell' runs only ':shell'.")}
    {h3('resume')}
    {h3('share')}
    {h3('snapshot')} <subcmd> [args]
      delete
      list
      pop
      push
      restore
      save
    {h3('ssh')} [options] [name|id] [-- extra ssh args]
      -c, --command <COMMAND>    {c('Execute an SSH command directly')}
      -p, --plain       {c('Leaves authentication up to user')}
      
      {h4('examples')}
        %bash
        vagrant ssh -c "pgrep chrome"
        # is equivalent to:
        vagrant@127.0.0.1 -p 2222 -o LogLevel=FATAL -o Compression=yes -o DSAAuthentication=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i C:/Users/CR-GBARN-HEROLO/dev/allotsecure/vagrant/.vagrant/machines/default/virtualbox/private_key -t bash -l -c 'pgrep chrome'
        /%bash
    {h3('ssh-config')}
    {h3('status')}
    {h3('suspend')}
    {h3('up')} [name|id]
  """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('vagrant')}
  {_ENV}
  {_CMD}
    """


def vim(subject=None):
    _MODES = f"""{h2('Modes')}
    normal → insert    A, a, C, I, i, O, o, S, s
    normal → command   :
    normal → command   v
    any → normal       Esc
    """
    _MOVEMENT = f"""{h2('Movement')}
    Keeps you in normal mode.
    {h3('Character   Motion         Units')}
    h . . . . . left . . . . . characters

    l . . . . . right. . . . . characters
    j . . . . . down . . . . . lines
    k . . . . . up . . . . . . lines
    $ . . . . . forward  . . . lines {c('(move to end of line)')}
    ^ . . . . . forward  . . . lines {c('(first non-blank char of line)')}
    0 . . . . . backward . . . lines {c('(first char of line)')}

    b[count]. . backward . . . words
    B[count]. . backward . . . words
    w[count]  . forward  . . . words
    W[count]  . forward  . . . WORDS
    e . . . . . forward  . . . Forward to the end of word [count] inclusive
    E . . . . . forward  . . . Forward to the end of WORD [count] inclusive

    t<char> . . forward  . . . Till before [count]'th occurrence of <char> to the right
    T<char> . . backward . . . Till before [count]'th occurrence of <char> to the left
    f<char> . . forward  . . . To [count]'th occurrence of <char> to the right
    F<char> . . backward . . . To [count]'th occurrence of <char> to the left

    ;  . . . . . . . . . . . . Repeat latest f, t, F or T [count] times
    ,  . . . . . . . . . . . . Repeat latest f, t, F or T [count] times in opposite direction

    < . . . . . backward . . . paragraphs
    > . . . . . forward  . . . paragraphs
    
    ctrl-d . .  down . . . . . 1/2 screen
    ctrl-u . .  up . . . . . . 1/2 screen
    ctrl-b . .  backward . . . 1/2 screen
    ctrl-f . .  forward  . . . 1/2 screen
    """
    _MOVEMENT = re.sub(r'(?<=[^.])(\. )+',lambda match:black(match.group()), _MOVEMENT)
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('vim')}
  {c('https://factorpad.com/tech/vim-cheat-sheet.html')}
  {c('https://www.fprintf.net/vimCheatSheet.html')}
  Command structure:    {i('[count][operator]motion')}

  {h2('Counts')}
    A count requires an operator and / or a motion.
    1-9 are normal counts; 0 moves cursor to first col of line

  {_MODES}
  {h2('Operators')}
    c     {c('Change')}
    d     {c('Delete')}
    g~    {c('Swap case')}
    gu    {c('To lowercase')}
    gU    {c('To uppercase')}
    y     {c('Yank (copy)')}
    p     {c('Paste')}
    u     {c('Undo')}
    <     {c('Shift left')}
    >     {c('Shift right')}

  {_MOVEMENT}

  {h2('Insertion')}
    i    {c('Insert text before the cursor')}
    I    {c('Insert text before the first character in the line')}
    a    {c('Append text after the cursor')}
    A    {c('Append text at the end of the line')}
    o    {c('Insert new command line below the current one')}
    O    {c('Insert new command line above the current one')}
  
  {h2('Delete and Insert')}
    ctrl-h       {c('While in Insert mode: delete character before the cursor')}
    ctrl-w       {c('While in Insert mode: delete word before the cursor')}
    d<motion>    {c('Delete text that <motion> moves over')}
    dd           {c('Delete line')}
    D            {c('Delete characters under the cursor until the end of the line')}
    c<motion>    {c('Delete <motion> text and start insert')}
    cc           {c('Delete line and start insert')}
    C            {c('Delete to the end of the line and start insert')}
    r<char>      {c('Replace the character under the cursor with <char>')}
    R            {c('Enter replace mode: Each character replaces existing one')}
    x            {c('Delete count characters under and after the cursor')}
    X            {c('Delete count characters before the cursor')}
  
  {h2('Examples')}
    yiw    {c('yank current word (excluding surrounding whitespace)')}
    yaw    {c('yank current word (including leading or trailing whitespace)')}
    ytx    {c('yank from the current cursor position up to and before the character (Til x)')}
    yfx    {c('yank from the current cursor position up to and including the character (Find x)')}
    yTx    {c('yank backward up to character')}
    yFx    {c('backward through character')}
  
  {h2('Registers')}
    :h registers    {c('help')}
    "*              {c('system clipboard; so `"*y$` copies to line end to sys clpbrd, `"*p` pastes')}
  """

@syntax
def vipe(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('vipe')}
  {h3('cat')}
    %bash
    echo "hello world" > hello.txt
    cat hello.txt | vipe | $SHELL   # or just "... | sh"
    # or:
    cat hello.txt | vipe | xargs -I % $SHELL -c "%"
    /%bash
    {i('hello world')}
  
  {h3('?')}
    %bash 1
    vipe <&- | $SHELL
  
  {h3('Pipe to stdin')} (is it really stdin?)
    %bash
    : | vipe | $SHELL
    # or:
    : | vipe | xargs -I % $SHELL -c "%"
    # or:
    vipe < /tmp/scratch.sh | $SHELL
    /%bash
  
  {h3('Load to variable')}
    %bash 2
    cmd=$(echo -n "$line" | vipe)
    eval "$cmd"
    """
@alias('wmc')
def wmctrl(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('wmctrl')} {i('[OPTION] ACTION <WIN> ...')}
  {h2('Examples')}
    wmc -lGxp                 {c(f'full list')}
    wmc -iR 0x0620019c        {c(f'Focus this HEXID')}
    wmc -iR 83886085          {c(f'Focus this WID')}
    wmc -r :SELECT: -b 'toggle,above'
  
  {h2('Options')}
    -i                         {c(f'<[H]WID> wid (e.g. "100901473") or hex. xdt getters or wmc -l 0th col')}
    -F                         {c(f'<WIN CLS or TITLE> exact string (case sensitive)')}
    -x                         {c(f'<WIN CLS> (case insensitive)')}
    -u                         {c(f'override auto-detection (force UTF-8 mode)')}
    -v                         {c(f'verbose')}
    {h3('-l')}                         {c('list')}
    {c('| HEX WID | DESK ID | PID | X | Y | W | H | WIN CLS | TITLE |')}
      -G                       {c('Geometry')}
      -x                       {c('Class name')}
      -p                       {c('PID (e.g. "10695")')}
  
  {h2('Actions')} {i('ACTION <[H]WIN>')} {c('[(:ACTIVE:|:SELECT:)]')}
    -R                         {c('Move <[H]> to the current desktop, raise and give it focus')}
    -a                         {c("Switch to <[H]>'s desktop, raise and give it focus")}
    -c                         {c('close gracefully')}

    {h3('-r <[H]WIN>')}               {c('specify target window for ACTION')}
      -e '0,3840,0,-1,-1'     {c('gravity, x, y, w, h')}
      {h4('-b (remove|add|toggle),<PROP1>[,<PROP2>]')}  {c('where PROP can be')}
        modal
        sticky
        maximized_vert
        maximized_horz,
        shaded
        skip_taskbar
        skip_pager
        hidden
        fullscreen
        above     {c('always on top')}
        below
    """


def wolfram(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        f"""{h1('Wolfram')}
    https://reference.wolfram.com/language/guide/GroupTheory.html

    """


def xclip(subject=None):
    return f"""{h1('xclip')}
  -i, -in       {c('from stdin or files (default)')}
  -o, -out      {c('print selection to stdout, e.g "xclip -o -selection clipboard"')}
  -d, -display  {c('e.g "localhost:0". defaults to $DISPLAY')}
  -selection (primary|secondary|clipboard)  {c('XA_PRIMARY (default) | XA_SECONDARY | XA_CLIPBOARD')}
    """


@alias('xdt')
def xdotool(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('xdotool')}
  https://gitlab.com/cunidev/gestures/wikis/xdotool-list-of-key-codes

  {h2('Getters')}
    getactivewindow {c(': WID → 98566151')}
    getwindowfocus [-f] {c(': WID → 98566151. Prints currently focused window.')}
    getwindowname <WID> {c(': str → "MyTool - myman.py"')}
    getwindowpid <WID> {c(': PID → 9779')}
    selectwindow {c(': WID → 98566151')}

    getwindowgeometry [--shell] [window] {c('x, y, width, height, screen num. --shell suitable for eval')}
    getdisplaygeometry
      
    get_num_desktops
    get_desktop_viewport [--shell]
    get_desktop
    get_desktop_for_window [window]

  {h2('search')} {c('[options] REGEXP → WID ("71303175")')}
    --class
    --classname
    --name
    {c('default tries all three')}
    --maxdepth <N> {c('default infinite = -1')}
    --onlyvisible
    --screen <N>
    --desktop <N>
    --limit <N> {c('break search after N results')}
    --shell {c('print results as shell array WINDOWS=( ... )')}
    --all {c('require all conditions to be true')}
    --any {c('require any condition to be true (default)')}
    --sync {c('wait until search result is found')}

  {h2('Setters')}
    windowactivate <[H]WID>
      
    windowclose
      
    windowfocus [--sync] [window] (vs raise?)
      
    windowkill [window]
      
    windowmap [--sync] [window]
      
    windowminimize [--sync] [window]
      
    windowmove [options] [window] <X> <Y>
      xdotool getactivewindow windowmove x 100
      --relative
      --sync
      
    windowraise [window] (vs focus?)
      
    windowreparent [source_window] <destination_window>
      Make source child of destination
      
    windowsize [options] [window] <width> <height>
      --usehints
      --sync
      
    windowunmap [--sync] [WID=%1]
      No longer appears on screen
      
    set_window [options] [WID=%1]
      --name <name>         {c('WM_NAME')}
      --icon-name <name>    {c('WM_ICON_NAME')}
      --role <role>         {c('WM_WINDOW_ROLE')}
      --classname <name>    {c('not the window class')}
      --class <class>       {c('not the window class name')}
      --overrideredirect <value>
        
    set_num_desktop <N>
    set_desktop_viewport <x> <y>
    set_desktop [--relative] <N>
    set_desktop_for_window [window] <N>

  {h2('Actions')}
    {h3('Mouse')}
      {h4('click')} [options] <button>
        {c('mousedown followed by mouseup after 12ms delay')}
        button              {c('1: left, 2: middle, 3: right, 4: whlup, 5: whldown')}
        --clearmodifiers
        --repeat <repeat>   {c('default 1.  for dbl-click: `--repeat 2`')}
        --delay <ms>        {c('ignored unless --repeat > 1')}
        --window <WID>      {c('default %1')}

      {h4('mousedown')} ...
      {h4('mouseup')} ...

      {h4('mousemove')} [options] <X> <Y> or 'restore'
        --window <WID>
        --screen <SCREEN>
        --polar
        --clearmodifiers
        --sync

      {h4('mousemove_relative')} [options] <X> <Y>

      {h4('getmouselocation')} [--shell]
        --shell             {c('X Y SCREEN=0 WINDOW=16777250')}
        
      {h4('behave_screen_edge')} <where> <command>
        where               {c('left, top-left, top, top-right, right, bottom-right, bottom, bottom-left')}
        xdotool behave_screen_edge bottom-left search --class google-chrome windowactivate

    {h3('Keyboard')}
      {h4('key')} {c(f'[--window WID]')} {c(f'[--delay ms=12]')} {c(f'[--clearmodifiers]')}
        {c('"alt+r", "Control_L+J", "ctrl+alt+n", BackSpace, XF86Forward, Return')}
        xdt key F2
        xdt key Aacute
        xdt key ctrl+l BackSpace
        {c("Send ctrl+c to all windows matching title 'gdb':")}
        xdt search --name gdb key ctrl+c

      {h4('keydown')} ...

      {h4('keyup')} ...

    {h3('type')} {c(f'[--window WID]')} {c(f'[--delay ms]')} {c(f'[--clearmodifiers]')}
      xdt type 'Hello world!'

  {h2('behave')} <window> <action> <command> ...
    {h3('Examples')}
      {c('Print cursor location on mouse enter to any visible window')}
      xdotool search --onlyvisible . behave %@ mouse-enter getmouselocation

      {c('Print window title and pid whenever an xterm gets focus')}
      xdotool search --class xterm behave %@ focus getwindowname getwindowpid

      {c('Emulate focus-follows-mouse')}
      xdotool search . behave %@ mouse-enter windowfocus
      
    {h3('Events')}
      mouse-enter
      mouse-leave
      mouse-click     {c('when released')}
      focus
      blur

  {h2('exec')} [--sync]
    xdotool search --onlyvisible terminator behave %@ mouse-enter exec echo hi
    
  {h2('sleep')} <sec>
    xdotool sleep 0.4
    """


def xonsh(subject=None):
    envstr = '{...}'
    _ENVIRONMENT = f"""{h2('environment')}
    {h3('Environment Object')}
      >>> __xonsh__.env {c('or')} ${envstr}

      >>> 'HOME' in ${envstr}
      {c('True')}

      >>> ${envstr}.help('XONSH_DEBUG')

      {c('tempor. change env vars:')}
      >>> with ${envstr}.swap(SOMEVAR='foo'):
      >>>     echo $SOMEVAR
      {c('foo')}

    {h3('Lookup')}
      >>> x = 'HOME'
      >>> ${{x}}
      {c("'/home/gilad'")}

      >>> print(x)
      {c('HOME')}

    {h3('Captured subprocess')}
      >>> dirs = $(ls)
      >>> type(dirs)
      {c('str')}

      >>> dirs = !(ls)
      >>> type(dirs)
      {c('xonsh.__amalgam__.CommandPipeline')}

      >>> bool(!(ls nowhere))
      {c('False')}

      {h4('"Escaping" xonsh')}
        >>> echo '${{'

      {h4('Iteration')}
        >>> for d in !(ls){c('.itercheck()')}:
        >>>     ...

      {h4('Variable injection')}
        >>> codedir = 'Code'
        >>> res = $(echo $HOME/@(codedir))
        >>> res
        {c(f"'/home/gilad/Code/{linebreak}'")}

      {h4('Uncaptured subprocesses')}
        >>> x = $[ls -l] {c('or ![ls -l]')}
        {c('bin boot cdrom dev ...')}
        >>> x is None
        {c('True')}

    {h3('Python evaluation')}
      >>> x, y = 'xonsh', 'party'
      >>> echo @(x + ' ' + y)
      {c('xonsh party')}
      >>> echo @([42, 'yo'])
      {c('42 yo')}
      >>> echo "hello" | @(lambda a, s=None: s.read().strip() + " world\\n")
      {c('hello world')}
      >>> @(['echo', 'hello', 'world'])
      {c('hello world')}

    {h3('Python evaluation')}
      >>> xontrib load abbrevs
      >>> abbrevs['gst'] = 'git status'
    continue here:
    https://xon.sh/tutorial.html#python-evaluation-with
    """

    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('xonsh')}

  {_ENVIRONMENT}
    """


def xvkbd(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return rf"""{h1('xvkbd')}
  {c('http://xahlee.info/linux/linux_show_keycode_keysym.html')}
  -no-repeat            {c('even if key is depressed long time (default: on)')}
  -true-keypad          {c('use XK_KP_1 instead of XK_1')}
  -secure               {c('Disable invocation of external commands')}
  -modifiers MODS       {c('e.g -modifiers shift,control,meta,alt. send modifiers only while sending chars')}
  {h2('-text')}
    \r - Return
    \t - Tab
    \b - Backspace
    \e - Escape
    \d - Delete
    \{{keysym}}           {c(f'e.g {backslash}{{Left}}. process in more primitive matter.')}
                          {c('Control_L, Meta_L')}
                          {c(f'{backslash}{{+keysym}}, {backslash}{{-keysym}} for press and release')}
    \D<digit> - delay digit * 100 ms
    {h3('mouse')}
      \x<val>, \y<val> - move mouse pointer
                -<val> +<val> for relative
      \m<digit>     mouse click
    {h3('modifiers')}
      \S - Shift    {c(f'sometimes doesnt work e.g. "a{backslash}Cb{backslash}ScD{backslash}CE" → a, Control+b, c, Shift+D, Control+Shift+E')}
      \C - Control
      \A - Alt
      \M - Meta
      \W - Super

  {h2('examples')}
    /usr/bin/zsh -c "xvkbd -xsendevent -no-sync -text '('"
    xvkbd -no-jump-pointer -text '\[Left]'
    xvkbd -no-jump-pointer -text '\C\A\[Left]'
    xvkbd -text '\m1\Mq'  {c('Meta-Q')}
    """


@syntax
def yarn(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('yarn')}
  {h2('info')} <package>
    outputs lots of json-like information about [installed?] package

  {h2('list')} [package]
    like npm list
    
  {h2('upgrade')} [flags]
    also: upgrade-interactive / upgradeInteractive
    -L, --latest        {c('list latest ver of package, ignoring package.json')}
    -E, --exact         {c('install exact ver. Only with --latest.')}
    --verbose
    --non-interactive
    --silent
    --cwd <dir>         {c('--cwd "$(yarn global dir)"')}
    

  """


def youtube_dl(subject=None):
    return f"""{h1('youtube-dl')} [OPTIONS] URL [URL...]
  {h2('install')}
    sudo snap install youtube-dl
    
  {h2('options')}
    -F                    {c('list formats')}
    -f, --format <FORMAT>
       'best[ext=mp4]+bestvideo[height=1080]'
       'best[ext=mp4]+best[height=1080]'
       '(mp4)[height=1080]'
       '(mp4)worstvideo+bestaudio'
       '(mp4)[height=1080]+bestaudio'
       'bestvideo[height=1080]+bestaudio'
  
    -v, --verbose
    -s, --simulate             {c('Do not download the video and do not write anything to disk')}
  
    --console-title            {c('Show progress in console title')}
    
    --yes-playlist             {c('Download playlist even if url points to vid')}
    --playlist-start=15        {c('Download starting from part PART')}
    --playlist-items '1-3,7,10-13'
    --flat-playlist            {c('only list playlist files, dont download')}
    
    -o, --output <TEMPLATE>
      '%(playlist)s/%(playlist_index)s___%(title)s.%(ext)s'
  
    --ignore-config            {c('~/.config/youtube-dl/config or /etc/youtube-dl.conf')}
    --config-location PATH
    
    --restrict-filenames       {c('remove spaces and e.g. "&" in file names')}
  
    --no-continue              {c('dont resume partial downloads; start from beginning')}
  
    --get-<url | title | id | thumbnail | description | duration | filename | format> {c('dont dl vid')}
  
    --list-subs
    --write-sub
    --sub-langs iw
    --write-auto-sub
    --embed-subs
    --convert-subs <FORMAT>    {c('srt|ass|vtt|lrc')}
  
    --recode-video <FORMAT>    {c('mp4|flv|ogg|webm|mkv|avi')}
  
    -x, --extract-audio        {c('only audio')}
    --audio-quality <QUALITY>  {c('VBR: 0 (better) to 9 (worse); CBR: 128K')}
    --audio-format <FORMAT>    {c('"best", "aac", "flac", "mp3", "m4a", "opus", "vorbis", or "wav"; "best" by default; No effect without -x')}
  
    --mark-watched

  {h2('examples')}
    youtube-dl -v --yes-playlist --mark-watched --playlist-start=15 --restrict-filenames --console-title -o '%(playlist)s/%(playlist_index)s___%(title)s.%(ext)s' -f '(mp4)bestvideo' 'https://www.youtube.com/playlist?list=PLsyeobzWxl7r2ukVgTqIQcl-1T0C2mzau'
    youtube-dl $(cat /home/gilad/.config/youtube-dl/config | tr '\n' ' ') 'PLNmW52ef0uwtUY4OFRF0eV1mlT5lKhe_j'
    """


@syntax('friendly')
def zenity(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('zenity')}
  {c('zenity [global options] <dialog type> [dialog-specific options]')}
  
  {h2('dialog type')}
    
    {h3('--calendar')}
    
    {h3('--entry')}
      --entry-text=STRING
      --hide-text
    
    {h3('--error')}
      --no-wrap
      --no-markup
    
    {h3('--file-selection')}
    
    {h3('--info')}
      --no-wrap
      --no-markup
    
    {h3('--list')}
      zenity --list --checklist --column "Buy" --column "Item" TRUE Apples FALSE Oranges
      find  ... | zenity --list --title "Search Results" --text "Finding..." --column "Files"
    
    {h3('--notification')}
      --text=STRING
      --listen         {c("Toggle listen to stdin for 'message: STR', 'tooltip: STR', 'icon: PATH_OR_LEVEL', and 'visible: BOOL' separated by a colon")}
    
    {h3('--progress')}
      --percentage=INT
      --auto-close     {c('when reaches 100%')}
      --auto-kill      {c('cancel button kills process')}
      --pulsate
      --no-cancel      {c('hide cancel button')}
      find ... | zenity --progress --pulsate
    
    {h3('--question')}
      --no-wrap
      --no-markup
      --ok-label
      --cancel-label
    
    {h3('--text-info')}
      --filename=FILE
      --editable
      --font=FONT
      --checkbox=TEXT
      --html
      --url=URL        {c('requires --html')}
      --ok-label       {c('Set OK button text')}
      --cancel-label   {c('Set cancel button text')}
    
    {h3('--warning')}
      --no-wrap
      --no-markup
    
    {h3('--scale')}
    
    {h3('--color-selection')}
    
    {h3('--password')}
      --username    {c('display username field')}
    
    {h3('--forms')}

  {h2('global options')}
    --text=STRING   {c('(irrelevant to --text-info)')}
    --title=STRING
    --window-icon{c('=/path/to/icon_path|info|warning|question|error')}
    --width=WIDTH
    --height=HEIGHT
    --timeout=SECS
  """


def zip_(subject=None):
    return f"""{h1('zip')}
  {h2('options')}
    -r      {c('recursive')}
    -i, --include <GLOB>
    -x, --exclude <GLOB>
    -v, --verbose
    -<int>  {c('0: no compression; 9: most compression')}

  {h2('examples')}
    zip -r -9 'outfile' . -i "somedir/*"
    zip -r -9 'out' 'vid.mkv'
    zip -d compressed.zip "somedir/*"       {c('Delete from zip')}
    
{h1('unzip')} [-Z] [-cflptTuvz[abjnoqsCDKLMUVWX$/:^]] file[.zip] [file(s) ...]  [-x xfile(s) ...] [-d exdir='.']
  {h2('options')}
    -x <GLOB>   {c("Example: '-x */*' extract all files in root but none in subdirs")}

  {h2('examples')}
    {c('View contents')}
    unzip -l rsevents.zip
    """


@syntax('monokai')
def zsh(subject=None):
    _ZLE = f"""{h2('zle')} - Z-Shell Line Editor
    # https://github.com/mskar/setup/blob/5d9dddd447a05e8d866b9c09b06a085f02e41bd3/.zshrc#L686
    zle up-history
    zle push-line
    zle accept-line
    zle -N <function>
    """

    _COMMANDS = f"""{h2('zsh commands')}
    {h3('print')}
    {c('http://zsh.sourceforge.net/Guide/zshguide03.html#l33')}
    print -z print -z print This is a line    {c('Put in buffer')}
    
    {h3('zparseopts')} [ -D -E -F -K -M ] [ -a array ] [ -A assoc ] [ - ] spec ...
    {c('https://xpmo.gitlab.io/post/using-zparseopts/')}
    {c('man zshmodules')}
    
    {h4('Flags')}
      -D    {c('Remove matches from $@')}
      -E    {c("Don't stop at first string that doesn't match specj")}
      
    {h4('Examples')}
      %bash
      # Example 1
      zmodload zsh/zutil
      zparseopts -D -E -F - a:=arg_val -arg:=arg_val f=flag -flag=flag {backslash}
      	F=foobar -foo=foobar B=foobar -bar=foobar || exit 1
      
      # remove first -- or -
      end_opts=$@[(i)(--|-)]
      set -- "${{@[0,end_opts-1]}}" "${{@[end_opts+1,-1]}}"
      
      # Example 2
      zparseopts -D -E - a:+=a_and_b b:+=a_and_b
      
      # Example 3
      zparseopts -D -E - v+=flag_v -verbose+=flag_v q+=flag_q -quiet+=flag_q
      (( verbosity = $#flag_v - $#flag_q ))
      /%bash
    """
    
    _KEYS = f"""{h2('Keyboard Shortcuts')}
    {c('show all with just `bindkey`')}
    {h3('Glossary')}
      ^X      {c('ctrl x')}
      ^[x     {c('alt x')}
      ^[^X    {c('ctrl alt x')}
      ^[X     {c('shift alt x, ESC x')}
      
      \\e[3D   {c('alt left? dirhistory')} 
    
    {h4('Keys hex values')}
      ^[      ESC
      ^M      Enter
      ^[[A    Up
      ^[[B    Down
      ^[[C    Right
      ^[[D    Left
      ^[[H    Home
      ^[[F    End
      ^[[2~   Ins
      ^[[3~   Del
      ^[[5~   PgUp
      ^[[6~   PgDn
      ^[OP    F1
      ^[OQ    F2
      ^[OR    F3
      ^[OS    F4
      ^[[15~  F5
      ^[[17~  F6
      ^[[18~  F7
      ^[[19~  F8
      ^[[20~  F9
      ^[[21~  F10
      ^[[24~  F12
      
    {h3('ESC <key>')}
      ESC m     {c('copy-prev-shell-word')}
      ESC h     {c('run-help')}
      ESC "     {c('single-quote from line start to cursor')}
      ESC '     {c('single-quote line')}
      ESC .     {c('insert-last-word')}
      ESC ?     {c('which-command')}
    
    {h3('CTRL X <key>')} (hold control)
      ^X^E    {c('edit-command-line')}
      ^X^B    {c('vi-match-bracket')}
      ^X^O    {c('overwrite mode')}
      ^X^U    {c('undo')}

    {h3('More zle functions')}  {c('zle <FN>')}
      .kill-buffer    {c('dirhistory plugin')}
      .accept-line    
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return rf"""{h1('zsh')}
  http://zsh.sourceforge.net/Guide/zshguide04.html
  autoload -U add-zsh-hook
  autoload -Uz compinit
  add-zsh-hook chpwd chpwd_dirhistory    {c('dirhistory plugin')}
  emulate -L zsh
  emulate -RL zsh
  {_COMMANDS}
  
  {_ZLE}

  {_KEYS}
  {h2('bindkey')}
    %bash
    hexdump
    # OR:
    showkey -a
    # Press F1. Prints:
    # [OP'
    
    # Examples:
    bindkey "\e[3A" <function> # alt+up
    bindkey "\e"man <function>
    /%bash
  """
