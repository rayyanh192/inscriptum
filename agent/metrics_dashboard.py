"""
Live Metrics Dashboard - Real-time agent learning observability

Run alongside server.py to monitor agent learning in real-time.
Access at: http://localhost:5002/dashboard
"""

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
import os
import json

app = Flask(__name__)
CORS(app)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()


def get_learning_metrics() -> Dict:
    """Compute comprehensive learning metrics."""
    
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'learning_proof': {},
        'people_graph': {},
        'decisions': {},
        'patterns': {},
        'exploration': {}
    }
    
    # 1. LEARNED PATTERNS/RULES
    try:
        patterns_doc = db.collection('learned_patterns').document('importance').get()
        if patterns_doc.exists:
            patterns = patterns_doc.to_dict().get('rules', [])
            metrics['patterns']['total_rules'] = len(patterns)
            metrics['patterns']['recent_rules'] = [
                {
                    'description': p.get('description', 'Pattern'),
                    'confidence': p.get('confidence', 0),
                    'times_used': p.get('times_used', 0)
                }
                for p in patterns[-5:]
            ]
        else:
            metrics['patterns']['total_rules'] = 0
            metrics['patterns']['recent_rules'] = []
    except Exception as e:
        metrics['patterns']['error'] = str(e)
    
    # 2. PEOPLE KNOWLEDGE GRAPH
    try:
        people = list(db.collection('people').stream())
        metrics['people_graph']['total_people'] = len(people)
        
        # Relationship distribution
        relationship_counts = defaultdict(int)
        importance_distribution = defaultdict(int)
        
        for person in people:
            data = person.to_dict()
            rel_type = data.get('relationship', {}).get('type', 'unknown')
            relationship_counts[rel_type] += 1
            
            importance = data.get('importance_score', 0)
            if importance >= 0.8:
                importance_distribution['high'] += 1
            elif importance >= 0.5:
                importance_distribution['medium'] += 1
            else:
                importance_distribution['low'] += 1
        
        metrics['people_graph']['relationships'] = dict(relationship_counts)
        metrics['people_graph']['importance_dist'] = dict(importance_distribution)
    except Exception as e:
        metrics['people_graph']['error'] = str(e)
    
    # 3. DECISION HISTORY & CONFIDENCE
    try:
        decisions = list(db.collection('agent_decisions').limit(100).stream())
        
        if decisions:
            # Time-based analysis
            now = datetime.utcnow()
            recent = []  # Last hour
            older = []   # Older than hour
            
            action_counts = defaultdict(int)
            confidence_by_action = defaultdict(list)
            
            for dec in decisions:
                data = dec.to_dict()
                timestamp = data.get('timestamp')
                decision = data.get('decision', {})
                action = decision.get('action', 'unknown')
                confidence = decision.get('confidence', 0)
                
                action_counts[action] += 1
                confidence_by_action[action].append(confidence)
                
                if timestamp:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', ''))
                        if (now - dt).total_seconds() < 3600:
                            recent.append(confidence)
                        else:
                            older.append(confidence)
            
            metrics['decisions']['total_decisions'] = len(decisions)
            metrics['decisions']['actions'] = dict(action_counts)
            
            if recent:
                metrics['decisions']['recent_confidence'] = {
                    'avg': sum(recent) / len(recent),
                    'count': len(recent)
                }
            
            if older:
                metrics['decisions']['older_confidence'] = {
                    'avg': sum(older) / len(older),
                    'count': len(older)
                }
            
            # Confidence improvement calculation
            if recent and older:
                improvement = (sum(recent)/len(recent)) - (sum(older)/len(older))
                metrics['learning_proof']['confidence_improvement'] = improvement
                metrics['learning_proof']['is_learning'] = improvement > 0
            
            # Per-action confidence
            avg_conf_by_action = {
                action: sum(confs)/len(confs) 
                for action, confs in confidence_by_action.items()
            }
            metrics['decisions']['confidence_by_action'] = avg_conf_by_action
        else:
            metrics['decisions']['total_decisions'] = 0
    except Exception as e:
        metrics['decisions']['error'] = str(e)
    
    # 4. EXPLORATION HYPOTHESES
    try:
        hypotheses = list(db.collection('exploration_hypotheses').limit(20).stream())
        
        validated = 0
        rejected = 0
        pending = 0
        
        for hyp in hypotheses:
            data = hyp.to_dict()
            status = data.get('status', 'pending')
            if status == 'validated':
                validated += 1
            elif status == 'rejected':
                rejected += 1
            else:
                pending += 1
        
        metrics['exploration']['total_hypotheses'] = len(hypotheses)
        metrics['exploration']['validated'] = validated
        metrics['exploration']['rejected'] = rejected
        metrics['exploration']['pending'] = pending
        
        if validated + rejected > 0:
            success_rate = validated / (validated + rejected)
            metrics['exploration']['success_rate'] = success_rate
    except Exception as e:
        metrics['exploration']['error'] = str(e)
    
    # 5. FEEDBACK LOOP
    try:
        feedback = list(db.collection('training_feedback').limit(50).stream())
        
        feedback_types = defaultdict(int)
        for fb in feedback:
            data = fb.to_dict()
            fb_type = data.get('feedback_type', 'unknown')
            feedback_types[fb_type] += 1
        
        metrics['learning_proof']['total_feedback'] = len(feedback)
        metrics['learning_proof']['feedback_types'] = dict(feedback_types)
    except Exception as e:
        metrics['learning_proof']['feedback_error'] = str(e)
    
    return metrics


