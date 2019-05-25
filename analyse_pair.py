"""
Analyse a pair of histogram and objdump, producing summary statistics.

Usage:
    ./analyse_pair.py [--static] [name] [cc] [histogram] [dump]

Should output
[name], [cc], [load effective address count], [index load count], [clear upper word count]
"""
import sys
import numpy as np
import logging
import argparse

from tools import objdump, process
from tools.fusion import opportunities

module = sys.modules['__main__'].__file__
log = logging.getLogger(module)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, # level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')

    parser = argparse.ArgumentParser(description='Analyse an objdump and (optionally) corresponding histogram(s).')

    parser.add_argument('dump', type=argparse.FileType('rt'), help='Objdump file')
    parser.add_argument('histograms', type=argparse.FileType('rt'), nargs='*')

    parser.add_argument('--name', help='Benchmark name', default='unknown')
    parser.add_argument('--compiler', help='Compiler used', default='unknown')
    parser.add_argument('--limit', help='Perform limit study', action='store_true')
    parser.add_argument('--percentages', help='Show percentages', action='store_true')
    parser.add_argument('--readable', help='Produce human-readable output', action='store_true')

    parser.add_argument('-v', action='count', default=0, help='Increase verbosity.')

    # Optionally provide a histogram -> this is optional, since we can give the number of static opportunities without
    # a histogram.

    args = parser.parse_args()

    log.setLevel(max(3 - args.v, 0) * 10)

    dump = args.dump
    name = args.name
    compiler = args.compiler
    histogram = args.histograms
    readable = args.readable
    percentages = args.percentages

    if len(histogram) == 0:
        log.debug('Performing static analysis.')

        neighbour_count, limit_count, distances = process.process_static(dump)

        distances = { x: np.median(y) for x, y in distances.items() }

        print('benchmark name: %s' % name)
        print('compiler: %s' % compiler)

        print('basic analysis:')

        for x in opportunities:
            print('  %s: %d' % (x, neighbour_count[x]))

        print('limit study:')

        for x in opportunities:
            print('  %s:' % x)
            print('    count: %d' % limit_count[x])
            print('    median distance: %d' % distances[x])
    else:
        log.debug('Performing dynamic analysis.')

        df, total = process.process_dynamic(dump, histogram, args.limit)
        sums = df.sum()

        if readable:
            print('Total dynamic instructions: %d' % total)

            opportunity_count = 0
            for x in opportunities:
                print('  %s: %d (%.2f %%)' % (x, sums[x], 100 * sums[x] / total))
                opportunity_count += sums[x]

            # total percentage reduction:
            print('Total reduction: %.2f %%' % (100 * opportunity_count / total))
        else:
            if percentages:
                scale = 100 / total
            else:
                scale = 1

            lea = scale * sums['lea']
            ix_ld = scale * sums['ix_ld']
            cuw = scale * sums['cuw']

            if percentages:
                print('%s,%s,%d,%.2f,%.2f,%.2f' % (name, compiler, total, lea, ix_ld, cuw))
            else:
                print('%s,%s,%d,%d,%d,%d' % (name, compiler, total, lea, ix_ld, cuw))


