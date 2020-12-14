import inspect
import re

from functools import wraps
from typing import Literal, Dict, Type

from pygments.lexer import Lexer

from mytool.myman.formatting import h1, h2, h3, h4, h5, b, c, i, black
from mytool.tipes import ManFn
from pygments import highlight as pyglight
# TODO: if lang ipython and style is None -> friendly. this means pyghighlight and custom highlight function
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import (get_lexer_by_name,
                             MySqlLexer, JavascriptLexer, PythonLexer, BashLexer, IniLexer,
                             JsonLexer, CssLexer, TypeScriptLexer)

linebreak = r'\n'
backslash = '\\'
color = '\x1b['
Style = Literal['friendly', 'native', 'algol_nu', 'solarized-dark', 'inkpot']
Language = Literal['mysql', 'python', 'bash', 'ipython', 'ini', 'json', 'js', 'ts', 'css']
langs = Language.__args__
HIGHLIGHT_START_RE = re.compile(fr'%({"|".join(langs)})(?: )?(\d|{"|".join(Style.__args__)})?')
HIGHLIGHT_END_RE = re.compile(fr'/%({"|".join(langs)})')
formatters: Dict[Style, TerminalTrueColorFormatter] = dict.fromkeys(Style.__args__, None)
lexers: Dict[Language, Lexer] = dict.fromkeys(langs, None)


#### HELPER FUNCTIONS

def _get_lexer_ctor(lang: Language) -> Type[Lexer]:
    if lang == 'bash':
        return BashLexer
    if lang == 'css':
        return CssLexer
    if lang == 'ini':
        return IniLexer
    if lang == 'ipython':
        return lambda o=lang: get_lexer_by_name('ipython')
    if lang == 'js':
        return JavascriptLexer
    if lang == 'ts':
        return TypeScriptLexer
    if lang == 'json':
        return JsonLexer
    if lang == 'mysql':
        return MySqlLexer
    if lang == 'python':
        return PythonLexer
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
    # friendly (less bright than native)
    # native
    # algol_nu (b&w)
    # solarized-dark (weird for python)
    # inkpot
    if style is None:
        style = 'native'
    global formatters
    formatter = formatters.get(style)
    if formatter is None:
        formatter = TerminalTrueColorFormatter(style=style)
        formatters[style] = formatter
        return formatter
    return formatter


def highlight(text: str, lang: Language, style: Style = None) -> str:
    lexer = _get_lexer(lang)
    if style is None:
        if lang == 'ipython':
            style = 'friendly'
        elif lang == 'js' or lang == 'json':
            style = 'default'
    formatter = _get_color_formatter(style)
    highlighted = pyglight(text, lexer, formatter)
    return highlighted


def alias(_alias: str):
    def wrap(fn):
        fn.alias = _alias
        return fn
    
    return wrap


def syntax(_fn_or_style: ManFn = None, **default_styles):
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
                            highlighted = highlight(text, lang, style)
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
                            # no closing tag → highlight only first line
                            # TODO: in setuppy, under setup(), first line not closing %bash doesnt work
                            #  Consider highlighting until end of string (better behavior and maybe solves this bug?)
                            text = lines[idx + 1]
                            highlighted = highlight(text, lang, style)
                            highlighted_strs.append(highlighted)
                            idx = j
                            break
                        else:
                            if HIGHLIGHT_END_RE.fullmatch(nextline.strip()):
                                text = '\n'.join(lines[idx + 1:j])
                                
                                highlighted = highlight(text, lang, style)
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


#### MANUALS

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


