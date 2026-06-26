"""
Inline keyboard builders. One function per decision point in the flow,
named to match the state machine so it's obvious which keyboard belongs
to which state.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def resume_or_restart_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Continue", callback_data="resume:continue")
    builder.button(text="🔄 Start Over", callback_data="resume:restart")
    builder.adjust(2)
    return builder.as_markup()


def mode_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Write", callback_data="mode:write")
    builder.button(text="📝 Assess", callback_data="mode:assess")
    builder.adjust(2)
    return builder.as_markup()


def task_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Task 1", callback_data="task:task1")
    builder.button(text="Task 2", callback_data="task:task2")
    builder.adjust(2)
    return builder.as_markup()


def review_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data="review:edit")
    builder.button(text="✅ Submit for AI", callback_data="review:submit")
    builder.adjust(2)
    return builder.as_markup()


def result_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 New Submission", callback_data="result:new")
    builder.button(text="🏠 Main Menu", callback_data="result:menu")
    builder.adjust(2)
    return builder.as_markup()


def back_to_mode_kb() -> InlineKeyboardMarkup:
    """Used on the task-selection screen to let users back out to mode choice."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back", callback_data="nav:back_to_mode")
    return builder.as_markup()
