## Option(Parameter)
  // https://click.palletsprojects.com/en/8.0.x/options/
  ```python
  @click.option('-s', '--string-to-echo', 'variable_name',
                help: str = None,
                metavar=None,                # How it's displayed 
                required=False,
                show_default: str | bool = False,     # if a str, show it instead of value

                type: type | tuple = None,   # e.g type=int, type=(str, int), 
                                               # type=click.Choice(...), type=click.types.INT
                show_choices=False,          # if type is Choice

                is_flag=False,
                flag_value=False,
                multiple=False,
                count=False,                 # Increment and int

                prompt: bool | str = False,
                confirmation_prompt: bool | str = False,
                prompt_required: bool = False,
                hide_input: bool = False,

                allow_from_autoenv=False,    # ?
                show_envvar=False,

                hidden: bool = False,

                ...
                )
  ```

  ### Example
    #### Multi-value options         // Tuple
      ```python
      @click.option('--pos', nargs=2)
      def findme(pos):
        click.echo('%s / %s' % pos)

      >>> findme --pos 2.0 3.0
      ```

    #### Multiple options            // Tuple[T]
      ```python
      @click.option('--message', '-m', multiple=True, type=T)
      def commit(message):
        click.echo('\\n'.join(message))

      >>> commit -m foo -m bar
      ```

    #### Boolean Flags
      ```python
      @click.option('--shout/--no-shout')
      def info(shout):  # Pass either

      @click.option('--shout', is_flag=True)
      def info(shout):  # --shout -> True
      ```

    #### Feature Switches            // Multiple options
      ```python 2
      @click.option('--upper', 'transformation', flag_value='upper', default=True)
      @click.option('--lower', 'transformation', flag_value='lower')

    #### Prompt
      ```python 1
      @click.option('--name', prompt='Your name please')

    #### Dynamic Defaults
      ```python 3
      @click.option('--username', prompt=True,
              default=lambda: os.environ.get('USER', ''),
              show_default='current user')