@syntax
def apt(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('apt')}
  {h2('list')} [GLOB]                        {c('list packages based on package names')}
    {c('Without subcommand, lists all known packages')}
    --installed
    --upgradeable
    --all-versions

  {h2('search')} REGEX                       

  {h2('show')} NAME

  {h2('update')}                             {c('download package information (avail versions)')}

  {h2('upgrade')}                            {c('does not remove existing packages')}
    {h3('full-upgrade')}                     {c('removes existing packages')}

  {h2('install')} PKG
    {h3('install from web')}
      install <REGEX, GLOB, EXACT>
      install <REGEX, GLOB, EXACT>/<stable | testing | unstable | buster | bullseye | sid ...>
      install <REGEX, GLOB, EXACT>=

    {h3('install from file')}
      install /path/to/pkg.deb

    {h3('options')}
      install --no-install-recommends  {c('skips installing the extra recommended packages')}
      --only-upgrade install PKG       {c('upgrade only specific')}

  {h2('reinstall')} <REGEX, GLOB, EXACT>     {c('maybe supports file?')}

  {h2('purge')} <REGEX, GLOB, EXACT>         {c('clean the config remove left behind')}
                                               {c('does not remove files in home dir')}

  {h2('remove')} <REGEX, GLOB, EXACT>

  {h2('autoremove')}                         {c('remove dependencies of removed packages')}
                                                {c(f'apt-mark deps you like')}
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
    # _SUBPROCESS = _SUBPROCESSES
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
def bash(subject=None):
    # _Bash(){
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
    # "
    #
    # 	}
    # 	_arrays(){
    # 		printf "$(_h1 'Array')
    #   $(_h2 'Initialization')
    #     array=( zero one two three four five )
    #
    #   $(_h2 'Get')
    #     \${array[0]}                        $(_# 'zero')
    #     \${array:0}                         $(_# 'zero')
    #     \${array[1]}                        $(_# 'one')
    #     \${array:1}                         $(_# 'ero')
    #
    #   $(_h2 'Lengths')
    #     \${#array[0]}                       $(_# '4')
    #     \${#array}                          $(_# '4 (alias for above)')
    #     \${#array[*]}                       $(_# '6; num of elements in array')
    #     \${#array:[@]}                      $(_# 'same as above')
    #
    #   $(_h2 'Misc')
    #     arr=(\${dockers//\$'\\\n'/ })         $(_# 'Split a string with newlines to array')
    #
    # "
    # 	}
    # 	_conditionals(){
    # 		printf "$(_h1 Conditionals)
    #   $(_h2 'Positional Parameters')
    #     echo \${*:2}                        $(_# 'Echoes second and following positional parameters.')
    #     echo \${@:2}                        $(_# 'Same as above.')
    #     echo \${*:2:3}                      $(_# 'Echoes three positional parameters, starting at second.')
    #
    #   $(_h2 'Conditionals applied on variables')
    #     if [[ \${string} == *\"My long\"* ]]  ${comment('Check if substring exists in string')}
    #     if [[ \"\$dockers\" =~ \$'\\\n' ]]     $(_# 'Check if newline exists in str')
    #     if [[ \$(expr index \"\$dockers\" \$'\\\n') != \"0\" ]]    $(_# 'Same as above')
    #     if [[ \${iter} != 0 ]];             $(_# $'After "converting" arg to number: iter=\$((\$1 + 0))')
    #     if [ \"\$monitor_amount\" -eq 2 ]
    #     if [ -z \"\$1\" ]                   $(_# 'string length IS zero')
    #     if [ -n \"\$(pgrep flameshot)\" ]   $(_# 'string length NON zero')
    #
    #     EXPRESSION1 -a EXPRESSION2          $(_# 'both EXPRESSION1 and EXPRESSION2 are true')
    #     EXPRESSION1 -o EXPRESSION2          $(_# 'either EXPRESSION1 or EXPRESSION2 is true')
    #
    #   $(_h2 Ternary)
    #     [[ \${b} = 5 ]] && a=\"\$c\" || a=\"\$d\"
    #
    
    #
    #
    #
    # ";
    # 	}
    # 	_for(){
    # 		printf "$(_h1 'for')
    #   for reqsubstr in 'o' 'M' 'alt' 'str';
    #
    #   for ((i=0; i<6; i++));
    #
    #   for l in \$(git diff --summary gilad | grep -o -P \"(?<=\d{6}\s).*\");
    #
    # ";
    # 	}
    # 	_while(){
    # 		printf "$(_h1 'while')
    #   x=1
    #   while [[ \${x} -le 5 ]]; do
    #     echo \"Welcome \$x times\"
    #     x=\$((x + 1))
    #   done
    #
    # "
    # 	}
    # 	_case(){
    # 		printf "$(_h1 'case')
    #   case \$1 in
    #     verbose)    echo \"verbose\";;
    #     false)   echo \"is false\";;
    #     [Yy][Ee][Ss])   echo \"some regex\"; break;;
    #     *)   echo \"none of the above\";;
    #   esac
    #
    # "
    # 	}
    # 	_help(){
    # 	  printf "
    #     str | string | strings
    #     list | lists | arr | array | arrays
    #     cond | condition | conditionals | if
    #     for
    #     while
    #     case
    # "
    # 	}
    # 	case $1 in
    # 	  str | string | strings) _strings;;
    # 	  list | lists | arr | array | arrays) _arrays;;
    # 	  cond | condition | conditionals | if) _conditionals;;
    # 	  for) _for;;
    # 	  while) _while;;
    # 	  case) _case;;
    #     help) _help;;
    # 	  *)
    # 	    _strings;
    # 	    _arrays;
    # 	    _conditionals;
    # 	    _for;
    # 	    _while;
    # 	    _case;
    #   esac
    #
    #   [[ "$1" != "help" ]] && printf "
    # _Bash \$1: $1, \$2: $2
    # "
    # }
    # TODO: git diff -w "$@" | view -
    __ARGUMENTS = __ARGS = f"""{h3('Arguments')}

    {h4('Parse args / kwargs')}
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
          val=$(echo -e "${{1:8}}")     # start from index 8 and on, of var '1'
          echo kwarg $1 with val $val
          shift
          ;;
          -s|--switch)
          # 's foo' or '--switch foo'
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
    
    {h4('Get by index')}
      ${{#}}                  {c('get number of args (myfn "hello world" indeed → 2)')}
      ${{*:2}} {c('or')} ${{@:2}}      {c('2nd and following pos args')}
      ${{*:2:3}}              {c('three pos args, starting from 2nd')}
      ${{2}}                  {c('2nd arg exactly')}
      
      {h5('second-to-last, like sys.argv[-2]')}
        %bash 1
        ${{*:$((${{#}} - 1)):1}}  
        {c('or')}
        %bash 1
        $@[$(($# - 1))]
        {c('or')}
        %bash 1
        $*[$(($# - 1))]
      
      {h5('last arg')}
        %bash 1
        $@[$#]
    
    {h4('Examples')}
      {h5('Check if no cmd args')}
        %bash 1
        if (( $# == 0 )) ; then
  
      {h5('${*} vs $@')}
        %bash
        function star() {{ echo "${{*:2}}" }}
        > star hello world
        /%bash
        {i("llo world")}
      
        %bash
        function at() {{ echo "${{@:2}}" }}
        > at hello world
        /%bash
        {i("world")}
        'at "hello world"' is 1 var
      
        %bash
        function star() {{ printf "args: '%s'{linebreak}" "${{*}}" }}
        > star hello world
        /%bash
        {i("args: 'hello world'")}
    
        %bash
        function at() {{ printf "args: '%s'{linebreak}" "$@" }}  # ${{@}} same
        > at hello world
        /%bash
        {i("args: 'hello'")}
        {i("args: 'world'")}
        {c('note: function is called once even though it looks like twice')}
        
        
  """
    
    __ARRAY = f"""{h3("Arrays")}
    %bash
    numbers_arr=( zero one two three four five )
    # initialize empty
      declare -a empty_arr=()
    
    # initialize with values
      foo_arr=('foo'
      'bar')

    # initialize with values at specific index
      foo_arr=( [index]=value )
    
    # get
      #TODO: this is all wrong?
      ${{numbers_arr[0]}}        # zero
      ${{numbers_arr:0}}         # zero
      ${{numbers_arr[1]}}        # one
      ${{numbers_arr:1}}         # ero
  
    # length
      ${{#numbers_arr[0]}}       #4
      ${{#numbers_arr}}          #4
      ${{#numbers_arr[*]}}       #6 (num of items)
      ${{#numbers_arr:[@]}}      #6
    
    # append
      numbers_arr+=("six")
    
    # print
      echo $foo_arr              # foo bar
    
    # concatenating two arrays
      array=(${{array_1[@]}} ${{array_2[@]}})
  
    # split string to array by linebreak
      arr=(${{wids//$'\\n'/}})  # possibly space after '\\n'/
      arr=( $(echo $wids | pyp lines) ) # no quotes
      arr=( $(echo $wids | python3 -c "import sys; print(sys.stdin.read())") )
  
    # last item
      ${{array[${{#array}}]}}
    /%bash
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
    __EXEC = f"""{h3('exec and $(...)')}
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
      -t  {c('file descriptor is open and refers to a terminal')}
          {c('when not piped, -t 1 is True')}
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
    count=$((0))
    count=$((0+1))
    count=$((count+1))      {c('$((count + 1)) also fine')}
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
    -n, -o noexec             {c('Read commands but do not execute them.')}
    -x, -o xtrace             {c('Print commands and their arguments as they are executed.')}
    -v, -o verbose            {c('Print shell input lines as they are read.')}
    -o interactive-comments   {c('allow comments to appear in interactive commands')}
    --                        {c('Assign any remaining arguments to the positional parameters.')}
                              {c('  If there are no remaining arguments, the positional parameters are unset.')}
    -                         {c('Assign any remaining arguments to the positional parameters.')}
                              {c('  The -x and -v options are turned off.')}

      """
    __STRING = rf"""{h3('strings')}
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
      
      # Replace substring:
      echo "AxxBC" | tr xyz _           # A__BC
    /%bash
    """
    __VARIABLES = __VARS = f"""{h3('Variables')}
    %bash 2
    ${{var:?}}        {c('fail if the variable is unset (or empty)')}
    : "${{var:=5}}"    {c('initialize it to a default value (5) if uninitialized')}
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
    {i('command: "$(echo hi)"')}"""
    __WHILE = f"""{h3('while')}
    x=1
    while [[ ${{x}} -le 5 ]]; do
      echo "Welcome $x times"
      x=$((x + 1))
    done
    """
    __PIPE = __PROCESSES = __FILEDESCRIPTORS = f"""{h2('Pipe, Processes, File Descriptors, Background, Foreground, >, >>, <, <<, <<<')}
    {c('https://stackoverflow.com/questions/35116699/piping-not-working-with-echo-command')}
    %bash
    nohup CMD &>/dev/null &
    CMD 2>&1

    echo "echo lol" | $SHELL  # lol
    
    eho "$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS" 2>bad.log
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
      >       {c('output to file')}
      >>      {c('append to file')}
      <       {c('read input from file')}
      <<      {c('here document')}
        [n]<<word
            here-document
        delimiter
        {c('n is file descriptor, defaults to stdin (0). can be <<- to remove leading <tab> chars')}
        
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
        /%bash
      
      <<<     {c('reverse pipe')}
        %bash
        # The following are the same:
        echo "hi" | cut -c 1
        cut -c 1 <<< "hi"
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
    
    _DPKG = f"""{h2('dpkg')} [option...] <action>   {c('options first')}
    {h3('action')}
      -i, --install <package-file>...
      --unpack <package-file>...
      -r, --remove <package>...     {c('removes everything except conffiles and other data')}
      -P, --purge <package>...
    
    {h3('option')}
      --no-act, --dry-run, --simulate
      -G, --refuse-downgrade      {c('do nothing if newer is installed')}
      -E, --skip-same-version     {c('do nothing if same version is installed')}
      --log=<filename>            {c('instead of to /var/log/dpkg.log')}
    
    {h3('dpkg-query')}
      -l, --list <package-name-pattern>...    {c('list matching packages')}
      -s, --status <package-name>...
      -L, --listfiles <package-name-pattern>...    {c('list files from packages')}
      -S, --search <filename-name-pattern>...    
      -p, --print-avail <package-name>...     {c('display details')}
      
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
    """
    
    _FIND = f"""{h2('find')}

    {h3('examples')}
    find . -path '*.py' -and -not -path '*playground*'
    find . -path '*.py' ! -path '*playground*'
    find -E . -type f -regex ".*b.*" -exec {i('rm')} "{{}}" ";"
    find . -maxdepth 1 -type d      {c('list dirs in current directory')}
    
    -E          {c('extended regex. takes effect only with "-[i]regex" (and "-[i]wholename"?)')}
    -X          {c('safe with xargs')}
    -d          {c('depth-first')}
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
    
    _FZF = f"""{h2('fzf')}
  https://www.youtube.com/watch?v=qgG5Jhi_Els
  https://github.com/junegunn/fzf#options
  
  %bash
  # Aliases:
    alias fzfp="fzf --preview 'bat --style=numbers --color=always {{}}' --preview-window=right:60%"
    alias fzff="find . -type f | fzf"
    alias fzffp="find . -type f | fzf --preview 'bat --style=numbers --color=always {{}}' --preview-window=right:60%"
    alias fzfd="find . -type d | fzf"
    alias fzfdp="find . -type d | fzf --preview 'bat --style=numbers --color=always {{}}' --preview-window=right:60%"
  
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
    INITIAL_QUERY=""
    RG_PREFIX="rg --column --line-number --no-heading --color=always --smart-case "
    FZF_DEFAULT_COMMAND="$RG_PREFIX '$INITIAL_QUERY'" fzf --bind "change:reload:$RG_PREFIX {{q}} || true" --ansi --phony --query "$INITIAL_QUERY" --layout=reverse
  /%bash
    """
  
    _GREP = f"""{h2('grep')}
    {h4('grep')} [OPTION...] PATTERN [FILE...]
    {h4('grep')} [OPTION...] -e PATTERN... [FILE...]
    {h4('grep')} [OPTION...] -f PATTERN_FILE... [FILE...]
    
    {h3('options')}
      {h4('pattern syntax')}
        -E, --extended-regexp
        -F, --fixed-strings      {c('take pattern literally, dont interpret regex chars')}
        -P, --perl-regexp        {c('only linux?')}
      
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

    {h3('Examples')}
      grep -r -w --color 'HereB' .    {c('-recursive, -word')}
      grep -n [-C -A -B] 2 'Ace' .    {c('line num, 2 context lines')}
      grep --exclude-dir "*home/gilad/Downloads/ANGRYsearch*" --exclude "file.zip" -riPa "angrysearch"
      grep -nIrEH -C 1 --exclude="*.log" --exclude-dir="src" "[^def ]loadDataFromS3" .
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
    
    _SYMLINKS = _LN = _LINK = f"""{h2('ln - make links between files')}
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
    
    _SSH = f"""{h2('ssh')}
    {h3('Check access to site')}
      ssh -T git@bitbucket.org

    {h3('Add ssh key')}
      eval `ssh-agent`
      ssh-add -K ~/.ssh/<private_key_file>

    {h3('Check if ssh valid:')}
      ssh-keygen -l -f /Users/gilad/.ssh/id_rsa.pub

    {h3('Create new ssh key:')}
      ssh-keygen
    """
    
    _SCP = f"""{h2('scp')}
    scp -i /Users/gilad/Code/rapyd/CD-COMMON.pem ./test29.json5 ubuntu@172.20.10.121:/home/rapusr/reconciliation-testing-tools/scenarios
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
    
    # Delete substring:
    foo="\n hi\nbye\n "
    echo "$foo" | tr -d ' \n'           # hibye%
    echo "$foo" | tr -d '\n'            #  hibye %
    echo -n $(echo "$foo" | tr -d '\n') # hibye%
    echo -n $(echo "$foo" | tr -d ' ')  # hi bye%
    /%bash
    """
    
    _TRAP = f"""{h2('trap')}
  %bash
  # example
  set -o errtrace
  trap 'function_name' ERR
  /%bash
    """
    
    _TREE = f"""{h2('/snap/bin/tree')}
  {h3('filtering')}
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

  {h3('output')}
    -h    {c('Human size')}
    -p Print the protections for each file
    
    {h4('sorting')}
    -v    {c('alphanumerically by version')}
    -t    {c('last modification time')}
    -c    {c('last status change time')}
    --dirsfirst
    --sort <name|version|size|mtime|ctime>
    
    """
    
    _VIPE = f"""{h2('vipe examples')}
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
      /%bash

    {h3('Load to variable')}
      %bash 2
      cmd=$(echo -n "$line" | vipe)
      eval "$cmd"
    """
    
    _XARGS = f"""{h2('xargs')}
    ls | xargs echo
    ls | xargs -L 1 echo            {c('-L max-lines. Implies -x')}
    xargs -0 -I % cp % ~/backups    {c('"-I %" specifies which placeholder char, "cp %" is where to place it')}
    -0 seems to keep line breaks?   {c("cat requirements.txt | cut -d'=' -f1 | xargs")}
    cat zooecho | vipe | xargs -I % $SHELL -c "%"
    """
    
    _WC = f"""{h2('wc')} {c('[OPTION]... [FILE]...')}
    -l, --lines     {c('newline count')}
    -w, --words     {c('word count')}
    -m, --chars     {c('character count')}
    -c, --bytes     {c('byte count')}
    
    apt list | wc -l
    wc -l data.json
    """
    
    if subject:
        if subject.startswith('<') or subject.startswith('>') or subject in ('!', '?', '&', '|'):
            return __FILEDESCRIPTORS
        
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('bash')}
  http://www.etalabs.net/sh_tricks.html
  {_CHMOD}
  {_CUT}
  {_DIFF}
  {_DPKG}
  {_DU}
  {_CP}
  {_ECHO}
  {_FIND}
  {_FZF}
  {_GREP}
  {_LESS}
  {_MOUNT}
  {_PS}
  {_READ}
  {_SCP}
  {_SED}
  {_SORT}
  {_SPLIT}
  {_SSH}
  {_STAT}
  {_SYMLINKS}
  {_SYNTAX}
  {_TR}
  {_TRAP}
  {_TREE}
  {_VIPE}
  {_WC}
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


def click_(subject=None):
    return f"""{h1('Click')}

  {h2('Options')}

    show_default = True
    ('-s', '--string-to-echo', 'variable_name')
    type=(str, int) or type=click.types.ParamType   {c('Choice, INT, ...')}

    {h3('Multi-value options')}         {c('Tuple')}
      @click.option('--pos', nargs=2)
      def findme(pos):
        click.echo('%s / %s' % pos)

      {i('>>> findme --pos 2.0 3.0')}

    {h3('Multiple options')}            {c('Tuple[T]')}
      @click.option('--message', '-m', multiple=True, type=T)
      def commit(message):
        click.echo('\\n'.join(message))

      {i('>>> commit -m foo -m bar')}

    {h3('Boolean Flags')}
      @click.option('--shout/--no-shout')
      def info(shout):                  {c('Pass either')}

      @click.option('--shout', is_flag=True)
      def info(shout):                  {c(f'{i("--shout")} → True')}

    {h3('Feature Switches')}            {c('Multiple options')}
      @click.option('--upper', 'transformation', flag_value='upper', default=True)
      @click.option('--lower', 'transformation', flag_value='lower')

    {h3('Prompt')}
      @click.option('--name', prompt='Your name please')

    {h3('Dynamic Defaults')}
      @click.option('--username', prompt=True,
              default=lambda: os.environ.get('USER', ''),
              show_default='current user')
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
    git clone mi-mevi-ma    # empty repo
    cd mi-mevi-ma

    # create a manage.py besides .gitignore, and mimevima/ dir with asgi.py, setting.py, urls.py, wsgi.py:
    django-admin startproject mimevima .

    # create m3app/ dir with admin.py etc:
    python manage.py startapp m3app
    /%bash
    """
    _MAKEMIGRATIONS = f"""{h2('makemigrations')} {c('[app_label]')}
    --dry-run
    afterwards, run migrate
    """
    
    _RUNSERVER = f"""{h2('runserver')}
    --no[threading reload static]
    --insecure      {c('serve static even if DEBUG is False')}
    --settings {i('myproject.settings.main')}   {c('python module path. default: DJANGO_SETTINGS_MODULE env var')}
    --pythonpath {i('PYTHONPATH')}
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
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Django 3')}
  {c('https://cloud.google.com/python/django/appengine')}

  {_RUNSERVER}

  {_MAKEMIGRATIONS}

  {_MODELS}

  {_MISC}
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
    ffmpeg -i {i('vid.mkv')} -codec copy {i('vid.mp4')}

    {h3('between audio formats')}
    ffmpeg -i {i('song.m4a')} -acodec lame_enc -aq 2 {i('song.mp3')}

    {h3('mp4 to gif')}
    ffmpeg -i {i('vid.mp4')} -f gif -s 960x540 -r 10 {i('vid.gif')}
    ffmpeg -i {i('vid.mp4')} -filter_complex '[0:v] fps=30,scale=480:-1,split [a][b];[a] palettegen [p];[b][p] paletteuse' {i('vid.gif')}
    """
    _SRT = f"""{h2('SRT')}
    {h3('embed srt')}
    ffmpeg -i {i('vid.mp4')} -c copy -filter:v subtitles={i('vid.srt vid_with_subs.mp4')}
    ffmpeg -i {i('vid.mp4')} -i {i('vid.srt')} -map 0 -map 1 -c copy -metadata:s:s:0 language=eng -metadata:s:s:1 language=ipk {i('vid_with_subs.mkv')}

    {h3('extract srt from mkv')}
    ffmpeg -i {i('vid.mkv')}-map 0:s:0 {i('vid.srt')}
    """
    _SUBS = _SRT
    _AUDIO = f"""{h2('Audio')}
    {h3('reduce filesize')}
    ffmpeg -i {i('input.mp3')} -map 0:a:0 -b:a 96k {i('output.mp3')}

    {h3('compress')}
    ffmpeg -i {i('input.mp3')} -filter_complex 'compand=attacks=0:points=3/1' {i('output.mp3')}
    """
    _CONCAT = f"""{h3('Concat')}
      ffmpeg -i {i('vid1.mp4')} -c copy -bsf:v h264_mp4toannexb -f mpegts {i('tmp1.ts')}
      ffmpeg -i {i('vid2.mp4')} -c copy -bsf:v h264_mp4toannexb -f mpegts {i('tmp2.ts')}
      ffmpeg -i "concat:{i('tmp1.ts|tmp2.ts')}" -c copy -bsf:a aac_adtstoasc {i('out.mp4')}
      rm {i('tmp1.ts tmp2.ts')}
    """
    _MERGE = f"""{h3('Merge (audio and video)')}
      ffmpeg -i video.mp4 -i audio.wav -c copy {i('output.mkv')}
      {c('OR (replace existing audio)')}
      ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -strict experimental -map 0:v:0 -map 1:a:0 {i('output.mp4')}
    """
    _TRIM = f"""{h3('Trim')}
      {c('starting from 00:32:44 and lasting 11m:')}
      ffmpeg -ss 00:32:44 -i full.mp4 -c copy -t 00:11:00 trimmed.mp4
    """
    _CROP = f"""{h3('Crop')}
      -qp [0/lossless : 50/lossy]

      {c('for ancient devices')}
      -profile:v baseline -level 3.0

      {c('puts info at beginning of file, good for streaming (youtube)')}
      {c('https://trac.ffmpeg.org/wiki/Encode/H.264')}
      ffmpeg -i {i('input.mp4')} -filter:v "crop=w:h:x:y" -qp 12 -preset ultrafast -tune zerolatency -profile:v baseline -level 3.0 -movflags +faststart {i('output.mp4')}
    """
    _SIZE = f"""{h3('Reduce filesize (10x)')}
      {c('30/1.25 == 24')}
      ffmpeg -i {i('input.mp4')} -vf "setpts=1.25*PTS" -r 24 {i('output.mp4')}

      {c('constant rate; higher = lower bitrate')}
      ffmpeg -i {i('input.mp4')} -vcodec [h264 / libx265] [-crf 20] [-acodec [mp3 / aac]] {i('output.mp4')}
    """
    _FILESIZE = _SIZE
    _FRAMERATE = f"""{h3('Framerate')}
      ffmpeg -i {i('input.avi')} -r 24 -b:v 1640k -bufsize 1640k {i('output.avi')}

      {c('OR (with reencoding, takes time, much smaller filesize)')}
      {c('setpts=1.25*PTS makes it 1.25x SLOWER')}
      ffmpeg -i {i('input.mp4')} -vf "setpts=1.25*PTS" -r 24 {i('output.mp4')}

      {c('OR (without reencoding, takes some time, same filesize)')}
      ffmpeg -i {i('input.mp4')} -c copy -f h264 {i('output.h264')}
      ffmpeg -r 24 -i {i('output.h264')} -c copy {i('output.mp4')}
    """
    _VIDEO = f"""{h2('Video')}
    {_CONCAT}

    {_MERGE}

    {_TRIM}

    {_CROP}

    {_SIZE}

    {_FRAMERATE}
    """
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
    _BRANCH = f"""{h2('branch')}
    {h3('Rename branch')}
      git branch -m {i('newname')}
      git push origin :{i('old-name newname')}
      git push origin -u {i('newname')}

    {h3(f"Create new branch off of master")}
      git checkout -b {i('newbranch master')}
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
      https://github.com/Talship/sport-bingo/compare/gilad-staging...master
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
      git diff HEAD origin        {c('Compare local to origin')}
      git diff HEAD^ HEAD         {c('Compare the version before the last commit and the last commit')}
      git diff b8c59b3 -- src/renderer.ts
    
    {h3('Dots')}
      git diff topic..master      {c("same as 'git diff topic master'")}
      git diff topic...master     {c(f"Changes that occurred on {i('master')} since when {i('topic')} was started off it")}
    
    {h3('Lines of code')}
      git diff --stat 4b825dc642cb6eb9a060e54bf8d69288fbee4904
      git ls-files | xargs wc -l
    
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
        git diff --ignore-cr-at-eol --ignore-space-at-eol -b -w --ignore-blank-lines
    
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

    {h3(f'-G{i("<regex>")}')}
      {c('https://stackoverflow.com/a/35301258/11842164')}
      Look for differences whose patch text contains added/removed lines that match <regex>
      
      · basic regular expression
      · supports grouping () and OR-ing groups with |
      · supports \s, \W, etc
      · does not support lookbehind/ahead
      · supports ^&
      
      --pickaxe-all   {c(f'show all changes in changeset, not just files with change in {i("<regex>")}')}
      
      {h4('Examples')}
        git diff -G"def*" --pickaxe-all
        git diff -w -G'(^[^\*# /])|(^#\w)|(^\s+[^\*#/])'
        
        {c('Only show file differences with at least one line that mentions foo:')}
        git diff -G'foo'
        
        {c('Show file differences for everything except lines that start with a #:')}
        git diff -G'^[^#]'
        
        {c('Show files that have differences mentioning FIXME or TODO:')}
        git diff -G`(FIXME)|(TODO)`

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
    git log {i("SHA")}          {c('of commit / branch')}
    git log {i('my_branch')} --pretty=oneline --graph
    
    {h3('Commit Limiting')}
      {h4('amount')}
        git log -n {i('1')}                {c('limit')}
        git log --skip={i('n')}            {c('dont show first n')}

      {h4('when')}
        --[since until]={i('date')}

      {h4('who')}
        --author={i('pattern')}

      {h4('filtering')}
        --grep={i('pattern')}             {c('filter log message')}
        --all-match                       {c('if mult greps, return only which matched all (not any)')}
        --invert-grep                     {c('if mult greps, return only which matched all (not any)')}
        --i                               {c('ignore case')}
        --E                               {c('extended')}
        --[no]-merges                     {c('only do [not] return commits with parents > 1')}
        --[branches tags remotes]={i('pattern')}
        --exclude={i('pattern')}

        """
    
    _MERGE = f"""{h2('Merge')}
    {h3('strategy')}    {c(f'-s {i("strategy")} --strategy={i("strategy")}')}
      Can supply more than one (order matters).
      ours                  {c("does not even look at what the other tree contains at all")}
      recursive -Xours      {c("conflicting hunks to be auto-resolved cleanly by favoring our version")}


    {h3('Force merge branches')}
      git push -f origin master

      {c(f"keep content of {i('better_branch')}, but record a merge")}
      git merge --strategy=ours master
      git checkout master

      {c(f"fast-forward master up to the me")}
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
      -v, --verbose     {c('prints 1 line for fetch and 1 for push sources, e.g. "origin https://... (fetch)"')}
      add [-t <BRANCH>] [-m <MASTER>] [-f] <NAME> <URL>
      rename <OLD> <NEW>
      remove <NAME>
      prune [-n | --dry-run] <NAME>
      get-url <NAME>
      set-url <NAME> <NEWURL> [<OLDURL>]
    
    {h3('Change remote after forking')}
      git remote rename origin upstream
      git remote add origin https://github.com/giladbarnea/MY-FORK.git
      git fetch origin && git push --set-upstream origin master
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
    git stash       {c('puts in stash')}
    show            {c('relevant file names')}
    list            {c('all stashed entries ever')}
    apply           {c('load from stash')}
    pop             {c('load latest from stash and remove it from list')}
    clear           {c('remove all. will be pruned.')}
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
    
    _MISC = f"""{h2('Misc')}
    {h3('Unignore only specific subdir')}
      !/node_modules/
      /node_modules/**
      !/node_modules/pyano_local_modules/
    """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('git')}

  {_BRANCH}

  {_CHECKOUT}

  {_CLONE}

  {_COMMIT}

  {_COMPARE}

  {_CONFIG}

  {_DIFF}

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

  {_MISC}
    """

@syntax
@alias('gh')
def githubcli(subject=None):
    _RELEASE = f"""{h2('release')} <command> [flags]
    {h4('commands')}
      create      {c('Create a new release')}
      delete      {c('Delete a release')}
      download    {c('Download release assets')}
      list        {c('List releases in a repository')}
      upload      {c('Upload assets to a release')}
      view        {c('View information about a release')}
    
    {h4('flags')}
      -R, --repo [HOST/]OWNER/REPO
    
    {h4('Examples')}
      gh release list -R flameshot-org/flameshot
    """
    
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('gh')} <command> <subcommand> [flags]
  {c('https://cli.github.com/manual')}
  
  {h2('Commands')}
    gist          {c('Manage gists')}
    issue         {c('Manage issues')}
    pr            {c('Manage pull requests')}
    release       {c('Manage GitHub releases')}
    repo          {c('Create, clone, fork, and view repositories')}
  
    {h4('some more:')}
    alias         {c('Create command shortcuts')}
    api           {c('Make an authenticated GitHub API request')}
    auth          {c('Login, logout, and refresh your authentication')}
    completion    {c('Generate shell completion scripts')}
    config        {c('Manage configuration for gh')}
    help          {c('Help about any command ')}
  
  {h2('Flags')}
    --help
  
  {_RELEASE}
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
    https://docs.python.org/3/library/inspect.html
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
    """


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
    
    _EDIT = f"""{h2('%edit')} [options] [args]
    {h3('options')}
      -n {i('NUM')}       open editor at a specified line number
      -p                  call editor with same data as the previous time
      -r                  raw input
      -x                  don't exec immediately upon exit

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
    %load {i('http://.../myscript.py')}
    %load -r {i('5-10,40: myscript.py')}
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
    
    _SHELL = f"""{h2('TerminalInteractiveShell')} {c('IPython.terminal.interactiveshell.TerminalInteractiveShell')}
      {h3('Properties')}
        user_ns[_hidden]{c(': dict')}
        user_global_ns{c(': dict')}
        user_module{c(': module')}
        ... and all configurable props
    """
    
    _PROFILE = _PROFILER = _PRUN = f"""{h2('%prun')} {c(f"[options]")} {i('STATEMENT')}
    {c('Profiler Run')}

    -l {i('<limit>')}      {c('str (fn names), int (lines) or float (% of output). repeatable')}
    -s {i('<key>')}        {c('sort. repeatable.')}
        {c('calls cumulative file module pcalls line name nfl stdname time')}
    -r              {c('Return Stats obj')}
    -T {i('file')}         {c('Write stats to text file')}

    {h4('Examples')}
      stats = %prun -r -l 10 objs[0].get()

  {h2('%lprun')}             {c('Line by line profiler')}
    Requires pip installing line_profiler, and
    c.InteractiveShellApp.extensions = ['line_profiler']
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
    -t [-N{i('<N>')}]                       {c('print timing information at the end of the run')}
    -d {i('[-b40]')} myscript               {c('with pdb')}
    -d {i('[-b otherfile:20]')} myscript    {c('specify bp in a different file')}
    -p {i('[prof options]')} myscript
    -m module
    
    {h4('See also: %rerun, %prun')}
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
    
    _TIME = f"""{h2('%time')}                         Time execution of statement

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
  from IPython import start_ipython
  start_ipython(argv=[], user_ns=dict(**locals(), **globals()))
  /%python
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
  // call: sets 'this' via first arg, then ...args
  const increased: number = increase.call(obj, 1, 1);
  console.log(increased); // (2+1) * 1 * 1 == 3
  
  // bind: sets 'this' explicitly, then ...args
  const bound: (extra: number, moreExtra: number) => number = increase.bind(obj);
  console.dir(bound);
  console.log(bound(2, 100)); // (2+1) * 2 * 100 == 600
  
  // apply: like 'call', only with [...args]
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


@syntax(bash='friendly')
def jupyter(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('jupyter')}
  {h2('JupyterLab')}
    
    jupyter lab [cmd] [options]
    
    {h3('Install virtualenv')}
      %bash 2
      . env/bin/activate
      (env) python -m ipykernel install --user --name <CUSTOM_ENV_NAME>
    
    {h3('Native')}
      %bash 2
      jupyter lab --no-browser
      google-chrome --app="http://localhost:8888/?token=1275aa6bfa03172197ac328c8696b4ac682f8a240cdbd5d9"
    
    {h3('config')}
      jupyter lab --generate-config
              
    {h3('labextension')}
      npm search <NAME>
      jupyter labextension list, check
      jupyter labextension install|uninstall|update|enable|disable <NAME>

    {h3('nbextension')}
      https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/nbextensions.html
      pip install jupyter_contrib_nbextensions
      jupyter nbextension list
      jupyter nbextension install|uninstall|enable|disable [--py] <NAME>  {c('from a python package')}

    {h3('cmd')}
      build
      clean
      path  
      paths
      workspace
      workspaces
    
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
def lazygit(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('lazygit')}
  https://www.youtube.com/watch?v=CPLdltN7wgE
  https://github.com/jesseduffield/lazygit/#usage
  
  lazygit --config
  
  """

