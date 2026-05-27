"""
Celery 任务

定义所有后台异步任务
"""
from datetime import timedelta

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

from api.notifications import ChannelRegistry
from api.services import build_fund_context, build_position_context, run_ai_analysis
from api.sources import SourceRegistry
from api.utils.trading_calendar import is_trading_day

logger = logging.getLogger(__name__)


@shared_task
def update_fund_nav():
    """
    定时更新基金净值（昨日净值）
    
    默认从数据源获取最新可用的历史净值并同步到基金主表。
    """
    try:
        call_command('update_nav')
        logger.info('基金昨日/最新净值同步完成')
        return '净值同步完成'
    except Exception as e:
        logger.error(f'基金净值自动更新失败: {str(e)}')
        raise


@shared_task
def update_fund_today_nav():
    """
    定时更新基金当日确认净值
    
    每天晚间执行，尝试从确权接口抓取今日净值。
    """
    try:
        call_command('update_nav', '--today')
        logger.info('基金今日净值确权完成')
        return '当日净值更新完成'
    except Exception as e:
        logger.error(f'基金当日净值确权失败: {str(e)}')
        raise


@shared_task
def capture_estimate_snapshot():
    """
    捕捉 15:00 收盘估值快照
    
    每个交易日 15:05 执行，将收盘估值锁定，用于晚间与真实净值对比计算误差。
    """
    from api.models import Fund, EstimateAccuracy
    from api.utils.trading_calendar import is_trading_day
    from django.utils import timezone

    today = timezone.localdate()
    if not is_trading_day(today):
        logger.info(f'{today} 不是交易日，跳过估值捕捉')
        return '非交易日'

    funds = Fund.objects.exclude(estimate_nav__isnull=True)
    count = 0
    for fund in funds:
        # 只捕捉当天的预估
        if fund.estimate_time and fund.estimate_time.date() == today:
            EstimateAccuracy.objects.update_or_create(
                source_name='eastmoney',
                fund=fund,
                estimate_date=today,
                defaults={
                    'estimate_nav': fund.estimate_nav
                }
            )
            count += 1

    logger.info(f'已捕捉 {count} 个基金的收盘估值快照')
    return f'捕捉完成：{count}'


@shared_task
def check_notification_rules():
    """
    检查通知规则并发送通知

    每 5 分钟执行一次，检查所有激活的通知规则，
    判断是否触发条件，发送通知并记录日志。
    """
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    from api.models import NotificationRule, NotificationLog
    from api.notifications import ChannelRegistry

    rules = NotificationRule.objects.filter(is_active=True).select_related(
        'fund', 'user'
    ).prefetch_related('channels')

    triggered = 0
    sent = 0

    for rule in rules:
        fund = rule.fund
        if fund.estimate_growth is None:
            continue

        growth = Decimal(str(fund.estimate_growth))

        # 判断是否触发
        triggered_flag = False
        if rule.rule_type == 'growth_up' and growth >= rule.threshold:
            triggered_flag = True
        elif rule.rule_type == 'growth_down' and growth <= -rule.threshold:
            triggered_flag = True

        if not triggered_flag:
            continue

        triggered += 1

        # 检查冷却时间
        cooldown_cutoff = timezone.now() - timedelta(minutes=rule.cooldown_minutes)
        recent_log = NotificationLog.objects.filter(
            rule=rule,
            trigger_time__gte=cooldown_cutoff,
            status='success',
        ).exists()

        if recent_log:
            logger.debug(f'规则 {rule.id} 在冷却期内，跳过')
            continue

        # 构建通知内容
        direction = '涨幅' if rule.rule_type == 'growth_up' else '跌幅'
        title = f'基金{direction}提醒：{fund.fund_name}'
        content = (
            f'{fund.fund_name}（{fund.fund_code}）当前{direction} {abs(growth):.2f}%，'
            f'已超过您设定的阈值 {rule.threshold}%。'
        )

        # 逐渠道发送
        for channel_obj in rule.channels.filter(is_active=True):
            channel_impl = ChannelRegistry.get_channel(channel_obj.channel_type)
            if not channel_impl:
                logger.warning(f'未找到渠道实现：{channel_obj.channel_type}')
                continue

            success = False
            error_msg = None
            try:
                success = channel_impl.send(title, content, channel_obj.config)
            except Exception as e:
                error_msg = str(e)
                logger.error(f'发送通知异常：rule={rule.id}, channel={channel_obj.id}, 错误：{e}')

            NotificationLog.objects.create(
                rule=rule,
                channel=channel_obj,
                fund_code=fund.fund_code,
                fund_name=fund.fund_name,
                growth=growth,
                status='success' if success else 'failed',
                error_message=error_msg,
            )

            if success:
                sent += 1

    logger.info(f'通知检查完成：触发 {triggered} 条规则，发送 {sent} 条通知')
    return f'触发 {triggered} 条，发送 {sent} 条'


@shared_task
def audit_accuracy():
    """
    审计估值准确率

    每个交易晚间执行，计算所有捕捉到的快照与最终净值的误差。
    """
    from api.utils.trading_calendar import is_trading_day
    from django.utils import timezone

    today = timezone.localdate()
    if not is_trading_day(today):
        logger.info(f'{today} 不是交易日，跳过准确率审计')
        return '非交易日'

    try:
        call_command('calculate_accuracy', date=today.isoformat())
        logger.info(f'{today} 准确率审计完成')
        return '审计完成'
    except Exception as e:
        logger.error(f'准确率审计失败: {str(e)}')
        raise


