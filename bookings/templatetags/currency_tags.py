from django import template

register = template.Library()

RATES = {
    'INR': {'symbol': '₹', 'rate': 1.0},
    'USD': {'symbol': '$', 'rate': 0.012},  # 1 INR = 0.012 USD
    'EUR': {'symbol': '€', 'rate': 0.011},  # 1 INR = 0.011 EUR
}

@register.filter
def currency(value, request):
    """
    Converts amount based on request.session['currency']
    """
    try:
        val = float(value)
    except (ValueError, TypeError):
        val = 0.0

    curr = 'INR'
    if request and hasattr(request, 'session'):
        curr = request.session.get('currency', 'INR')

    info = RATES.get(curr, RATES['INR'])
    converted = val * info['rate']

    if converted == int(converted):
        return f"{info['symbol']}{int(converted):,}"
    return f"{info['symbol']}{converted:,.2f}"
