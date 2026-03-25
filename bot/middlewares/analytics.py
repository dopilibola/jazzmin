"""
Analytics Middleware.
Automatically tracks all bot events without modifying existing handlers.
"""
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update
from aiogram.fsm.context import FSMContext

from bot.services.analytics_tracker import AnalyticsTracker

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(BaseMiddleware):
    """
    Middleware that automatically tracks all user interactions.

    Tracks:
    - Commands (/start, /help, etc.)
    - Button clicks (reply keyboard)
    - Callback queries (inline keyboard)
    - State transitions
    - Messages

    Does NOT modify any existing bot logic.
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Process update and track analytics."""
        # Extract user info and event details
        user_info = self._extract_user_info(event)
        event_info = self._extract_event_info(event, data)

        if user_info and event_info:
            # Track the event asynchronously (don't block the handler)
            try:
                await AnalyticsTracker.track_event(
                    telegram_id=user_info['telegram_id'],
                    event_type=event_info['type'],
                    event_name=event_info['name'],
                    username=user_info.get('username'),
                    first_name=user_info.get('first_name'),
                    metadata=event_info.get('metadata'),
                )
            except Exception as e:
                # Never let analytics break the bot
                logger.error(f"Analytics tracking failed: {e}")

        # Continue to the handler
        return await handler(event, data)

    def _extract_user_info(self, event: Update) -> Optional[Dict[str, Any]]:
        """Extract user information from update."""
        user = None

        if event.message and event.message.from_user:
            user = event.message.from_user
        elif event.callback_query and event.callback_query.from_user:
            user = event.callback_query.from_user
        elif event.inline_query and event.inline_query.from_user:
            user = event.inline_query.from_user

        if not user:
            return None

        return {
            'telegram_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
        }

    def _extract_event_info(self, event: Update, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract event information from update."""

        # Handle Message events
        if event.message:
            message = event.message

            # Command
            if message.text and message.text.startswith('/'):
                command = message.text.split()[0]
                return {
                    'type': 'command',
                    'name': command,
                    'metadata': {'full_text': message.text[:100]},
                }

            # Reply keyboard button click
            if message.text:
                return {
                    'type': 'button_click',
                    'name': message.text[:100],
                    'metadata': None,
                }

            # Contact shared
            if message.contact:
                return {
                    'type': 'message',
                    'name': 'contact_shared',
                    'metadata': None,
                }

            # Photo sent
            if message.photo:
                return {
                    'type': 'message',
                    'name': 'photo_sent',
                    'metadata': {'photo_count': len(message.photo)},
                }

            # Document sent
            if message.document:
                return {
                    'type': 'message',
                    'name': 'document_sent',
                    'metadata': {'mime_type': message.document.mime_type},
                }

            # Other message
            return {
                'type': 'message',
                'name': 'text_message',
                'metadata': None,
            }

        # Handle Callback Query events
        if event.callback_query:
            callback = event.callback_query
            return {
                'type': 'callback',
                'name': callback.data or 'unknown_callback',
                'metadata': None,
            }

        return None


class StateTrackingMiddleware(BaseMiddleware):
    """
    Middleware that tracks FSM state transitions.
    Useful for understanding where users spend time.
    """

    # Store previous states
    _previous_states: Dict[int, str] = {}

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Track state transitions."""
        # Get user ID
        user_id = None
        user_info = {}

        if event.message and event.message.from_user:
            user_id = event.message.from_user.id
            user_info = {
                'username': event.message.from_user.username,
                'first_name': event.message.from_user.first_name,
            }
        elif event.callback_query and event.callback_query.from_user:
            user_id = event.callback_query.from_user.id
            user_info = {
                'username': event.callback_query.from_user.username,
                'first_name': event.callback_query.from_user.first_name,
            }

        # Get FSM context
        state: FSMContext = data.get('state')
        current_state_name = None

        if state:
            current_state = await state.get_state()
            if current_state:
                current_state_name = current_state

        # Execute handler first
        result = await handler(event, data)

        # Check for state change after handler
        if state and user_id:
            new_state = await state.get_state()
            new_state_name = new_state if new_state else None

            previous = self._previous_states.get(user_id)

            # State entered
            if new_state_name and new_state_name != previous:
                try:
                    await AnalyticsTracker.track_event(
                        telegram_id=user_id,
                        event_type='state_enter',
                        event_name=new_state_name,
                        username=user_info.get('username'),
                        first_name=user_info.get('first_name'),
                    )
                except Exception as e:
                    logger.error(f"State tracking failed: {e}")

            # State exited
            if previous and previous != new_state_name:
                try:
                    await AnalyticsTracker.track_event(
                        telegram_id=user_id,
                        event_type='state_exit',
                        event_name=previous,
                        username=user_info.get('username'),
                        first_name=user_info.get('first_name'),
                    )
                except Exception as e:
                    logger.error(f"State tracking failed: {e}")

            # Update previous state
            self._previous_states[user_id] = new_state_name

        return result


def setup_analytics_middleware(dp) -> None:
    """
    Setup analytics middleware on dispatcher.
    Call this in bot_main.py after creating dispatcher.
    """
    dp.update.outer_middleware(AnalyticsMiddleware())
    dp.update.outer_middleware(StateTrackingMiddleware())
    logger.info("Analytics middleware registered")
