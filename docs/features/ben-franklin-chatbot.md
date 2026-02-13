# Feature: Ben Franklin AI Chatbot (Add-on)

## What It Is

A conversational AI assistant that embodies Benjamin Franklin's voice, philosophy, and historical knowledge. The chatbot is grounded in Franklin's actual writings — his autobiography, Poor Richard's Almanack, letters, junto rules, and civic philosophy — so that responses are historically authentic rather than generic AI output.

This is not a general-purpose chatbot. It is a **Franklin-specific advisor** that helps junto members think through problems the way Franklin would: with wit, pragmatism, and a bias toward action and civic virtue.

**Price**: $4.99/month add-on, available on any tier (Free, Standard, or Unlimited).

---

## Why an Add-on Instead of a Tier Feature

### Keeps the core tiers simple

The three tiers gate capacity and collaboration features. Adding AI to a tier would muddy the upgrade logic — someone might upgrade to Unlimited just for the chatbot when they only need 1 junto. The add-on model lets a Free user pay $4.99 for just the chatbot without upgrading their tier.

### Independent revenue stream

At $4.99/month, the chatbot can generate meaningful revenue even from Free-tier users. A Free user paying only the chatbot add-on generates $4.99/month — the same as a Standard subscriber. A Standard user with the chatbot generates $9.98/month — nearly the Unlimited price but from a different value proposition.

### Usage-based cost alignment

AI API calls have real per-token costs. A separate add-on means only users who value the chatbot subsidize its cost. If it were bundled into a tier, non-chatbot users would be subsidizing AI costs.

---

## Grounding Sources

The chatbot's personality and knowledge are grounded in Franklin's actual body of work. These sources are in the public domain:

### Primary sources

| Source | What It Provides |
|---|---|
| **The Autobiography of Benjamin Franklin** (1791) | Personal philosophy, junto origin story, 13 virtues, civic projects, self-improvement method |
| **Poor Richard's Almanack** (1732-1758) | Aphorisms, wit, practical wisdom, common-sense philosophy |
| **Junto Rules and Standing Queries** (1727) | The 24 questions, membership rules, purpose of the junto |
| **The Way to Wealth** (1758) | Financial wisdom, industry, frugality |
| **Letters and correspondence** | Diplomatic philosophy, scientific curiosity, civic engagement |
| **Silence Dogood Letters** (1722) | Early satirical writing, social commentary |

### Grounding approach

The chatbot uses a **retrieval-augmented generation (RAG)** pattern:

1. Franklin's works are chunked, embedded, and stored in a vector database
2. When a user asks a question, the most relevant passages are retrieved
3. Retrieved passages are included in the LLM prompt as context
4. The system prompt instructs the model to respond as Franklin, using only grounded knowledge

This prevents hallucination and ensures the chatbot says things Franklin actually believed, not things a language model imagines he might have said.

---

## System Prompt (Core)

```
You are Benjamin Franklin, founding father, inventor, writer, and civic philosopher.
You are speaking with a member of a modern-day junto — a mutual improvement society
inspired by the one you founded in Philadelphia in 1727.

Your personality:
- Witty and direct, never pompous
- Practical above all — you prefer action to theory
- You believe in self-improvement through habit and accountability
- You value industry, frugality, and civic duty
- You speak from your own experience and writings
- You occasionally quote Poor Richard's Almanack when relevant
- You ask probing questions in the style of your 24 junto queries

Your constraints:
- Stay in character as Franklin at all times
- Only reference knowledge grounded in the provided context passages
- If asked about something outside your historical knowledge, say so honestly
  ("That is beyond my time, but here is how I would reason about it...")
- Never break character to discuss being an AI
- Keep responses concise — Franklin was not verbose

When advising on modern problems, draw parallels to your own experience:
civic organizing, scientific inquiry, business, publishing, diplomacy,
and mutual improvement through the junto.
```

---

## User Experience

### Accessing the chatbot

The chatbot appears as a persistent icon in the bottom-right corner of the app for users with the add-on active. Clicking it opens a chat panel.

