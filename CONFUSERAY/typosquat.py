def _edit_distance(a, b):
    """Standard DP Levenshtein distance."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))

    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp

    return dp[n]


def check_typosquat(name, internal_names, threshold=2):
    
    best_name = None
    best_dist = threshold + 1

    for internal in internal_names:
        if name == internal:
            continue
        dist = _edit_distance(name, internal)
        if dist <= threshold and dist < best_dist:
            best_dist = dist
            best_name = internal

    return best_name


def find_typosquats(dependencies, internal_names, threshold=2):
    
    results = {}
    for name, _spec, _meta in dependencies:
        match = check_typosquat(name, internal_names, threshold)
        if match:
            results[name] = match
    return results
