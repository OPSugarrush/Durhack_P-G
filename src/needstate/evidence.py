"""Shared action-readiness rules for category changes across all views."""
def supported_change(evidence):
    e = evidence
    return bool(e.get('buyers',0)>=20 and e.get('category_buyers',0)>=10
                and e.get('q',1)<.05 and (e.get('low',0)>0 or e.get('high',0)<0)
                and ((e.get('up',0)>e.get('down',0) and e.get('change',0)>0)
                     or (e.get('down',0)>e.get('up',0) and e.get('change',0)<0)))
