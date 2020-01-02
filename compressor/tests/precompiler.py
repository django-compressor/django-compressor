#!/usr/bin/env python
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
        with open(options.filename) as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    content = content.replace('background:', 'color:')

    if options.outfile:
        with open(options.outfile, 'w') as f:
            f.write(content)
    else:
        print(content)


if __name__ == '__main__':
    main()
