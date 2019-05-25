"""
Process parsed objdumps and/or histograms to generate statistics.
"""
import sys
import pandas as pd
import logging

from collections import defaultdict

from . import code, objdump
from .fusion import opportunities, checkers

module = "process"  # sys.modules['__main__'].__file__
log = logging.getLogger(module)


def process_static(dump):
    """
    Find the number of fusion opportunities that exist statically in a binary
    i.e. don't multiply by the number of times each thing actually happens in
    a particular execution. This is useful for observing the effect of compiler
    changes.
    """
    blocks = code.find_basic_blocks(objdump.parse_objdump(dump)[0])

    neighbour_count = {x: 0 for x in opportunities}
    limit_count = {x: 0 for x in opportunities}

    distances = {x: [] for x in opportunities}

    for block in blocks:
        for x in opportunities:
            neighbours, limit, distance = checkers[x](block)

            neighbour_count[x] += len(neighbours)
            limit_count[x] += len(limit)

            distances[x].extend(distance)

    return neighbour_count, limit_count, distances


def process_dynamic(dump, histograms, do_limit=False):
    """
    Find the number of fusion opportunities encountered in a specific run of a program.
    This is equivalent to computing the 'effective' instruction count, after fusion is
    performed.
    """
    if do_limit:
        log.debug("Performing limit study.")

    assert len(histograms) > 0

    dump, dump_df = objdump.parse_objdump(dump)
    blocks = code.find_basic_blocks(dump)
    address_count = defaultdict(lambda: {x: 0 for x in opportunities})

    limit_count = 0

    for block in blocks:
        for x in opportunities:
            neighbours, limit, _ = checkers[x](block)

            for addr in neighbours:
                address_count[addr][x] = 1

            if do_limit:
                for addr in limit:
                    limit_count += 1
                    address_count[addr][x] = 1

    df_hist = None

    for histogram in histograms:
        df = code.load_histogram(histogram)

        if df_hist is None:
            df_hist = df
        else:
            df_hist = df.add(df_hist, fill_value=0)

    assert df_hist is not None

    # find out how many instructions were executed in this run within the particular
    # binary.
    total = df_hist.join(dump_df, how="inner").sum()["count"]

    addresses = pd.DataFrame.from_dict(address_count, orient="index")

    # Most addresses in the histogram should be in `addresses`, the only exceptions being
    # addresses in the proxy kernel. Hence we should inner join to make sure we only pick
    # addresses in the binary that are executed.
    df = df_hist.join(addresses, how="inner")

    for x in opportunities:
        df[x] *= df["count"]

    return df, total
