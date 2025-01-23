"""
Test scenarios of pages with the same name but their relation is not
straightforward, e.g not directly aside or directly below; either as
a result of actual structure, or because of fuzzing etc.

For example:

`tw python typing` ->
python/
├── types.py
│   ├── typing = ....
pages.py
├── python()
│   ├── logging = ...


Note: should test product of these scenarios:
- exact name match is found in different places (e.g. replace 'logging' with 'typing')
- only after fzfing, exact name match is found in different places
- bait deep_search with 1 'easy' page, and another somewhere deep and far,
    and expect to find both.

https://docs.google.com/spreadsheets/d/1Pj0zUSd-zPTDLsOJl6ufXFrXObeKRGwhmMT0qB3oFOk/edit?usp=sharing
"""
