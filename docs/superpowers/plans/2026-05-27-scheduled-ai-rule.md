# 定时 AI 规则 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增每日固定时间、仅交易日触发的定时 AI 规则，触发前刷新最新估值/净值并将完整分析结果通过现有消息渠道发送。

**Architecture:** 采用独立的定时 AI 规则模型与日志模型，不改造现有涨跌通知规则。后端复用现有 AI 模板、通知渠道和交易日工具，新增统一的 AI 分析服务与上下文构造服务供手动分析和定时任务共享。前端在系统设置页新增独立卡片管理这类规则。

**Tech Stack:** Django、DRF、Celery、React、Ant Design、Vitest、pytest。

---

### Task 1: 建立后端数据模型与迁移

**Files:**
- Modify: `backend/api/models.py`
- Create: `backend/api/migrations/0011_scheduled_airule_and_log.py`

- [ ] **Step 1: 写失败测试**

新增 `backend/tests/test_scheduled_ai_rule_models.py`，覆盖：

```python
def test_scheduled_ai_rule_requires_matching_template_type():
    ...

def test_position_rule_rejects_parent_account():
    ...

def test_rule_requires_target_and_channels():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/test_scheduled_ai_rule_models.py -v`
Expected: 因模型不存在或校验未实现而失败。

- [ ] **Step 3: 实现最小模型**

在 `backend/api/models.py` 新增：

```python
class ScheduledAIRule(models.Model):
    """定时 AI 规则"""

    TARGET_TYPE_CHOICES = [
        ('fund', '基金分析'),
        ('position', '持仓分析'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_ai_rules')
    name = models.CharField(max_length=100)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, null=True, blank=True, related_name='scheduled_ai_rules')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name='scheduled_ai_rules')
    template = models.ForeignKey(AIPromptTemplate, on_delete=models.PROTECT, related_name='scheduled_ai_rules')
    channels = models.ManyToManyField(NotificationChannel, related_name='scheduled_ai_rules')
    schedule_time = models.TimeField()
    trading_day_only = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
```

并新增：

```python
class ScheduledAIRuleLog(models.Model):
    """定时 AI 规则执行日志"""

    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
    ]
```

在 `clean()` 中实现：

```python
if self.target_type == 'fund' and not self.fund:
    raise ValidationError(...)
if self.target_type == 'position' and (not self.account or self.account.parent is None):
    raise ValidationError(...)
if self.template and self.template.context_type != self.target_type:
    raise ValidationError(...)
```

- [ ] **Step 4: 生成并应用迁移**

Run: `python backend/manage.py makemigrations api`
Run: `python backend/manage.py migrate`

- [ ] **Step 5: 回归测试**

Run: `pytest backend/tests/test_scheduled_ai_rule_models.py -v`
Expected: PASS

---

### Task 2: 抽离 AI 分析与上下文构造服务

**Files:**
- Create: `backend/api/services/ai_analysis.py`
- Create: `backend/api/services/ai_context.py`
- Modify: `backend/api/services/__init__.py`
- Modify: `backend/api/views.py`

- [ ] **Step 1: 写失败测试**

新增 `backend/tests/test_scheduled_ai_rule_services.py`，覆盖：

```python
def test_build_fund_context_includes_expected_keys():
    ...

def test_render_ai_prompt_replaces_placeholders():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/test_scheduled_ai_rule_services.py -v`
Expected: 服务未实现而失败。

- [ ] **Step 3: 实现上下文构造**

在 `backend/api/services/ai_context.py` 新增：

```python
def build_fund_context(user, fund) -> dict:
    """构造基金 AI 分析上下文。"""

def build_position_context(user, account) -> dict:
    """构造子账户 AI 分析上下文。"""
```

优先复用现有页面字段语义，字段名保持与模板占位符一致。

- [ ] **Step 4: 实现 AI 分析服务**

在 `backend/api/services/ai_analysis.py` 新增：

```python
def replace_placeholders(template: str, context_data: dict) -> str:
    """替换模板占位符。"""

def run_ai_analysis(request_user, template, context_data) -> str:
    """调用 OpenAI 协议接口并返回分析正文。"""
```

把 `backend/api/views.py` 里的 `ai_analyze` 改成调用该服务。

- [ ] **Step 5: 导出服务**

在 `backend/api/services/__init__.py` 中导出新服务函数，供任务层调用。