@syntax
@alias('md')
def markdown(subject=None):
    _LINKS = f"""{h2('links')}
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
      textfilter <sh-command>    {c("applies <sh-command> to selection, e.g. 'textfilter sort-n'")}
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


def pip(subject=None):
    _INSTALL = f"""{h2('install')}

    {h3('From repo')}
      {c('watch the slashes etc when pasting')}
      pip install -e "git+ssh://git@bitbucket.org/cashdash/reconciliation_services.git@recon-services-v2.4.0#egg=reconciliation_services"
      pip install -e "git+ssh://git@github.com/giladbarnea/more_termcolor.git#egg=more_termcolor"

    {h3('From local dir')}
      {c('sudo chmod 777 target dir, and make sure no prompts in target setup.py')}
      (env) pip install --log ./PIP.log -v -e /home/gilad/Code/IGit

    --src {i('<dir>')}        {c('virenv default is "<venv path>/src", global default is "<current dir>/src"')}
    --root {i('<dir>')}        {c('Install everything relative to this alternate root directory')}
    --user                      {c('install to user dir (~/.local/ or %APPDATA%/Python)')}
    -t, --target {i('<dir>')}
    -e, --editable {i('<path/url>')}      {c('implies setuptool "develop" mode')}

    pip3 freeze | grep -v "^-e" | xargs pip3 uninstall -y   {c('uninstall all packages')}
    """
    
    _SEARCH = f"""{h2('search')}

        """
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('pip')}
    {_INSTALL}
    {_SEARCH}
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

  -E  {c("Ignore PYTHON* env vars like PYTHONPATH and PYTHONHOME")}
  -d  {c("Turn on parser debugging | PYTHONDEBUG")}
  -v  {c("Print when a module is initialized | PYTHONVERBOSE")}
  -vv {c("Also on each file that's searched | PYTHONVERBOSE=2")}
  -i  {c("enter interactive mode after execution. PYTHONSTARTUP is not read | PYTHONINSPECT")}
  -s  {c("don't add user site-packages to sys.path")}
  -I  {c("isolated mode: implies -E and -s. no: script dir, user site-packages, PYTHON* env vars")}
  -O  {c("remove assert statements and any code conditional on the value of __debug__ | PYTHONOPTIMIZE")}
  -OO {c("Do -O and also discard docstrings | PYTHONOPTIMIZE=2")}
  -q  {c("no copyright and version messages")}

  -W {i('action:message:category:module:line')}
    {c('Can be specified multiple times | PYTHONWARNINGS')}
    {h4('action')}: ignore|default|all|module|once|error
      {c(f'{i("module")} print only first time each module')}
      {c(f'{i("once")} only first time per warning')}
    {h4('message')}: matches start of the warning. case-insensitive
    {h4('category')}: full warning (super) class name
    {h4('module')}: module name. case-sensitive.
    {h4('line')}: number. 0 matches all == unspecified

  -X importtime  {c("python3 -X importtime -c 'import asyncio' | PYTHONPROFILEIMPORTTIME")}
    """
    
    _DATE = _DATETIME = _TIME = f"""{h2('date / datetime / time')}
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
  
  {h3('date')}
    %python 1
    from datetime import date
    
    {h4('Static Methods')}
      today = date.today() {c('→ date')}
      date.fromtimestamp(1600000000) {c('→ date')}
    
    {h4('Instance Methods / Attrs')}
      today.day, .month, .year {c('→ int')}
      today.ctime() {c('→ "Wed Sep  2 00:00:00 2020"')}
      today.isoformat() {c('→ "2020-12-30"')}
      today.strftime(format) {c('→ "2020-12-30"')}
  
  {h3('datetime')}
    %python 1
    from datetime import datetime as dt
    
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
      now = dt.now() {c('→ datetime (vs dt.utcnow()?)')}
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
  {c(f'This is why @arg_dec has to return something that {i("expects")} a function (liked naked_dec)')}

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
    ignore|default|all|module|once|error

  PYTHONPROFILEIMPORTTIME {c('like -X importtime')}

    """
    _LOGGING = f"""{h2(f'logging')}
  {h3('LogRecord attributes')} {c('%(attr)[s f d]')}
  {c('https://docs.python.org/3/library/logging.html#logrecord-attributes')}
    asctime
    created           when LogRecord was created
    exc_info          Exception tuple (à la sys.exc_info)
    filename
    funcName
    levelname
    levelno           numeric
    lineno
    message
    module
    msecs
    name              logging.getLogger(name)
    pathname
    process           process ID
    processName       process name
    relativeCreated   ms between logging module was loaded and LogRecord created
    stack_info
    thread            thread ID
    threadName
    """
    _OPEN = rf"""{h2(f'with open(path, mode="rt" {c("default")}, errors=None)')}
  {h2('mode')}
    w                   {c("truncate file first. doesn't raise")}
    x                   {c(f"create new file (implies 'w', raises {i('FileExistsError')} if exists)")}
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
      {i(c('the the'))}

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

    {h3("fn                       returns             prints      out in ret  accepts     raises")}
    sp.run()                 CompletedProcess    yes         no          input
    sp.run(stdout=PIPE)      CompletedProcess    no          yes         input
    sp.Popen()               Popen               yes         no
    sp.Popen(stdout=PIPE)    Popen               no          yes
    sp.check_output()        bytes               no          yes         input       on non-zero
    sp.check_call()          0?                  yes         no                      on non-zero
    sp.call()                0 or 1              yes         no
    sp.getoutput()           str                 no          yes

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
    
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Python')}
  {_BITWISE}

  {_CMD}

  {_DATE}
  
  {_DECORATORS}

  {_DIFFLIB}

  {_DOCTEST}

  {_ENV}

  {_LOGGING}

  {_OPEN}

  {_PATHLIB}

  {_REGEX}

  {_SUBPROCESS}
        """


