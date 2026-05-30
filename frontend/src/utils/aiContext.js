/**
 * 将持仓操作记录格式化为 AI 提示词可直接使用的多行文本。
 *
 * Args:
 *   operations: 原始持仓操作记录数组。
 *   limit: 需要保留的最新记录数量，默认 30。
 *
 * Returns:
 *   按时间倒序排列的操作记录文本。
 */
const formatOperationHistory = (operations = [], limit = 30) => {
  if (!Array.isArray(operations) || operations.length === 0) {
    return '';
  }

  const operationTypeMap = {
    BUY: '买入',
    SELL: '卖出',
  };

  const getTimestamp = (value) => {
    const timestamp = Date.parse(value || '');
    return Number.isNaN(timestamp) ? 0 : timestamp;
  };

  return [...operations]
    .filter(Boolean)
    .sort((a, b) => {
      const dateDiff = getTimestamp(b.operation_date || b.date) - getTimestamp(a.operation_date || a.date);
      if (dateDiff !== 0) {
        return dateDiff;
      }
      return getTimestamp(b.created_at || b.createdAt) - getTimestamp(a.created_at || a.createdAt);
    })
    .slice(0, limit)
    .map((operation) => [
      operation.operation_date || operation.date || '',
      operation.account_name || operation.account?.name || '',
      operation.fund_code || operation.fund?.fund_code || '',
      operation.fund_name || operation.fund?.fund_name || '',
      operationTypeMap[operation.operation_type] || operation.operation_type || '',
      operation.amount ?? '',
      operation.share ?? '',
      operation.nav ?? '',
    ].join('|'))
    .join('\n');
};

export default formatOperationHistory;
