import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Typography, 
  Input, 
  InputNumber, 
  Button, 
  Row, 
  Col, 
  Table, 
  Alert, 
  Spin, 
  notification,
  Divider,
  Tag,
  Slider,
  Tabs,
  Badge
} from 'antd'
import { CalculatorOutlined, CheckOutlined, UserOutlined, BarChartOutlined } from '@ant-design/icons'
import Plot from 'react-plotly.js'
import { prometheeAPI } from '../services/api'
import DepotManagerSurvey from './DepotManagerSurvey'

const { Title, Text } = Typography

const PROMETHEEIIScoringInterface = ({ prometheeResults, setPrometheeResults, setCurrentPhase }) => {
  const [numCriteria, setNumCriteria] = useState(3)
  const [numSuppliers, setNumSuppliers] = useState(3)
  const [criteriaNames, setCriteriaNames] = useState([])
  const [criteriaWeights, setCriteriaWeights] = useState([])
  const [supplierNames, setSupplierNames] = useState([])
  const [supplierScores, setSupplierScores] = useState({})
  const [loading, setLoading] = useState(false)
  const [evaluationSummary, setEvaluationSummary] = useState(null)
  const [activeTab, setActiveTab] = useState('survey')

  // Load AHP configuration from localStorage on component mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('ahpConfig')
    if (savedConfig) {
      const config = JSON.parse(savedConfig)
      setNumCriteria(config.numCriteria || 3)
      setNumSuppliers(config.supplierNames?.length || 0)
      if (config.criteriaNames) {
        setCriteriaNames(config.criteriaNames)
      }
      if (config.criteriaWeights) {
        setCriteriaWeights(config.criteriaWeights)
      }
      if (config.supplierNames) {
        setSupplierNames(config.supplierNames)
      }
    }
  }, [])

  useEffect(() => {
    // Reset supplier data when count changes
    setSupplierScores({})
    fetchEvaluationSummary()
  }, [numSuppliers])
  
  const fetchEvaluationSummary = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/depot-evaluations/summary')
      const data = await response.json()
      setEvaluationSummary(data.summary)
    } catch (error) {
      console.error('Error fetching evaluation summary:', error)
    }
  }
  
  const fetchPrometheeResults = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/promethee/results')
      const data = await response.json()
      setPrometheeResults(data.results)
    } catch (error) {
      console.error('Error fetching PROMETHEE results:', error)
    }
  }

  useEffect(() => {
    // Only reset criteria if they're not already loaded from config
    const savedConfig = localStorage.getItem('ahpConfig')
    if (!savedConfig || !JSON.parse(savedConfig).criteriaNames) {
      setCriteriaNames(Array(numCriteria).fill('').map((_, i) => `Criteria ${i + 1}`))
      setCriteriaWeights(Array(numCriteria).fill(1.0))
    }
  }, [numCriteria])

  // Listen for configuration changes from admin panel
  useEffect(() => {
    let updateTimeout
    
    const handleStorageChange = (e) => {
      console.log('Storage change detected in PROMETHEEIIScoringInterface:', e)
      if (e.key === 'ahpConfig' && e.newValue) {
        // Clear any existing timeout to debounce multiple rapid changes
        if (updateTimeout) {
          clearTimeout(updateTimeout)
        }
        
        // Use setTimeout to defer state updates and debounce rapid changes
        updateTimeout = setTimeout(() => {
          const config = JSON.parse(e.newValue)
          console.log('Updating PROMETHEE II config from storage:', config)
          setNumCriteria(config.numCriteria || 3)
          setNumSuppliers(config.supplierNames?.length || 0)
          if (config.criteriaNames) {
            setCriteriaNames(config.criteriaNames)
          }
          if (config.criteriaWeights) {
            setCriteriaWeights(config.criteriaWeights)
          }
          if (config.supplierNames) {
            setSupplierNames(config.supplierNames)
          }
          // Reset supplier scores when config changes
          setSupplierScores({})
          fetchEvaluationSummary()
          updateTimeout = null
        }, 100) // 100ms debounce
      }
    }
    
    // Add listener for custom storage events (for same-window updates)
    window.addEventListener('storage', handleStorageChange)
    
    // Also check for updates on visibility change (when switching tabs)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        const savedConfig = localStorage.getItem('ahpConfig')
        if (savedConfig) {
          const config = JSON.parse(savedConfig)
          // Only update if config actually changed
          if (JSON.stringify(config) !== JSON.stringify({
            numCriteria,
            numSuppliers,
            criteriaNames,
            criteriaWeights,
            supplierNames
          })) {
            console.log('Updating PROMETHEE II config on visibility change:', config)
            setNumCriteria(config.numCriteria || 3)
            setNumSuppliers(config.supplierNames?.length || 0)
            if (config.criteriaNames) {
              setCriteriaNames(config.criteriaNames)
            }
            if (config.criteriaWeights) {
              setCriteriaWeights(config.criteriaWeights)
            }
            if (config.supplierNames) {
              setSupplierNames(config.supplierNames)
            }
          }
        }
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      if (updateTimeout) {
        clearTimeout(updateTimeout)
      }
      window.removeEventListener('storage', handleStorageChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [numCriteria, numSuppliers, criteriaNames, criteriaWeights, supplierNames])

  const handleCriteriaNameChange = (index, value) => {
    const newNames = [...criteriaNames]
    newNames[index] = value || `Criteria ${index + 1}`
    setCriteriaNames(newNames)
  }

  const handleCriteriaWeightChange = (index, value) => {
    const newWeights = [...criteriaWeights]
    newWeights[index] = value || 1.0
    setCriteriaWeights(newWeights)
  }


  const handleScoreChange = (supplierIndex, criteriaIndex, score) => {
    const key = `${supplierIndex}-${criteriaIndex}`
    
    setSupplierScores(prev => ({
      ...prev,
      [key]: score
    }))
  }

  const calculatePrometheeScores = async () => {
    setLoading(true)
    
    try {
      // Normalize weights
      const weightSum = criteriaWeights.reduce((sum, w) => sum + w, 0)
      const normalizedWeights = criteriaWeights.map(w => w / weightSum)
      
      const requestData = {
        criteria_names: criteriaNames,
        criteria_weights: normalizedWeights
      }
      
      const response = await fetch('http://localhost:8000/api/promethee/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      })
      
      const data = await response.json()
      
      if (response.ok) {
        setPrometheeResults(data.results)
        
        notification.success({
          message: 'PROMETHEE II Calculation Complete',
          description: 'Supplier ranking completed successfully! You can now proceed to the Supply Chain Optimization tab.'
        })
        
        setActiveTab('results')
      } else {
        throw new Error(data.detail || 'Failed to calculate PROMETHEE scores')
      }
    } catch (error) {
      console.error('Error calculating PROMETHEE scores:', error)
      notification.error({
        message: 'Calculation Error',
        description: 'Failed to calculate PROMETHEE scores. Please ensure you have depot evaluations submitted.'
      })
    } finally {
      setLoading(false)
    }
  }

  const renderResults = () => {
    if (!prometheeResults) return null

    const isPromethee = prometheeResults

    if (isPromethee && prometheeResults) {
      // PROMETHEE II Results
      const resultsData = prometheeResults.suppliers.map((supplierId, index) => ({
        key: index,
        supplier: prometheeResults.supplier_names[index],
        supplier_id: supplierId,
        net_flow: prometheeResults.net_flows[index].toFixed(3),
        positive_flow: prometheeResults.positive_flows[index].toFixed(3),
        negative_flow: prometheeResults.negative_flows[index].toFixed(3),
        ranking: prometheeResults.ranking.indexOf(index) + 1,
        evaluations: prometheeResults.evaluation_counts ? 
          (prometheeResults.evaluation_counts[supplierId] || 0) : 0
      }))

      const sortedResults = [...resultsData].sort((a, b) => a.ranking - b.ranking)

      const resultsColumns = [
        {
          title: 'Rank',
          dataIndex: 'ranking',
          key: 'ranking',
          width: 70,
          render: (rank) => <Tag color="blue">#{rank}</Tag>
        },
        {
          title: 'Supplier',
          dataIndex: 'supplier',
          key: 'supplier',
        },
        {
          title: 'Net Flow',
          dataIndex: 'net_flow',
          key: 'net_flow',
          sorter: (a, b) => parseFloat(a.net_flow) - parseFloat(b.net_flow),
          render: (value) => <Text strong>{value}</Text>
        },
        {
          title: 'Positive Flow',
          dataIndex: 'positive_flow',
          key: 'positive_flow',
          render: (value) => <Text style={{ color: '#52c41a' }}>{value}</Text>
        },
        {
          title: 'Negative Flow',
          dataIndex: 'negative_flow',
          key: 'negative_flow',
          render: (value) => <Text style={{ color: '#ff4d4f' }}>{value}</Text>
        },
        {
          title: 'Evaluations',
          dataIndex: 'evaluations',
          key: 'evaluations',
          render: (evaluations) => <span>{evaluations}</span>
        }
      ]

      const weightsData = criteriaNames.map((criteria, index) => ({
        key: index,
        criteria,
        weight: (criteriaWeights[index] * 100).toFixed(1) + '%'
      }))

      const weightsColumns = [
        {
          title: 'Criteria',
          dataIndex: 'criteria',
          key: 'criteria',
        },
        {
          title: 'Weight',
          dataIndex: 'weight',
          key: 'weight',
        }
      ]

      // Create bar chart data for net flows
      const barData = [{
        x: sortedResults.map(r => r.supplier),
        y: sortedResults.map(r => parseFloat(r.net_flow)),
        type: 'bar',
        marker: {
          color: sortedResults.map(r => r.ranking === 1 ? '#52c41a' : '#1890ff')
        }
      }]

      const barLayout = {
        title: 'PROMETHEE II Net Flows',
        xaxis: { title: 'Supplier' },
        yaxis: { title: 'Net Flow' },
        height: 400
      }

      // Create pie chart data
      const pieData = [{
        values: criteriaWeights,
        labels: criteriaNames,
        type: 'pie',
        hole: 0.4
      }]

      const pieLayout = {
        title: 'Criteria Weight Distribution',
        height: 400
      }

      return (
        <div>
          <Title level={4}>📊 Results: PROMETHEE II Supplier Ranking</Title>
          
          <Alert
            message="PROMETHEE II Ranking Methodology"
            description="Suppliers are ranked by Net Flow (Positive Flow - Negative Flow). Higher net flow indicates better overall performance. Evaluations show the number of depot manager submissions for each supplier."
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
          
          <Table 
            dataSource={sortedResults} 
            columns={resultsColumns} 
            pagination={false}
            style={{ marginBottom: 24 }}
          />

          <Title level={4}>📋 Criteria Weights Summary</Title>
          <Table 
            dataSource={weightsData} 
            columns={weightsColumns} 
            pagination={false}
            style={{ marginBottom: 24 }}
          />

          <Row gutter={24}>
            <Col span={12}>
              <Card title="📊 PROMETHEE II Net Flows">
                <Plot
                  data={barData}
                  layout={barLayout}
                  style={{ width: '100%', height: '400px' }}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="🎯 Criteria Weights Distribution">
                <Plot
                  data={pieData}
                  layout={pieLayout}
                  style={{ width: '100%', height: '400px' }}
                />
              </Card>
            </Col>
          </Row>

          <Alert
            message="PROMETHEE II ranking completed! You can now proceed to the Supply Chain Optimization tab."
            type="success"
            showIcon
            icon={<CheckOutlined />}
            style={{ marginTop: 24 }}
          />
        </div>
      )
    }

    return null
  }

  return (
    <div>
      <Title level={2}>🧮 PROMETHEE II Supplier Scoring</Title>
      <Text style={{ fontStyle: 'italic' }}>
        Evaluate suppliers using PROMETHEE II methodology with depot manager evaluations
      </Text>


      <Alert
        style={{ marginTop: 24 }}
        message="Configuration Managed Centrally"
        description="Criteria names and weights are now configured in Admin Management → AHP Configuration tab. Use this interface to enter supplier information and calculate scores."
        type="info"
        showIcon
      />

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>Current Configuration</Title>
        <Row gutter={16}>
          <Col span={12}>
            <Text strong>Criteria: </Text>
            {criteriaNames.map((name, index) => (
              <Tag key={index} style={{ margin: '2px' }}>{name}</Tag>
            ))}
          </Col>
          <Col span={12}>
            <Text strong>Weights: </Text>
            {criteriaWeights.map((weight, index) => (
              <Tag key={index} color="blue" style={{ margin: '2px' }}>{criteriaNames[index]}: {weight}</Tag>
            ))}
          </Col>
        </Row>
      </Card>

      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab} 
        style={{ marginTop: 24 }}
        items={[
          {
            key: 'survey',
            label: (
              <span>
                <UserOutlined />
                Depot Manager Survey
                {evaluationSummary && (
                  <Badge 
                    count={evaluationSummary.total_evaluations} 
                    style={{ backgroundColor: '#1890ff', marginLeft: 8 }}
                  />
                )}
              </span>
            ),
            children: <DepotManagerSurvey onSurveyComplete={fetchEvaluationSummary} />
          },
          {
            key: 'summary',
            label: (
              <span>
                <BarChartOutlined />
                Evaluation Summary
              </span>
            ),
            children: (
              <Card title="Evaluation Summary">
                {evaluationSummary ? (
                  <div>
                    <Row gutter={16} style={{ marginBottom: 24 }}>
                      <Col span={8}>
                        <Card size="small">
                          <div style={{ textAlign: 'center' }}>
                            <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
                              {evaluationSummary.total_evaluations}
                            </Title>
                            <Text type="secondary">Total Evaluations</Text>
                          </div>
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card size="small">
                          <div style={{ textAlign: 'center' }}>
                            <Title level={2} style={{ margin: 0, color: '#52c41a' }}>
                              {evaluationSummary.supplier_evaluations?.length || 0}
                            </Title>
                            <Text type="secondary">Suppliers Evaluated</Text>
                          </div>
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card size="small">
                          <div style={{ textAlign: 'center' }}>
                            <Title level={2} style={{ margin: 0, color: '#fa8c16' }}>
                              {evaluationSummary.depot_evaluations?.length || 0}
                            </Title>
                            <Text type="secondary">Depots Participated</Text>
                          </div>
                        </Card>
                      </Col>
                    </Row>
                    
                    <Row gutter={16}>
                      <Col span={12}>
                        <Card title="Evaluations by Supplier" size="small">
                          <Table
                            dataSource={evaluationSummary.supplier_evaluations || []}
                            columns={[
                              { title: 'Supplier', dataIndex: 'supplier', key: 'supplier' },
                              { title: 'Evaluations', dataIndex: 'count', key: 'count' }
                            ]}
                            rowKey="supplier"
                            pagination={false}
                            size="small"
                          />
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card title="Evaluations by Depot" size="small">
                          <Table
                            dataSource={evaluationSummary.depot_evaluations || []}
                            columns={[
                              { title: 'Depot', dataIndex: 'depot', key: 'depot' },
                              { title: 'Evaluations', dataIndex: 'count', key: 'count' }
                            ]}
                            rowKey="depot"
                            pagination={false}
                            size="small"
                          />
                        </Card>
                      </Col>
                    </Row>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <Spin size="large" />
                    <div style={{ marginTop: 16 }}>
                      <Text>Loading evaluation summary...</Text>
                    </div>
                  </div>
                )}
              </Card>
            )
          },
          {
            key: 'results',
            label: (
              <span>
                <CalculatorOutlined />
                PROMETHEE II Results
              </span>
            ),
            children: (
              <Card title="PROMETHEE II Supplier Ranking">
                <div style={{ marginBottom: 24 }}>
                  <Button
                    type="primary"
                    icon={<CalculatorOutlined />}
                    onClick={calculatePrometheeScores}
                    loading={loading}
                    size="large"
                  >
                    🔍 Calculate PROMETHEE II Ranking
                  </Button>
                  <Button
                    style={{ marginLeft: 8 }}
                    onClick={fetchPrometheeResults}
                  >
                    Refresh Results
                  </Button>
                </div>
                
                {renderResults()}
              </Card>
            )
          }
        ]}
      />
    </div>
  )
}

export default PROMETHEEIIScoringInterface