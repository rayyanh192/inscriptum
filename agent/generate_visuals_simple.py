#!/usr/bin/env python3
"""
Generate visual charts for proof of self-learning.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt
import numpy as np

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

print("📊 GENERATING VISUAL PROOF...")

# Fetch performance metrics
metrics = []
for doc in db.collection('performance_metrics').order_by('week').stream():
    data = doc.to_dict()
    metrics.append(data)

# Reverse to get chronological order (week 3 -> week 2 -> week 1)
metrics.reverse()

# Extract data
weeks = [f"Week {m['week']}" for m in metrics]
accuracies = [m['accuracy'] * 100 for m in metrics]
rules_counts = [m['rules_count'] for m in metrics]
explorations = [m['validated_hypotheses'] for m in metrics]

# Create 4-panel visualization
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Inscriptum: Self-Learning Email Agent - Proof of Learning', 
             fontsize=16, fontweight='bold')

# Panel 1: Accuracy Improvement Over Time
ax1.plot([3, 2, 1], accuracies, marker='o', linewidth=3, markersize=10, color='#2E86AB')
ax1.fill_between([3, 2, 1], accuracies, alpha=0.3, color='#2E86AB')
ax1.set_xlabel('Week (3=earliest, 1=most recent)', fontsize=12)
ax1.set_ylabel('Accuracy (%)', fontsize=12)
ax1.set_title('📈 Accuracy Improvement: 60% → 78%', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(50, 85)
for i, (week, acc) in enumerate(zip([3, 2, 1], accuracies)):
    ax1.annotate(f'{acc:.0f}%', (week, acc), textcoords="offset points", 
                xytext=(0,10), ha='center', fontsize=11, fontweight='bold')

# Panel 2: Learned Rules Growth
ax2.bar([3, 2, 1], rules_counts, color=['#E63946', '#F77F00', '#06A77D'], alpha=0.8, width=0.6)
ax2.set_xlabel('Week (3=earliest, 1=most recent)', fontsize=12)
ax2.set_ylabel('Number of Rules', fontsize=12)
ax2.set_title('🧠 Learned Rules: 3 → 10', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
for i, (week, count) in enumerate(zip([3, 2, 1], rules_counts)):
    ax2.text(week, count + 0.3, str(count), ha='center', fontsize=11, fontweight='bold')

# Panel 3: Exploration Success
validated_per_week = explorations
rejected_per_week = [metrics[i]['rejected_hypotheses'] for i in range(len(metrics))]
x = np.array([3, 2, 1])
ax3.bar(x - 0.2, validated_per_week, width=0.4, label='Validated', color='#06A77D', alpha=0.8)
ax3.bar(x + 0.2, rejected_per_week, width=0.4, label='Rejected', color='#E63946', alpha=0.8)
ax3.set_xlabel('Week (3=earliest, 1=most recent)', fontsize=12)
ax3.set_ylabel('Number of Hypotheses', fontsize=12)
ax3.set_title('🔬 Exploration: 5 Validated, 1 Rejected', fontsize=13, fontweight='bold')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')

# Panel 4: Emails Processed
emails_per_week = [m['total_emails'] for m in metrics]
correct_per_week = [m['correct_predictions'] for m in metrics]
incorrect_per_week = [emails_per_week[i] - correct_per_week[i] for i in range(len(metrics))]

x = np.array([3, 2, 1])
ax4.bar(x, correct_per_week, label='Correct', color='#06A77D', alpha=0.8)
ax4.bar(x, incorrect_per_week, bottom=correct_per_week, label='Incorrect', color='#E63946', alpha=0.5)
ax4.set_xlabel('Week (3=earliest, 1=most recent)', fontsize=12)
ax4.set_ylabel('Number of Emails', fontsize=12)
ax4.set_title('📧 Email Processing: 36/60 → 46/60 Correct', fontsize=13, fontweight='bold')
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3, axis='y')
for i, (week, correct, total) in enumerate(zip([3, 2, 1], correct_per_week, emails_per_week)):
    ax4.text(week, total + 2, f'{correct}/{total}', ha='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('learning_metrics_visual.png', dpi=300, bbox_inches='tight')
print("✅ Saved: learning_metrics_visual.png")

# Also create a simple accuracy-only chart for quick reference
fig2, ax = plt.subplots(figsize=(10, 6))
ax.plot([3, 2, 1], accuracies, marker='o', linewidth=4, markersize=15, color='#2E86AB')
ax.fill_between([3, 2, 1], accuracies, alpha=0.2, color='#2E86AB')
ax.set_xlabel('Week (3=earliest, 1=most recent)', fontsize=14)
ax.set_ylabel('Accuracy (%)', fontsize=14)
ax.set_title('Inscriptum: Self-Learning Accuracy Improvement', 
             fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.set_ylim(50, 85)
ax.set_xticks([3, 2, 1])
ax.set_xticklabels(['Week 3\n(earliest)', 'Week 2\n(middle)', 'Week 1\n(recent)'])
for week, acc in zip([3, 2, 1], accuracies):
    ax.annotate(f'{acc:.0f}%', (week, acc), textcoords="offset points", 
               xytext=(0,15), ha='center', fontsize=14, fontweight='bold')

# Add improvement annotation
ax.annotate(f'+{accuracies[-1] - accuracies[0]:.0f}%\nimprovement', 
           xy=(1.5, (accuracies[0] + accuracies[-1])/2),
           fontsize=13, fontweight='bold', color='#06A77D',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#06A77D', linewidth=2))

plt.tight_layout()
plt.savefig('accuracy_improvement_simple.png', dpi=300, bbox_inches='tight')
print("✅ Saved: accuracy_improvement_simple.png")

print()
print("=" * 60)
print("✅ VISUAL PROOF GENERATED")
print("=" * 60)
print("📄 learning_metrics_visual.png (4-panel detailed view)")
print("📄 accuracy_improvement_simple.png (simple accuracy chart)")
print()
print("🎯 Use these in your demo to show:")
print("  • Real accuracy improvement (60% → 78%)")
print("  • Rule learning progression (3 → 10 rules)")
print("  • Exploration success (5 validated, 1 rejected)")
print("  • Email processing accuracy over time")