# Dashboard HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Email Agent - Learning Metrics</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .timestamp {
            opacity: 0.9;
            font-size: 0.9em;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        .card-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .icon {
            font-size: 1.5em;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-label {
            color: #4a5568;
            font-weight: 500;
        }
        .metric-value {
            color: #2d3748;
            font-weight: 700;
            font-size: 1.1em;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success {
            background: #c6f6d5;
            color: #22543d;
        }
        .badge-warning {
            background: #feebc8;
            color: #7c2d12;
        }
        .badge-info {
            background: #bee3f8;
            color: #2c5282;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
        .list-item {
            padding: 10px;
            margin: 8px 0;
            background: #f7fafc;
            border-radius: 6px;
            border-left: 3px solid #667eea;
        }
        .list-item strong {
            color: #2d3748;
        }
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: white;
            color: #667eea;
            border: none;
            padding: 16px 24px;
            border-radius: 30px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }
        .loading {
            text-align: center;
            color: white;
            font-size: 1.2em;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Email Agent Learning Dashboard</h1>
            <p class="timestamp" id="timestamp">Loading...</p>
        </div>
        
        <div id="content" class="loading">
            Loading metrics...
        </div>
    </div>
    
    <button class="refresh-btn" onclick="loadMetrics()">🔄 Refresh</button>
    
    <script>
        function loadMetrics() {
            fetch('/api/metrics')
                .then(r => r.json())
                .then(data => renderDashboard(data))
                .catch(err => {
                    document.getElementById('content').innerHTML = 
                        '<div class="loading">Error loading metrics: ' + err + '</div>';
                });
        }
        
        function renderDashboard(metrics) {
            const timestamp = new Date(metrics.timestamp).toLocaleString();
            document.getElementById('timestamp').textContent = 'Last updated: ' + timestamp;
            
            const html = `
                <div class="grid">
                    <!-- Learning Proof -->
                    <div class="card">
                        <div class="card-title">
                            <span class="icon">🧠</span>
                            Learning Proof
                        </div>
                        ${renderLearningProof(metrics.learning_proof)}
                    </div>
                    
                    <!-- Decisions -->
                    <div class="card">
                        <div class="card-title">
                            <span class="icon">⚡</span>
                            Decisions
                        </div>
                        ${renderDecisions(metrics.decisions)}
                    </div>
                    
                    <!-- People Graph -->
                    <div class="card">
                        <div class="card-title">
                            <span class="icon">👥</span>
                            People Knowledge Graph
                        </div>
                        ${renderPeopleGraph(metrics.people_graph)}
                    </div>
                    
                    <!-- Patterns -->
                    <div class="card">
                        <div class="card-title">
                            <span class="icon">📊</span>
                            Learned Patterns
                        </div>
                        ${renderPatterns(metrics.patterns)}
                    </div>
                    
                    <!-- Exploration -->
                    <div class="card">
                        <div class="card-title">
                            <span class="icon">🔬</span>
                            Exploration
                        </div>
                        ${renderExploration(metrics.exploration)}
                    </div>
                </div>
            `;
            
            document.getElementById('content').innerHTML = html;
        }
        
        function renderLearningProof(data) {
            if (!data) return '<p>No data</p>';
            
            let html = '';
            
            if (data.confidence_improvement !== undefined) {
                const improvement = (data.confidence_improvement * 100).toFixed(1);
                const badge = data.is_learning ? 'badge-success' : 'badge-warning';
                html += `
                    <div class="metric">
                        <span class="metric-label">Confidence Improvement</span>
                        <span class="badge ${badge}">${improvement > 0 ? '+' : ''}${improvement}%</span>
                    </div>
                `;
            }
            
            if (data.total_feedback !== undefined) {
                html += `
                    <div class="metric">
                        <span class="metric-label">Total Feedback</span>
                        <span class="metric-value">${data.total_feedback}</span>
                    </div>
                `;
            }
            
            if (data.feedback_types) {
                html += '<div style="margin-top: 12px;"><strong>Feedback Types:</strong></div>';
                for (const [type, count] of Object.entries(data.feedback_types)) {
                    html += `
                        <div class="metric">
                            <span class="metric-label">${type}</span>
                            <span class="metric-value">${count}</span>
                        </div>
                    `;
                }
            }
            
            return html || '<p>Building learning history...</p>';
        }
        
        function renderDecisions(data) {
            if (!data || data.total_decisions === 0) return '<p>No decisions yet</p>';
            
            let html = `
                <div class="metric">
                    <span class="metric-label">Total Decisions</span>
                    <span class="metric-value">${data.total_decisions}</span>
                </div>
            `;
            
            if (data.recent_confidence) {
                const conf = (data.recent_confidence.avg * 100).toFixed(1);
                html += `
                    <div class="metric">
                        <span class="metric-label">Recent Confidence</span>
                        <span class="metric-value">${conf}%</span>
                    </div>
                `;
            }
            
            if (data.older_confidence) {
                const conf = (data.older_confidence.avg * 100).toFixed(1);
                html += `
                    <div class="metric">
                        <span class="metric-label">Older Confidence</span>
                        <span class="metric-value">${conf}%</span>
                    </div>
                `;
            }
            
            if (data.actions) {
                html += '<div style="margin-top: 12px;"><strong>Actions:</strong></div>';
                for (const [action, count] of Object.entries(data.actions)) {
                    html += `
                        <div class="metric">
                            <span class="metric-label">${action}</span>
                            <span class="metric-value">${count}</span>
                        </div>
                    `;
                }
            }
            
            return html;
        }
        
        function renderPeopleGraph(data) {
            if (!data) return '<p>No data</p>';
            
            let html = `
                <div class="metric">
                    <span class="metric-label">Total People</span>
                    <span class="metric-value">${data.total_people || 0}</span>
                </div>
            `;
            
            if (data.importance_dist) {
                html += '<div style="margin-top: 12px;"><strong>Importance:</strong></div>';
                for (const [level, count] of Object.entries(data.importance_dist)) {
                    const percentage = data.total_people ? 
                        ((count / data.total_people) * 100).toFixed(0) : 0;
                    html += `
                        <div class="metric">
                            <span class="metric-label">${level}</span>
                            <span class="metric-value">${count} (${percentage}%)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${percentage}%"></div>
                        </div>
                    `;
                }
            }
            
            if (data.relationships) {
                html += '<div style="margin-top: 12px;"><strong>Relationships:</strong></div>';
                const sorted = Object.entries(data.relationships)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5);
                for (const [type, count] of sorted) {
                    html += `
                        <div class="metric">
                            <span class="metric-label">${type}</span>
                            <span class="metric-value">${count}</span>
                        </div>
                    `;
                }
            }
            
            return html;
        }
        
        function renderPatterns(data) {
            if (!data) return '<p>No data</p>';
            
            let html = `
                <div class="metric">
                    <span class="metric-label">Total Rules</span>
                    <span class="metric-value">${data.total_rules || 0}</span>
                </div>
            `;
            
            if (data.recent_rules && data.recent_rules.length > 0) {
                html += '<div style="margin-top: 12px;"><strong>Recent Rules:</strong></div>';
                for (const rule of data.recent_rules) {
                    const conf = (rule.confidence * 100).toFixed(0);
                    html += `
                        <div class="list-item">
                            <strong>${rule.description}</strong><br>
                            <small>Used ${rule.times_used}x | ${conf}% confidence</small>
                        </div>
                    `;
                }
            } else {
                html += '<p style="margin-top: 12px; color: #718096;">No patterns learned yet</p>';
            }
            
            return html;
        }
        
        function renderExploration(data) {
            if (!data) return '<p>No data</p>';
            
            let html = `
                <div class="metric">
                    <span class="metric-label">Total Hypotheses</span>
                    <span class="metric-value">${data.total_hypotheses || 0}</span>
                </div>
            `;
            
            if (data.validated !== undefined) {
                html += `
                    <div class="metric">
                        <span class="metric-label">Validated</span>
                        <span class="badge badge-success">${data.validated}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Rejected</span>
                        <span class="badge badge-warning">${data.rejected}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Pending</span>
                        <span class="badge badge-info">${data.pending}</span>
                    </div>
                `;
            }
            
            if (data.success_rate !== undefined) {
                const rate = (data.success_rate * 100).toFixed(1);
                html += `
                    <div class="metric">
                        <span class="metric-label">Success Rate</span>
                        <span class="metric-value">${rate}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${rate}%"></div>
                    </div>
                `;
            }
            
            return html;
        }
        
        // Auto-refresh every 30 seconds
        setInterval(loadMetrics, 30000);
        
        // Initial load
        loadMetrics();
    </script>
</body>
</html>
"""


@app.route('/dashboard')
def dashboard():
    """Serve the dashboard HTML."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/metrics')
def api_metrics():
    """API endpoint for metrics data."""
    metrics = get_learning_metrics()
    return jsonify(metrics)


@app.route('/health')
def health():
    """Health check."""
    return jsonify({"status": "healthy", "service": "metrics_dashboard"})


if __name__ == '__main__':
    print("🎯 Starting Metrics Dashboard on http://localhost:5002")
    print("📊 View dashboard at: http://localhost:5002/dashboard")
    print("🔌 API endpoint: http://localhost:5002/api/metrics")
    app.run(host='0.0.0.0', port=5002, debug=False)
