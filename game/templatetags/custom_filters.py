from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplies the arg and value together."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return ''
