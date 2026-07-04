from graph.debate_graph import run_debate

result = run_debate(
    case_text='45 year old male, crushing chest pain radiating to left arm, sweating heavily, heart rate 110, blood pressure 90/60',
    user_diagnosis='I think this is a heart attack',
    severity_flag='serious',
    mode='doctor'
)

print('=== FULL DEBATE TRANSCRIPT ===')
for entry in result['debate_log']:
    print(f"\n--- {entry['agent_name'].upper()} (Round {entry['round_number']}) ---")
    print(entry['response'])
    print()

print('\n=== FINAL VERDICT ===')
print(result['final_verdict'])

print('\n=== COMPARISON ===')
print(result['comparison_result']['response'])