import { Layout, Space, Typography } from 'antd';
import { GithubOutlined } from '@ant-design/icons';

const { Footer: AntFooter } = Layout;
const { Link, Text } = Typography;
const REPOSITORY_URL = 'https://github.com/xx5921/FundVal-Live';

const Footer = () => {
  return (
    <AntFooter
      style={{
        textAlign: 'center',
        padding: '16px 24px',
        background: '#fafafa',
        borderTop: '1px solid #f0f0f0',
      }}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          © 2024-2026 Fundval. Licensed under{' '}
          <Link
            href={`${REPOSITORY_URL}/blob/main/LICENSE`}
            target="_blank"
            rel="noopener noreferrer"
          >
            AGPL-3.0
          </Link>
          .
        </Text>
        <Space size="middle">
          <Link
            href={REPOSITORY_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Space>
              <GithubOutlined style={{ fontSize: 16 }} />
              <span>GitHub</span>
            </Space>
          </Link>
          <Link
            href={`${REPOSITORY_URL}/stargazers`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>⭐ Star</span>
          </Link>
        </Space>
      </Space>
    </AntFooter>
  );
};

export default Footer;
