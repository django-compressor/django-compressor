#!/usr/bin/env python
import optparse

def main():
    p = optparse.OptionParser()
    options, arguments = p.parse_args()
    
    f = open(arguments[0])
    content = f.read()
    f.close()
    
    f = open(arguments[1], 'w')
    f.write(content.replace('background:', 'color:'))
    f.close()

 
if __name__ == '__main__':
    main()
    