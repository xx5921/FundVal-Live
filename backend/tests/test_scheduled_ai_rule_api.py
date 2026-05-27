"""
测试定时 AI 规则 API
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from api.models import AIPromptTemplate, Account, Fund, NotificationChannel

User = get_user_model()


@pytest.mark.django_db
class TestScheduledAIRuleAPI:
    """定时 AI 规则 API 测试"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def _create_child_account(self):
        parent = Account.objects.create(user=self.user, name='父账户')
        return Account.objects.create(user=self.user, name='子账户', parent=parent)

    def _create_channel(self):
        return NotificationChannel.objects.create(
            user=self.user,
            channel_type='webhook',
            config={'webhook_url': 'https://example.com/hook'},
        )

    def test_user_can_create_own_scheduled_ai_rule(self):
        """用户可以创建自己的定时 AI 规则"""
        fund = Fund.objects.create(fund_code='000001', fund_name='测试基金')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )
        channel = self._create_channel()

        response = self.client.post('/api/scheduled-ai-rules/', {
            'name': '下午基金分析',
            'target_type': 'fund',
            'fund': str(fund.id),
            'template': template.id,
            'schedule_time': '14:30:00',
            'trading_day_only': True,
            'channel_ids': [str(channel.id)],
            'is_active': True,
        }, format='json')

        assert response.status_code == 201
        assert response.data['name'] == '下午基金分析'
        assert response.data['fund_code'] == '000001'

    def test_cannot_bind_parent_account_to_position_rule(self):
        """持仓规则不能绑定父账户"""
        parent = Account.objects.create(user=self.user, name='父账户')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='持仓模板',
            context_type='position',
            system_prompt='sys',
            user_prompt='user',
        )
        channel = self._create_channel()

        response = self.client.post('/api/scheduled-ai-rules/', {
            'name': '持仓健康度',
            'target_type': 'position',
            'account': str(parent.id),
            'template': template.id,
            'schedule_time': '14:30:00',
            'channel_ids': [str(channel.id)],
        }, format='json')

        assert response.status_code == 400

    def test_cannot_bind_foreign_channel(self):
        """不能绑定其他用户的渠道"""
        other_user = User.objects.create_user(username='other', password='pass')
        fund = Fund.objects.create(fund_code='000001', fund_name='测试基金')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )
        other_channel = NotificationChannel.objects.create(
            user=other_user,
            channel_type='webhook',
            config={'webhook_url': 'https://example.com/hook'},
        )

        response = self.client.post('/api/scheduled-ai-rules/', {
            'name': '下午基金分析',
            'target_type': 'fund',
            'fund': str(fund.id),
            'template': template.id,
            'schedule_time': '14:30:00',
            'channel_ids': [str(other_channel.id)],
        }, format='json')

        assert response.status_code == 400

    def test_list_only_own_rules(self):
        """列表只返回当前用户规则"""
        from api.models import ScheduledAIRule

        fund = Fund.objects.create(fund_code='000001', fund_name='测试基金')
        template = AIPromptTemplate.objects.create(
            user=self.user,
            name='基金模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )
        rule = ScheduledAIRule.objects.create(
            user=self.user,
            name='下午基金分析',
            target_type='fund',
            fund=fund,
            template=template,
            schedule_time='14:30:00',
        )
        rule.channels.add(self._create_channel())

        other_user = User.objects.create_user(username='other', password='pass')
        other_fund = Fund.objects.create(fund_code='000002', fund_name='其他基金')
        other_template = AIPromptTemplate.objects.create(
            user=other_user,
            name='其他模板',
            context_type='fund',
            system_prompt='sys',
            user_prompt='user',
        )
        other_channel = NotificationChannel.objects.create(
            user=other_user,
            channel_type='webhook',
            config={'webhook_url': 'https://example.com/other'},
        )
        other_rule = ScheduledAIRule.objects.create(
            user=other_user,
            name='其他规则',
            target_type='fund',
            fund=other_fund,
            template=other_template,
            schedule_time='15:00:00',
        )
        other_rule.channels.add(other_channel)

        response = self.client.get('/api/scheduled-ai-rules/')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['name'] == '下午基金分析'
