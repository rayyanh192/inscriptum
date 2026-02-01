# 🔍 How to See Confidence Improvement in Weave

## Quick Answer

**Weave does NOT calculate "improvement" automatically** - it shows raw traces. You have to compare manually.

---

## 📊 Weave Dashboard Guide

### Step 1: Open Weave
Go to: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave

### Step 2: Click "Traces" Tab
You'll see a list of all `process_email` calls

### Step 3: Pick a Sender (e.g., "sarah@company.com")
Filter traces to see only emails from one person:
- Click the search/filter
- Type the sender's email

### Step 4: Open 3 Traces from That Sender
Click on each trace to expand it. Look for:

```
Trace 1 (First email from Sarah):
├─ process_email
│  └─ Output:
│     └─ decision:
│        └─ confidence: 0.45  ← LOW (first time)
│        └─ action: "ask"

Trace 2 (Second email from Sarah):
├─ process_email
│  └─ Output:
│     └─ decision:
│        └─ confidence: 0.68  ← MEDIUM (learning)
│        └─ action: "reply"

Trace 3 (Third email from Sarah):
├─ process_email
│  └─ Output:
│     └─ decision:
│        └─ confidence: 0.87  ← HIGH (confident)
│        └─ action: "reply"
```

### Step 5: Calculate Improvement Manually
```
0.87 - 0.45 = 0.42 = +42% improvement ✅
```

---

## 🎯 What Each Dashboard Shows

| Feature | Metrics Dashboard | Weave Dashboard |
|---------|------------------|-----------------|
| **URL** | http://localhost:5002/dashboard | https://wandb.ai/.../weave |
| **Shows** | Aggregated stats | Individual traces |
| **Improvement** | ✅ Auto-calculated | ❌ Manual only |
| **Best For** | Quick overview | Deep debugging |
| **Updates** | Every 30 sec | Real-time |

---

## 📸 Screenshot Guide

### Metrics Dashboard:
```
┌─────────────────────────────┐
│ 🧠 Learning Proof           │
├─────────────────────────────┤
│ Confidence Improvement      │
│         +13.2% ← HERE!      │ ✅ AUTO-CALCULATED
└─────────────────────────────┘
```

### Weave Dashboard:
```
Traces:
  ▶ process_email (2026-02-01 10:23:45)
    Output: { confidence: 0.87 } ← See this
  
  ▶ process_email (2026-02-01 09:45:12)
    Output: { confidence: 0.68 } ← Compare to this
  
  ▶ process_email (2026-02-01 09:12:33)
    Output: { confidence: 0.45 } ← Manually calc difference
```

---

## 🚀 Quick Test: See It NOW

### Option 1: Use Metrics Dashboard (Easiest)
```bash
# Start metrics dashboard
cd /Users/edrickchang/Desktop/inscriptum
source .venv/bin/activate
python agent/metrics_dashboard.py
```
Then open: http://localhost:5002/dashboard
Look for: "Learning Proof" → "Confidence Improvement"

### Option 2: Check Weave (More Detail)
1. Go to: https://wandb.ai/inscriptum85-inscriptum/email-agent/weave
2. Click "Traces"
3. Find any `process_email` trace
4. Expand it
5. Look at `Output` → `decision` → `confidence`
6. Compare confidence across multiple traces

---

## ❓ Why No Improvement Showing?

### Metrics Dashboard Shows 0.0%:
**Cause**: All decisions made in last hour (no "older" baseline)
**Fix**: Wait 2+ hours OR process emails over multiple days

### Weave Shows All Different Confidences:
**Cause**: Every email is different (different senders)
**Fix**: Filter by ONE sender to see progression

---

## 💡 Real Example

Let's say you want to see if agent learned about your professor:

### In Metrics Dashboard:
- Shows overall improvement: `+8.3%` (all senders combined)

### In Weave:
1. Filter traces: `sender contains "professor.edu"`
2. Open first trace: confidence = 0.50
3. Open second trace: confidence = 0.72
4. Open third trace: confidence = 0.85
5. **Manual calc**: 0.85 - 0.50 = +35% for this professor ✅

---

## 🎯 Bottom Line

**Metrics Dashboard**: 
- Shows improvement automatically
- But needs 2+ hours of data
- Currently shows "0.0%" (no baseline yet)

**Weave Dashboard**:
- Shows every decision in detail
- You manually compare confidence values
- Best for debugging specific sender patterns

**For showing improvement**: Use Metrics Dashboard once you have data over time.

**For debugging**: Use Weave to see why agent made specific decisions.
