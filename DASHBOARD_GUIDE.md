# 📊 Dashboard Quick Guide - What Each Number Means

## 🎯 ONE SENTENCE SUMMARY

**The dashboard shows improvement ONLY if "Confidence Improvement" is positive (+5%, +10%, etc.)**

---

## 📈 How to See if Agent is Learning

### ✅ GOOD (Agent is Learning):
```
Older Confidence:    65%
Recent Confidence:   78%
Improvement:        +13%  ← POSITIVE = LEARNING! ✅
```

### ❌ BAD (Agent Not Learning Yet):
```
Older Confidence:   0.0%
Recent Confidence:  75%
Improvement:        N/A   ← No baseline yet ❌
```

**Your current state**: All decisions are recent (last hour), so no "older" baseline exists yet.

---

## 🔢 What Each Number Actually Means

### 1. **Total Feedback: 50**
- How many times you clicked buttons (correct/wrong/etc.)
- **Higher = better** (more training data)

### 2. **action_correct: 21 | action_wrong: 19**
- **21**: Times you said agent was RIGHT
- **19**: Times you said agent was WRONG
- **Current accuracy**: 21/40 = 52% (barely better than coin flip)
- **Goal**: Get to 80%+ correct (only 20% wrong)

### 3. **Total Decisions: 100**
- How many emails agent has processed
- **100+ is good** for basic patterns
- **500+ is great** for advanced learning

### 4. **Total People: 126**
- How many unique senders agent knows
- Agent builds a profile for each person
- **More people = more personalized decisions**

### 5. **Learned Patterns: 2 rules**
- **2 rules**: Agent discovered 2 patterns from your feedback
- Examples:
  - "Emails from these domains are often starred"
  - "User replies to 21/190 emails"
- **Goal**: Grow to 10-20+ rules over time

### 6. **Exploration: 20 pending hypotheses**
- **20 pending**: Agent made 20 guesses but hasn't gotten feedback yet
- **0 validated**: None confirmed correct yet
- **0 rejected**: None confirmed wrong yet
- **This means**: Agent is trying new things but you haven't responded to them

---

## 🧪 Simple Test to Show Learning NOW

### Step 1: Pick one sender (e.g., your professor)

### Step 2: Go to Firebase and look at their decisions
```
First email:  Confidence: 45% (uncertain)
Second email: Confidence: 65% (learning)
Third email:  Confidence: 85% (confident)
```

### Step 3: Calculate improvement
```
85% - 45% = +40% improvement ✅
```

**This is proof the agent learned!**



## 🎯 Three Ways to Prove Learning

### Method 1: **Time-Based** (Dashboard Automatic)
- Wait 2+ hours
- Dashboard compares "recent" vs "older" decisions
- Positive improvement = learning

### Method 2: **Per-Person** (Manual Check)
- Look at decisions for one sender over time
- Check if confidence increases for same person

### Method 3: **Accuracy Over Time** (Weekly Check)
```
Week 1: 52% accurate (19 wrong / 40 total)
Week 2: 68% accurate (12 wrong / 40 total)
Week 3: 81% accurate (7 wrong / 40 total)
```
Accuracy going up = learning ✅

---

## 🚨 Your Current Dashboard Explained

### Why "Older Confidence: 0.0%"?
All 100 decisions made in last hour → no "older" data to compare

### Why "20 Pending Hypotheses"?
Agent tried new strategies but you haven't given feedback yet

### Why "2 Rules Only"?
Agent just starting to discover patterns

### Is It Learning?
**Can't tell yet!** Need either:
1. Wait 2+ hours for time separation OR
2. Check individual sender confidence trends OR
3. Track accuracy improving week-over-week

---

## 💡 Bottom Line

**To show improvement, you need BEFORE vs AFTER**:

**BEFORE** (No Training):
- Confidence: 50% (guessing)
- Rules: 0
- Accuracy: 50%

**AFTER** (Training):
- Confidence: 80% (+30%) ✅
- Rules: 15 (+15) ✅
- Accuracy: 82% (+32%) ✅

**Your next step**: Process 20 more emails over next few hours, then refresh dashboard to see "Older Confidence" vs "Recent Confidence"

---

## 📊 Quick Reference

| Metric | Current | Good Target | Great Target |
|--------|---------|-------------|--------------|
| Confidence | 0% improvement | +10% | +20% |
| Rules | 2 | 10-15 | 20-30 |
| Accuracy | 52% | 75% | 85%+ |
| People | 126 | 150+ | 200+ |
| Validated Hypotheses | 0 | 5+ | 10+ |

**When all metrics hit "Good Target" → Agent is learning! ✅**
