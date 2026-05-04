import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.db.models import AdaptiveQuestionBank  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402

UNIVERSAL_QUESTIONS: list[dict[str, Any]] = [
    {
        "text": "Расскажите о ситуации последней недели, которая вызвала у вас стресс.",
        "theme_tags": ["cbt", "gestalt", "psychosomatic"],
        "order_universal": 1,
    },
    {
        "text": "Опишите ваши ключевые отношения сейчас — с кем и как они складываются.",
        "theme_tags": ["family", "gestalt", "existential"],
        "order_universal": 2,
    },
    {
        "text": "Какую цель вы хотели бы достичь в ближайшие полгода и почему именно её?",
        "theme_tags": ["cbt", "existential", "nlp"],
        "order_universal": 3,
    },
    {
        "text": "Как ваше тело реагирует, когда вы устали или волнуетесь?",
        "theme_tags": ["psychosomatic", "gestalt"],
        "order_universal": 4,
    },
    {
        "text": "Опишите типичный конфликт, в который вы попадаете, и свою роль в нём.",
        "theme_tags": ["cbt", "family", "gestalt"],
        "order_universal": 5,
    },
]


ADAPTIVE_QUESTIONS: list[dict[str, Any]] = [
    {"text": "Что вы говорите себе, когда у вас что-то не получается?", "theme_tags": ["cbt"]},
    {"text": "Какие слова-абсолютисты («всегда», «никогда») вы замечаете в своей речи?", "theme_tags": ["cbt"]},
    {"text": "Что самое страшное может случиться, если вы совершите ошибку?", "theme_tags": ["cbt"]},
    {"text": "Бывает ли, что одна неудача обесценивает все ваши достижения?", "theme_tags": ["cbt"]},
    {"text": "Как часто вы проверяете свои выводы на предмет искажений?", "theme_tags": ["cbt"]},
    {"text": "Какие убеждения о себе вы считаете незыблемыми?", "theme_tags": ["cbt"]},

    {"text": "Какие эмоции прямо сейчас вам сложно осознавать?", "theme_tags": ["gestalt"]},
    {"text": "Как вы понимаете, что разговор для вас закончен?", "theme_tags": ["gestalt"]},
    {"text": "Опишите ситуацию, к которой вы мысленно возвращаетесь снова и снова.", "theme_tags": ["gestalt"]},
    {"text": "Какие свои потребности вы замечаете чаще всего?", "theme_tags": ["gestalt"]},
    {"text": "Бывает ли у вас ощущение «оцепенения» в значимый момент?", "theme_tags": ["gestalt"]},
    {"text": "Как вы реагируете, когда чувствуете раздражение?", "theme_tags": ["gestalt"]},

    {"text": "Что в вашей семье считалось «правильным», а что нет?", "theme_tags": ["family"]},
    {"text": "Какие фразы родителей вы ловите себя на том, что повторяете?", "theme_tags": ["family"]},
    {"text": "Какую роль вы обычно занимаете в семье сейчас?", "theme_tags": ["family"]},
    {"text": "Когда вы последний раз поступали наперекор ожиданиям родителей?", "theme_tags": ["family"]},
    {"text": "Какая тема в семье табуирована или замалчивается?", "theme_tags": ["family"]},
    {"text": "Что вы переняли от родителей и хотели бы передать дальше?", "theme_tags": ["family"]},

    {"text": "Что для вас значит «прожить эту неделю осмысленно»?", "theme_tags": ["existential"]},
    {"text": "За что в своей жизни вы готовы взять полную ответственность?", "theme_tags": ["existential"]},
    {"text": "Чем для вас является свобода выбора — облегчением или нагрузкой?", "theme_tags": ["existential"]},
    {"text": "Опишите три ценности, без которых вы не были бы собой.", "theme_tags": ["existential"]},
    {"text": "Что вы делаете, когда не знаете, ради чего просыпаться утром?", "theme_tags": ["existential"]},
    {"text": "Опишите момент, когда вы чувствовали глубокое одиночество.", "theme_tags": ["existential"]},

    {"text": "Где в теле вы обычно чувствуете напряжение в конце рабочего дня?", "theme_tags": ["psychosomatic"]},
    {"text": "Какие телесные симптомы появляются у вас перед сложной встречей?", "theme_tags": ["psychosomatic"]},
    {"text": "Опишите, что чувствует ваше тело, когда вы злитесь.", "theme_tags": ["psychosomatic"]},
    {"text": "Бывает ли, что вы не можете назвать словами, что чувствуете?", "theme_tags": ["psychosomatic"]},
    {"text": "Какая часть тела «помнит» неприятный опыт?", "theme_tags": ["psychosomatic"]},
    {"text": "Замечаете ли вы изменения дыхания в стрессовой ситуации?", "theme_tags": ["psychosomatic"]},

    {"text": "Опишите ваш идеальный рабочий день — как он выглядит?", "theme_tags": ["nlp"]},
    {"text": "Какие звуки или голоса вспоминаются вам, когда вы думаете о детстве?", "theme_tags": ["nlp"]},
    {"text": "На что похоже ваше текущее эмоциональное состояние?", "theme_tags": ["nlp"]},
    {"text": "Когда вы думаете об успехе, что появляется первым: картинка, звук или ощущение?", "theme_tags": ["nlp"]},
    {"text": "Опишите свою цель через сравнение или метафору.", "theme_tags": ["nlp"]},
    {"text": "Какое слово описывает вашу неделю лучше всего и почему?", "theme_tags": ["nlp"]},
]


async def seed_one(
    session: Any, text: str, theme_tags: list[str], is_universal: bool, order_universal: int | None
) -> bool:
    existing = (
        await session.execute(
            select(AdaptiveQuestionBank).where(AdaptiveQuestionBank.text == text)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False
    session.add(
        AdaptiveQuestionBank(
            text=text,
            theme_tags=theme_tags,
            is_universal=is_universal,
            order_universal=order_universal,
        )
    )
    return True


async def main() -> None:
    created = 0
    skipped = 0
    async with AsyncSessionLocal() as session:
        for q in UNIVERSAL_QUESTIONS:
            was_created = await seed_one(
                session,
                text=q["text"],
                theme_tags=q["theme_tags"],
                is_universal=True,
                order_universal=q["order_universal"],
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        for q in ADAPTIVE_QUESTIONS:
            was_created = await seed_one(
                session,
                text=q["text"],
                theme_tags=q["theme_tags"],
                is_universal=False,
                order_universal=None,
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        await session.commit()
    total = len(UNIVERSAL_QUESTIONS) + len(ADAPTIVE_QUESTIONS)
    print(
        f"[seed-adaptive] done: created={created} skipped={skipped} "
        f"total={total} (universal={len(UNIVERSAL_QUESTIONS)}, adaptive={len(ADAPTIVE_QUESTIONS)})"
    )


if __name__ == "__main__":
    asyncio.run(main())
