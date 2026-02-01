# 🎯 Agent Learning Workflows & Metrics - Complete Guide

## 📋 **TL;DR**

You now have **3 ways** to monitor how the agent learns:

1. **🌐 Web Dashboard**: http://localhost:5002/dashboard (real-time, auto-refreshing)
2. **💬 Discord Command**: Type `metrics` in Discord channel
3. **🔍 Weave Traces**: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave (deep inspection)

All services are currently **running** ✅

---

## 🧠 How the Agent Learns (Step-by-Step)

### Phase 1: **First Encounter** (No History)
```
New Email Arrives
    ↓
Agent analyzes sender (creates people profile)
    ↓
Predicts importance using base model
    ↓
Makes decision with LOW confidence (no history)
    ↓
Notifies user + asks for feedback
```

**Example**: First email from recruiter → Agent marks as "maybe important?" (60% confidence) → User clicks "Reply" → Agent learns "recruiter emails = important"

---

### Phase 2: **Pattern Recognition** (Building Knowledge)
```
Similar Email Arrives
    ↓
Agent checks: "Have I seen this pattern before?"
    ↓
Finds learned rule: "Recruiter emails → HIGH importance"
    ↓
Applies rule → Higher confidence (85%)
    ↓
Takes action automatically (less bothering user)
```

**Example**: Second email from different recruiter → Agent recognizes pattern → Automatically marks important (85% confidence)

---

### Phase 3: **Exploration** (Testing New Strategies)
```
Uncertain Situation (confidence 60-75%)
    ↓
Agent thinks: "Should I try something different?"
    ↓
Creates hypothesis: "Maybe newsletters from X are actually important?"
    ↓
Tests alternative action
    ↓
User feedback validates or rejects hypothesis
    ↓
If validated → Becomes new learned rule
If rejected → Agent avoids this strategy
```

**Example**: Newsletter about job postings → Agent usually archives newsletters BUT this one mentions "jobs" → Tries marking as important → User confirms → Agent learns "job newsletters = important, other newsletters = not important"

---

### Phase 4: **Continuous Improvement** (Self-Correction)
```
Agent makes mistake
    ↓
User clicks "Wrong Action" button
    ↓
Agent records: "I thought X but user wanted Y"
    ↓
Updates people profile for sender
    ↓
Adds to learned rules
    ↓
Next similar email → Applies correction
```

**Example**: Agent marks professor email as "not urgent" → User corrects to "urgent" → Agent learns "emails from Prof. Smith = always urgent" → Next email from Prof. Smith automatically marked urgent

---

## 📊 **What Each Metric Means**

### 🧠 **Confidence Improvement** (CRITICAL)
- **What it shows**: Is the agent getting more confident over time?
- **Formula**: `avg(recent decisions) - avg(older decisions)`
- **Good**: **+5% to +15%** (agent is learning)
- **Bad**: **Negative** (agent is confused, needs more feedback)
- **How to fix**: Give more explicit feedback when agent makes mistakes

**Real Example**:
- Week 1: 65% avg confidence (new to your emails)
- Week 2: 72% avg confidence (learned some patterns)
- Week 3: 81% avg confidence (confident in most decisions)
- **Improvement: +16%** ✅ Agent is learning!

---

### 👥 **People Knowledge Graph**
- **What it shows**: How many people the agent knows about
- **Importance Distribution**:
  - **High** (≥0.8): Your boss, close colleagues, important clients
  - **Medium** (0.5-0.8): Regular contacts, classmates
  - **Low** (<0.5): Newsletters, automated emails, strangers

**Real Example**:
- Total People: 147
- High: 12 (VIPs like boss, family)
- Medium: 45 (regular contacts)
- Low: 90 (newsletters, spam)

**Why it matters**: More people = better personalization

---

### 📊 **Learned Patterns/Rules**
- **What it shows**: Concrete rules agent discovered from your feedback
- **Confidence**: How accurate this rule has been (% correct)
- **Times Used**: How often this rule applies

**Real Examples**:
1. "Emails from Sarah marked URGENT → Reply immediately" (95% confidence, used 23x)
2. "LinkedIn notifications → Archive automatically" (88% confidence, used 145x)
3. "Job application responses → Star + Reply" (92% confidence, used 8x)

---

### 🔬 **Exploration Hypotheses**
- **What it shows**: Alternative strategies the agent tested
- **Validated**: Strategies that worked (you approved)
- **Rejected**: Strategies that failed (you corrected)
- **Success Rate**: How often agent's experiments work out

