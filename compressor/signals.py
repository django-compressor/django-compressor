import django.dispatch


post_compress = django.dispatch.Signal(providing_args=['type', 'mode', 'context'])