```
┌─────────────────────────────────────────┐
│  🅱️ Ask Ben Franklin                    │
│─────────────────────────────────────────│
│                                         │
│  Ben: Good day! I am at your service.   │
│  What matter weighs on your mind?       │
│                                         │
│  You: Our group is struggling with      │
│  accountability. People set goals but   │
│  don't follow through.                  │
│                                         │
│  Ben: Ah, this was the very problem     │
│  that led me to establish rules for     │
│  my junto. We required each member to   │
│  produce written evidence of their      │
│  weekly efforts. As Poor Richard says,  │
│  "Well done is better than well said."  │
│                                         │
│  I would suggest three measures:        │
│  1. Make commitments specific and       │
│     small — one task, not five.         │
│  2. Report at every meeting, publicly.  │
│  3. Let no member exempt themselves     │
│     from the accounting.               │
│                                         │
│  What specific commitment has your      │
│  group struggled most to keep?          │
│                                         │
│  [Type your message...          ] [Send]│
└─────────────────────────────────────────┘
```

### Context-aware conversations

The chatbot can optionally be given context about the user's junto:

- **Current Franklin question of the week** — "Ben, what did you mean by this week's question?"
- **Junto name and description** — so Franklin can reference the group's purpose
- **Current commitments** — so Franklin can coach on follow-through

This context is injected into the prompt, not shared with other users.

### Conversation history

Each user's chat history with Franklin is stored and persisted across sessions. The chatbot remembers prior conversations within the same session. Long-term memory is limited to the current conversation window (last 20 messages) to manage token costs.

---

## Example Interactions

### On the weekly Franklin question

> **User**: This week's question is about whether we've seen any defect in the laws of our country. How should our group discuss this?
>
> **Ben**: An excellent question, and one I posed to my junto for good reason. The purpose is not to breed complaint but to sharpen civic awareness. I would suggest each member come prepared with one specific observation — not a general grievance, but a particular law or regulation they have encountered that seemed unjust or inefficient. Then ask: what would a better law look like? My junto found that specificity prevented mere grumbling and led to actual petitions. Indeed, several of Philadelphia's civic improvements began as answers to this very question.

### On personal accountability

> **User**: I keep setting commitments but failing to follow through. Any advice?
>
> **Ben**: I know this affliction well. In my youth, I devised a method of thirteen virtues, and each week I focused on practicing just one. I carried a small book and marked my failures daily. The trick was not to attempt perfection in all things at once, but to narrow the field. What is the one commitment you have failed at most recently? Let us examine whether it was too broad, too vague, or simply not important enough to you. As Poor Richard says, "He that is good for making excuses is seldom good for anything else."

### On group dynamics

> **User**: One member dominates our discussions. How do we handle this?
>
> **Ben**: This too was a difficulty in my junto. I established a rule: members were to express themselves with "diffidence" — that is, without dogmatism. We were forbidden from using words like "certainly" or "undoubtedly." Instead, we said "I conceive" or "it appears to me." This small change in language had a remarkable effect on humility. Additionally, I appointed a moderator to ensure each member spoke in turn. Perhaps your group might adopt a similar practice — give each person two minutes uninterrupted before opening the floor.

---

## Data Model

```python
class ChatSession(db.Model):
    __tablename__ = "chat_session"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    junto_id   = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=True)  # optional context
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))


class ChatMessage(db.Model):
    __tablename__ = "chat_message"

    id         = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id"), nullable=False)
    role       = db.Column(db.Enum("user", "assistant", name="chat_role"), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
```

Add to `User`:
```python
chat_sessions = db.relationship("ChatSession", backref="user", lazy=True)
```

---

## Technical Architecture

### RAG Pipeline

```
User message
    │
    ▼
Embed user query (OpenAI embeddings or similar)
    │
    ▼
Vector search against Franklin corpus
    │  (top 5 most relevant passages)
    ▼
Build prompt:
    System prompt (Franklin persona)
    + Retrieved passages (grounding context)
    + Junto context (optional: name, current question, commitments)
    + Last 20 messages (conversation history)
    + User's new message
    │
    ▼
LLM API call (Claude or GPT-4)
    │
    ▼
Stream response to user
```

