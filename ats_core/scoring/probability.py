def map_probability(edge, prior_up, Q):
    p_up = prior_up + 0.35*edge*Q
    p_up = max(0.0, min(1.0, p_up))
    return p_up, 1.0 - p_up