"""
持仓重算服务
"""
from decimal import Decimal
from typing import Optional

from django.db import transaction

from ..models import Position, PositionOperation


def recalculate_position(account_id, fund_id) -> Optional[Position]:
    """
    重新计算持仓汇总

    Args:
        account_id: 账户 ID
        fund_id: 基金 ID

    Returns:
        Position: 更新后的持仓对象，清仓时返回 None
    """
    from ..models import Account, Fund

    account = Account.objects.get(id=account_id)
    fund = Fund.objects.get(id=fund_id)

    operations = PositionOperation.objects.filter(
        account_id=account_id,
        fund_id=fund_id,
    ).order_by('operation_date', 'created_at')

    total_share = Decimal('0')
    total_cost = Decimal('0')

    for op in operations:
        if op.operation_type == 'BUY':
            total_share += op.share
            total_cost += op.amount
        elif op.operation_type == 'SELL' and total_share > 0:
            sell_share = min(op.share, total_share)
            cost_per_share = total_cost / total_share
            total_share -= sell_share
            total_cost -= sell_share * cost_per_share
            total_cost = total_cost.quantize(Decimal('0.01'))

    if total_share > 0:
        holding_nav = (total_cost / total_share).quantize(Decimal('0.0001'))
    else:
        holding_nav = Decimal('0')

    with transaction.atomic():
        if total_share > 0:
            position, _ = Position.objects.update_or_create(
                account=account,
                fund=fund,
                defaults={
                    'holding_share': total_share,
                    'holding_cost': total_cost,
                    'holding_nav': holding_nav,
                },
            )
            return position

        Position.objects.filter(account=account, fund=fund).delete()
        return None


def recalculate_all_positions(account_id: Optional[str] = None):
    """
    重算所有持仓

    Args:
        account_id: 可选，只重算指定账户的持仓
    """
    if account_id:
        operations = PositionOperation.objects.filter(account_id=account_id)
    else:
        operations = PositionOperation.objects.all()

    account_fund_pairs = operations.values_list('account_id', 'fund_id').distinct()

    for current_account_id, current_fund_id in account_fund_pairs:
        recalculate_position(current_account_id, current_fund_id)