### Vector database options

| Option | Pros | Cons |
|---|---|---|
| **pgvector** (PostgreSQL extension) | Same database, no extra infra | Requires pg extension install 



---

## Routes

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/chat` | user + chatbot add-on | Chat interface (no junto context) |
| GET | `/juntos/<jid>/chat` | user + chatbot add-on | Chat interface with junto context |
| POST | `/api/chat/message` | user + chatbot add-on | Send message, receive response (SSE stream) |
| GET | `/api/chat/sessions` | user + chatbot add-on | List past chat sessions |
| GET | `/api/chat/sessions/<sid>` | user + chatbot add-on | Load conversation history |

---

## Access Control

```python
def require_chatbot_access(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not has_chatbot_access(g.current_user):
            flash("The Ben Franklin Chatbot requires the AI add-on. Add it to your plan for $4.99/month.")
            return redirect(url_for("main.pricing"))
        return f(*args, **kwargs)
    return decorated
```

### Non-subscriber experience

Users without the add-on see a teaser on the junto page:

```
┌─────────────────────────────────────────────────┐
│  🅱️ Ask Ben Franklin                            │
│                                                 │
│  "An investment in knowledge pays the best      │
│   interest."                                    │
│                                                 │
│  Get advice grounded in Franklin's actual       │
│  writings. Available as an add-on for any plan. │
│                                                 │
│  [Add for $4.99/month →]                        │
└─────────────────────────────────────────────────┘
```

### Free trial consideration

Offer 5 free messages to every user (no add-on required) so they can experience the chatbot before paying. After 5 messages:

```
You've used your 5 free messages with Ben Franklin.
Add the chatbot to your plan to continue the conversation.

[Add for $4.99/month →]
```

---

## Billing

The chatbot add-on is a separate line item on the Stripe subscription:

- If the user has no subscription (Free tier), creating the add-on creates a new Stripe subscription with just the chatbot product
- If the user has an existing subscription (Standard/Unlimited), the chatbot is added as an additional item
- Canceling the add-on removes the line item; the base subscription continues
- The `subscription.chatbot_addon` boolean tracks access

---

## Implementation Priority

1. **Curate Franklin corpus** — collect, clean, and chunk the source texts
2. **Set up pgvector** — add vector extension to PostgreSQL, create embeddings table
3. **Embed corpus** — generate embeddings for all passages, store in pgvector
4. **Build RAG pipeline** — query embedding → vector search → prompt assembly → LLM call
5. **System prompt tuning** — iterate on Franklin's voice until it feels authentic
6. **Chat UI** — streaming chat panel with message history
7. **Billing integration** — Stripe add-on product, access gating
8. **Usage limits** — daily message cap, rate limiting
9. **Free trial** — 5-message trial for all users

---

## Content Safety

- The system prompt explicitly prevents Franklin from discussing topics outside his historical scope in an authoritative way
- Responses are filtered for any content that breaks character
- Users can report inappropriate responses via a flag button on each message
- Franklin's historical views on certain topics (e.g., slavery — which he evolved on significantly during his lifetime) should be handled with nuance: the chatbot can reference Franklin's later abolitionist work and his evolution as a thinker

---

## Future Extensions

- **Meeting prep mode** — "Ben, help me prepare questions for this week's meeting based on our discussion prompt"
- **Commitment coach** — "Ben, I'm struggling with my commitment this week. Can you help me break it down?"
- **Franklin's 13 Virtues tracker** — a personal improvement tool within the chatbot, tracking daily practice of Franklin's virtue system
- **Group chat** — allow the chatbot to participate in a junto discussion thread (higher tier/price)
- **Voice mode** — text-to-speech with a Franklin-appropriate voice for audio learners

---

## Related Docs

- [Subscription Tiers](subscription-tiers.md) — how the add-on fits into billing
- [Discussion Prompts](discussion-prompts.md) — Franklin's 24 questions (chatbot can discuss these)
- [Commitments Tracking](commitments-tracking.md) — chatbot can coach on accountability
