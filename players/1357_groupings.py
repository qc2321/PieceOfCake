from itertools import combinations

def find_ratio_groupings(requests, m, tolerance):
    # define target ratios for each group size
    if m == 2:
        target_ratios = [1, 3]
    elif m == 3:
        target_ratios = [1, 3, 5]
    else:
        target_ratios = [1, 3, 5, 7]
    
    # normalize target ratios to compare with actual values in group
    target_sum = sum(target_ratios)
    normalized_ratios = [ratio / target_sum for ratio in target_ratios]
    
    requests.sort()
    valid_groupings = []
    
    def is_valid_group(group):
        """Check if a group meets the required ratio within tolerance."""
        group_sum = sum(group)
        normalized_group = [val / group_sum for val in group]
        return all(
            abs(nr - ng) <= tolerance for nr, ng in zip(normalized_ratios, normalized_group)
        )
    
    def backtrack(remaining_requests, current_grouping):
        """Backtracking function to find the valid groupings."""
        if not remaining_requests:
            valid_groupings.append(current_grouping)
            return True

        # try forming groups from the remaining requests
        for group in combinations(remaining_requests, m):
            if is_valid_group(group):
                new_remaining = remaining_requests[:]
                for num in group:
                    new_remaining.remove(num)
                # recur with the new list and updated grouping
                if backtrack(new_remaining, current_grouping + [group]):
                    return True
        
        return False
    
    # start backtracking
    backtrack(requests, [])
    
    return valid_groupings

# Example
requests = [12, 36, 60, 15, 45, 75, 21, 63, 100, 11, 54, 70]
m = 3
T = .10

valid_groupings = find_ratio_groupings(requests, m, T)
print("Valid groupings:", valid_groupings)
