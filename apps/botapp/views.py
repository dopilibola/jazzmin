"""
Admin views for botapp - Advanced Analytics Dashboard.
Complete analytics system with charts, funnels, and user tracking.
"""
import json
import asyncio
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse

# Import analytics functions
from bot.services.analytics_tracker import (
    get_total_users,
    get_new_users_today,
    get_active_users,
    get_button_stats,
    get_session_stats,
    get_hourly_activity,
    get_daily_activity,
    get_drop_off_points,
    get_most_active_users,
    get_retention_rate,
    get_category_stats,
    get_funnel_stats,
    get_time_spent_by_step,
    get_all_users_with_journey,
    get_user_journey_details,
    get_drop_off_users,
    AnalyticsTracker,
)

# Also import legacy analytics for backward compatibility
from bot.database.analytics import (
    get_events_since,
    get_unique_users,
    count_events_by_type,
    count_users_by_event,
    calculate_funnel,
    get_daily_users,
    get_hourly_activity as get_hourly_activity_legacy,
    REGISTRATION_FUNNEL,
    GRAVE_FUNNEL,
    ORDER_FUNNEL,
)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Create a new loop in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


@staff_member_required
def analytics_view(request):
    """Main analytics dashboard view."""
    period = request.GET.get('period', '24h')

    if period == '7d':
        hours = 168
        days = 7
        period_label = "7 kun"
    elif period == '30d':
        hours = 720
        days = 30
        period_label = "30 kun"
    else:
        hours = 24
        days = 1
        period_label = "24 soat"

    # Fetch all analytics data
    try:
        # User metrics
        total_users = run_async(get_total_users())
        new_users_today = run_async(get_new_users_today())
        dau = run_async(get_active_users(24))
        wau = run_async(get_active_users(168))

        # Session metrics
        session_stats = run_async(get_session_stats(hours))

        # Button stats
        button_stats = run_async(get_button_stats(20))

        # Activity data
        hourly_activity = run_async(get_hourly_activity(hours))
        daily_activity = run_async(get_daily_activity(days if days > 1 else 7))

        # Drop-off points
        drop_off_points = run_async(get_drop_off_points(hours))

        # Most active users
        most_active_users = run_async(get_most_active_users(10))

        # Retention rate
        retention_rate = run_async(get_retention_rate(7))

        # Category stats
        category_stats = run_async(get_category_stats(hours))

        # Funnel stats
        funnel_stats = run_async(get_funnel_stats(hours))

        # Time spent by step
        time_by_step = run_async(get_time_spent_by_step(hours))

    except Exception as e:
        # Fallback to legacy analytics if new system fails
        events = get_events_since(hours)
        total_users = len(get_unique_users(events))
        new_users_today = 0
        dau = total_users
        wau = total_users
        session_stats = {'total_sessions': 0, 'avg_duration': 0, 'avg_events_per_session': 0}
        button_stats = []
        hourly_activity = get_hourly_activity_legacy(events)
        daily_activity = [{'date': d['date'], 'users': d['users'], 'events': 0} for d in get_daily_users(events, days)]
        drop_off_points = []
        most_active_users = []
        retention_rate = 0
        category_stats = {}
        funnel_stats = {}
        time_by_step = []

    # Calculate additional metrics
    avg_session_duration_min = round(session_stats.get('avg_duration', 0) / 60, 1)
    peak_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else 0

    # Prepare chart data
    daily_chart_data = json.dumps({
        'labels': [d['date'][5:] if isinstance(d['date'], str) else d['date'].strftime('%m-%d') for d in daily_activity],
        'users': [d['users'] for d in daily_activity],
        'events': [d.get('events', 0) for d in daily_activity],
    })

    hourly_chart_data = json.dumps({
        'labels': [f"{h}:00" for h in range(24)],
        'data': [hourly_activity.get(h, 0) for h in range(24)],
    })

    category_chart_data = json.dumps({
        'labels': list(category_stats.keys()) if category_stats else ['No data'],
        'data': list(category_stats.values()) if category_stats else [0],
    })

    # Funnel chart data
    funnel_chart_data = json.dumps({
        'labels': list(funnel_stats.keys()) if funnel_stats else [],
        'data': list(funnel_stats.values()) if funnel_stats else [],
    })

    # Calculate conversion rates
    conversions = {
        'registration': 0,
        'grave': 0,
        'payment': 0,
    }
    if funnel_stats:
        start = funnel_stats.get('start', 0)
        if start > 0:
            conversions['registration'] = round(funnel_stats.get('registration', 0) / start * 100, 1)
            conversions['grave'] = round(funnel_stats.get('grave_completed', 0) / start * 100, 1)
            conversions['payment'] = round(funnel_stats.get('payment_completed', 0) / start * 100, 1)

    context = {
        'title': 'Bot Analitikasi',
        'period': period,
        'period_label': period_label,

        # Main metrics
        'total_users': total_users,
        'new_users_today': new_users_today,
        'dau': dau,
        'wau': wau,
        'retention_rate': retention_rate,

        # Session metrics
        'total_sessions': session_stats.get('total_sessions', 0),
        'avg_session_duration': avg_session_duration_min,
        'avg_events_per_session': session_stats.get('avg_events_per_session', 0),
        'peak_hour': f"{peak_hour}:00",

        # Conversion rates
        'conversions': conversions,

        # Button stats
        'button_stats': button_stats[:15],

        # Drop-off points
        'drop_off_points': drop_off_points,

        # Most active users
        'most_active_users': most_active_users,

        # Time spent by step
        'time_by_step': time_by_step[:10],

        # Chart data
        'daily_chart_data': daily_chart_data,
        'hourly_chart_data': hourly_chart_data,
        'category_chart_data': category_chart_data,
        'funnel_chart_data': funnel_chart_data,

        # Funnel stats
        'funnel_stats': funnel_stats,
    }

    return render(request, 'admin/botapp/analytics.html', context)


