from backend.brain.identity import OWNER_NAME
from backend.brain.intent import classify
from backend.brain.understanding import LanguageUnderstanding
from backend.brain.language import detect_language
from backend.core.policy import apply_override

UNDERSTANDING = LanguageUnderstanding()


def _format_knowledge_gap(result, message):
    subject = result.get("understood_as") or "that topic"
    ideas = result.get("ideas") or []
    language = detect_language(message)

    if language == "telugu":
        lines = [
            f"'{subject}' గురించి నాకు ఇంకా నమ్మదగిన సమాధానం లేదు.",
            f"మీ ప్రశ్న {subject} గురించి అని నేను అర్థం చేసుకున్నాను.",
            "నమ్మకం లేని విషయాన్ని ఊహించి చెప్పడం నాకు ఇష్టం లేదు.",
        ]
        if ideas:
            lines.append("పరిశీలించగల ముఖ్యమైన దిశలు:")
            lines.extend(f"- {idea}" for idea in ideas[:4])
        lines.append("ప్రశ్నలో కొంచెం అదనపు వివరాలు ఇస్తే అర్థాన్ని మరింత స్పష్టంగా తెలుసుకోగలను.")
        return "\n".join(lines)

    if language == "roman_telugu":
        lines = [
            f"'{subject}' gurinchi naaku inka nammakamaina samadhanam ledu.",
            f"Nee question {subject} gurinchi ani nenu ardham chesukunnanu.",
            "Nammakam leni vishayanni oohinchi cheppadam naaku ishtam ledu.",
        ]
        if ideas:
            lines.append("Parishodhinchagalige mukhyamaina directions:")
            lines.extend(f"- {idea}" for idea in ideas[:4])
        lines.append("Question konchem ambiguous ga unte, oka extra detail ivvu. Appudu meaning ni narrow cheyagalanu.")
        return "\n".join(lines)

    lines = [
        f"I don't have a reliable answer for '{subject}' yet.",
        f"I understand your question as being about {subject}.",
        "I don't want to invent a fact just to sound confident.",
    ]
    if ideas:
        lines.append("Useful directions to investigate:")
        lines.extend(f"- {idea}" for idea in ideas[:4])
    lines.append("If the question is ambiguous, give me one extra detail and I can narrow the meaning.")
    return "\n".join(lines)


def _localize_answer(answer: str, language: str) -> str:
    if language == "roman_telugu":
        translations = {
            "Hi Sathwik. I'm here. How are you?": "Hi Sathwik. Nenu ikkade unna. Nuvvu ela vunnavu?",
            "Hello Sathwik. What are we working on?": "Hello Sathwik. Manam em meeda work chestunnam?",
            "Hey Sathwik. I'm here.": "Hey Sathwik. Nenu ikkade unna.",
            "Good morning, Sathwik. What are we working on?": "Good morning, Sathwik. Manam em meeda work chestunnam?",
            "I'm functioning normally and ready to talk with you.": "Nenu normal ga function avutunna. Neetho matladataniki ready ga unna.",
            "I'm functioning normally too. I'm here and ready to help you, Sathwik.": "Nenu kuda normal ga function avutunna. Ikkade unna, neeku help cheyadaniki ready ga unna, Sathwik.",
            "I'm here, processing what you need and ready to help.": "Nuvvu em kavalo process chestu ikkade unna. Help cheyadaniki ready ga unna.",
            "You're welcome.": "Parvaledu.",
            "I'm Medha, your personal AI assistant.": "Nenu Medha, nee personal AI assistant ni.",
            "My name is Medha.": "Na peru Medha.",
            "You are Sathwik, my owner. I'm your personal AI assistant.": "Nuvvu Sathwik, naa owner. Nenu nee personal AI assistant ni.",
            "You are Sathwik, my owner, and I'm Medha, my personal AI assistant.": "Nuvvu Sathwik, naa owner. Nenu Medha, nee personal AI assistant ni.",
        }
        return translations.get(answer, answer)
    return answer


