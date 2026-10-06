# Medha teacher-data policy

Qwen/Ollama is a teacher, not Medha.

Teacher output must pass validation before entering Medha's training dataset.

## Reject

Reject an example when the assistant response is primarily:

- "I'm sorry, I can't assist with that" or equivalent refusal boilerplate.
- "I cannot/can't assist, help, provide, or comply" boilerplate.
- Claims that the request violates the teacher's safety policy, guidelines, rules, or limitations.
- "As an AI/language model..." teacher-identity boilerplate.
- References to the teacher's internal policies or model identity.
- Malformed JSON or invalid role ordering.
- Empty, duplicated, or low-quality conversation.

## Keep

Keep useful content even when the conversation discusses danger, safety,
risk, law, security, or other sensitive subjects. A factual explanation is
not automatically a refusal.

Example to keep:
"Driving without a helmet is dangerous because it increases the risk of
serious head injury."

Example to reject:
"I'm sorry, but I can't assist because this goes against my safety
limitations."

## Separation

The teacher is used only to generate training examples.

    Ollama/Qwen
        -> generated conversations
        -> filter and validate
        -> Medha dataset
        -> Medha fine-tuning
        -> models/conversational-medha

After training, the Medha runtime must not call Ollama or load the teacher
checkpoint.

Medha's own safety design is a separate future component and must not be
copied from the teacher.
