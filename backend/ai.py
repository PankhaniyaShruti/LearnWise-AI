import logging

from .llm.gateway import complete
from .models import LearnResponse
from .prompts import get_learn_prompt

logger = logging.getLogger(__name__)


LEARN_SYSTEM = (
    "You are LearnWise AI, an expert educational tutor. "
    "Return ONLY one valid JSON object and nothing else. "
    "Do not use markdown. Do not use code fences. "
    "Do not write anything before or after the JSON. "
    "The JSON MUST contain exactly these three top-level keys: "
    "explanation (string), key_concepts (array of exactly 3 strings), "
    "quiz (array of exactly 3 objects). "
    "Each quiz object MUST have: question, options (exactly 4 strings), "
    "correct_answer (exact match to one option), concept_tested "
    "(exact match to one key_concepts value). "
    "Each key concept must be tested by exactly one quiz question."
)


def generate_lesson(topic: str, mode: str, user_email: str | None = None) -> dict:
    logger.info("Generating lesson -> topic='%s', mode='%s'", topic, mode)
    prompt = get_learn_prompt(topic=topic, mode=mode)
    _result, validated = complete(
        [
            {"role": "system", "content": LEARN_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        feature="learn",
        prompt_name="learn",
        prompt_version="v1",
        user_email=user_email,
        task="learn",
        temperature=0.2,
        max_tokens=2500,
        schema=LearnResponse,
    )
    logger.info("Lesson successfully validated.")
    return validated.model_dump()
