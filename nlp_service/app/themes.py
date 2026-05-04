from typing import Any

from app.core.config import settings
from app.features import _tokenize

THEME_TAGS: tuple[str, ...] = (
    "cbt",
    "gestalt",
    "family",
    "existential",
    "nlp",
    "psychosomatic",
)

THEME_KEYWORDS: dict[str, frozenset[str]] = {
    "cbt": frozenset({
        "должен", "должна", "должно", "должны",
        "обязан", "обязана", "обязано", "обязаны",
        "всегда", "никогда",
        "ужасно", "катастрофа",
        "идеальный", "идеальная", "идеальное", "идеальные", "идеальной", "идеальным", "идеальному",
        "неудачник", "неудачница",
        "виноват", "виновата", "виноваты",
        "провал",
    }),
    "gestalt": frozenset({
        "чувствую", "чувствуешь", "чувствует",
        "сейчас",
        "осознаю", "осознаёшь", "осознает",
        "злюсь", "злость",
        "обида", "обижен", "обижена",
        "контакт", "диалог",
        "замечаю", "проживаю",
    }),
    "family": frozenset({
        "родители", "родителей", "родителям", "родителями",
        "мама", "маму", "мамой", "маме",
        "мать", "матери",
        "папа", "папу", "папой",
        "отец", "отца", "отцу",
        "брат", "брата",
        "сестра", "сестру",
        "детство", "детства",
        "семья", "семье", "семьёй",
        "муж", "мужа",
        "жена", "жену",
        "ребёнок", "ребёнка",
        "родственники",
    }),
    "existential": frozenset({
        "смысл", "смысла",
        "жизнь", "жизни",
        "смерть", "смерти",
        "одиночество", "одиночества",
        "свобода", "свободы",
        "выбор", "выбора",
        "ответственность", "ответственности",
        "бессмыслица",
        "конечность",
        "экзистенция",
    }),
    "nlp": frozenset({
        "представляю", "представляешь",
        "образ", "образа",
        "якорь", "якоря",
        "ресурс", "ресурса",
        "цель", "цели",
        "будущее", "будущего",
        "визуализирую", "визуализируешь",
        "состояние", "состояния",
        "моделирую",
        "метапрограмма",
    }),
    "psychosomatic": frozenset({
        "болит", "болят", "ноет", "давит", "колет", "тошнит", "ломит", "жжёт",
        "голова", "головы", "голову",
        "спина", "спины", "спину",
        "живот", "живота",
        "грудь", "груди",
        "симптом", "симптома", "симптомы",
        "тело", "тела",
        "напряжение",
        "тяжесть", "тяжести",
    }),
}

THEME_REFERENCES: dict[str, tuple[str, ...]] = {
    "cbt": (
        "Я должен быть идеальным во всём",
        "Никогда не справлюсь, я полный неудачник",
        "Это катастрофа, я во всём виноват",
    ),
    "gestalt": (
        "Я чувствую сейчас сильную тревогу внутри",
        "У меня внутри злость, которую я не выражаю",
        "Я не закрыл важный диалог из прошлого",
    ),
    "family": (
        "Мои родители всегда давили на меня",
        "В детстве мама была холодной и далёкой",
        "С отцом у нас сложные отношения",
    ),
    "existential": (
        "Я ищу смысл своей жизни",
        "Меня пугает мысль о смерти и одиночестве",
        "Свобода и ответственность давят на меня",
    ),
    "nlp": (
        "Я представляю свой образ успеха",
        "Якорь спокойствия помогает мне сосредоточиться",
        "Я визуализирую цель и пути к ней",
    ),
    "psychosomatic": (
        "У меня постоянно болит голова от стресса",
        "Тяжесть в груди и одышка преследуют меня",
        "Желудок сжимается, когда я нервничаю",
    ),
}

_theme_ref_embeddings: dict[str, list[Any]] | None = None


def _get_rubert() -> tuple[Any, Any]:
    try:
        from app.main import _MODELS, _model_state

        if _model_state.get("loaded") and _MODELS["tokenizer"] is not None:
            return _MODELS["tokenizer"], _MODELS["model"]
    except ImportError:
        pass

    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        settings.MODEL_NAME,
        cache_dir=settings.MODEL_CACHE_DIR,
    )
    model = AutoModel.from_pretrained(
        settings.MODEL_NAME,
        cache_dir=settings.MODEL_CACHE_DIR,
    )
    model.eval()
    return tokenizer, model


def _embed_text(text: str) -> Any:
    import torch

    tokenizer, model = _get_rubert()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[0, 0, :]


def _ensure_theme_embeddings() -> dict[str, list[Any]]:
    global _theme_ref_embeddings
    if _theme_ref_embeddings is None:
        cache: dict[str, list[Any]] = {}
        for tag, sentences in THEME_REFERENCES.items():
            cache[tag] = [_embed_text(s) for s in sentences]
        _theme_ref_embeddings = cache
    return _theme_ref_embeddings


def unload_theme_embeddings() -> None:
    global _theme_ref_embeddings
    _theme_ref_embeddings = None


def _cosine(a: Any, b: Any) -> float:
    import torch.nn.functional as F

    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0), dim=-1).item())


def detect_themes(text: str) -> list[dict[str, Any]]:
    if not text.strip():
        return []

    tokens = _tokenize(text)
    text_emb = _embed_text(text)
    refs = _ensure_theme_embeddings()

    results: list[dict[str, Any]] = []
    for tag in THEME_TAGS:
        kw_hits = sum(1 for t in tokens if t in THEME_KEYWORDS[tag])
        kw_score = min(1.0, kw_hits / 4.0)
        cos_max = max(_cosine(text_emb, ref) for ref in refs[tag])
        cos_norm = max(0.0, min(1.0, (cos_max - 0.5) * 2.0))
        score = min(1.0, 0.6 * kw_score + 0.5 * cos_norm)
        if score > 0.3:
            results.append({"tag": tag, "score": float(score)})

    return sorted(results, key=lambda r: r["score"], reverse=True)
