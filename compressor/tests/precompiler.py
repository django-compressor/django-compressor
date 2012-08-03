#!/usr/bin/env python
from __future__ import with_statement
import optparse
import sys


def main():
    p = optparse.OptionParser()
    p.add_option('-f', '--file', action="store",
                type="string", dest="filename",
                help="File to read from, defaults to stdin", default=None)
    p.add_option('-o', '--output', action="store",
                type="string", dest="outfile",
                help="File to write to, defaults to stdout", default=None)

    options, arguments = p.parse_args()

    if options.filename:
        f = open(options.filename)
        content = f.read()
        f.close()
    else:
        content = sys.stdin.read()

    content = content.replace('background:', 'color:')

    if options.outfile:
        with open(options.outfile, 'w') as f:
            f.write(content)
    else:
        print content


if __name__ == '__main__':
    main()
