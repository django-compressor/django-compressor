try:
    import scss
except ImportError:
    raise Exception("can't find scss")


def run(css, wrap=None):
    compiler = scss.Scss()
    return compiler.compile(css)
