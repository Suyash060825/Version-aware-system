from models import CompiledAnswer, db

class AnswerStore:
    def get_answer(self, answer_id: int) -> CompiledAnswer:
        return db.session.get(CompiledAnswer, answer_id)
