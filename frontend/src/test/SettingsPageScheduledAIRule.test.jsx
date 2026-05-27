import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';

import SettingsPage from '../pages/SettingsPage';
import * as api from '../api';

vi.mock('../api', () => ({
  sourceAPI: {
    getStatus: vi.fn(),
    getQRCode: vi.fn(),
    logout: vi.fn(),
  },
  aiAPI: {
    getConfig: vi.fn(),
    updateConfig: vi.fn(),
    listTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
  fundsAPI: {
    search: vi.fn(),
  },
  accountsAPI: {
    list: vi.fn(),
  },
  notificationChannelsAPI: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    test: vi.fn(),
  },
  notificationRulesAPI: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  scheduledAIRulesAPI: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../contexts/PreferenceContext', () => ({
  usePreference: () => ({ preferredSource: 'eastmoney', updatePreference: vi.fn() }),
}));

vi.mock('../App', () => ({
  isNativeApp: () => false,
}));

let mockScreens = { md: true };
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    Grid: { useBreakpoint: () => mockScreens },
  };
});

describe('SettingsPage 定时 AI 规则', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockScreens = { md: true };
    api.notificationChannelsAPI.list.mockResolvedValue({
      data: [{ id: 'channel-1', channel_type: 'webhook', config: { webhook_url: 'https://example.com/hook' }, is_active: true }],
    });
    api.notificationRulesAPI.list.mockResolvedValue({ data: [] });
    api.scheduledAIRulesAPI.list.mockResolvedValue({ data: [] });
    api.aiAPI.getConfig.mockResolvedValue({ data: { api_key: '', model_name: '' } });
    api.aiAPI.listTemplates.mockResolvedValue({
      data: [{ id: 1, name: '基金趋势分析', context_type: 'fund', is_default: true }],
    });
    api.accountsAPI.list.mockResolvedValue({
      data: [
        { id: 'parent-1', name: '父账户', parent: null },
        { id: 'child-1', name: '子账户', parent: 'parent-1' },
      ],
    });
    api.sourceAPI.getStatus.mockResolvedValue({ data: { logged_in: false } });
  });

  it('显示定时 AI 规则卡片', async () => {
    render(<BrowserRouter><SettingsPage /></BrowserRouter>);

    await waitFor(() => {
      expect(screen.getByText('定时 AI 规则')).toBeInTheDocument();
    });
  });

  it('打开创建弹窗后显示关键字段', async () => {
    const user = userEvent.setup();

    render(<BrowserRouter><SettingsPage /></BrowserRouter>);

    await waitFor(() => {
      expect(screen.getByText('定时 AI 规则')).toBeInTheDocument();
    });

    const addButtons = screen.getAllByRole('button', { name: /添加规则/ });
    await user.click(addButtons[addButtons.length - 1]);

    await waitFor(() => {
      expect(screen.getByText('添加定时规则')).toBeInTheDocument();
    });

    expect(screen.getAllByLabelText('触发时间').length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText('仅交易日触发').length).toBeGreaterThan(0);
  });
});