**Real Example**:
- Total Hypotheses: 34
- Validated: 19 (strategies that worked)
- Rejected: 15 (strategies that failed)
- **Success Rate: 56%** (more hits than misses ✅)

**Good Success Rate**: >50% (agent's exploration is smart)
**Bad Success Rate**: <40% (agent guessing too wildly)

---

## 🎯 **How to Measure Learning**

### Daily Check (30 seconds)
1. Open http://localhost:5002/dashboard
2. Look at **Confidence Improvement**: Should be **positive** ✅
3. Check **Recent Decisions**: Are confidence scores >75%?
4. Scan **Recent Rules**: Do they make sense?

### Weekly Review (5 minutes)
1. Visit Weave: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave
2. Click on recent **Traces**
3. Expand decision pipeline to see:
   - What data the agent considered
   - Why it chose that action
   - What rules it applied
4. Look for patterns in mistakes (same sender? same email type?)

### Monthly Analysis (15 minutes)
1. Export metrics to CSV:
   ```bash
   curl http://localhost:5002/api/metrics > metrics_$(date +%Y%m%d).json
   ```
2. Compare to last month:
   - **Confidence**: Should be higher
   - **Learned Rules**: Should have more
   - **Exploration Success Rate**: Should stabilize >50%
3. Calculate accuracy:
   - Count user corrections vs total decisions
   - Target: <10% correction rate (90%+ accuracy)

---

## 🔍 **Detailed Workflow Examples**

### Example 1: Learning About a New Contact

**Email 1** (Day 1):
```
From: Alice (alice@company.com)
Subject: "Quick question about project"
Body: "Hey, can you send me the files?"

Agent Analysis:
├─ Sender: Unknown (first time seeing Alice)
├─ Urgency: Medium (word "quick")
├─ Importance Prediction: 50% (no history)
├─ Decision: ASK USER
└─ Confidence: 45% (very uncertain)

User Action: Clicks "Reply" button
Agent Learning: "Alice → Important, Reply needed"
```

**Email 2** (Day 3):
```
From: Alice (alice@company.com)
Subject: "Follow up on files"

Agent Analysis:
├─ Sender: Alice (importance: 0.75, replied to her before)
├─ Urgency: Medium
├─ Importance Prediction: 75% (using learned profile)
├─ Decision: REPLY
└─ Confidence: 72% (much more confident)

User Action: None (agent was correct)
Agent Learning: "Alice profile confirmed ✅"
```

**Email 3** (Day 7):
```
From: Alice (alice@company.com)
Subject: "Urgent: Meeting in 30 mins"

Agent Analysis:
├─ Sender: Alice (importance: 0.85, consistently important)
├─ Urgency: HIGH (word "Urgent", time-sensitive)
├─ Importance Prediction: 95%
├─ Decision: REPLY + NOTIFY
└─ Confidence: 91% (very confident)

User Action: Replies immediately
Agent Learning: "Alice urgent emails = top priority ✅"
```

---

### Example 2: Pattern Discovery Through Exploration

**Newsletter Email**:
```
From: TechCrunch (newsletter@techcrunch.com)
Subject: "Today's top tech news"

Agent Analysis:
├─ Sender: Newsletter (usually archives these)
├─ Base Decision: ARCHIVE (80% confidence)
├─ BUT: Content mentions "job postings" + "hiring"
├─ Exploration Mode: "Should I try marking important?"
│   └─ Hypothesis: "Job-related newsletters = important"
├─ Alternative Decision: STAR (for later reading)
└─ Confidence: 60% (exploring)

User Action: Clicks "Good call!" button
Agent Learning:
├─ Hypothesis VALIDATED ✅
├─ New Rule: "Newsletters with job keywords → Star"
└─ Confidence Boost: Future similar emails 85% confidence
```

**Next Newsletter Email**:
```
From: TechCrunch (newsletter@techcrunch.com)
Subject: "iPhone 20 announcement"

Agent Analysis:
├─ Sender: Newsletter
├─ Content: No job keywords
├─ Decision: ARCHIVE (applies base rule)
└─ Confidence: 88%

Agent Thinking: "This newsletter doesn't have job keywords,
so I'll archive it. But if it mentioned jobs, I'd star it."
```

---

## 🛠️ **Troubleshooting Learning Issues**

### Issue 1: "Confidence not improving"
**Symptoms**: Dashboard shows 0% or negative confidence improvement

**Causes**:
- Not enough decisions made yet (need >20)
- Emails too varied (no patterns)
- Not enough user feedback

**Fix**:
1. Give explicit feedback on 10-15 decisions
2. Correct agent when it's wrong (click "Wrong Action")
3. Wait for more emails to arrive

---

### Issue 2: "Agent keeps making same mistake"
**Symptoms**: Agent marks X as unimportant but you always correct to important

**Causes**:
- Rule not specific enough
- Sender profile not updated
- Exploration overriding learned rule

**Fix**:
1. Check Weave trace to see why agent chose that action
2. Look for conflicting rules (maybe one says "archive" and another says "reply")
3. Give consistent feedback (always correct to same action)

---

### Issue 3: "Too many hypotheses rejected"
**Symptoms**: Exploration success rate <40%

**Causes**:
- Agent exploring too aggressively
- Not enough training data
- Email patterns unclear

**Fix**:
1. Let agent run for 1-2 more weeks to gather data
2. Give more binary feedback (clear yes/no)
3. Consider reducing exploration rate (edit `exploration.py`)

---

## 📈 **Expected Learning Curve**

### Week 1: **Data Collection**
- Confidence: **55-65%** (lots of uncertainty)
- Learned Rules: **0-5** (just starting)
- User Interventions: **High** (agent asks a lot)
- What's happening: Building people profiles, gathering patterns

### Week 2: **Pattern Recognition**
- Confidence: **65-75%** (recognizing common senders)
- Learned Rules: **5-15** (basic patterns discovered)
- User Interventions: **Medium** (less asking)
- What's happening: Applying learned rules, testing hypotheses

### Week 3: **Autonomous Operation**
- Confidence: **75-85%** (confident in most decisions)
- Learned Rules: **15-30** (comprehensive ruleset)
- User Interventions: **Low** (mostly works alone)
- What's happening: Handling most emails automatically

### Week 4+: **Optimization**
- Confidence: **80-90%** (very confident)
- Learned Rules: **30-50+** (mature knowledge base)
- User Interventions: **Rare** (only edge cases)
- What's happening: Fine-tuning, handling edge cases

---

## 🎓 **Advanced: Custom Metrics**

Want to track specific metrics? Edit `agent/metrics_dashboard.py`:

```python
# Add to get_learning_metrics() function:

# Track accuracy per sender type
sender_types = defaultdict(lambda: {'correct': 0, 'total': 0})
for decision in decisions:
    sender_type = decision.get('sender_type', 'unknown')
    was_corrected = 'feedback' in decision
    sender_types[sender_type]['total'] += 1
    if not was_corrected:
        sender_types[sender_type]['correct'] += 1

# Calculate accuracy by type
accuracy_by_type = {
    type_name: stats['correct'] / stats['total']
    for type_name, stats in sender_types.items()
}

metrics['accuracy_by_sender_type'] = accuracy_by_type
```

Then display in dashboard HTML template.

---

## 🚀 **Next Steps**

1. ✅ All services running (dashboard, agent, Discord bot)
2. ✅ Web dashboard accessible at http://localhost:5002/dashboard
3. ✅ Discord metrics command working (type `metrics`)
4. ✅ Weave traces recording every decision

**Now**:
1. Process some emails (wait for them to arrive or run scraper manually)
2. Give feedback on decisions (click buttons)
3. Watch dashboard metrics update in real-time
4. After 10+ decisions, check Weave for detailed traces
5. After 1 week, review learning curve (is confidence improving?)

---

## 📚 **Resources**

- **Dashboard**: http://localhost:5002/dashboard
- **API Docs**: http://localhost:5002/api/metrics (JSON)
- **Weave UI**: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave
- **Discord**: Type `metrics` for quick stats
- **Observability Guide**: [OBSERVABILITY.md](./OBSERVABILITY.md)

---

## ❓ **FAQ**

**Q: How long until agent is "trained"?**
A: 2-3 weeks for basic patterns, 1 month for autonomous operation

**Q: What's a "good" confidence score?**
A: 70%+ is good, 80%+ is excellent, 90%+ is expert-level

**Q: How many learned rules should I have?**
A: Week 1: 5-10, Week 2: 15-25, Month 1: 30-50, After: 50+

**Q: Agent keeps asking me about the same sender?**
A: Make sure you're clicking the feedback buttons (not just replying manually)

**Q: Can I see what the agent is thinking?**
A: Yes! Check Weave traces for full decision pipeline

**Q: How do I export metrics for analysis?**
A: `curl http://localhost:5002/api/metrics > metrics.json`

---

**Last Updated**: February 1, 2026
**Services Status**: All 3 services running ✅
