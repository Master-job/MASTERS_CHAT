from aiogram.fsm.state import State, StatesGroup


class OrderSteps(StatesGroup):
    """Один общий стейт на весь интерактивный сценарий (квиз, запись на
    время, экран результата) — какой именно шаг сейчас, определяется
    данными в FSMContext (data['screen'], data['step_index'] и т.п.),
    а не отдельным State на каждый вопрос. Это и даёт единообразную
    Назад/Пропустить/К мастеру логику на любом шаге."""
    quiz = State()
