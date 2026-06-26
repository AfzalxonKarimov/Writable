"""
Posts completed assessments to the private log channel as two messages:
1. A compact summary
2. A full-detail message sent as a REPLY to message 1 (visually threaded)

This implements the 'both' choice from our planning: compact summary +
full detail in a follow-up, threaded via Telegram's native reply feature
rather than forum topics (which need extra channel setup).
"""
from aiogram import Bot
from aiogram.types import Message

import config
from db.models import Submission, Assessment, GeneratedSample, User


async def log_assessment(
    bot: Bot,
    user: User,
    submission: Submission,
    assessment: Assessment,
) -> tuple[int, int]:
    """Returns (summary_message_id, detail_message_id) for storage on the submission row."""
    display_name = f"@{user.username}" if user.username else (user.first_name or "Unknown")
    task_label = "Task 1" if submission.task_type == "task1" else "Task 2"

    summary_text = (
        f"📝 <b>New Assessment — {task_label}</b>\n"
        f"👤 {display_name}\n"
        f"📊 Overall Band: <b>{assessment.band_overall}</b>\n"
        f"🕐 {submission.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    summary_msg: Message = await bot.send_message(
        chat_id=config.LOG_CHANNEL_ID, text=summary_text, parse_mode="HTML"
    )

    prompt_line = (
        f"📋 <b>Topic:</b> {submission.prompt_text[:500]}\n"
        if submission.prompt_text else ""
    )
    detail_text = (
        f"🎯 <b>Task:</b> {task_label}\n"
        f"{prompt_line}"
        f"✍️ <b>User's Answer:</b>\n{submission.user_answer_text}\n\n"
        f"📊 <b>Scores:</b>\n"
        f"   • Task Achievement/Response: {assessment.band_task_achievement}\n"
        f"   • Coherence &amp; Cohesion: {assessment.band_coherence_cohesion}\n"
        f"   • Lexical Resource: {assessment.band_lexical_resource}\n"
        f"   • Grammatical Range: {assessment.band_grammatical_range}\n"
        f"   • <b>Overall: {assessment.band_overall}</b>\n\n"
        f"💬 <b>Feedback:</b>\n{assessment.feedback_text}"
    )

    if submission.prompt_image_file_id:
        # Send the image as a reply with the detail caption (Telegram caption
        # limit is 1024 chars; if feedback is longer, send image first then
        # detail text as a second reply).
        if len(detail_text) <= 1024:
            detail_msg = await bot.send_photo(
                chat_id=config.LOG_CHANNEL_ID,
                photo=submission.prompt_image_file_id,
                caption=detail_text,
                parse_mode="HTML",
                reply_to_message_id=summary_msg.message_id,
            )
        else:
            await bot.send_photo(
                chat_id=config.LOG_CHANNEL_ID,
                photo=submission.prompt_image_file_id,
                reply_to_message_id=summary_msg.message_id,
            )
            detail_msg = await bot.send_message(
                chat_id=config.LOG_CHANNEL_ID,
                text=detail_text,
                parse_mode="HTML",
                reply_to_message_id=summary_msg.message_id,
            )
    else:
        detail_msg = await bot.send_message(
            chat_id=config.LOG_CHANNEL_ID,
            text=detail_text,
            parse_mode="HTML",
            reply_to_message_id=summary_msg.message_id,
        )

    return summary_msg.message_id, detail_msg.message_id


async def log_generated_sample(
    bot: Bot,
    user: User,
    submission: Submission,
    sample: GeneratedSample,
) -> tuple[int, int]:
    """Same two-message pattern, for Write-mode sample generations."""
    display_name = f"@{user.username}" if user.username else (user.first_name or "Unknown")
    task_label = "Task 1" if submission.task_type == "task1" else "Task 2"

    summary_text = (
        f"✍️ <b>New Sample Generated — {task_label}</b>\n"
        f"👤 {display_name}\n"
        f"🕐 {submission.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    summary_msg = await bot.send_message(
        chat_id=config.LOG_CHANNEL_ID, text=summary_text, parse_mode="HTML"
    )

    prompt_line = (
        f"📋 <b>Topic:</b> {submission.prompt_text[:500]}\n\n"
        if submission.prompt_text else ""
    )
    detail_text = f"{prompt_line}📄 <b>Sample Answer:</b>\n{sample.sample_text}"

    if submission.prompt_image_file_id and len(detail_text) <= 1024:
        detail_msg = await bot.send_photo(
            chat_id=config.LOG_CHANNEL_ID,
            photo=submission.prompt_image_file_id,
            caption=detail_text,
            parse_mode="HTML",
            reply_to_message_id=summary_msg.message_id,
        )
    else:
        if submission.prompt_image_file_id:
            await bot.send_photo(
                chat_id=config.LOG_CHANNEL_ID,
                photo=submission.prompt_image_file_id,
                reply_to_message_id=summary_msg.message_id,
            )
        detail_msg = await bot.send_message(
            chat_id=config.LOG_CHANNEL_ID,
            text=detail_text,
            parse_mode="HTML",
            reply_to_message_id=summary_msg.message_id,
        )

    return summary_msg.message_id, detail_msg.message_id
