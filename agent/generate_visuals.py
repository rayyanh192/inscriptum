"""
Generate Visual Metrics - Create charts for demo

Requires: pip install matplotlib
"""

import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json
import os


async def generate_visuals():
    """Generate visual charts from real data."""
    
    # Initialize Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate('convo/firebase-service-account.json')
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    
    print("📊 Generating visual metrics...")
    
    # Load proof data
    if os.path.exists('proof_for_demo.json'):
        with open('proof_for_demo.json', 'r') as f:
            data = json.load(f)
    else:
        print("❌ Run extract_proof.py first to generate proof_for_demo.json")
        return
    
    # Create figure with 4 subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Self-Learning Email Agent - Real Performance Metrics', fontsize=16, fontweight='bold')
    
    # 1. Accuracy Improvement
    weeks = ['Week 1\n(oldest)', 'Week 2', 'Week 3\n(recent)']
    accuracy_values = [
        data['accuracy']['week_1'] * 100,
        data['accuracy']['week_2'] * 100,
        data['accuracy']['week_3'] * 100
    ]
    
    bars1 = ax1.bar(weeks, accuracy_values, color=['#ff6b6b', '#feca57', '#48dbfb'])
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.set_title('Accuracy Improvement Over Time', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.axhline(y=70, color='gray', linestyle='--', alpha=0.5, label='Target: 70%')
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # Add improvement annotation
    improvement = accuracy_values[2] - accuracy_values[0]
    ax1.annotate(f'+{improvement:.1f}%', 
                xy=(2, accuracy_values[2]), 
                xytext=(1.5, accuracy_values[2] + 10),
                arrowprops=dict(arrowstyle='->', color='green', lw=2),
                fontsize=12, color='green', fontweight='bold')
    
    # 2. Confidence Growth
    confidence_values = [
        data['confidence']['week_1'] * 100,
        data['confidence']['week_2'] * 100,
        data['confidence']['week_3'] * 100
    ]
    
    ax2.plot(weeks, confidence_values, marker='o', linewidth=3, markersize=10, color='#5f27cd')
    ax2.fill_between(range(len(weeks)), confidence_values, alpha=0.3, color='#5f27cd')
    ax2.set_ylabel('Confidence (%)', fontsize=12)
    ax2.set_title('Agent Confidence Growth', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for i, val in enumerate(confidence_values):
        ax2.text(i, val + 3, f'{val:.1f}%', ha='center', fontweight='bold')
    
    # 3. Learned Rules
    rules_data = data['top_rules'][:5]
    rule_names = [f"Rule {i+1}" for i in range(len(rules_data))]
    times_used = [r['times_used'] for r in rules_data]
    
    bars3 = ax3.barh(rule_names, times_used, color=['#00d2d3', '#1abc9c', '#2ecc71', '#3498db', '#9b59b6'])
    ax3.set_xlabel('Times Used', fontsize=12)
    ax3.set_title('Top Learned Rules by Usage', fontsize=14, fontweight='bold')
    ax3.invert_yaxis()
    
    # Add value labels
    for i, bar in enumerate(bars3):
        width = bar.get_width()
        accuracy = rules_data[i]['accuracy'] * 100
        ax3.text(width + 1, bar.get_y() + bar.get_height()/2.,
                f'{int(width)} uses ({accuracy:.0f}% acc)',
                va='center', fontweight='bold')
    
    # 4. Exploration Success Rate
    exploration = data['exploration']
    labels = ['Validated\n(Worked)', 'Rejected\n(Failed)']
    sizes = [exploration['validated'], exploration['rejected']]
    colors = ['#2ecc71', '#e74c3c']
    explode = (0.1, 0)
    
    wedges, texts, autotexts = ax4.pie(sizes, explode=explode, labels=labels, colors=colors,
                                        autopct='%1.0f%%', shadow=True, startangle=90,
                                        textprops={'fontsize': 12, 'fontweight': 'bold'})
    ax4.set_title('Exploration Success Rate', fontsize=14, fontweight='bold')
    
    # Add total in center
    total = sum(sizes)
    success_rate = (exploration['validated'] / total * 100) if total > 0 else 0
    ax4.text(0, 0, f'{success_rate:.0f}%\nSuccess', 
            ha='center', va='center', fontsize=20, fontweight='bold', color='darkgreen')
    
    plt.tight_layout()
    
    # Save
    output_file = 'learning_metrics_visual.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Saved visual metrics to: {output_file}")
    
    # Generate summary table
    print("\n" + "="*70)
    print("📊 VISUAL PROOF GENERATED")
    print("="*70)
    print(f"""
Charts created:
1. Accuracy Improvement: {accuracy_values[0]:.1f}% → {accuracy_values[2]:.1f}% (+{improvement:.1f}%)
2. Confidence Growth: {confidence_values[0]:.1f}% → {confidence_values[2]:.1f}%
3. Top Learned Rules: Showing {len(rules_data)} most-used rules
4. Exploration Success: {success_rate:.0f}% of experiments worked

Use {output_file} in your presentation!
""")


if __name__ == '__main__':
    try:
        asyncio.run(generate_visuals())
    except ImportError:
        print("❌ matplotlib not installed")
        print("Run: pip install matplotlib")