@staff_member_required
def analytics_api(request):
    """API endpoint for real-time analytics data."""
    period = request.GET.get('period', '24h')

    if period == '7d':
        hours = 168
    elif period == '30d':
        hours = 720
    else:
        hours = 24

    try:
        data = {
            'total_users': run_async(get_total_users()),
            'dau': run_async(get_active_users(24)),
            'wau': run_async(get_active_users(168)),
            'new_users': run_async(get_new_users_today()),
            'session_stats': run_async(get_session_stats(hours)),
            'retention_rate': run_async(get_retention_rate(7)),
            'timestamp': datetime.now().isoformat(),
        }
    except Exception as e:
        data = {'error': str(e)}

    return JsonResponse(data)


@staff_member_required
def user_journey_view(request, telegram_id):
    """View detailed user journey."""
    from bot.database.analytics import get_user_journey

    try:
        journey = run_async(get_user_journey(telegram_id))
    except Exception:
        journey = "Ma'lumot topilmadi"

    return render(request, 'admin/botapp/user_journey.html', {
        'title': f'User Journey: {telegram_id}',
        'telegram_id': telegram_id,
        'journey': journey,
    })


@staff_member_required
def users_tracking_view(request):
    """User tracking page - shows all users with their journey status."""
    from apps.botapp.models import TelegramUser

    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = 30
    offset = (page - 1) * per_page

    # Get users with journey data
    try:
        users_data, total_count = run_async(get_all_users_with_journey(
            search=search if search else None,
            limit=per_page,
            offset=offset,
        ))
    except Exception as e:
        users_data = []
        total_count = 0

    # Enrich with phone numbers from Django model
    for user in users_data:
        try:
            tg_user = TelegramUser.objects.filter(chat_id=user['telegram_id']).first()
            if tg_user:
                user['phone_number'] = tg_user.phone_number or ''
                user['full_name'] = tg_user.full_name or user['first_name'] or ''
            else:
                user['phone_number'] = ''
                user['full_name'] = user['first_name'] or ''
        except Exception:
            user['phone_number'] = ''
            user['full_name'] = user['first_name'] or ''

    # Pagination
    total_pages = (total_count + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1

    context = {
        'title': 'Foydalanuvchilar - Yo\'nalish Analizi',
        'users': users_data,
        'search': search,
        'total_count': total_count,
        'page': page,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'page_range': range(max(1, page - 2), min(total_pages + 1, page + 3)),
    }

    return render(request, 'admin/botapp/users_tracking.html', context)


@staff_member_required
def user_detail_view(request, telegram_id):
    """Detailed view of a single user's journey."""
    from apps.botapp.models import TelegramUser

    try:
        user_data = run_async(get_user_journey_details(telegram_id))
    except Exception as e:
        user_data = None

    if not user_data:
        return render(request, 'admin/botapp/user_detail.html', {
            'title': 'Foydalanuvchi topilmadi',
            'user': None,
            'telegram_id': telegram_id,
        })

    # Get phone number from Django model
    try:
        tg_user = TelegramUser.objects.filter(chat_id=telegram_id).first()
        if tg_user:
            user_data['phone_number'] = tg_user.phone_number or ''
            user_data['full_name'] = tg_user.full_name or user_data.get('first_name', '')
            user_data['language'] = tg_user.language
        else:
            user_data['phone_number'] = ''
            user_data['full_name'] = user_data.get('first_name', '')
            user_data['language'] = ''
    except Exception:
        user_data['phone_number'] = ''
        user_data['full_name'] = user_data.get('first_name', '')
        user_data['language'] = ''

    context = {
        'title': f"Foydalanuvchi: {user_data['full_name'] or user_data['telegram_id']}",
        'user': user_data,
    }

    return render(request, 'admin/botapp/user_detail.html', context)
