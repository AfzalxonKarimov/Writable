"""
/start handler. Implements our decision: if the user has an in-progress flow,
ask 'Continue or Start Over?' instead of silently resetting.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from db.database import get_or_create_user, set_user_state, clear_pending_data
from states.flow_states import Flow
from utils.keyboards import resume_or_restart_kb, mode_selection_kb

router = Router()


WELCOME_TEXT = (
    "👋 Welcome to the IELTS Writing Bot!\n\n"
    "I can help you in two ways:\n"
    "✍️ <b>Write</b> — give me a Task 1 chart/photo or a Task 2 topic, "
    "and I'll generate a band-9 model answer for you to study.\n"
    "📝 <b>Assess</b> — submit your own writing and get a real IELTS-style "
    "band score (Task Achievement, Coherence, Lexical Resource, Grammar) "
    "plus detailed feedback.\n\n"
    "What would you like to do?"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if user.current_state and user.current_state not in ("IDLE", "RESULT_SHOWN"):
        await message.answer(
            "👋 Welcome back! You have an unfinished submission in progress.\n\n"
            "Would you like to continue where you left off, or start over?",
            reply_markup=resume_or_restart_kb(),
        )
        await state.set_state(Flow.resume_prompt)
        return

    await state.set_state(Flow.choosing_mode)
    await set_user_state(message.from_user.id, "CHOOSING_MODE")
    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=mode_selection_kb())


@router.callback_query(F.data == "resume:restart")
async def resume_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await clear_pending_data(callback.from_user.id)
    await state.set_state(Flow.choosing_mode)
    await set_user_state(callback.from_user.id, "CHOOSING_MODE")
    await callback.message.edit_text(
        WELCOME_TEXT, parse_mode="HTML", reply_markup=mode_selection_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "resume:continue")
async def resume_continue(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Resume logic: re-enter the saved state with pending_data intact.
    The actual re-rendering of each state's prompt/keyboard is delegated to
    submission_flow.py's render_state() so there's one source of truth for
    'what does state X look like on screen' rather than duplicating it here.
    """
    from handlers.submission_flow import render_state  # local import avoids circular import

    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    await render_state(callback.message, state, user.current_state, user.pending_data)
    await callback.answer()
