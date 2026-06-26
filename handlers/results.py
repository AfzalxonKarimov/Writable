"""
Handles 'Submit for AI' -> calls the AI, writes Submission + Assessment/
GeneratedSample rows, posts to the log channel, and shows the result.
This is the AI_PROCESSING -> RESULT_SHOWN transition in our state machine.
"""
import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from db.database import async_session, set_user_state, clear_pending_data, get_or_create_user
from db.models import Submission, Assessment, GeneratedSample
from services import ai_client, prompts, channel_logger
from states.flow_states import Flow
from utils.keyboards import result_kb, mode_selection_kb

logger = logging.getLogger(__name__)
router = Router()


async def _get_image_url(bot: Bot, file_id: str) -> str:
    """
    OpenRouter needs a fetchable URL, not a Telegram file_id. Telegram file
    URLs are public-by-token (anyone with the link + your bot token segment
    can fetch them for a limited time), which is fine for a single
    server-side API call made immediately after upload.
    """
    file = await bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"


@router.callback_query(Flow.review_before_submit, F.data == "review:submit")
async def submit_for_ai(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    telegram_id = callback.from_user.id

    await state.set_state(Flow.ai_processing)
    await set_user_state(telegram_id, "AI_PROCESSING", data)
    await callback.message.edit_text("⏳ Analyzing your writing... this can take up to a minute.")
    await callback.answer()

    user = await get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)

    mode = data.get("mode")
    task_type = data.get("task_type")
    image_file_id = data.get("image_file_id")
    topic_text = data.get("topic_text")
    answer_text = data.get("answer_text")

    image_url = await _get_image_url(bot, image_file_id) if image_file_id else None

    try:
        if mode == "assess":
            await _handle_assess(bot, callback, state, user, task_type, image_file_id, image_url, topic_text, answer_text)
        else:
            await _handle_write(bot, callback, state, user, task_type, image_file_id, image_url, topic_text)
    except ai_client.AIRequestError as e:
        logger.error(f"AI request failed for user {telegram_id}: {e}")
        await callback.message.answer(
            "😔 Sorry, the AI service is having trouble right now (all backup "
            "models failed too). Please try again in a few minutes."
        )
        await state.set_state(Flow.review_before_submit)
        await set_user_state(telegram_id, "REVIEW_BEFORE_SUBMIT", data)


async def _handle_assess(bot, callback, state, user, task_type, image_file_id, image_url, topic_text, answer_text) -> None:
    if task_type == "task1":
        prompt = prompts.build_assess_task1_prompt(answer_text)
    else:
        prompt = prompts.build_assess_task2_prompt(topic_text, answer_text)

    result, model_used = await ai_client.assess_writing(prompt, image_file_url=image_url)

    async with async_session() as session:
        submission = Submission(
            user_id=user.id,
            mode="assess",
            task_type=task_type,
            prompt_image_file_id=image_file_id,
            prompt_text=topic_text,
            user_answer_text=answer_text,
            ai_model_used=model_used,
            status="completed",
        )
        session.add(submission)
        await session.flush()  # get submission.id before creating the assessment row

        assessment = Assessment(
            submission_id=submission.id,
            band_task_achievement=result["band_task_achievement"],
            band_coherence_cohesion=result["band_coherence_cohesion"],
            band_lexical_resource=result["band_lexical_resource"],
            band_grammatical_range=result["band_grammatical_range"],
            band_overall=result["band_overall"],
            feedback_text=result["feedback"],
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(submission)
        await session.refresh(assessment)

        summary_id, detail_id = await channel_logger.log_assessment(bot, user, submission, assessment)
        submission.log_summary_message_id = summary_id
        submission.log_detail_message_id = detail_id
        await session.commit()

    result_text = (
        f"📊 <b>Your IELTS Band Scores</b>\n\n"
        f"Task Achievement/Response: <b>{assessment.band_task_achievement}</b>\n"
        f"Coherence &amp; Cohesion: <b>{assessment.band_coherence_cohesion}</b>\n"
        f"Lexical Resource: <b>{assessment.band_lexical_resource}</b>\n"
        f"Grammatical Range: <b>{assessment.band_grammatical_range}</b>\n"
        f"🎯 <b>Overall Band: {assessment.band_overall}</b>\n\n"
        f"💬 <b>Feedback:</b>\n{assessment.feedback_text}"
    )
    await callback.message.answer(result_text, parse_mode="HTML", reply_markup=result_kb())
    await state.set_state(Flow.result_shown)
    await set_user_state(user.telegram_id, "RESULT_SHOWN", {})


async def _handle_write(bot, callback, state, user, task_type, image_file_id, image_url, topic_text) -> None:
    if task_type == "task1":
        prompt = prompts.build_write_task1_prompt()
    else:
        prompt = prompts.build_write_task2_prompt(topic_text)

    result, model_used = await ai_client.generate_sample(prompt, image_file_url=image_url)
    sample_text = result["sample_answer"]
    # For Task 1, the AI also describes the image -- store that as prompt_text
    derived_prompt_text = result.get("image_description") if task_type == "task1" else topic_text

    async with async_session() as session:
        submission = Submission(
            user_id=user.id,
            mode="write",
            task_type=task_type,
            prompt_image_file_id=image_file_id,
            prompt_text=derived_prompt_text,
            ai_model_used=model_used,
            status="completed",
        )
        session.add(submission)
        await session.flush()

        sample = GeneratedSample(submission_id=submission.id, sample_text=sample_text)
        session.add(sample)
        await session.commit()
        await session.refresh(submission)
        await session.refresh(sample)

        summary_id, detail_id = await channel_logger.log_generated_sample(bot, user, submission, sample)
        submission.log_summary_message_id = summary_id
        submission.log_detail_message_id = detail_id
        await session.commit()

    result_text = f"📄 <b>Your Band-9 Model Answer</b>\n\n{sample_text}"
    await callback.message.answer(result_text, parse_mode="HTML", reply_markup=result_kb())
    await state.set_state(Flow.result_shown)
    await set_user_state(user.telegram_id, "RESULT_SHOWN", {})


@router.callback_query(Flow.result_shown, F.data == "result:new")
async def result_new_submission(callback: CallbackQuery, state: FSMContext) -> None:
    await clear_pending_data(callback.from_user.id)
    await state.set_state(Flow.choosing_mode)
    await set_user_state(callback.from_user.id, "CHOOSING_MODE", {})
    await callback.message.answer("What would you like to do?", reply_markup=mode_selection_kb())
    await callback.answer()


@router.callback_query(Flow.result_shown, F.data == "result:menu")
async def result_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await clear_pending_data(callback.from_user.id)
    await state.set_state(Flow.choosing_mode)
    await set_user_state(callback.from_user.id, "CHOOSING_MODE", {})
    await callback.message.answer("🏠 Main Menu\n\nWhat would you like to do?", reply_markup=mode_selection_kb())
    await callback.answer()
