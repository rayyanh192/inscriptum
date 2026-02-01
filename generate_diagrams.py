#!/usr/bin/env python3
"""Generate demo infographics for Inscriptum"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')
print("Generating demo infographics...")

# ============================================
# 1. SYSTEM ARCHITECTURE DIAGRAM
# ============================================
fig, ax = plt.subplots(figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_title('Inscriptum: System Architecture', fontsize=24, fontweight='bold', pad=20)

colors = {'gmail': '#EA4335', 'discord': '#5865F2', 'firebase': '#FFCA28', 'agent': '#4285F4', 'llm': '#34A853'}

# Gmail API Box
gmail = FancyBboxPatch((0.5, 6), 3, 2.5, boxstyle="round,pad=0.1", facecolor=colors['gmail'], alpha=0.9, edgecolor='black', linewidth=2)
ax.add_patch(gmail)
ax.text(2, 7.6, 'Gmail API', fontsize=14, fontweight='bold', ha='center', color='white')
ax.text(2, 7.0, 'OAuth2 Auth', fontsize=11, ha='center', color='white')
ax.text(2, 6.5, 'Fetch Emails', fontsize=11, ha='center', color='white')

# Discord Bot Box
discord = FancyBboxPatch((0.5, 1.5), 3, 2.5, boxstyle="round,pad=0.1", facecolor=colors['discord'], alpha=0.9, edgecolor='black', linewidth=2)
ax.add_patch(discord)
ax.text(2, 3.1, 'Discord Bot', fontsize=14, fontweight='bold', ha='center', color='white')
ax.text(2, 2.5, 'User Interface', fontsize=11, ha='center', color='white')
ax.text(2, 2.0, 'Feedback Loop', fontsize=11, ha='center', color='white')

# Firebase Box
firebase = FancyBboxPatch((6, 3.5), 4, 3, boxstyle="round,pad=0.1", facecolor=colors['firebase'], alpha=0.9, edgecolor='black', linewidth=2)
ax.add_patch(firebase)
ax.text(8, 5.8, 'Firebase Firestore', fontsize=14, fontweight='bold', ha='center')
ax.text(8, 5.1, 'emails collection', fontsize=11, ha='center')
ax.text(8, 4.6, 'people collection', fontsize=11, ha='center')
ax.text(8, 4.1, 'learned_rules', fontsize=11, ha='center')

# Agent Box
agent = FancyBboxPatch((12, 5.5), 3.5, 3, boxstyle="round,pad=0.1", facecolor=colors['agent'], alpha=0.9, edgecolor='black', linewidth=2)
ax.add_patch(agent)
ax.text(13.75, 7.8, 'AI Agent', fontsize=14, fontweight='bold', ha='center', color='white')
ax.text(13.75, 7.1, 'Process Emails', fontsize=11, ha='center', color='white')
ax.text(13.75, 6.6, 'Learn Rules', fontsize=11, ha='center', color='white')
ax.text(13.75, 6.1, 'Draft Responses', fontsize=11, ha='center', color='white')

# LLM Box
llm = FancyBboxPatch((12, 1.5), 3.5, 2.5, boxstyle="round,pad=0.1", facecolor=colors['llm'], alpha=0.9, edgecolor='black', linewidth=2)
ax.add_patch(llm)
ax.text(13.75, 3.3, 'Groq LLM', fontsize=14, fontweight='bold', ha='center', color='white')
ax.text(13.75, 2.6, 'llama-3.1-8b', fontsize=11, ha='center', color='white')
ax.text(13.75, 2.1, 'NL Understanding', fontsize=11, ha='center', color='white')

# Arrows
arrow_style = dict(arrowstyle='->', color='#666', lw=3, mutation_scale=20)
ax.annotate('', xy=(6, 7), xytext=(3.5, 7), arrowprops=arrow_style)
ax.text(4.75, 7.4, 'Scrape', fontsize=10, ha='center', fontweight='bold')
ax.annotate('', xy=(6, 3.5), xytext=(3.5, 2.75), arrowprops=arrow_style)
ax.text(4.75, 2.5, 'Queries', fontsize=10, ha='center', fontweight='bold')
ax.annotate('', xy=(12, 6.5), xytext=(10, 5), arrowprops=arrow_style)
ax.text(11, 6.2, 'Data', fontsize=10, ha='center', fontweight='bold')
ax.annotate('', xy=(10, 4.5), xytext=(12, 6), arrowprops=dict(arrowstyle='->', color='#06A77D', lw=2, mutation_scale=15, linestyle='dashed'))
ax.text(10.5, 5.8, 'Learn', fontsize=10, ha='center', fontweight='bold', color='#06A77D')
ax.annotate('', xy=(13.75, 5.5), xytext=(13.75, 4), arrowprops=dict(arrowstyle='<->', color='#666', lw=2, mutation_scale=15))
ax.annotate('', xy=(3.5, 3.25), xytext=(6, 4), arrowprops=dict(arrowstyle='->', color='#06A77D', lw=2, mutation_scale=15))
ax.text(4.5, 4.0, 'Results', fontsize=10, ha='center', fontweight='bold', color='#06A77D')

plt.tight_layout()
plt.savefig('diagram_architecture.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved: diagram_architecture.png")

# ============================================
# 2. LEARNING LOOP DIAGRAM
# ============================================
fig2, ax2 = plt.subplots(figsize=(14, 10))
ax2.set_xlim(0, 14)
ax2.set_ylim(0, 10)
ax2.axis('off')
ax2.set_title('Inscriptum: Self-Learning Feedback Loop', fontsize=24, fontweight='bold', pad=20)

theta = np.linspace(0, 2*np.pi, 100)
x_circle = 7 + 3.5 * np.cos(theta)
y_circle = 5 + 3.5 * np.sin(theta)
ax2.plot(x_circle, y_circle, 'k--', alpha=0.3, linewidth=2)

nodes = [
    (7, 8.8, 'New Email\nArrives', '#EA4335'),
    (10.5, 6.5, 'Agent\nProcesses', '#4285F4'),
    (10.5, 3.5, 'User\nFeedback', '#5865F2'),
    (7, 1.2, 'Learn &\nAdapt', '#34A853'),
    (3.5, 3.5, 'Update\nRules', '#FFCA28'),
    (3.5, 6.5, 'Improve\nAccuracy', '#06A77D'),
]

for i, (x, y, label, color) in enumerate(nodes):
    circle = Circle((x, y), 1.1, facecolor=color, edgecolor='black', linewidth=2, alpha=0.9)
    ax2.add_patch(circle)
    text_color = 'white' if color != '#FFCA28' else 'black'
    ax2.text(x, y, label, fontsize=11, ha='center', va='center', fontweight='bold', color=text_color)

for i in range(len(nodes)):
    start = nodes[i]
    end = nodes[(i+1) % len(nodes)]
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist = np.sqrt(dx**2 + dy**2)
    start_x, start_y = start[0] + 1.2*dx/dist, start[1] + 1.2*dy/dist
    end_x, end_y = end[0] - 1.2*dx/dist, end[1] - 1.2*dy/dist
    ax2.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y), arrowprops=dict(arrowstyle='->', color='#333', lw=2.5, mutation_scale=20))

ax2.text(7, 5, 'CONTINUOUS\nLEARNING', fontsize=16, ha='center', va='center', fontweight='bold', color='#333',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#333', linewidth=2))

plt.tight_layout()
plt.savefig('diagram_learning_loop.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved: diagram_learning_loop.png")

# ============================================
# 3. FEATURE SHOWCASE
# ============================================
fig4, ax4 = plt.subplots(figsize=(14, 10))
ax4.set_xlim(0, 14)
ax4.set_ylim(0, 10)
ax4.axis('off')
ax4.set_title('Inscriptum: Key Features', fontsize=28, fontweight='bold', pad=20, color='#333')

features = [
    (2, 7.5, 'Self-Learning', 'Learns from behavior\n(star, reply, delete)', '#4285F4'),
    (7, 7.5, 'Gmail Integration', 'Auto email scraping\nevery 5 minutes', '#EA4335'),
    (12, 7.5, 'Discord Interface', 'Natural conversation\nwith your emails', '#5865F2'),
    (2, 4, 'People Tracking', 'Tracks who matters\nbased on interactions', '#34A853'),
    (7, 4, 'Smart Search', 'Finds emails by sender\nsubject, or content', '#F77F00'),
    (12, 4, 'Privacy First', 'Your data stays in\nyour Firebase', '#06A77D'),
]

for x, y, title, desc, color in features:
    box = FancyBboxPatch((x-1.8, y-1.2), 3.6, 2.4, boxstyle="round,pad=0.15", facecolor=color, alpha=0.15, edgecolor=color, linewidth=3)
    ax4.add_patch(box)
    circle = Circle((x, y+0.5), 0.4, facecolor=color, edgecolor='white', linewidth=2)
    ax4.add_patch(circle)
    ax4.text(x, y-0.1, title, fontsize=13, ha='center', va='center', fontweight='bold', color='#333')
    ax4.text(x, y-0.7, desc, fontsize=10, ha='center', va='center', color='#555')

ax4.add_patch(FancyBboxPatch((1, 0.5), 12, 1.5, boxstyle="round,pad=0.1", facecolor='#333', alpha=0.9, edgecolor='black', linewidth=2))
ax4.text(7, 1.25, '60% to 78% Accuracy  |  10 Learned Rules  |  86+ People  |  244 Emails', fontsize=12, ha='center', va='center', color='white', fontweight='bold')

plt.tight_layout()
plt.savefig('diagram_features.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved: diagram_features.png")

# ============================================
# 4. TECH STACK
# ============================================
fig5, ax5 = plt.subplots(figsize=(12, 8))
ax5.set_xlim(0, 12)
ax5.set_ylim(0, 8)
ax5.axis('off')
ax5.set_title('Inscriptum: Technology Stack', fontsize=24, fontweight='bold', pad=20)

stack = [
    (2, 6, 'Frontend', 'Discord.js\nNode.js', '#5865F2'),
    (6, 6, 'Backend', 'Python\nExpress.js', '#4285F4'),
    (10, 6, 'AI/ML', 'Groq API\nLLaMA 3.1', '#34A853'),
    (2, 2.5, 'Database', 'Firebase\nFirestore', '#FFCA28'),
    (6, 2.5, 'APIs', 'Gmail API\nOAuth2', '#EA4335'),
    (10, 2.5, 'Infra', 'Node.js\nPython venv', '#F77F00'),
]

for x, y, category, items, color in stack:
    box = FancyBboxPatch((x-1.5, y-1), 3, 2, boxstyle="round,pad=0.1", facecolor=color, alpha=0.9, edgecolor='black', linewidth=2)
    ax5.add_patch(box)
    text_color = 'white' if color != '#FFCA28' else 'black'
    ax5.text(x, y+0.5, category, fontsize=14, ha='center', va='center', fontweight='bold', color=text_color)
    ax5.text(x, y-0.3, items, fontsize=11, ha='center', va='center', color=text_color)

plt.tight_layout()
plt.savefig('diagram_tech_stack.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved: diagram_tech_stack.png")

print()
print("=" * 50)
print("ALL DEMO INFOGRAPHICS GENERATED")
print("=" * 50)
print("diagram_architecture.png - System architecture")
print("diagram_learning_loop.png - Feedback cycle")
print("diagram_features.png - Key features")
print("diagram_tech_stack.png - Technology stack")
