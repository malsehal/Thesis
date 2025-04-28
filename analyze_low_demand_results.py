import pandas as pd

# Path to the results CSV file
csv_path = "results/low_demand/event_driven_results_low.csv"

# Load the CSV file
df = pd.read_csv(csv_path)

def flag_inconsistencies(row):
    issues = []
    # 1. Interference in Centralized/No Mitigation
    if row.get('coordination_mode') == 'Centralized' and row.get('interference_mitigation') == 'No Mitigation':
        if row.get('Num_Interfering_Assignments', 0) > 0:
            issues.append("Interference in Centralized/No Mitigation mode.")
    # 2. Blocking probability logic
    if row.get('Requests_Total', 0) > 0:
        blocking_prob = row.get('Blocking_Prob', 0)
        denied = row.get('Requests_Denied', 0)
        total = row.get('Requests_Total', 1)
        expected_blocking = denied / total
        if abs(blocking_prob - expected_blocking) > 0.01:
            issues.append("Blocking_Prob does not match Requests_Denied/Requests_Total.")
    # 3. Mean Quality check
    if not (0 <= row.get('Mean_Quality', 1) <= 1):
        issues.append("Mean_Quality out of [0,1] range.")
    # 4. SUE and Correct_SUE should be close
    if abs(row.get('SUE', 0) - row.get('Correct_SUE', 0)) > 0.1:
        issues.append("SUE and Correct_SUE differ by > 0.1.")
    # 5. Negative or zero active users with nonzero granted requests
    if row.get('Total_Active_Users', 0) <= 0 and row.get('Requests_Total', 0) > 0:
        issues.append("Zero or negative active users despite granted requests.")
    # 6. Interference rate vs. number interfering
    if row.get('Num_Interfering_Assignments', 0) > 0 and row.get('Interference_Rate', 0) == 0:
        issues.append("Nonzero interfering assignments but zero interference rate.")
    # 7. Coordination cost in Manual mode
    if row.get('licensing_mode') == 'Manual' and row.get('Coordination_Cost', 0) > 0:
        issues.append("Coordination cost in Manual licensing mode (should typically be zero).")
    return issues

# Analyze each row
for idx, row in df.iterrows():
    issues = flag_inconsistencies(row)
    if issues:
        print(f"Row {idx} (arch_id: {row.get('architecture_id', 'N/A')}):")
        for issue in issues:
            print(f"  - {issue}")
        print("-" * 60)

print("Analysis complete.")

# New: Group by coordination cost, blocking probability, and correct SUE
def print_group_counts(df, metric_name, display_name=None):
    display_name = display_name or metric_name
    value_counts = df[metric_name].value_counts().sort_index()
    print(f"\nNumber of architectures sharing the same {display_name}:")
    for value, count in value_counts.items():
        print(f"  {display_name} = {value}: {count} architectures")
        # Optionally, print a few example architectures
        example_archs = df[df[metric_name] == value]["architecture_id"].head(3)
        for example in example_archs:
            print(f"    Example: {example}")
        if count > 3:
            print(f"    ...and {count-3} more.")

print_group_counts(df, 'Coordination_Cost', 'Coordination Cost')
print_group_counts(df, 'Blocking_Prob', 'Blocking Probability')
print_group_counts(df, 'Correct_SUE', 'Correct SUE')
