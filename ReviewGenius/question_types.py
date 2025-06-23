class Question:
    def __init__(self, question_type, stem, answer, score=5):
        self.question_type = question_type
        self.stem = stem
        self.answer = answer
        self.score = score

    def to_dict(self):
        return {
            "question_type": self.question_type,
            "stem": self.stem,
            "answer": self.answer,
            "score": self.score,
        }

    @staticmethod
    def from_dict(data):
        question_type = data.get("question_type")
        if question_type == "multiple_choice":
            return MultipleChoiceQuestion.from_dict(data)
        elif question_type == "fill_in_the_blank":
            return FillInTheBlankQuestion.from_dict(data)
        elif question_type == "short_answer":
            return ShortAnswerQuestion.from_dict(data)
        else:
            raise ValueError(f"Unknown question type: {question_type}")


class MultipleChoiceQuestion(Question):
    def __init__(self, stem, options, answer, score=5):
        super().__init__("multiple_choice", stem, answer, score)
        self.options = options

    def to_dict(self):
        data = super().to_dict()
        data["options"] = self.options
        return data

    @staticmethod
    def from_dict(data):
        return MultipleChoiceQuestion(
            stem=data.get("stem"),
            options=data.get("options"),
            answer=data.get("answer"),
            score=data.get("score", 5),
        )


class FillInTheBlankQuestion(Question):
    def __init__(self, stem, answer, score=5):
        super().__init__("fill_in_the_blank", stem, answer, score)

    @staticmethod
    def from_dict(data):
        return FillInTheBlankQuestion(
            stem=data.get("stem"),
            answer=data.get("answer"),
            score=data.get("score", 5),
        )


class ShortAnswerQuestion(Question):
    def __init__(self, stem, answer, score=10):
        super().__init__("short_answer", stem, answer, score)

    @staticmethod
    def from_dict(data):
        return ShortAnswerQuestion(
            stem=data.get("stem"),
            answer=data.get("answer"),
            score=data.get("score", 10),
        ) 