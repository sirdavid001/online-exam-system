import csv
import io
from dataclasses import dataclass
from typing import Dict, List, Tuple

from exam.models import Question


EXPECTED_ORDER = [
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

    missing = [key for key in ("question", "marks", "option1", "option2", "option3", "option4", "answer") if key not in resolved]
    if missing:
        raise QuestionUploadError(
            "Missing required columns: " + ", ".join(missing)
        )

    return resolved


def _normalize_answer(raw_answer: str, option_values: Tuple[str, str, str, str]) -> str:
    token = (raw_answer or "").strip().lower()
    if token in ANSWER_MAP:
        return ANSWER_MAP[token]

    options = [opt.strip().lower() for opt in option_values]
    if token in options:
        index = options.index(token) + 1
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
                raw_question = (row.get(header_map["question"], "") or "").strip()
                raw_marks = (row.get(header_map["marks"], "") or "").strip()
                option1 = (row.get(header_map["option1"], "") or "").strip()
                option2 = (row.get(header_map["option2"], "") or "").strip()
                option3 = (row.get(header_map["option3"], "") or "").strip()
                option4 = (row.get(header_map["option4"], "") or "").strip()
                raw_answer = (row.get(header_map["answer"], "") or "").strip()
                raw_difficulty = (row.get(header_map.get("difficulty", ""), "") or "").strip()
                explanation = (row.get(header_map.get("explanation", ""), "") or "").strip()
            else:
                values = [str(value).strip() for value in row]
                values += [""] * (len(EXPECTED_ORDER) - len(values))
                raw_question, raw_marks, option1, option2, option3, option4, raw_answer, raw_difficulty, explanation = values[: len(EXPECTED_ORDER)]

            if not raw_question:
                raise QuestionUploadError("Question text is required.")

            try:
                marks = int(raw_marks)
            except (TypeError, ValueError) as exc:
                raise QuestionUploadError(f"Marks must be a positive integer, got '{raw_marks}'.") from exc

            if marks <= 0:
                raise QuestionUploadError("Marks must be greater than 0.")

            if not all([option1, option2, option3, option4]):
                raise QuestionUploadError("All four options are required.")

            answer = _normalize_answer(raw_answer, (option1, option2, option3, option4))
            difficulty = _normalize_difficulty(raw_difficulty)

            questions.append(
                Question(
                    course=course,
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
