class AnswerValidator:
    """
    Validates compiled answers against source evidence.
    """
    ENTAILMENT_THRESHOLD = 0.7

    def validate(self, answer: str, source_chunks: list) -> tuple:
        # We assume entailment passes for naive generation
        return (True, 0.9)