- [ ] **Step 6: 回归测试**

Run: `pytest backend/tests/test_scheduled_ai_rule_services.py -v`
Expected: PASS

---

### Task 3: 新增后端序列化器、视图集与路由

**Files:**
- Modify: `backend/api/serializers.py`
- Modify: `backend/api/viewsets.py`
- Modify: `backend/api/urls.py`
- Create: `backend/tests/test_scheduled_ai_rule_api.py`

- [ ] **Step 1: 写失败测试**

新增 API 测试，覆盖：

```python
def test_user_can_create_own_scheduled_ai_rule():
    ...

def test_cannot_bind_parent_account_to_position_rule():
    ...

def test_cannot_bind_foreign_channel():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/test_scheduled_ai_rule_api.py -v`
Expected: 路由或序列化器不存在而失败。

- [ ] **Step 3: 实现序列化器**

在 `backend/api/serializers.py` 新增：

```python
class ScheduledAIRuleSerializer(serializers.ModelSerializer):
    """定时 AI 规则序列化器"""
```

包含：

```python
fund_name = serializers.CharField(source='fund.fund_name', read_only=True)
fund_code = serializers.CharField(source='fund.fund_code', read_only=True)
account_name = serializers.CharField(source='account.name', read_only=True)
template_name = serializers.CharField(source='template.name', read_only=True)
channel_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
```

并在 `validate()` 中校验：

```python
if target_type == 'fund' and not fund:
    ...
if target_type == 'position' and (not account or account.parent is None):
    ...
if template.context_type != target_type:
    ...
```

- [ ] **Step 4: 实现 ViewSet**

在 `backend/api/viewsets.py` 新增：

```python
class ScheduledAIRuleViewSet(viewsets.ModelViewSet):
    """定时 AI 规则 ViewSet"""
```

`get_queryset()` 仅返回当前用户数据，`perform_create()` 自动绑定 `user`，并复用 `channel_ids` 设置 M2M。

- [ ] **Step 5: 暴露路由**

在 `backend/api/urls.py` 注册：

```python
router.register(r'scheduled-ai-rules', viewsets.ScheduledAIRuleViewSet, basename='scheduled-ai-rule')
```

- [ ] **Step 6: 回归测试**

Run: `pytest backend/tests/test_scheduled_ai_rule_api.py -v`
Expected: PASS

---

### Task 4: 实现定时扫描任务与发送日志

**Files:**
- Modify: `backend/api/tasks.py`
- Modify: `backend/fundval/settings.py`
- Create: `backend/tests/test_scheduled_ai_rule_tasks.py`

- [ ] **Step 1: 写失败测试**

新增任务测试，覆盖：

```python
def test_skip_non_trading_day():
    ...

def test_skip_when_already_sent_today():
    ...

def test_send_to_all_channels_after_refresh():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/test_scheduled_ai_rule_tasks.py -v`
Expected: 任务未实现而失败。

- [ ] **Step 3: 实现任务**

在 `backend/api/tasks.py` 新增：

```python
@shared_task
def check_scheduled_ai_rules():
    """扫描并执行定时 AI 规则。"""
```

任务内流程：

```python
1. 获取当前北京时间
2. 找出 schedule_time 匹配的规则
3. 非交易日直接跳过
4. 按 rule + run_date 幂等去重
5. 刷新基金或子账户数据
6. 构造上下文
7. 调用 AI 分析
8. 逐渠道发送
9. 写 ScheduledAIRuleLog
```

- [ ] **Step 4: 添加 Beat 调度**

在 `backend/fundval/settings.py` 的 `CELERY_BEAT_SCHEDULE` 中新增：

```python
'check-scheduled-ai-rules': {
    'task': 'api.tasks.check_scheduled_ai_rules',
    'schedule': crontab(minute='*'),
},
```

- [ ] **Step 5: 回归测试**

Run: `pytest backend/tests/test_scheduled_ai_rule_tasks.py -v`
Expected: PASS

---

