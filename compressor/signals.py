import django.dispatch


post_compress = django.dispatch.Signal(providing_args=['name', 'type', 'mode', 'context'])
