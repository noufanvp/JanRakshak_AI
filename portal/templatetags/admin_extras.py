"""Custom Django template filters for the admin panel."""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Allow dict access with a variable key in templates: {{ dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.filter
def pct(value, total):
    """Return percentage string: {{ value|pct:total }}"""
    try:
        return round((float(value) / float(total)) * 100, 1) if total else 0
    except (TypeError, ZeroDivisionError):
        return 0
