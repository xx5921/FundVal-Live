"""
测试定时 AI 规则任务
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models import AIPromptTemplate, Account, Fund, NotificationChannel, ScheduledAIRule, ScheduledAIRuleLog

User = get_user_model()


@pytest.mark.django_db
class TestScheduledAIRuleTasks:
    """定时 AI 规则任务测试"""

    def setup_method(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys {{fund_code}}',
            user_prompt='user {{fund_name}}',
        )
        self.fund = Fund.objects.create(
            fund_code='000001',
            fund_name='测试基金',
            latest_nav='1.2000',
            latest_nav_date='2026-05-26',
            estimate_nav='1.2300',
            estimate_growth='1.50',
        )
        self.channel = NotificationChannel.objects.create(
            user=self.user,
            channel_type='webhook',
            config={'webhook_url': 'https://example.com/hook'},
        )

    def _create_rule(self, **kwargs):
        rule = ScheduledAIRule.objects.create(
            user=self.user,
            name='下午基金分析',
            target_type='fund',
            fund=self.fund,
            template=self.template,
            schedule_time='14:30:00',
            **kwargs,
        )
        rule.channels.add(self.channel)
        return rule

    def test_skip_non_trading_day(self):
        """非交易日跳过"""
        rule = self._create_rule()

        with patch('api.tasks.is_trading_day', return_value=False), \
             patch('api.tasks.timezone.localtime', return_value=datetime(2026, 5, 27, 14, 30)), \
             patch('api.tasks.run_ai_analysis') as mock_ai, \
             patch('api.tasks.ChannelRegistry.get_channel') as mock_get_channel:
            from api.tasks import check_scheduled_ai_rules
            result = check_scheduled_ai_rules()

        assert '非交易日' in result
        assert not mock_ai.called
        assert not mock_get_channel.called

    def test_skip_when_already_sent_today(self):
        """当天已成功发送则跳过"""
        rule = self._create_rule()
        ScheduledAIRuleLog.objects.create(
            rule=rule,
            channel=self.channel,
            run_date=timezone.localdate(),
            analysis_target_name='测试基金',
            status='success',
        )

        with patch('api.tasks.is_trading_day', return_value=True), \
             patch('api.tasks.run_ai_analysis') as mock_ai:
            from api.tasks import check_scheduled_ai_rules
            result = check_scheduled_ai_rules()

        assert '跳过' in result or '0' in result
        assert not mock_ai.called

    def test_send_to_all_channels_after_refresh(self):
        """刷新后发送到所有渠道"""
        second_channel = NotificationChannel.objects.create(
            user=self.user,
            channel_type='email',
            config={
                'smtp_host': 'smtp.example.com',
                'smtp_port': 465,
                'smtp_ssl': True,
                'username': 'test@example.com',
                'password': 'secret',
                'to_email': 'to@example.com',
            },
        )
        rule = self._create_rule()
        rule.channels.add(second_channel)

        mock_channel_impl = MagicMock()
        mock_channel_impl.send.return_value = True

        with patch('api.tasks.is_trading_day', return_value=True), \
             patch('api.tasks.timezone.localtime', return_value=datetime(2026, 5, 27, 14, 30)), \
             patch('api.tasks.run_ai_analysis', return_value='分析结果') as mock_ai, \
             patch('api.tasks.ChannelRegistry.get_channel', return_value=mock_channel_impl), \
             patch('api.tasks.SourceRegistry.get_source') as mock_source:
            mock_source_instance = MagicMock()
            mock_source.return_value = mock_source_instance
            mock_source_instance.fetch_estimate.return_value = {
                'estimate_nav': '1.2300',
                'estimate_growth': '1.50',
                'estimate_time': timezone.make_aware(datetime(2026, 5, 27, 14, 30)),
            }
            mock_source_instance.fetch_realtime_nav.return_value = {
                'nav': '1.2000',
                'nav_date': timezone.localdate(),
            }

            from api.tasks import check_scheduled_ai_rules
            result = check_scheduled_ai_rules()

        assert '发送' in result
        assert mock_ai.called
        assert mock_channel_impl.send.call_count == 2
