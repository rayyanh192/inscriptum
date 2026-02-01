# 🎯 Inscriptum Agent Observability

## Overview

The Inscriptum agent provides **3 levels of observability** to monitor learning and self-improvement:

### 1. 🌐 **Live Web Dashboard** (Real-time Metrics)
- **URL**: http://localhost:5002/dashboard
- **Purpose**: Visual real-time metrics with auto-refresh
- **Shows**:
  - Learning proof (confidence improvement over time)
  - Decision statistics (total, confidence trends)
  - People knowledge graph (relationships, importance distribution)
  - Learned patterns/rules (with confidence and usage)
  - Exploration hypotheses (validated/rejected/pending)

**Start**:
```bash
cd /Users/edrickchang/Desktop/inscriptum
source .venv/bin/activate
python agent/metrics_dashboard.py
```

### 2. 💬 **Discord Commands** (Quick Stats)
- **Command**: Type `metrics`, `show metrics`, or `show stats` in Discord
- **Purpose**: Quick snapshot without leaving Discord
- **Shows**: Same metrics as web dashboard in Discord embed format

### 3. 🔍 **Weave Traces** (Deep Inspection)
- **URL**: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave
- **Purpose**: Detailed execution traces for every decision
- **Shows**:
  - Full decision-making pipeline (step-by-step)
  - Input/output for each function call
  - Reasoning chains from LLM
  - Exploration vs exploitation choices
  - Feedback loop validations

---

## Key Metrics Explained

### 🧠 **Learning Proof**
- **Confidence Improvement**: Change in avg confidence (recent vs older decisions)
  - **Positive value** = Agent is learning ✅
  - **Negative value** = Agent needs more feedback
- **Total Feedback**: Number of user corrections received
- **Feedback Types**: `action_correct`, `action_wrong`, `response_used`, etc.

### ⚡ **Decisions**
- **Total Decisions**: How many emails processed
- **Recent Confidence**: Avg confidence in last hour
- **Older Confidence**: Avg confidence before last hour
- **Actions Distribution**: `reply`, `star`, `archive`, `ask` counts

### 👥 **People Knowledge Graph**
- **Total People**: Unique senders profiled
- **Importance Distribution**:
  - **High** (≥0.8): VIPs, bosses, close contacts
  - **Medium** (0.5-0.8): Regular contacts
  - **Low** (<0.5): Newsletters, automated emails
- **Relationships**: `boss`, `colleague`, `recruiter`, `friend`, etc.

### 📊 **Learned Patterns**
- **Total Rules**: Number of patterns discovered from feedback
- **Recent Rules**: Last 3-5 learned patterns with:
  - Description (what the rule does)
  - Confidence (how accurate it's been)
  - Times Used (how often applied)

### 🔬 **Exploration**
- **Total Hypotheses**: Alternative strategies tested
- **Validated**: Hypotheses that worked (user approved)
- **Rejected**: Hypotheses that failed (user corrected)
- **Success Rate**: Validated / (Validated + Rejected)
  - **>50%** = Good exploration strategy
  - **<50%** = Agent needs to be more conservative

---

## How the Agent Learns

### 1️⃣ **Initial Decision** (Base Model)
```python
# Agent uses importance predictor + people graph
importance = predict_importance(email, sender_profile, cluster_context)
action = decide_action(importance, urgency, sender_importance)
```

### 2️⃣ **Apply Learned Rules** (Override)
```python
# If agent has learned a better strategy, use it
learned_rules = get_learned_rules(email_features)
if learned_rules:
    action = apply_learned_rules(action, learned_rules)
```

### 3️⃣ **Exploration** (Try New Strategies)
```python
# When uncertain, explore alternatives
if should_explore(confidence):
    alternative = generate_alternative_strategy(email, context)
    hypothesis = store_hypothesis(alternative)
    action = alternative.action
```

### 4️⃣ **User Feedback** (Validate/Reject)
```python
# User clicks button or corrects draft
feedback = record_feedback(decision_id, 'action_correct')
await process_feedback_for_learning(feedback)
# → Updates people profiles, patterns, hypotheses
```

---

## Monitoring Workflow

### Daily Check
1. Open http://localhost:5002/dashboard
2. Check **Confidence Improvement** (should be positive)
3. Check **Exploration Success Rate** (should be >50%)
4. Review **Recent Rules** (are they making sense?)

### Weekly Review
1. Visit Weave dashboard: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave
2. Look at **Traces** for recent decisions
3. Verify reasoning chains are logical
4. Check for errors or unexpected patterns

### When Agent Makes Mistakes
1. Discord → Click "Wrong Action" button
2. Dashboard → Watch **Total Feedback** increase
3. Next similar email → Agent should apply learned rule
4. Weave → Inspect trace to see rule application

---

## Running All Services

### Option 1: Full Stack (for development)
```bash
# Terminal 1: Metrics Dashboard
cd /Users/edrickchang/Desktop/inscriptum
source .venv/bin/activate
python agent/metrics_dashboard.py

# Terminal 2: Python Agent Server
source .venv/bin/activate
python agent/server.py

# Terminal 3: Discord Bot
cd convo
node discord-bot.js
```

### Option 2: Production (background processes)
```bash
cd /Users/edrickchang/Desktop/inscriptum

# Start all services in background
source .venv/bin/activate
python agent/metrics_dashboard.py &
python agent/server.py &
cd convo && node discord-bot.js &

# Check status
ps aux | grep -E "(metrics_dashboard|server\.py|discord-bot)"

# Kill all
pkill -f "python agent/metrics_dashboard.py"
pkill -f "python agent/server.py"
pkill -f "node discord-bot.js"
```

---

## API Endpoints

### Metrics Dashboard (Port 5002)
- `GET /dashboard` - Web UI
- `GET /api/metrics` - JSON metrics
- `GET /health` - Health check

### Python Agent (Port 5001)
- `POST /process-email` - Process email through agent
- `POST /generate-draft` - Generate contextual response
- `GET /health` - Health check

### Discord Bot (Port 3000)
- `GET /` - Status page with bot stats

---

## Troubleshooting

### Dashboard shows "Metrics Dashboard Offline"
```bash
# Start metrics dashboard
python agent/metrics_dashboard.py
```

### Discord metrics command shows "Offline"
```bash
# Check if dashboard is running
curl http://localhost:5002/health

# Restart dashboard
pkill -f metrics_dashboard.py
python agent/metrics_dashboard.py &
```

### No confidence improvement showing
- **Cause**: Need more feedback data
- **Solution**: Process more emails, give more feedback
- **Check**: Weave traces to verify feedback is being recorded

### Weave traces not showing
```bash
# Verify WANDB credentials
echo $WANDB_API_KEY
echo $WANDB_PROJECT

# Re-authenticate
weave login
```

---

## Data Sources

All metrics come from **Firebase Firestore** collections:

- `agent_decisions` - Every decision made by agent
- `training_feedback` - User feedback on decisions
- `learned_patterns` - Discovered rules/patterns
- `people` - Sender profiles with importance scores
- `exploration_hypotheses` - Alternative strategies tested

---

## Next Steps

1. ✅ Start all 3 services
2. ✅ Process some emails
3. ✅ Give feedback (click buttons)
4. ✅ Watch metrics improve
5. 🎯 Build custom dashboards with Weave's API
6. 🎯 Add email to custom metrics (accuracy per sender type)
7. 🎯 Export metrics to CSV for analysis

---

## Questions?

- **Dashboard not loading?** Check Firebase credentials in `.env`
- **No data showing?** Process emails first, metrics update in real-time
- **Want more metrics?** Edit `agent/metrics_dashboard.py` to add custom calculations