def generate_response(message, context, knowledge, search_manager, user_id=None):
    message = message.strip()
    language = detect_language(message)

    policy_check = apply_override("", message)
    if not policy_check["allowed"]:
        return {
            "answer": policy_check["response"],
            "source": "core_override",
        }

    if not message:
        return {
            "answer": f"I'm here, {OWNER_NAME}. Say something.",
            "source": "system",
        }

    normalized = " ".join(message.lower().split()).rstrip("?!.")
    if normalized in {"who am i to you", "what am i to you", "i am to you", "wt i am to u", "what is our relationship"}:
        identity_name = OWNER_NAME
        if user_id is not None:
            try:
                from backend.chats.store import get_user_by_id
                account = get_user_by_id(user_id)
                identity_name = account.get("username") if account else OWNER_NAME
            except Exception:
                identity_name = OWNER_NAME
        if language == "telugu":
            return {"answer": f"నువ్వు {identity_name}, నా యూజర్. నేను మెధా, నీ వ్యక్తిగత AI అసిస్టెంట్‌ను.", "source": "identity"}
        if language == "roman_telugu":
            return {"answer": f"Nuvvu {identity_name}, naa user. Nenu Medha, nee personal AI assistant ni.", "source": "identity"}
        return {"answer": f"You are {identity_name}, my user. I'm Medha, your personal AI assistant.", "source": "identity"}
    answer = UNDERSTANDING.best_memory_answer(message, context, user_id)
    if answer:
        return {
            "answer": _localize_answer(answer, language),
            "source": "memory",
        }

    intent = classify(message)

    if intent in {"casual", "memory", "personal"}:
        if intent == "personal":
            answers = {
                "telugu": "సరే. దీన్ని భవిష్యత్ సంభాషణల కోసం గుర్తుంచుకుంటాను.",
                "roman_telugu": "Sare. Dinni future conversations kosam gurthunchukunta.",
            }
            return {
                "answer": answers.get(language, "Got it. I'll keep that in mind for future conversations."),
                "source": "personal",
            }

        if intent == "memory":
            answers = {
                "telugu": "అది నాకు ఇంకా తెలియదు. ముఖ్యమైన వివరాన్ని చెప్పండి. భవిష్యత్ సంభాషణల కోసం గుర్తుంచుకుంటాను.",
                "roman_telugu": "Adi naaku inka teliyadu. Important detail cheppu. Future conversations kosam gurthunchukunta.",
            }
            return {
                "answer": answers.get(language, "I don't know that yet. Tell me the important detail and I'll remember it for future conversations."),
                "source": "memory_request",
            }

        answers = {
            "telugu": "అది నాకు ఇంకా తెలియదు. సమాధానం చెబితే ఉపయోగకరమైన విషయాన్ని గుర్తుంచుకుంటాను.",
            "roman_telugu": "Adi naaku inka teliyadu. Answer cheppu, useful part ni gurthunchukunta.",
        }
        return {
            "answer": answers.get(language, "I don't know that yet. Tell me the answer and I'll remember the useful part for future conversations."),
            "source": "ask_user",
        }

    result = search_manager.process(message, context)

    if result and result.get("answer"):
        return {
            "answer": _localize_answer(result["answer"], language),
            "source": result.get("source", "search"),
        }

    if result and result.get("source") == "knowledge_gap":
        return {
            "answer": _format_knowledge_gap(result, message),
            "source": "knowledge_gap",
        }

    answers = {
        "telugu": f"దీనికి నమ్మదగిన సమాచారం నాకు ఇంకా దొరకలేదు, {OWNER_NAME}.",
        "roman_telugu": f"Daaniki nammakamaina information naaku inka dorakaledu, {OWNER_NAME}.",
    }
    return {
        "answer": answers.get(language, f"I couldn't find reliable information about that yet, {OWNER_NAME}."),
        "source": "fallback",
    }
