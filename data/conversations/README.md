# Medha conversational training data

This directory contains training conversations for Medha's learned language brain. These examples teach conversational behavior, not fixed answer lookup.

## JSONL format

Each line is one multi-turn conversation:
{"messages":[{"role":"user","content":"Hi"},{"role":"assistant","content":"Hey there!"}]}

Include varied wording, slang, short messages, follow-ups, corrections, topic changes, questions, answers, and natural conversation endings.

Do not put secrets, passwords, API keys, private credentials, or sensitive personal information in training data.

## Training rule

Conversation examples teach the model how to communicate. User-specific facts belong in Medha's memory system, not in model weights.
