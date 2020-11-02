import django.dispatch

# arguments: type, mode, context
post_compress = django.dispatch.Signal()
