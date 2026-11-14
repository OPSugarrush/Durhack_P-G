"""Offline evidence narrator. No API key, external calls or invented consumer motives."""
def describe_candidate(products, functions):
    return {"label": "Cross-function purchase hypothesis", "source": "evidence template",
            "description": f"Observed product group: {', '.join(products)}. Functions: {', '.join(functions)}. Investigate whether the association replicates in held-out consumers and retailers. This does not establish a shopping motivation or unmet demand."}