@alias('rst')
def restructured_text(subject=None):
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('reStructuredText')}
  {c('https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html')}
  
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
      -g, --glob <GLOB>           {c("filter paths. --glob '!*.py' to exclude")}
      --pre <COMMAND>             {c('search stdoud of COMMAND FILE. see "man rg" for example.')}
      --pre-glob <GLOB> ...       {c('apply "--pre" only on files matching GLOB(s)')}

    {h3('match control')}
      -s, --case-sensitive        {c('overrides -i/--ignore-case and -S/--smart-case')}
      -i, --ignore-case
      -S, --smart-case            {c('insensitive if all lowercase, sensitive otherwise')}
      -F, --fixed-strings         {c('treat PATTERN literally, so no need to escape regex chars')}
      -U, --multiline

    {h3('output')}
      -N, --no-line-number        {c('dont show line numbers')}
      -o, --only-matching         {c('show only the matched parts')}
      -A, -B, -C                  {c('context')}
      -v                          {c('invert match')}
      -c, --count                 {c('how many lines had a match per file')}
      --count-matches             {c('how many matches per file')}
      --files                     {c('print files that would be searched (no actual search)')}
      -l, --files-with-matches    {c('print paths of files with matches')}
      --files-without-match       {c('print paths of files without matches')}
      -q, --quiet                 {c('dont print matches to stdout. exit code still works.')}
      --sort[r] <none | path | modified | accessed | created>   {c('"none" is multithreaded')}
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
      'igit @ file:///home/gilad/Code/IGit#egg=igit'
      ]

    # pip install -e .[dev], or pip install -e "/home/gilad/Code/MyTool[dev]"
    extras_require={{'dev': ['pytest', 'ipdb', 'IPython', 'semver']}},
    /%python

  {h2('Upload to pypi')}
    %bash
    # rm -rf dist build
    (env) python setup.py sdist bdist_wheel
    (env) python -m twine upload dist/*
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

  {h2('remove')} [options] <pkg>   {c('removes named instance from system')}
    --purge           {c('also remove snapshot data')}
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
    _META = f"""{h2('MetaData')}
    meta = sqlalchemy.schema.MetaData()
    meta.reflect(bind=engine)
    meta.tables{c(': Dict[str, Table]')}
    """
    _METADATA = _META
    
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


def tar(subject=None):
    return f"""{h1('tar')}
  -x        {c('extract')}
  -f --file={c('file')}
  -t        {c('list content of archive')}
  -v        {c('verbose')}
    """


@syntax('friendly')
@alias('ts')
def typescript(subject=None):
    _SYNTAX = f"""{h2('3.7')}
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
    _TYPES = f"""{h2('Utility Types')}
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
      
      // This is like: (the [keyof T] makes it a list of keys)
      // [ k for k in T.keys() if k extends Function ]
      type FunctionPropertyNames<T> = {{
            [K in keyof T]: T[K] extends Function ? K : never }}[keyof T];
      
      FunctionPropertyNames<Part> // "updatePart"
      
      // {{ k:v for k,v in T.items() if k extends Function }}
      type FunctionProperties<T> = Pick<T, FunctionPropertyNames<T>>;
      /%ts
    
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
    if subject:
        frame = inspect.currentframe()
        return frame.f_locals[subject]
    else:
        return f"""{h1('Typescript')}
  {_TSCONFIG}
  
  {_SYNTAX}
  
  {_TYPES}
  """


def vim(subject=None):
    return f"""{h1('vim')}
  https://factorpad.com/tech/vim-cheat-sheet.html
  https://www.fprintf.net/vimCheatSheet.html
  Command structure:    {i('[count][operator]motion')}

  echo hello | vi -     {c('from stdin')}
  {h2('Counts')}
    A count requires an operator and / or a motion.
    1-9 are normal counts; 0 moves cursor to first col of line

  {h2('Modes')}
    normal → insert    A, a, C, I, i, O, o, S, s
    normal → command   :
    normal → command   v
    any → normal       Esc

  {h2('Operators')}
    c   Change
    d   Delete
    g~  Swap case
    gu  To lowercase
    gU  To uppercase
    y   Yank (copy)
    p   Paste
    u   Undo
    <   Shift left
    >   Shift right

  {h2('Motions')}
    Keep you in normal mode.
    {h4('Character   Synonym(s)          Motion         Units')}
    h . . . . . backspace, ctrl-h . left . . . . . characters
    l . . . . . space . . . . . . . right . . . . .characters
    j . . . . . enter, ctrl-[jmn] . down . . . . . lines
    k . . . . . ctrl-p . . . . . . .up . . . . . . lines
    $ . . . . . . . . . . . . . . . forward . . . .lines {c('(move to end of line)')}
    $ . . . . . . . . . . . . . . . backward . . . lines {c('(move to beginning of line)')}
    b . . . . . . . . . . . . . . . backward . . . words
    w . . . . . . . . . . . . . . . forward . . . .words
    {{ . . . . . . . . . . . . . . . backward . . . paragraphs
    }} . . . . . . . . . . . . . . . forward . . . .paragraphs
    ctrl-d . . . . . . . . . . . . .down . . . . . 1/2 screen
    ctrl-u . . . . . . . . . . . . .up . . . . . . 1/2 screen
    ctrl-b . . . . . . . . . . . . .backward . . . 1/2 screen
    ctrl-f . . . . . . . . . . . . .forward . . . .1/2 screen

  {h2('Examples')}
    yiw         {c('yank current word (excluding surrounding whitespace)')}
    yaw         {c('yank current word (including leading or trailing whitespace)')}
    ytx         {c('yank from the current cursor position up to and before the character (Til x)')}
    yfx         {c('yank from the current cursor position up to and including the character (Find x)')}
    yTx         {c('yank backward up to character')}
    yFx         {c('backward through character')}
  
  {h2('Registers')}
    :h registers    {c('help')}
    "*              {c('system clipboard; so `"*y$` copies to line end to sys clpbrd, `"*p` pastes')}

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
  -i            {c('from stdin or files (default)')}
  -o            {c('print selection to stdout')}
  -r, -rmlastnl {c('remove line break from end if exists')}
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
  {h2('Examples')}
    xdotool key 'Home'
    xdotool search [--onlyvisible] [--name, --class] GL503VM
    xdotool windowactivate `xdotool search --class --onlyvisible pycharm | head -1`

  {h2('Functions')}
    {h3('getters')}
      getactivewindow {c(': WID → 98566151')}
      getwindowfocus {c(': WID → 98566151')}
      selectwindow {c(': WID → 98566151')}
      getwindowname {i('<WID>')} {c(': str → "MyTool - myman.py"')}
      getwindowpid {i('<WID>')} {c(': PID → 9779')}

      getwindowgeometry [--shell] {c('x, y, width, height, screen num. --shell suitable for eval')}
      getdisplaygeometry

    {h3('search')} {c('[options] REGEXP → WID ("71303175")')}
      --class
      --classname
      --name
      {c('default tries all three')}
      --maxdepth {i('N')} {c('default infinite = -1')}
      --onlyvisible
      --limit {i('N')} {c('break search after N results')}
      --shell {c('print results as shell array WINDOWS=( ... )')}
      --all {c('require all conditions to be true')}
      --any {c('require any condition to be true (default)')}
      --sync {c('wait until search result is found')}

    {h3('setters')}
      windowactivate {i('<[H]WID>')}
      windowclose
      windowfocus (vs raise?)
      windowkill
      windowmap ?
      windowminimize
      windowmove
      windowraise (vs focus?)
      windowreparent ?
      windowsize [options] [window] <width> <height>

    {h3('actions')}
      {h4('click')} {c('[options] button')}
        {c('mousedown followed by mouseup after 12ms delay')}
        --clearmodifiers
        --repeat <repeat>   {c('default 1.  for dbl-click: `--repeat 2`')}
        --delay <ms>        {c('ignored unless --repeat > 1')}
        --window <WID>      {c('default %1')}
      {h4('key')} {c(f'[--window {i("WID")}]')} {c(f'[--delay {i("ms=12")}]')} {c(f'[--clearmodifiers]')}
        {c('"alt+r", "Control_L+J", "ctrl+alt+n", "BackSpace"')}
        xdt key F2
        xdt key Aacute
        xdt key ctrl+l BackSpace
        {c("Send ctrl+c to all windows matching title 'gdb':")}
        xdt search --name gdb key ctrl+c
      keydown
      keyup
      mousedown
      {h4('type')} {c(f'[--window {i("WID")}]')} {c(f'[--delay {i("ms")}]')} {c(f'[--clearmodifiers]')}
        xdt type 'Hello world!'

    {h3('behave')} {i('window action command ...')}
      {h4('examples')}
        {c('Print cursor location on mouse enter to any visible window')}
        xdotool search --onlyvisible . behave %@ mouse-enter getmouselocation

        {c('Print window title and pid whenever an xterm gets focus')}
        xdotool search --class xterm behave %@ focus getwindowname getwindowpid

        {c('Emulate focus-follows-mouse')}
        xdotool search . behave %@ mouse-enter windowfocus
      {h4('events')}
        mouse-enter
        mouse-leave
        mouse-click     {c('when released')}
        focus
        blur

    {h3('exec')} {c('[--sync]')}
      xdotool search --onlyvisible terminator behave %@ mouse-enter exec echo hi
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
        bs = r'\\'
        rf"""{h1('xvkbd')}
  /usr/bin/zsh -c "xvkbd -xsendevent -no-sync -text '('"
  xvkbd -no-jump-pointer -text '\[Left]'
  xvkbd -no-jump-pointer -text '\C\A\[Left]'
  xvkbd -text '\m1\Mq'  {c('Meta-Q')}
  -no-repeat            {c('even if key is depressed long time (default: on)')}
  {h2('-text')}
    \r - Return
    \t - Tab
    \b - Backspace
    \e - Escape
    \d - Delete
    {h3('modifiers')}
      \S - Shift    {c(f'sometimes doesnt work e.g. "a{bs}Cb{bs}ScD{bs}CE" → a, Control+b, c, Shift+D, Control+Shift+E')}
      \C - Control
      \A - Alt
      \M - Meta
      \W - Super
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
    

  """


def youtube_dl(subject=None):
    return f"""{h1('youtube_dl')}
  -F                    {c('list formats')}
  -f, --format <FORMAT>
     'best[ext=mp4]+bestvideo[height=1080]'
     'best[ext=mp4]+best[height=1080]'
     '(mp4)[height=1080]'
     '(mp4)worstvideo+bestaudio'
     '(mp4)[height=1080]+bestaudio'
     'bestvideo[height=1080]+bestaudio'

  -v, --verbose
  --write-sub --sub-langs iw --embed-subs
  --restrict-filenames -o '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'
  --convert-subs <FORMAT>    {c('srt|ass|vtt|lrc')}
  --recode-video <FORMAT>    {c('mp4|flv|ogg|webm|mkv|avi')}
  --audio-quality <QUALITY>  {c('VBR: 0 (better) to 9 (worse); CBR: 128K')}
  -x, --extract-audio        {c('only audio')}
  --audio-format <FORMAT>    {c('"best", "aac", "flac", "mp3", "m4a", "opus", "vorbis", or "wav"; "best" by default; No effect without -x')}
  -o, --output <TEMPLATE>
 
  -s, --simulate             {c('Do not download the video and do not write anything to disk')}
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
      --listen=
    
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
    -i, --include FILES_GLOB
    -x, --exclude FILES_GLOB
    -v, --verbose
    -<int>  {c('0: no compression; 9: most compression')}

  {h2('examples')}
    zip -r -9 'outfile' . -i "somedir/*"
    zip -r -9 'out' 'vid.mkv'
    """
