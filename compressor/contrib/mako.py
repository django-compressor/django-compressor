#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mako.runtime import supports_caller
from compressor.templatetags.compress import compress as compressor


class NodeMock(object):
    def __init__(self, content, *args, **kwargs):
        self.content = content

    def render(self, *args, **kwargs):
        return self.content


class ParserMock(object):
    def __init__(self, body, *args, **kwargs):
        self.body = body

    def parse(self, *args, **kwargs):
        return NodeMock(self.body)

    def delete_first_token(self, *args, **kwargs):
        pass


class TokenMock(object):
    def __init__(self, *args, **kwargs):
        self.args = args

    def split_contents(self, *args, **kwargs):
        return self.args


@supports_caller
def compress(context, **kwargs):
    try:
        # Those arguments are mandatory to parse template fragment
        # and should be provided by mako
        capture = context['capture']
        caller = context['caller']
    except KeyError:
        return ''

    parser = ParserMock(capture(caller.body))

    # `kind` is mandatory for django-compressor. but `kwargs.get` will return
    # None if not provided, so `django-compressor` can handle the error
    args = ['compress', kwargs.get('kind')]

    if 'mode' in kwargs:
        args.append(kwargs['mode'])
        if 'name' in kwargs:
            args.append(kwargs['name'])

    token = TokenMock(*args)
    return compressor(parser, token).render({})


@supports_caller
def css(context, **kwargs):
    kwargs['kind'] = 'css'
    return compress(context, **kwargs)


@supports_caller
def js(context, **kwargs):
    kwargs['kind'] = 'js'
    return compress(context, **kwargs)
