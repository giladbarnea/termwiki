from termwiki.render.decorators import style, alias

def no_return():
    diet = f"""## Diet
    Bad: sugary foods
    Probably: oligoantigenic (unless avoiding food X then coming back makes you allergic to it). Lancet study.
    Omega3 (>1g EPA, fish oil). studies: effects are significant but modest, or no effect, but safe to assume helps lower dosage of meds.
      Modulaitng dopamine, makes it more available.
    """
    behavior = f"""## Behavior
    """
    cognitive = mental = f"""## Cognitive / Mental
    Open monitoring (vs soda-straw focus): 
      Higher time framerate. Can see 2 waldos. 

    Meditation (15m) - focus on breathing and body-scan
      Signif. reduced attentional blinks
    """
    with_underscore = f"""with underscore"""
    _leading_underscore = "leading underscore"
    _WITH_UPPERCASE = "with uppercase"

def no_return_no_assignment():
    f"""a rogue string"""

def _WITH_UPPERCASE_FUNCTION():
    return "with uppercase function"


@style('friendly')
def with_style_friendly_decorator():
    return "with @style('friendly') decorator"


@style(python='friendly')
def with_style_python_friendly_decorator():
    return "with @style(python='friendly') decorator"


@alias('with_alias', 'another alias')
def with_alias_decorator():
    return "with @alias('with_alias') decorator"

def bash():
    return "pages.py bash() function"