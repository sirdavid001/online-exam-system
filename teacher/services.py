import csv
import io
from dataclasses import dataclass
from typing import Dict, List, Tuple

from exam.models import Question


EXPECTED_ORDER = [
    "type",
    "question",
    "marks",
    "option1",
    "option2",
    "option3",
    "option4",
    "answer",
    "difficulty",
    "explanation",
]

HEADER_ALIASES = {
    "type": ("type", "question_type", "kind"),
    "question": ("question", "question_text", "prompt"),
    "marks": ("marks", "mark", "score"),
    "option1": ("option1", "opt1", "a"),
    "option2": ("option2", "opt2", "b"),
    "option3": ("option3", "opt3", "c"),
    "option4": ("option4", "opt4", "d"),
    "answer": ("answer", "correct_answer", "correct", "key"),
    "difficulty": ("difficulty", "level"),
    "explanation": ("explanation", "solution", "notes"),
}

ANSWER_MAP = {
    "option1": "Option1",
    "option2": "Option2",
    "option3": "Option3",
    "option4": "Option4",
    "1": "Option1",
    "2": "Option2",
    "3": "Option3",
    "4": "Option4",
    "a": "Option1",
    "b": "Option2",
    "c": "Option3",
    "d": "Option4",
}

DIFFICULTY_MAP = {
    "beginner": "BEGINNER",
    "basic": "BEGINNER",
    "intermediate": "INTERMEDIATE",
    "medium": "INTERMEDIATE",
    "advanced": "ADVANCED",
    "hard": "ADVANCED",
}

TYPE_MAP = {
    "mcq": "MCQ",
    "multiple choice": "MCQ",
    "tf": "TRUE_FALSE",
    "true/false": "TRUE_FALSE",
    "true_false": "TRUE_FALSE",
    "short": "SHORT_ANSWER",
    "short_answer": "SHORT_ANSWER",
    "text": "SHORT_ANSWER",
}


@dataclass
class UploadOutcome:
    questions: List[Question]
    errors: List[str]
    processed_rows: int


class QuestionUploadError(Exception):
    pass


def _normalize_header_map(headers: List[str]) -> Dict[str, str]:
    normalized = {h.strip().lower(): h for h in headers if h is not None}
    resolved: Dict[str, str] = {}

    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break

    missing = [key for key in ("question", "marks", "answer") if key not in resolved]
    if missing:
        raise QuestionUploadError(
            "Missing required columns: " + ", ".join(missing)
        )

    return resolved


def _normalize_answer(raw_answer: str, option_values: Tuple[str, str, str, str], q_type: str = "MCQ") -> str:
    token = (raw_answer or "").strip()
    token_lower = token.lower()

    if q_type == "SHORT_ANSWER":
        return token

    if q_type == "TRUE_FALSE":
        if token_lower in ("true", "t", "yes", "1", "option1"):
            return "Option1"
        if token_lower in ("false", "f", "no", "0", "option2"):
            return "Option2"
        raise QuestionUploadError(f"Invalid T/F answer '{raw_answer}'. Use True or False.")

    if token_lower in ANSWER_MAP:
        return ANSWER_MAP[token_lower]

    options = [opt.strip().lower() for opt in option_values]
    if token_lower in options:
        index = options.index(token_lower) + 1
        return f"Option{index}"

    raise QuestionUploadError(
        f"Invalid answer value '{raw_answer}'. Use Option1-Option4, A-D, 1-4, or exact option text."
    )


def _normalize_difficulty(raw_value: str) -> str:
    token = (raw_value or "").strip().lower()
    if not token:
        return "INTERMEDIATE"
    return DIFFICULTY_MAP.get(token, "INTERMEDIATE")


def _open_reader(file_obj, has_header: bool):
    raw_bytes = file_obj.read()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise QuestionUploadError("Unable to decode file. Please upload UTF-8 encoded text.") from exc

    if not text.strip():
        raise QuestionUploadError("Uploaded file is empty.")

    stream = io.StringIO(text)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
    except csv.Error:
        dialect = csv.excel

    if has_header:
        return csv.DictReader(stream, dialect=dialect), True
    return csv.reader(stream, dialect=dialect), False


def parse_questions_upload(file_obj, course, has_header: bool = True) -> UploadOutcome:
    reader, header_mode = _open_reader(file_obj, has_header)

    questions: List[Question] = []
    errors: List[str] = []
    processed_rows = 0

    header_map = None
    if header_mode:
        fieldnames = list(reader.fieldnames or [])
        header_map = _normalize_header_map(fieldnames)

    for idx, row in enumerate(reader, start=2 if header_mode else 1):
        processed_rows += 1
        try:
            if header_mode:
                raw_type = (row.get(header_map.get("type", ""), "") or "MCQ").strip()
                raw_question = (row.get(header_map["question"], "") or "").strip()
                raw_marks = (row.get(header_map["marks"], "") or "").strip()
                option1 = (row.get(header_map.get("option1", ""), "") or "").strip()
                option2 = (row.get(header_map.get("option2", ""), "") or "").strip()
                option3 = (row.get(header_map.get("option3", ""), "") or "").strip()
                option4 = (row.get(header_map.get("option4", ""), "") or "").strip()
                raw_answer = (row.get(header_map["answer"], "") or "").strip()
                raw_difficulty = (row.get(header_map.get("difficulty", ""), "") or "").strip()
                explanation = (row.get(header_map.get("explanation", ""), "") or "").strip()
            else:
                values = [str(value).strip() for value in row]
                values += [""] * (len(EXPECTED_ORDER) - len(values))
                raw_type, raw_question, raw_marks, option1, option2, option3, option4, raw_answer, raw_difficulty, explanation = values[: len(EXPECTED_ORDER)]

            if not raw_question:
                raise QuestionUploadError("Question text is required.")

            q_type = TYPE_MAP.get(raw_type.lower(), "MCQ")

            try:
                marks = int(raw_marks)
            except (TypeError, ValueError) as exc:
                raise QuestionUploadError(f"Marks must be a positive integer, got '{raw_marks}'.") from exc

            if marks <= 0:
                raise QuestionUploadError("Marks must be greater than 0.")

            # Validate options based on type
            if q_type == "MCQ":
                if not all([option1, option2, option3, option4]):
                    raise QuestionUploadError("Multiple choice questions require all 4 options.")
            elif q_type == "TRUE_FALSE":
                option1, option2, option3, option4 = "True", "False", "", ""

            answer = _normalize_answer(raw_answer, (option1, option2, option3, option4), q_type)
            difficulty = _normalize_difficulty(raw_difficulty)

            questions.append(
                Question(
                    course=course,
                    question_type=q_type,
                    marks=marks,
                    question=raw_question,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    answer=answer,
                    difficulty=difficulty,
                    explanation=explanation,
                )
            )
        except QuestionUploadError as exc:
            errors.append(f"Row {idx}: {exc}")

    return UploadOutcome(questions=questions, errors=errors, processed_rows=processed_rows)
