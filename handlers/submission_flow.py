"""
Collects the actual content (image file_id, topic text, user's answer text),
then shows the REVIEW_BEFORE_SUBMIT screen with Edit/Submit buttons.

Also hosts render_state(), the single source of truth for 're-display state X
on screen' -- used both by normal flow transitions and by the /start
'Continue' resume path, so the two never drift out of sync.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
from db.database import set_user_state
from states.flow_states import Flow
from utils.keyboards import review_kb

router = Router()


def _build_review_text(pending: dict) -> str:
    mode_label = "✍️ Write" if pending.get("mode") == "write" else "📝 Assess"
    task_label = "Task 1" if pending.get("task_type") == "task1" else "Task 2"

    lines = [f"<b>Review your submission</b>", f"{mode_label} — {task_label}", ""]

    if pending.get("task_type") == "task1":
        lines.append("📸 Image: attached" if pending.get("image_file_id") else "📸 Image: ⚠️ missing")
    else:
        topic = pending.get("topic_text", "")
        lines.append(f"📋 Topic: {topic[:300]}")

    if pending.get("mode") == "assess":
        answer = pending.get("answer_text", "")
        preview = answer[:300] + ("..." if len(answer) > 300 else "")
        lines.append(f"\n✍️ Your answer ({len(answer)} chars):\n{preview}")

    lines.append("\nLooks good, or want to change something?")
    return "\n".join(lines)


async def _go_to_review(message: Message, state: FSMContext, pending: dict, telegram_id: int) -> None:
    await state.set_state(Flow.review_before_submit)
    await set_user_state(telegram_id, "REVIEW_BEFORE_SUBMIT", pending)
    await message.answer(
        _build_review_text(pending), parse_mode="HTML", reply_markup=review_kb()
    )


@router.message(Flow.awaiting_image, F.photo)
async def receive_image(message: Message, state: FSMContext) -> None:
    # Telegram sends multiple sizes; the last one is the highest resolution
    file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=file_id)
    data = await state.get_data()

    if data.get("mode") == "assess":
        # Assess Task 1 needs the user's written answer too
        await state.set_state(Flow.awaiting_answer_text)
        await set_user_state(message.from_user.id, "AWAITING_ANSWER_TEXT", data)
        await message.answer(
            "✅ Got the image. Now please send your written description of "
            "this chart/graph/map (paste your full answer as a text message)."
        )
    else:
        # Write Task 1 has everything it needs now
        await _go_to_review(message, state, data, message.from_user.id)


@router.message(Flow.awaiting_image, ~F.photo)
async def reject_non_image(message: Message) -> None:
    await message.answer("⚠️ Please send a photo (not text) of your Task 1 chart/graph/map.")


@router.message(Flow.awaiting_topic_text, F.text)
async def receive_topic(message: Message, state: FSMContext) -> None:
    await state.update_data(topic_text=message.text)
    data = await state.get_data()

    if data.get("mode") == "assess":
        await state.set_state(Flow.awaiting_answer_text)
        await set_user_state(message.from_user.id, "AWAITING_ANSWER_TEXT", data)
        await message.answer(
            "✅ Got the topic. Now please paste your full essay as a text message."
        )
    else:
        await _go_to_review(message, state, data, message.from_user.id)


@router.message(Flow.awaiting_answer_text, F.text)
async def receive_answer(message: Message, state: FSMContext) -> None:
    if len(message.text) > config.MAX_ANSWER_LENGTH:
        await message.answer(
            f"⚠️ That's a bit too long ({len(message.text)} chars, max "
            f"{config.MAX_ANSWER_LENGTH}). Please shorten it and resend."
        )
        return

    await state.update_data(answer_text=message.text)
    data = await state.get_data()
    await _go_to_review(message, state, data, message.from_user.id)


@router.message(Flow.awaiting_answer_text, ~F.text)
async def reject_non_text_answer(message: Message) -> None:
    await message.answer("⚠️ Please send your answer as a text message (not a photo or file).")


@router.callback_query(Flow.review_before_submit, F.data == "review:edit")
async def review_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Simplest correct behavior: send them back to re-supply whichever piece
    of content matters most for their mode/task, since they may want to
    redo the image, the topic, or the answer text. We route back to the
    earliest required input so nothing is skipped.
    """
    data = await state.get_data()
    task_type = data.get("task_type")

    if task_type == "task1":
        await state.set_state(Flow.awaiting_image)
        await set_user_state(callback.from_user.id, "AWAITING_IMAGE", data)
        await callback.message.edit_text(
            "📸 Send a new photo of your Task 1 chart, graph, table, map, or "
            "process diagram."
        )
    else:
        await state.set_state(Flow.awaiting_topic_text)
        await set_user_state(callback.from_user.id, "AWAITING_TOPIC_TEXT", data)
        await callback.message.edit_text("📋 Send the (new) Task 2 essay topic.")
    await callback.answer()


# --- Resume rendering: single source of truth for 're-show state X' ---

async def render_state(message: Message, state: FSMContext, current_state: str, pending_data: dict) -> None:
    """
    Re-displays whatever screen corresponds to current_state, using the
    pending_data restored from the DB. Used by the /start 'Continue' button.
    """
    await state.set_data(pending_data)

    state_map = {
        "CHOOSING_MODE": (Flow.choosing_mode, "What would you like to do?", "mode"),
        "CHOOSING_TASK": (Flow.choosing_task, "Which task?", "task"),
        "AWAITING_IMAGE": (Flow.awaiting_image, "📸 Please resend your Task 1 image.", None),
        "AWAITING_TOPIC_TEXT": (Flow.awaiting_topic_text, "📋 Please resend the Task 2 topic.", None),
        "AWAITING_ANSWER_TEXT": (Flow.awaiting_answer_text, "✍️ Please resend your written answer.", None),
    }

    if current_state == "REVIEW_BEFORE_SUBMIT":
        await state.set_state(Flow.review_before_submit)
        await message.answer(
            _build_review_text(pending_data), parse_mode="HTML", reply_markup=review_kb()
        )
        return

    entry = state_map.get(current_state)
    if entry is None:
        # Unknown/expired state -- safest fallback is to restart cleanly
        from utils.keyboards import mode_selection_kb
        await state.set_state(Flow.choosing_mode)
        await set_user_state(message.chat.id, "CHOOSING_MODE", {})
        await message.answer("Let's start fresh. What would you like to do?", reply_markup=mode_selection_kb())
        return

    target_state, text, kb_kind = entry
    await state.set_state(target_state)
    if kb_kind == "mode":
        from utils.keyboards import mode_selection_kb
        await message.answer(text, reply_markup=mode_selection_kb())
    elif kb_kind == "task":
        from utils.keyboards import task_selection_kb
        await message.answer(text, reply_markup=task_selection_kb())
    else:
        await message.answer(text)