def _refresh_fund_data(fund, source_name='eastmoney'):
    """刷新基金估值和净值。"""
    source = SourceRegistry.get_source(source_name)
    if not source:
        raise ValueError(f'数据源 {source_name} 不存在')

    estimate_data = source.fetch_estimate(fund.fund_code)
    nav_data = source.fetch_realtime_nav(fund.fund_code)

    if not estimate_data or not nav_data:
        raise ValueError(f'刷新基金 {fund.fund_code} 数据失败')

    fund.estimate_nav = estimate_data.get('estimate_nav')
    fund.estimate_growth = estimate_data.get('estimate_growth')
    fund.estimate_time = estimate_data.get('estimate_time') or timezone.now()
    fund.latest_nav = nav_data.get('nav')
    fund.latest_nav_date = nav_data.get('nav_date')
    fund.save(update_fields=[
        'estimate_nav', 'estimate_growth', 'estimate_time',
        'latest_nav', 'latest_nav_date', 'updated_at',
    ])

    return fund


def _refresh_position_account_data(account, source_name='eastmoney'):
    """刷新子账户下所有持仓基金的数据。"""
    positions = account.positions.select_related('fund').all()
    if not positions.exists():
        raise ValueError('持仓账户无持仓，无法执行定时 AI 分析')

    for position in positions:
        _refresh_fund_data(position.fund, source_name=source_name)


def _build_rule_context(rule):
    """按规则构造 AI 分析上下文。"""
    if rule.target_type == 'fund':
        return build_fund_context(rule.user, rule.fund)
    return build_position_context(rule.user, rule.account)


def _build_rule_message(rule, content):
    """构造通知标题和正文。"""
    if rule.target_type == 'fund':
        target_name = f'{rule.fund.fund_name}（{rule.fund.fund_code}）'
        title = f'定时 AI 分析：{rule.template.name} - {rule.fund.fund_name}'
    else:
        target_name = rule.account.name
        title = f'定时 AI 分析：{rule.template.name} - {rule.account.name}'

    body = (
        f'规则名称：{rule.name}\n'
        f'触发时间：{timezone.localtime().strftime("%Y-%m-%d %H:%M")}\n'
        f'分析对象：{target_name}\n\n'
        f'{content}'
    )
    return title, body, target_name


@shared_task
def check_scheduled_ai_rules():
    """
    检查定时 AI 规则并发送通知

    每分钟执行一次，筛选到达触发时间且满足交易日条件的规则。
    """
    from api.models import ScheduledAIRule, ScheduledAIRuleLog

    now = timezone.localtime()
    today = now.date()

    rules = ScheduledAIRule.objects.filter(
        is_active=True,
        schedule_time__hour=now.hour,
        schedule_time__minute=now.minute,
    ).select_related('fund', 'account', 'template', 'user').prefetch_related('channels')

    if not rules.exists():
        return '触发 0 条，发送 0 条'

    triggered = 0
    sent = 0

    for rule in rules:
        if rule.trading_day_only and not is_trading_day(today):
            logger.info(f'{today} 不是交易日，跳过定时 AI 规则 {rule.id}')
            continue

        if ScheduledAIRuleLog.objects.filter(rule=rule, run_date=today, status='success').exists():
            logger.info(f'规则 {rule.id} 今日已成功执行，跳过')
            continue

        triggered += 1
        error_message = None

        try:
            if rule.target_type == 'fund':
                _refresh_fund_data(rule.fund)
            else:
                _refresh_position_account_data(rule.account)

            context_data = _build_rule_context(rule)
            analysis_result = run_ai_analysis(rule.user, rule.template, context_data)
            title, body, target_name = _build_rule_message(rule, analysis_result)

            for channel_obj in rule.channels.filter(is_active=True):
                channel_impl = ChannelRegistry.get_channel(channel_obj.channel_type)
                if not channel_impl:
                    logger.warning(f'未找到渠道实现：{channel_obj.channel_type}')
                    continue

                success = False
                channel_error = None
                try:
                    success = channel_impl.send(title, body, channel_obj.config)
                except Exception as error:
                    channel_error = str(error)
                    logger.error(f'发送定时 AI 通知异常：rule={rule.id}, channel={channel_obj.id}, 错误：{error}')

                ScheduledAIRuleLog.objects.create(
                    rule=rule,
                    channel=channel_obj,
                    run_date=today,
                    analysis_target_name=target_name,
                    status='success' if success else 'failed',
                    error_message=channel_error,
                )

                if success:
                    sent += 1

            rule.last_triggered_at = timezone.now()
            rule.save(update_fields=['last_triggered_at', 'updated_at'])

        except Exception as error:
            error_message = str(error)
            logger.error(f'执行定时 AI 规则失败：rule={rule.id}, 错误：{error}')
            for channel_obj in rule.channels.filter(is_active=True):
                ScheduledAIRuleLog.objects.create(
                    rule=rule,
                    channel=channel_obj,
                    run_date=today,
                    analysis_target_name=rule.fund.fund_name if rule.target_type == 'fund' else rule.account.name,
                    status='failed',
                    error_message=error_message,
                )

    logger.info(f'定时 AI 规则检查完成：触发 {triggered} 条规则，发送 {sent} 条通知')
    if rules and rules[0].trading_day_only and not is_trading_day(today):
        return '非交易日，跳过执行'
    return f'触发 {triggered} 条，发送 {sent} 条'
