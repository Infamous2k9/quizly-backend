from pydantic import BaseModel


class GeneratedQuestion(BaseModel):
    """Structure of a single question returned by Gemini."""

    question_title: str
    question_options: list[str]
    answer: str


class GeneratedQuiz(BaseModel):
    """Structure of a complete quiz returned by Gemini."""

    title: str
    description: str
    questions: list[GeneratedQuestion]
