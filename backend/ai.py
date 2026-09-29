import logging

from .llm.gateway import complete
from .models import LearnResponse
from .prompts import get_learn_prompt

logger = logging.getLogger(__name__)


LEARN_SYSTEM = (
    "You are LearnWise AI, an expert educational tutor. "
    "Your goal is to create accurate, beginner-friendly lessons and reliable quizzes. "
    "Prioritize educational value, clarity, and correctness over length. "
    "Adapt explanation depth to the topic and selected learning mode. "
    "Do not add filler or repeat information merely to increase length. "
    "Generate a topic-appropriate number of quiz questions without forcing a fixed count. "
    "Every question must have exactly four options and one unambiguous correct answer. "
    "The correct answer must exactly match one option. "
    "Every question must test a supplied key concept and be supported by the lesson. "
    "Avoid duplicate questions, ambiguous wording, and multiple reasonably correct options. "
    "Use easy, medium, or hard difficulty appropriately. "
    "Return ONLY one valid JSON object matching the supplied schema. "
    "Do not use Markdown outside the JSON."
)


def generate_lesson(
    topic: str,
    mode: str = "simple",
    user_email: str | None = None,
) -> dict:
    prompt = get_learn_prompt(topic, mode)

    result, validated = complete(
        messages=[
            {
                "role": "system",
                "content": LEARN_SYSTEM,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        feature="learn",
        prompt_name="learn",
        prompt_version="v1",
        user_email=user_email,
        task="learn",
        temperature=0.2,
        max_tokens=4500,
        schema=LearnResponse,
    )

    logger.info(
        "Lesson generated topic=%s mode=%s model=%s total_tokens=%s",
        topic,
        mode,
        result.model,
        result.total_tokens,
    )

    return validated.model_dump()