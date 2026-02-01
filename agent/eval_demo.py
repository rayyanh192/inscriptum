"""
Quick Demo: How Weave Evaluations Show Improvement

This shows the CONCEPT without running the full agent (much faster).
"""

print("\n" + "="*70)
print("🎯 WEAVE EVALUATIONS - HOW IT WORKS")
print("="*70)

print("\n📝 Test Set: 5 Emails (Same Every Time)")
print("-"*70)

test_cases = [
    ("Boss urgent request", "reply", "High priority"),
    ("Newsletter", "archive", "Low priority"),
    ("Recruiter", "reply", "Medium priority"),
    ("Professor notice", "archive", "Low urgency"),
    ("Friend dinner invite", "reply", "Time-sensitive")
]

for i, (email, expected, note) in enumerate(test_cases, 1):
    print(f"  {i}. {email:30} → Expected: {expected:10} ({note})")

print("\n" + "="*70)
print("📊 EVALUATION RUNS - See Improvement Over Time")
print("="*70)

runs = [
    {
        "run": 1,
        "when": "Baseline (Today)",
        "accuracy": 40,
        "results": ["❌", "✅", "❌", "✅", "❌"],
        "note": "Agent guessing, no training"
    },
    {
        "run": 2,
        "when": "After 1 Week (Training)",
        "accuracy": 60,
        "results": ["❌", "✅", "✅", "✅", "❌"],
        "note": "Learned newsletters = archive"
    },
    {
        "run": 3,
        "when": "After 2 Weeks (More Training)",
        "accuracy": 80,
        "results": ["✅", "✅", "✅", "✅", "❌"],
        "note": "Learned boss emails = urgent"
    },
    {
        "run": 4,
        "when": "After 1 Month (Fully Trained)",
        "accuracy": 100,
        "results": ["✅", "✅", "✅", "✅", "✅"],
        "note": "All patterns learned!"
    }
]

for run_data in runs:
    print(f"\n🔄 RUN {run_data['run']}: {run_data['when']}")
    print(f"   Accuracy: {run_data['accuracy']}%")
    print(f"   Results: {' '.join(run_data['results'])}")
    print(f"   Note: {run_data['note']}")

print("\n" + "="*70)
print("📈 IMPROVEMENT CHART")
print("="*70)

print("\nAccuracy Over Time:")
for run_data in runs:
    bar = "█" * (run_data['accuracy'] // 5)
    print(f"  Run {run_data['run']}: {bar} {run_data['accuracy']}%")

improvement = runs[-1]['accuracy'] - runs[0]['accuracy']
print(f"\n✅ TOTAL IMPROVEMENT: +{improvement}% (from {runs[0]['accuracy']}% → {runs[-1]['accuracy']}%)")

print("\n" + "="*70)
print("🎯 HOW TO USE THIS")
print("="*70)

print("""
1. Run evaluation script: `python agent/evaluation_pipeline.py`
   → Saves baseline to Weave

2. Use the bot for 1 week
   → Give feedback when agent is wrong
   → Let agent learn patterns

3. Re-run evaluation: `python agent/evaluation_pipeline.py`
   → Tests on SAME 5 emails
   → Compare to baseline in Weave

4. See improvement:
   → Week 1: 40% → Week 2: 60% → Week 3: 80%
   → This proves the agent learned! ✅

View all runs at:
https://wandb.ai/inscriptum85-inscriptum/email-agent/weave

Look for "Evaluations" tab to compare runs side-by-side.
""")

print("="*70)
print("💡 WHY THIS IS BETTER THAN DASHBOARD")
print("="*70)

comparison = [
    ("Shows improvement", "After 2+ hours", "Immediately"),
    ("Test consistency", "Different emails", "Same emails"),
    ("Proof quality", "Weak (time-based)", "Strong (A/B test)"),
    ("Clear metric", "Confidence %", "Accuracy %"),
]

print(f"\n{'Feature':<20} | {'Dashboard':<20} | {'Evaluations':<20}")
print("-" * 70)
for feature, dashboard, evals in comparison:
    print(f"{feature:<20} | {dashboard:<20} | {evals:<20}")

print("\n✅ Use evaluations to prove learning!")
print("✅ Use dashboard for real-time monitoring!\n")
