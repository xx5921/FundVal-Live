"""
测试定时 AI 规则服务
"""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from api.models import AIConfig, AIPromptTemplate, Account, Fund, FundNavHistory, Position, PositionOperation

User = get_user_model()


@pytest.mark.django_db
class TestAIContextService:
    """AI 上下文服务测试"""

    def setup_method(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_build_fund_context_includes_expected_keys(self):
        """基金上下文应包含模板依赖字段"""
        from api.services.ai_context import build_fund_context

        parent = Account.objects.create(user=self.user, name='父账户')
        child = Account.objects.create(user=self.user, name='子账户', parent=parent)
        fund = Fund.objects.create(
            fund_code='000001',
            fund_name='测试基金',
            fund_type='混合型',
            latest_nav='1.2300',
            latest_nav_date='2026-05-26',
            estimate_nav='1.2500',
            estimate_growth='1.63',
        )
        FundNavHistory.objects.create(
            fund=fund,
            nav_date='2026-05-25',
            unit_nav='1.2000',
        )
        Position.objects.create(
            account=child,
            fund=fund,
            holding_share='100.0000',
            holding_cost='120.00',
            holding_nav='1.2000',
        )
        PositionOperation.objects.create(
            account=child,
            fund=fund,
            operation_type='BUY',
            operation_date='2026-05-27',
            before_15=True,
            amount='120.00',
            share='100.0000',
            nav='1.2000',
        )

        context = build_fund_context(self.user, fund)

        assert context['fund_code'] == '000001'
        assert context['fund_name'] == '测试基金'
        assert 'nav_history' in context
        assert context['holding_share'] == '100.0000'
        assert 'operation_history' in context
        assert '子账户' in context['operation_history']
        assert '买入' in context['operation_history']

    def test_build_position_context_includes_expected_keys(self):
        """持仓上下文应包含模板依赖字段"""
        from api.services.ai_context import build_position_context

        parent = Account.objects.create(user=self.user, name='父账户')
        child = Account.objects.create(user=self.user, name='子账户', parent=parent)
        fund = Fund.objects.create(
            fund_code='000001',
            fund_name='测试基金',
            latest_nav='1.2300',
        )
        Position.objects.create(
            account=child,
            fund=fund,
            holding_share='100.0000',
            holding_cost='120.00',
            holding_nav='1.2000',
        )
        PositionOperation.objects.create(
            account=child,
            fund=fund,
            operation_type='BUY',
            operation_date='2026-05-27',
            before_15=True,
            amount='120.00',
            share='100.0000',
            nav='1.2000',
        )

        context = build_position_context(self.user, child)

        assert context['account_name'] == '子账户'
        assert 'positions' in context
        assert '000001|测试基金' in context['positions']
        assert 'operation_history' in context
        assert '子账户' in context['operation_history']
        assert '买入' in context['operation_history']


@pytest.mark.django_db
class TestAIAnalysisService:
    """AI 分析服务测试"""

    def setup_method(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.config = AIConfig.objects.create(
            user=self.user,
            api_endpoint='https://api.openai.com/v1',
            api_key='sk-test',
            model_name='gpt-4o-mini',
        )
        self.template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='系统：{{fund_code}}',
            user_prompt='用户：{{fund_name}}',
        )

    def test_replace_placeholders(self):
        """占位符应被替换"""
        from api.services.ai_analysis import replace_placeholders

        result = replace_placeholders('基金 {{fund_code}} - {{fund_name}}', {
            'fund_code': '000001',
            'fund_name': '测试基金',
        })

        assert result == '基金 000001 - 测试基金'

    def test_run_ai_analysis_returns_message_content(self):
        """AI 分析服务应返回消息内容"""
        from api.services.ai_analysis import run_ai_analysis

        with patch('api.services.ai_analysis.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': '分析结果'}}],
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = run_ai_analysis(
                user=self.user,
                template=self.template,
                context_data={'fund_code': '000001', 'fund_name': '测试基金'},
            )

        assert result == '分析结果'
