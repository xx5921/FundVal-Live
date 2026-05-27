"""
AI 分析上下文构造服务
"""
from datetime import date, datetime
from decimal import Decimal


def _format_decimal(value):
    """将 Decimal / 数字安全转为字符串。"""
    if value is None:
        return ''
    return str(value)


def _format_percent(value):
    """将收益率安全转为百分比字符串。"""
    if value is None:
        return ''
    numeric_value = Decimal(str(value))
    return f'{numeric_value * 100:.2f}'


def _to_decimal(value):
    """将值安全转为 Decimal。"""
    if value is None or value == '':
        return Decimal('0')
    return Decimal(str(value))


def _calculate_percent(value, base):
    """根据数值和基数计算百分比字符串。"""
    base_decimal = _to_decimal(base)
    if base_decimal == 0:
        return ''
    return _format_percent(_to_decimal(value) / base_decimal)


def _format_date(value):
    """将日期安全转为字符串。"""
    if value is None:
        return ''
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def build_fund_context(user, fund):
    """构造基金 AI 分析上下文。"""
    from api.models import Position

    position = Position.objects.filter(account__user=user, fund=fund).select_related('account').first()
    nav_history = fund.nav_history.all()[:30]

    return {
        'fund_code': fund.fund_code,
        'fund_name': fund.fund_name,
        'fund_type': fund.fund_type or '',
        'latest_nav': _format_decimal(fund.latest_nav),
        'latest_nav_date': _format_date(fund.latest_nav_date),
        'estimate_nav': _format_decimal(fund.estimate_nav),
        'estimate_growth': _format_decimal(fund.estimate_growth),
        'nav_history': ','.join(f'{item.nav_date}:{item.unit_nav}' for item in reversed(nav_history)),
        'holding_share': _format_decimal(position.holding_share) if position else '',
        'holding_cost': _format_decimal(position.holding_cost) if position else '',
        'holding_value': _format_decimal(_to_decimal(position.holding_share) * _to_decimal(fund.latest_nav)) if position else '',
        'pnl': _format_decimal(position.pnl) if position else '',
        'pnl_rate': _calculate_percent(position.pnl, position.holding_cost) if position else '',
    }


def build_position_context(user, account):
    """构造子账户 AI 分析上下文。"""
    positions = account.positions.select_related('fund').all()
    positions_text = '\n'.join(
        f'{pos.fund.fund_code}|{pos.fund.fund_name}|{pos.holding_share}|{pos.holding_cost}|'
        f'{_format_decimal(_to_decimal(pos.holding_share) * _to_decimal(pos.fund.latest_nav)) if pos.fund.latest_nav else ""}|{_format_decimal(pos.pnl)}'
        for pos in positions
    )

    return {
        'account_name': account.name,
        'holding_cost': _format_decimal(account.holding_cost),
        'holding_value': _format_decimal(account.holding_value),
        'pnl': _format_decimal(account.pnl),
        'pnl_rate': _format_percent(account.pnl_rate),
        'positions': positions_text,
    }
