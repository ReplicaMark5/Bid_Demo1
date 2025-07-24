import React, { useState } from 'react'
import { Layout, Typography, Tabs, Alert } from 'antd'
import { CalculatorOutlined, UserOutlined, SettingOutlined, FormOutlined } from '@ant-design/icons'
import PROMETHEEIIScoringInterface from './components/PROMETHEEIIScoringInterface'
import OptimizationInterface from './components/OptimizationInterface'
import SupplierDataInterface from './components/SupplierDataInterface'
import AdminSupplierManagement from './components/AdminSupplierManagement'
import DepotManagerSurvey from './components/DepotManagerSurvey'
import './App.css'

const { Header, Content } = Layout
const { Title, Text } = Typography

function App() {
  const [currentPhase, setCurrentPhase] = useState('promethee_scoring')
  const [prometheeResults, setPrometheeResults] = useState(null)

  const tabItems = [
    {
      key: 'supplier_data',
      label: (
        <span>
          <UserOutlined />
          Supplier Data Submission
        </span>
      ),
      children: <SupplierDataInterface />
    },
    {
      key: 'admin_management',
      label: (
        <span>
          <SettingOutlined />
          Admin Management
        </span>
      ),
      children: <AdminSupplierManagement />
    },
    {
      key: 'depot_manager_survey',
      label: (
        <span>
          <FormOutlined />
          Survey
        </span>
      ),
      children: <DepotManagerSurvey />
    },
    {
      key: 'promethee_scoring',
      label: (
        <span>
          <CalculatorOutlined />
          PROMETHEE II Supplier Scoring
        </span>
      ),
      children: (
        <PROMETHEEIIScoringInterface 
          prometheeResults={prometheeResults}
          setPrometheeResults={setPrometheeResults}
          setCurrentPhase={setCurrentPhase}
        />
      )
    },
    {
      key: 'optimization',
      label: (
        <span>
          🏭 Supply Chain Optimization
        </span>
      ),
      children: (
        <OptimizationInterface 
          prometheeResults={prometheeResults}
        />
      )
    }
  ]

  const handleTabChange = (key) => {
    setCurrentPhase(key)
  }

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <Header style={{ backgroundColor: '#fff', padding: '0 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          🏭 <Title level={3} style={{ margin: 0, color: '#1890ff', marginLeft: '16px' }}>
            Integrated AHP & Supply Chain Optimizer
          </Title>
        </div>
      </Header>

      <Content style={{ padding: '24px' }}>
        <div className="phase-indicator">
          <Text style={{ fontStyle: 'italic' }}>
            Seamlessly evaluate suppliers and optimize supply chains
          </Text>
        </div>

        <div className="phase-indicator">
          {currentPhase === 'ahp_scoring' ? (
            <Alert 
              message="📊 Phase 1: AHP Supplier Scoring" 
              type="success" 
              showIcon 
              style={{ marginBottom: '24px' }}
            />
          ) : (
            <Alert 
              message="🚀 Phase 2: Supply Chain Optimization" 
              type="success" 
              showIcon 
              style={{ marginBottom: '24px' }}
            />
          )}
        </div>

        <Tabs
          activeKey={currentPhase}
          onChange={handleTabChange}
          items={tabItems}
          size="large"
          style={{ backgroundColor: '#fff', borderRadius: '8px', padding: '16px' }}
        />
      </Content>
    </Layout>
  )
}

export default App