### Task 5: 前端系统设置页新增定时 AI 规则卡片

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/pages/SettingsPage.jsx`
- Create: `frontend/src/test/SettingsPageScheduledAIRule.test.jsx`

- [ ] **Step 1: 写失败测试**

新增前端测试，覆盖：

```jsx
expect(screen.getByText('定时 AI 规则')).toBeInTheDocument();
```

以及创建表单时的关键字段渲染：

```jsx
expect(screen.getByLabelText('触发时间')).toBeInTheDocument();
expect(screen.getByLabelText('仅交易日触发')).toBeInTheDocument();
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm test -- SettingsPageScheduledAIRule`
Expected: 新卡片不存在导致失败。

- [ ] **Step 3: 扩展 API 封装**

在 `frontend/src/api/index.js` 新增：

```javascript
export const scheduledAIRulesAPI = {
  list: () => api.get('/scheduled-ai-rules/'),
  create: (data) => api.post('/scheduled-ai-rules/', data),
  update: (id, data) => api.patch(`/scheduled-ai-rules/${id}/`, data),
  delete: (id) => api.delete(`/scheduled-ai-rules/${id}/`),
};
```

- [ ] **Step 4: 增加页面卡片**

在 `frontend/src/pages/SettingsPage.jsx` 新增 `ScheduledAIRulesCard`，结构参考 `NotificationRulesCard`，但表单字段改为：

```jsx
name
target_type
fund/account
template
schedule_time
trading_day_only
channel_ids
is_active
```

基金和子账户选择器分别复用现有 `fundsAPI` 与 `useAccounts()` 数据。

- [ ] **Step 5: 挂载到设置页**

在 `SettingsPage` 主体中插入：

```jsx
<ScheduledAIRulesCard />
```

位置放在 `NotificationRulesCard` 后、系统设置卡片前。

- [ ] **Step 6: 回归测试**

Run: `npm test -- SettingsPageScheduledAIRule`
Expected: PASS

---

### Task 6: 调整手动 AI 分析入口以复用统一服务

**Files:**
- Modify: `backend/api/views.py`
- Modify: `frontend/src/components/AIAnalysisModal.jsx`（必要时只做文案或字段对齐）
- Modify: `frontend/src/pages/FundDetailPage.jsx`
- Modify: `frontend/src/pages/PositionsPage.jsx`

- [ ] **Step 1: 写失败测试**

为 `backend/tests/test_ai_api.py` 增补一个用例，验证 `ai_analyze` 仍可正常返回分析结果。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/test_ai_api.py -v`
Expected: 由于服务抽离未完成或引用变化而失败。

- [ ] **Step 3: 切换到统一服务**

让 `ai_analyze` 视图调用 `run_ai_analysis(...)`。

- [ ] **Step 4: 校验前端上下文字段不漂移**

确认：

```jsx
buildAiContextData()
```

与后端服务生成的字段含义一致，必要时仅微调字段名或补齐缺失字段，不改变页面交互。

- [ ] **Step 5: 回归测试**

Run: `pytest backend/tests/test_ai_api.py -v`
Expected: PASS

---

### Task 7: 完整验证与整理

**Files:**
- Modify: 必要时仅修正前述文件

- [ ] **Step 1: 后端全量相关测试**

Run:

```bash
pytest backend/tests/test_scheduled_ai_rule_models.py -v
pytest backend/tests/test_scheduled_ai_rule_api.py -v
pytest backend/tests/test_scheduled_ai_rule_services.py -v
pytest backend/tests/test_scheduled_ai_rule_tasks.py -v
pytest backend/tests/test_ai_api.py -v
```

Expected: 全部通过。

- [ ] **Step 2: 前端相关测试**

Run:

```bash
npm test -- SettingsPageScheduledAIRule
npm test -- SettingsPageMobile
```

Expected: 新旧设置页测试通过。

- [ ] **Step 3: 手工核对页面**

确认系统设置页里：

```text
AI 配置
提示词模板
通知渠道
通知规则
定时 AI 规则
系统设置
```

顺序正确，且新增表单字段能按分析类型切换。

- [ ] **Step 4: 提交代码**

```bash
git add backend frontend
git commit -m "feat: add scheduled AI notification rules"
```

---

### Coverage Check

- 定时 AI 规则独立建模 -> Task 1, 3
- 每天固定时间触发 -> Task 1, 4, 5
- 仅交易日触发 -> Task 4
- 触发前刷新最新估值/净值 -> Task 2, 4
- 单只基金/单个子账户 -> Task 1, 3, 5
- 仅发送完整结果到消息渠道 -> Task 4
- 不保存历史正文 -> Task 1, 4
- 复用现有模板和渠道 -> Task 1, 3, 4, 5
- 复用手动 AI 分析语义 -> Task 2, 6
