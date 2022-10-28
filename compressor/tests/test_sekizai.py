from django.template import Template
from django.test import TestCase
from sekizai.context import SekizaiContext


class TestSekizaiCompressorExtension(TestCase):
    """
    Test case for Sekizai extension.
    """

    def test_postprocess_js(self):
        template_string = """
{% load static compress sekizai_tags %}
{% addtoblock "js" %}<script src="{% static 'js/one.js' %}" type="text/javascript"></script>{% endaddtoblock %}
{% addtoblock "js" %}<script async="async" defer="defer" src="https://maps.googleapis.com/maps/api/js?key={{ apiKey }}"></script>{% endaddtoblock %}
{% addtoblock "js" %}<script src="{% static 'js/two.js' %}" type="text/javascript"></script>{% endaddtoblock %}
{% addtoblock "js" %}<script src="https://code.jquery.com/jquery-3.3.1.min.js" type="text/javascript"></script>{% endaddtoblock %}
{% addtoblock "js" %}<script src="{% static 'js/three.js' %}" type="text/javascript"></script>{% endaddtoblock %}
{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}"""
        template = Template(template_string)
        context = SekizaiContext({"apiKey": "XYZ"})
        html = template.render(context).strip()
        self.assertEqual(
            html,
            """<script src="https://code.jquery.com/jquery-3.3.1.min.js" type="text/javascript"></script>
<script src="/static/CACHE/js/output.e682d84f6b17.js"></script>
<script async="async" defer="defer" src="https://maps.googleapis.com/maps/api/js?key=XYZ"></script>""",
        )

    def test_postprocess_css(self):
        template_string = """
{% load static compress sekizai_tags %}
{% addtoblock "css" %}<link href="{% static 'css/one.css' %}" rel="stylesheet" type="text/css" />{% endaddtoblock %}
{% addtoblock "css" %}<link href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.5/css/select2.min.css" rel="stylesheet" type="text/css" />{% endaddtoblock %}
{% addtoblock "css" %}<link href="{% static 'css/two.css' %}" rel="stylesheet" type="text/css" />{% endaddtoblock %}
{% render_block "css" postprocessor "compressor.contrib.sekizai.compress" %}"""
        template = Template(template_string)
        context = SekizaiContext()
        html = template.render(context).strip()
        self.assertEqual(
            html,
            """<link href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.5/css/select2.min.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/static/CACHE/css/output.44f040b05f91.css" type="text/css">""",
        )
