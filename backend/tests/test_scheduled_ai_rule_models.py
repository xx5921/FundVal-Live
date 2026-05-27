"""
测试定时 AI 规则模型
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from api.models import AIPromptTemplate, Account, Fund, NotificationChannel

User = get_user_model()


@pytest.mark.django_db
class TestScheduledAIRuleModel:
    """定时 AI 规则模型测试"""

    def setup_method(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_scheduled_ai_rule_requires_matching_template_type(self):
        """模板类型必须与规则类型一致"""
        from api.models import ScheduledAIRule

        fund = Fund.objects.create(fund_code='000001', fund_name='测试基金')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='持仓模板',
            context_type='position',
            system_prompt='sys',
            user_prompt='user',
        )

        rule = ScheduledAIRule(
            user=self.user,
            name='定时规则',
            target_type='fund',
            fund=fund,
            template=template,
            schedule_time='14:30',
        )

        with pytest.raises(ValidationError):
            rule.full_clean()

    def test_position_rule_rejects_parent_account(self):
        """持仓规则不能绑定父账户"""
        from api.models import ScheduledAIRule

        parent = Account.objects.create(user=self.user, name='父账户')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='持仓模板',
            context_type='position',
            system_prompt='sys',
            user_prompt='user',
        )

        rule = ScheduledAIRule(
            user=self.user,
            name='定时规则',
            target_type='position',
            account=parent,
            template=template,
            schedule_time='14:30',
        )

        with pytest.raises(ValidationError):
            rule.full_clean()

    def test_rule_requires_target_and_channels(self):
        """规则必须绑定分析对象和渠道"""
        from api.models import ScheduledAIRule

        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )

        rule = ScheduledAIRule(
            user=self.user,
            name='定时规则',
            target_type='fund',
            template=template,
            schedule_time='14:30',
        )

        with pytest.raises(ValidationError):
            rule.full_clean()


@pytest.mark.django_db
class TestScheduledAIRuleLogModel:
    """定时 AI 规则日志测试"""

    def setup_method(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_create_log(self):
        """可创建执行日志"""
        from api.models import ScheduledAIRule, ScheduledAIRuleLog

        fund = Fund.objects.create(fund_code='000001', fund_name='测试基金')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )
        channel = NotificationChannel.objects.create(
            user=self.user,
            channel_type='webhook',
            config={'webhook_url': 'https://example.com/hook'},
        )
        rule = ScheduledAIRule.objects.create(
            user=self.user,
            name='定时规则',
            target_type='fund',
            fund=fund,
            template=template,
            schedule_time='14:30',
        )
        rule.channels.add(channel)

        log = ScheduledAIRuleLog.objects.create(
            rule=rule,
            channel=channel,
            run_date='2026-05-27',
            analysis_target_name='测试基金',
            status='success',
        )

        assert log.status == 'success'
