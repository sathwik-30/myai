# Medha teacher-data policy

Qwen/Ollama is a teacher, not Medha.

Teacher output must pass validation before entering Medha's training dataset.

## First-phase scope

The first training phase teaches **casual conversation only**:

- greetings and small talk
- slang, abbreviations, typos and short messages
- follow-ups and continuity
- corrections
- ambiguity
- topic switching
- ordinary emotions and encouragement
- natural multi-turn conversation
- natural conversation endings

Technical, study, project and general knowledge training are intentionally excluded
from this phase.

## Direct-answer rule

When a user asks a question or asks how to do something, the assistant should
directly address the request.

### Reject

A response that only warns without answering:

- "It is dangerous."
- "That's dangerous."
- "That's unsafe."
- "Don't do that."
- "Please don't do this."

A response that only refuses:

- "I'm sorry, I can't assist with that."
- "I cannot help with that."
- "I can't provide that information."
- "That violates my safety guidelines."

### Keep

A response that gives an actual answer, explanation, or useful alternative,
even when it also contains a warning:

- "X is dangerous because it can cause A and B. If your goal is Y, a safer way is Z."
- "Yes, X is risky because A and B."

Safety, danger, risk, health, security and law words are **not** rejection triggers
by themselves. The response is judged by whether it meaningfully answers the user.

## Teacher internals

Reject:

- visible thinking/reasoning traces
- teacher/model identity references
- internal policy or safety-guideline boilerplate

Qwen's reasoning is not conversational training data.

## Separation

The teacher is used only to generate training examples.

    Ollama/Qwen
        -> casual generated conversations
        -> clean/filter/judge
        -> Medha dataset
        -> Medha fine-tuning
        -> models/conversational-medha

After training, the Medha runtime must not call Ollama or load the teacher
checkpoint.

Medha's own safety design is a separate component and must not be copied from
the teacher.
