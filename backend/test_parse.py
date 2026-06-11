import re

def _parse_funding_amount(text):
    text_lower = text.lower()
    amounts = []
    # Use finditer to catch all instances
    for match in re.finditer(r'\$\s*([\d,]+(?:\.\d+)?)\s*(b|m|billion|million|mn)?\b', text_lower):
        val_str = match.group(1).replace(',', '')
        suffix = match.group(2)
        try:
            val = float(val_str)
        except ValueError:
            continue
            
        # Check context after match to see if it's a valuation
        start, end = match.span()
        context_after = text_lower[end:end+20]
        if 'valuation' in context_after or 'valued' in context_after or 'appraised' in context_after:
            continue  # Skip valuations
            
        if suffix in ['b', 'billion']:
            amounts.append(val * 1000)
        elif suffix in ['m', 'million', 'mn']:
            amounts.append(val)
        else:
            # no suffix, check if raw dollars are large enough
            if val >= 1_000_000:
                amounts.append(val / 1_000_000)
            elif val >= 1:
                amounts.append(val)  # Assume it was already in millions if it's like $50
                
    if amounts:
        return amounts[0]
    return 0.0

cases = [
    "Notion Raises $200M Series F at $10B Valuation",
    "Stripe hits a $91 billion valuation amid lumpy payments growth",
    "HubSpot Raises $200M Series F at $10B Valuation",
    "CVC, EQT in talks to buy ValueLabs at $1 bn valuation",
    "Datadog raises annual forecast on strong cloud security demand; shares up 29%",
    "MongoDB vs. Datadog: Only 1 growth stock could make investors richer", # $1 is not matched due to $
    "Twilio Raises $200M Series F at $10B Valuation",
    "Company X raised $5,000,000",
    "Company Y raised $50",
]

for c in cases:
    print(f"'{c}' -> {_parse_funding_amount(c)}")
