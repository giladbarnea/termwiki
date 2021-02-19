from typing import Iterable, List


def has_duplicates(collection) -> bool:
    return len(set(collection)) < len(collection)


def get_duplicates(collection: Iterable):
    uniq = set()
    duplicates = []
    for item in collection:
        if item in uniq:
            duplicates.append(item)
        else:
            uniq.add(item)
    return duplicates


def remove_duplicates(collection: Iterable) -> List:
    without_duplicates = []
    for item in collection:
        if item not in without_duplicates:
            without_duplicates.append(item)
    return without_duplicates


def difference(coll1: Iterable, coll2: Iterable) -> List:
    diff = []
    for item in coll1:
        if item not in coll2:
            diff.append(item)
    return diff


def intersection(coll1: Iterable, coll2: Iterable) -> List:
    inter = []
    for item in coll1:
        if item in coll2:
            inter.append(item)
    return inter
