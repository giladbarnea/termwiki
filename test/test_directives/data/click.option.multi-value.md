A multi-value option is blablabla

```python
@click.option('--pos', nargs=2)
def findme(pos):
click.echo('%s / %s' % pos)

>>> findme --pos 2.0 3.0
```