"""Discover and replicate product pairs among comparable trips."""
from itertools import combinations

import numpy as np
from scipy.stats import norm

from needstate.baskets.construction import build_basket_matrix
from needstate.patterns.stats import benjamini_hochberg


def period_pairs(matrix, mask):
    """Conditional independence within a buyer's trips of identical basket size.

    With fixed marginal counts, overlap has hypergeometric mean and variance.
    Singletons and invariant products supply no variance or excess.
    """
    trips = matrix.receipts.loc[mask].copy()
    trips["size"] = matrix.X[mask].sum(axis=1)
    shape = (len(matrix.entities), len(matrix.entities))
    observed, expected, variance, buyers = (np.zeros(shape) for _ in range(4))
    for _, history in trips.groupby("customer_id"):
        buyer_excess = np.zeros(shape)
        for _, group in history.groupby("size"):
            n = len(group)
            if n < 2:
                continue
            items = matrix.X[group.index].astype(float)
            ids = np.flatnonzero(items.any(axis=0))
            items = items[:, ids]
            count = items.sum(axis=0)
            actual = items.T @ items
            mean = np.outer(count, count) / n
            variation = count * (n - count) / n
            ix = np.ix_(ids, ids)
            observed[ix] += actual
            expected[ix] += mean
            variance[ix] += np.outer(variation, variation) / (n - 1)
            buyer_excess[ix] += actual - mean
        buyers += buyer_excess > 1e-8
    i,j = np.triu_indices(len(matrix.entities), 1)
    excess = observed[i,j] - expected[i,j]
    sd = np.sqrt(variance[i,j])
    z = np.divide(excess - .5, sd, out=np.full_like(sd,-np.inf), where=sd>0)
    q = benjamini_hochberg(norm.sf(z))
    pairs = {}
    for k in np.flatnonzero((observed[i,j]>=4) & (expected[i,j]>=3) & (buyers[i,j]>=2) & (q<=.05)):
        a,b = i[k],j[k]
        lift = observed[a,b]/expected[a,b]
        if lift >= 1.25:
            pairs[(matrix.entities[a],matrix.entities[b])] = round(float(lift),3)
    return pairs


def replicated_pairs(lines):
    matrix = build_basket_matrix(lines)
    dates = matrix.receipts.timestamp.dt.normalize()
    midpoint = dates.min() + (dates.max()-dates.min())/2
    early = period_pairs(matrix, dates <= midpoint)
    late = period_pairs(matrix, dates > midpoint)
    confirmed = {pair:min(early[pair],late[pair]) for pair in early.keys() & late.keys()}
    return confirmed, early.keys() ^ late.keys()


def group_status(families, confirmed, variable):
    pairs = set(combinations(sorted(families),2))
    if not pairs:
        return "Single product"
    if pairs & variable:
        return "Uncertain · some pairings qualified in only one period"
    if pairs <= confirmed.keys():
        return "All pairs repeated across both periods"
    if pairs & confirmed.keys():
        return "Some pairs repeated across both periods"
    return "Suggested by product functions or categories"
