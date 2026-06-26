"""
Handles Write/Assess selection, then Task 1/Task 2 selection, branching into
the correct awaiting_* state per our state machine diagram.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from db.database import set_user_state
from states.flow_states import Flow
from utils.keyboards import task_selection_kb, back_to_mode_kb, mode_selection_kb

router = Router()


@router.callback_query(Flow.choosing_mode, F.data.startswith("mode:"))
async def choose_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[1]  # 'write' | 'assess'
    await state.update_data(mode=mode)
    await state.set_state(Flow.choosing_task)
    await set_user_state(callback.from_user.id, "CHOOSING_TASK", {"mode": mode})

    label = "✍️ Write Mode" if mode == "write" else "📝 Assess Mode"
    await callback.message.edit_text(
        f"{label}\n\nWhich task would you like to work on?",
        reply_markup=task_selection_kb(),
    )
    await callback.answer()


@router.callback_query(Flow.choosing_task, F.data == "nav:back_to_mode")
async def back_to_mode(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Flow.choosing_mode)
    await set_user_state(callback.from_user.id, "CHOOSING_MODE", {})
    await callback.message.edit_text(
        "What would you like to do?", reply_markup=mode_selection_kb()
    )
    await callback.answer()


@router.callback_query(Flow.choosing_task, F.data.startswith("task:"))
async def choose_task(callback: CallbackQuery, state: FSMContext) -> None:
    task_type = callback.data.split(":")[1]  # 'task1' | 'task2'
    data = await state.get_data()
    mode = data.get("mode")
    await state.update_data(task_type=task_type)

    pending = {"mode": mode, "task_type": task_type}

    if task_type == "task1":
        # Both Write and Assess Task 1 start by requesting the chart/graph image
        await state.set_state(Flow.awaiting_image)
        await set_user_state(callback.from_user.id, "AWAITING_IMAGE", pending)
        await callback.message.edit_text(
            "📸 Please send a photo of your Task 1 chart, graph, table, map, "
            "or process diagram."
        )
    else:
        # Task 2 starts by requesting the essay topic as text
        await state.set_state(Flow.awaiting_topic_text)
        await set_user_state(callback.from_user.id, "AWAITING_TOPIC_TEXT", pending)
        await callback.message.edit_text(
            "📋 Please send me the Task 2 essay topic/question you want to "
            + ("write about." if mode == "write" else "be assessed on.")
        )
    await callback.answer()
