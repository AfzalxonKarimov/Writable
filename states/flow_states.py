"""
aiogram FSM states. These names map 1:1 onto the state machine we designed:

IDLE -> CHOOSING_MODE -> CHOOSING_TASK ->
  AWAITING_IMAGE / AWAITING_TOPIC_TEXT -> [AWAITING_ANSWER_TEXT] ->
  REVIEW_BEFORE_SUBMIT -> AI_PROCESSING -> RESULT_SHOWN -> IDLE

Note: aiogram's built-in FSMContext is in-memory by default. We deliberately
do NOT rely on it alone -- db.database.set_user_state() mirrors every
transition to the database, since that's what survives restarts. Think of
FSMContext as a fast cache and the DB column as the source of truth.
"""
from aiogram.fsm.state import State, StatesGroup


class Flow(StatesGroup):
    idle = State()
    resume_prompt = State()
    choosing_mode = State()
    choosing_task = State()
    awaiting_image = State()
    awaiting_topic_text = State()
    awaiting_answer_text = State()
    review_before_submit = State()
    ai_processing = State()
    result_shown = State()
