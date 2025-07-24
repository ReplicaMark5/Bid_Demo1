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
  Badge,
  Select
} from 'antd'
import { CalculatorOutlined, CheckOutlined, UserOutlined, BarChartOutlined } from '@ant-design/icons'
import Plot from 'react-plotly.js'
import { prometheeAPI } from '../services/api'

const { Title, Text } = Typography
const { Option } = Select

// Preference function types for PROMETHEE II
const PREFERENCE_FUNCTION_TYPES = [
  { value: 'usual', label: 'Usual (Type I)', description: 'No threshold, strict preference' },
  { value: 'u_shape', label: 'U-Shape (Type II)', description: 'Indifference threshold only' },
  { value: 'v_shape', label: 'V-Shape (Type III)', description: 'Preference threshold only' },
  { value: 'level', label: 'Level (Type IV)', description: 'Both thresholds, plateau' },
  { value: 'linear', label: 'Linear (Type V)', description: 'Linear interpolation between thresholds' },
  { value: 'gaussian', label: 'Gaussian (Type VI)', description: 'Normal distribution curve' }
]

const PROMETHEEIIScoringInterface = ({ prometheeResults, setPrometheeResults, setCurrentPhase }) => {
  const [numCriteria, setNumCriteria] = useState(3)
  const [numSuppliers, setNumSuppliers] = useState(3)
  const [criteriaNames, setCriteriaNames] = useState([])
  const [criteriaWeights, setCriteriaWeights] = useState([])
  const [supplierNames, setSupplierNames] = useState([])
  const [supplierScores, setSupplierScores] = useState({})
  const [loading, setLoading] = useState(false)
  const [evaluationSummary, setEvaluationSummary] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')
  const [preferenceFunctions, setPreferenceFunctions] = useState({})
  const [preferenceThresholds, setPreferenceThresholds] = useState({})
  const [indifferenceThresholds, setIndifferenceThresholds] = useState({})

  // Load BWM configuration from backend on component mount, fallback to localStorage
  useEffect(() => {
    const loadBWMConfiguration = async () => {
      try {
        // First try to get from backend
        const response = await fetch('http://localhost:8000/api/bwm/weights/')
        const data = await response.json()
        
        if (response.ok && data.success && data.data) {
          const backendData = data.data
          setNumCriteria(backendData.criteria_names.length)
          setCriteriaNames(backendData.criteria_names)
          
          // Convert weights object to array in the same order as criteria names
          const weightsArray = backendData.criteria_names.map(name => backendData.weights[name])
          setCriteriaWeights(weightsArray)
          
          // Still need supplier names from localStorage since they're not stored with BWM weights
          const savedConfig = localStorage.getItem('bwmConfig')
          if (savedConfig) {
            const config = JSON.parse(savedConfig)
            if (config.supplierNames) {
              setSupplierNames(config.supplierNames)
              setNumSuppliers(config.supplierNames.length)
            }
          }
        } else {
          // Fallback to localStorage if no backend data
          const savedConfig = localStorage.getItem('bwmConfig')
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
        }
      } catch (error) {
        console.error('Error loading BWM configuration from backend:', error)
        // Fallback to localStorage on error
        const savedConfig = localStorage.getItem('bwmConfig')
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
      }
    }
    
    loadBWMConfiguration()
  }, [])

  useEffect(() => {
    // Reset supplier data when count changes
    setSupplierScores({})
    fetchEvaluationSummary()
  }, [numSuppliers])
  
  const fetchEvaluationSummary = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/supplier-evaluations/summary')
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
    const savedConfig = localStorage.getItem('bwmConfig')
    if (!savedConfig || !JSON.parse(savedConfig).criteriaNames) {
      setCriteriaNames(Array(numCriteria).fill('').map((_, i) => `Criteria ${i + 1}`))
      setCriteriaWeights(Array(numCriteria).fill(1.0))
    }
  }, [numCriteria])

  // Listen for configuration changes from admin panel
  useEffect(() => {
    let updateTimeout
    
    const handleStorageChange = async (e) => {
      console.log('Storage change detected in PROMETHEEIIScoringInterface:', e)
      if (e.key === 'bwmConfig' && e.newValue) {
        // Clear any existing timeout to debounce multiple rapid changes
        if (updateTimeout) {
          clearTimeout(updateTimeout)
        }
        
        // Use setTimeout to defer state updates and debounce rapid changes
        updateTimeout = setTimeout(async () => {
          try {
            // Load from backend first (weights should now be saved there)
            const response = await fetch('http://localhost:8000/api/bwm/weights/')
            const data = await response.json()
            
            if (response.ok && data.success && data.data) {
              const backendData = data.data
              console.log('Updating PROMETHEE II config from backend:', backendData)
              setNumCriteria(backendData.criteria_names.length)
              setCriteriaNames(backendData.criteria_names)
              const weightsArray = backendData.criteria_names.map(name => backendData.weights[name])
              setCriteriaWeights(weightsArray)
            }
            
            // Still get supplier names from localStorage
            const config = JSON.parse(e.newValue)
            if (config.supplierNames) {
              setSupplierNames(config.supplierNames)
              setNumSuppliers(config.supplierNames.length)
            }
            
            // Reset supplier scores when config changes
            setSupplierScores({})
            fetchEvaluationSummary()
          } catch (error) {
            console.error('Error loading BWM config on storage change:', error)
            // Fallback to localStorage
            const config = JSON.parse(e.newValue)
            console.log('Updating PROMETHEE II config from storage (fallback):', config)
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
            setSupplierScores({})
            fetchEvaluationSummary()
          }
          updateTimeout = null
        }, 100) // 100ms debounce
      }
    }
    
    // Add listener for custom storage events (for same-window updates)
    window.addEventListener('storage', handleStorageChange)
    
    // Also check for updates on visibility change (when switching tabs)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        const savedConfig = localStorage.getItem('bwmConfig')
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

  // Initialize preference functions when criteria change
  useEffect(() => {
    if (criteriaNames.length > 0) {
      const newPreferenceFunctions = {}
      const newPreferenceThresholds = {}
      const newIndifferenceThresholds = {}
      
      criteriaNames.forEach(name => {
        if (!preferenceFunctions[name]) {
          newPreferenceFunctions[name] = 'linear' // Default to linear
        } else {
          newPreferenceFunctions[name] = preferenceFunctions[name]
        }
        
        if (!preferenceThresholds[name]) {
          newPreferenceThresholds[name] = 2.0 // Default preference threshold
        } else {
          newPreferenceThresholds[name] = preferenceThresholds[name]
        }
        
        if (!indifferenceThresholds[name]) {
          newIndifferenceThresholds[name] = 0.5 // Default indifference threshold
        } else {
          newIndifferenceThresholds[name] = indifferenceThresholds[name]
        }
      })
      
      setPreferenceFunctions(newPreferenceFunctions)
      setPreferenceThresholds(newPreferenceThresholds)
      setIndifferenceThresholds(newIndifferenceThresholds)
    }
  }, [criteriaNames])

  const handlePreferenceFunctionChange = (criterionName, functionType) => {
    setPreferenceFunctions(prev => ({
      ...prev,
      [criterionName]: functionType
    }))
  }

  const handlePreferenceThresholdChange = (criterionName, value) => {
    setPreferenceThresholds(prev => ({
      ...prev,
      [criterionName]: value || 0
    }))
  }

  const handleIndifferenceThresholdChange = (criterionName, value) => {
    setIndifferenceThresholds(prev => ({
      ...prev,
      [criterionName]: value || 0
    }))
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
      // Fetch latest BWM weights from backend
      const bwmResponse = await fetch('http://localhost:8000/api/bwm/weights/')
      const bwmData = await bwmResponse.json()
      
      let finalCriteriaNames = criteriaNames
      let finalWeights = criteriaWeights
      
      if (bwmResponse.ok && bwmData.success && bwmData.data) {
        // Use weights from backend database
        const backendData = bwmData.data
        finalCriteriaNames = backendData.criteria_names
        finalWeights = backendData.criteria_names.map(name => backendData.weights[name])
        
        console.log('Using BWM weights from backend:', backendData.weights)
      } else {
        console.log('Using local weights (backend not available):', criteriaWeights)
      }
      
      // Normalize weights
      const weightSum = finalWeights.reduce((sum, w) => sum + w, 0)
      const normalizedWeights = finalWeights.map(w => w / weightSum)
      
      const requestData = {
        criteria_names: finalCriteriaNames,
        criteria_weights: normalizedWeights,
        preference_functions: finalCriteriaNames.reduce((acc, name) => {
          acc[name] = preferenceFunctions[name] || 'linear'
          return acc
        }, {}),
        preference_thresholds: finalCriteriaNames.reduce((acc, name) => {
          acc[name] = preferenceThresholds[name] || 2.0
          return acc
        }, {}),
        indifference_thresholds: finalCriteriaNames.reduce((acc, name) => {
          acc[name] = indifferenceThresholds[name] || 0.5
          return acc
        }, {})
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
        // Add the weights info that was actually used to the results
        const resultsWithWeights = {
          ...data.results,
          used_criteria_names: finalCriteriaNames,
          used_weights: finalWeights,
          weights_source: bwmResponse.ok && bwmData.success && bwmData.data ? 'backend' : 'local'
        }
        setPrometheeResults(resultsWithWeights)
        
        notification.success({
          message: 'PROMETHEE II Calculation Complete',
          description: `Supplier ranking completed successfully using ${resultsWithWeights.weights_source} weights! You can now proceed to the Supply Chain Optimization tab.`
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

      // Use the weights that were actually used in the calculation
      const actualCriteriaNames = prometheeResults.used_criteria_names || criteriaNames
      const actualWeights = prometheeResults.used_weights || criteriaWeights
      
      const weightsData = actualCriteriaNames.map((criteria, index) => ({
        key: index,
        criteria,
        weight: (actualWeights[index] * 100).toFixed(1) + '%'
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

      // Create pie chart data using actual weights
      const pieData = [{
        values: actualWeights,
        labels: actualCriteriaNames,
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
            style={{ marginBottom: 16 }}
          />
          
          {prometheeResults.weights_source && (
            <Alert
              message={`Weights Source: ${prometheeResults.weights_source === 'backend' ? 'Database (Saved BWM Configuration)' : 'Local Storage (Fallback)'}`}
              description={prometheeResults.weights_source === 'backend' 
                ? 'Using the most recent BWM weights saved to the database.' 
                : 'Backend weights not available - using local configuration as fallback.'}
              type={prometheeResults.weights_source === 'backend' ? 'success' : 'warning'}
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}
          
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

          {/* Per-Criteria Flow Charts */}
          {prometheeResults.criteria_flows && (
            <div style={{ marginTop: 24 }}>
              <Title level={4}>📋 Individual Criteria Flows</Title>
              <Row gutter={[16, 16]}>
                {Object.entries(prometheeResults.criteria_flows).map(([criterion, flows]) => {
                  // Create sorted criteria data matching the main sorting
                  const criteriaResultsData = resultsData.map((result, index) => ({
                    supplier: result.supplier,
                    net_flow: flows.net_flows[index].toFixed(3),
                    ranking: index + 1
                  }));
                  
                  // Sort by net flow for this criterion (descending)
                  const sortedCriteriaResults = [...criteriaResultsData].sort((a, b) => parseFloat(b.net_flow) - parseFloat(a.net_flow));

                  // Create bar chart data for this criterion
                  const criterionBarData = [{
                    x: sortedCriteriaResults.map(r => r.supplier),
                    y: sortedCriteriaResults.map(r => parseFloat(r.net_flow)),
                    type: 'bar',
                    marker: {
                      color: '#666666'  // Greyscale color
                    }
                  }];

                  const criterionLayout = {
                    title: {
                      text: criterion,
                      font: { size: 12 }
                    },
                    xaxis: { 
                      title: { text: 'Supplier', font: { size: 10 } },
                      tickfont: { size: 9 }
                    },
                    yaxis: { 
                      title: { text: 'Net Flow', font: { size: 10 } },
                      tickfont: { size: 9 }
                    },
                    height: 200,
                    margin: { t: 30, b: 40, l: 40, r: 20 },
                    plot_bgcolor: '#f8f8f8',
                    paper_bgcolor: 'white'
                  };

                  return (
                    <Col span={6} key={criterion}>
                      <Card size="small" style={{ backgroundColor: '#fafafa' }}>
                        <Plot
                          data={criterionBarData}
                          layout={criterionLayout}
                          style={{ width: '100%', height: '200px' }}
                          config={{ displayModeBar: false }}
                        />
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            </div>
          )}

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
              <Tag key={index} color="blue" style={{ margin: '2px' }}>{criteriaNames[index]}: {weight.toFixed(4)}</Tag>
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
                {/* Preference Function Configuration */}
                <Card 
                  title="Preference Function Configuration" 
                  type="inner" 
                  style={{ marginBottom: 24 }}
                  extra={<Text type="secondary">Configure how criteria differences are evaluated</Text>}
                >
                  <Row gutter={[16, 16]}>
                    {criteriaNames.map((criterionName, index) => (
                      <Col span={24} key={criterionName}>
                        <Card size="small" style={{ backgroundColor: '#fafafa' }}>
                          <Row gutter={16} align="middle">
                            <Col span={6}>
                              <Text strong>{criterionName}</Text>
                              <div>
                                <Tag color="blue" style={{ marginTop: 4 }}>
                                  Weight: {criteriaWeights[index]?.toFixed(4)}
                                </Tag>
                              </div>
                            </Col>
                            
                            <Col span={6}>
                              <Text>Preference Function:</Text>
                              <Select
                                value={preferenceFunctions[criterionName] || 'linear'}
                                onChange={(value) => handlePreferenceFunctionChange(criterionName, value)}
                                style={{ width: '100%', marginTop: 4 }}
                                placeholder="Select function type"
                              >
                                {PREFERENCE_FUNCTION_TYPES.map(type => (
                                  <Option key={type.value} value={type.value}>
                                    {type.label}
                                  </Option>
                                ))}
                              </Select>
                            </Col>
                            
                            <Col span={6}>
                              <Text>Indifference Threshold:</Text>
                              <InputNumber
                                value={indifferenceThresholds[criterionName] || 0.5}
                                onChange={(value) => handleIndifferenceThresholdChange(criterionName, value)}
                                min={0}
                                max={10}
                                step={0.1}
                                style={{ width: '100%', marginTop: 4 }}
                                placeholder="0.5"
                              />
                              <Text type="secondary" style={{ fontSize: '11px' }}>Below this: no preference</Text>
                            </Col>
                            
                            <Col span={6}>
                              <Text>Preference Threshold:</Text>
                              <InputNumber
                                value={preferenceThresholds[criterionName] || 2.0}
                                onChange={(value) => handlePreferenceThresholdChange(criterionName, value)}
                                min={0}
                                max={10}
                                step={0.1}
                                style={{ width: '100%', marginTop: 4 }}
                                placeholder="2.0"
                              />
                              <Text type="secondary" style={{ fontSize: '11px' }}>Above this: strict preference</Text>
                            </Col>
                          </Row>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                  
                  <Alert
                    message="Preference Function & Threshold Guide"
                    description={
                      <div>
                        <Divider orientation="left" style={{ margin: '12px 0' }}>Preference Functions</Divider>
                        
                        <div style={{ marginBottom: '12px' }}>
                          <Text strong>Usual (Type I):</Text> Binary preference - any difference creates strict preference.
                          <br /><Text type="secondary">Use for: Binary criteria (pass/fail, certified/not certified). Thresholds ignored.</Text>
                        </div>
                        
                        <div style={{ marginBottom: '12px' }}>
                          <Text strong>U-Shape (Type II):</Text> Sharp transition at indifference threshold only.
                          <br /><Text type="secondary">Use for: Quality grades where small differences don't matter until a clear threshold is crossed.</Text>
                        </div>
                        
                        <div style={{ marginBottom: '12px' }}>
                          <Text strong>V-Shape (Type III):</Text> Linear increase from 0 to preference threshold.
                          <br /><Text type="secondary">Use for: Cost differences where every unit matters equally up to a maximum.</Text>
                        </div>
                        
                        <div style={{ marginBottom: '12px' }}>
                          <Text strong>Level (Type IV):</Text> Constant preference level between thresholds.
                          <br /><Text type="secondary">Use for: Performance metrics with acceptable ranges and clear performance bands.</Text>
                        </div>
                        
                        <div style={{ marginBottom: '12px' }}>
                          <Text strong>Linear (Type V):</Text> Gradual linear transition between both thresholds.
                          <br /><Text type="secondary">Use for: Most general criteria with smooth preference changes (recommended default).</Text>
                        </div>
                        
                        <div style={{ marginBottom: '16px' }}>
                          <Text strong>Gaussian (Type VI):</Text> Smooth S-curve transition with normal distribution.
                          <br /><Text type="secondary">Use for: Subjective criteria where extreme differences matter less than moderate ones.</Text>
                        </div>
                        
                        <Divider orientation="left" style={{ margin: '12px 0' }}>Threshold Settings</Divider>
                        
                        <div style={{ marginBottom: '8px' }}>
                          <Text strong>Indifference Threshold:</Text> Below this difference, no preference exists between alternatives.
                          <br /><Text type="secondary">Example: For cost criteria, differences under $500 might be considered negligible.</Text>
                        </div>
                        
                        <div style={{ marginBottom: '8px' }}>
                          <Text strong>Preference Threshold:</Text> Above this difference, strict preference is established.
                          <br /><Text type="secondary">Example: For cost criteria, differences over $2000 show clear preference for the cheaper option.</Text>
                        </div>
                        
                        <div style={{ backgroundColor: '#f0f8ff', padding: '8px', borderRadius: '4px', marginTop: '12px' }}>
                          <Text strong>💡 Setting Guidelines:</Text>
                          <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                            <li>Set indifference threshold to the smallest meaningful difference</li>
                            <li>Set preference threshold to where differences become clearly significant</li>
                            <li>For percentage-based criteria: try 5% (indifference) and 20% (preference)</li>
                            <li>For score-based criteria (1-10): try 0.5 (indifference) and 2.0 (preference)</li>
                            <li>Always ensure: indifference threshold ≤ preference threshold</li>
                          </ul>
                        </div>
                      </div>
                    }
                    type="info"
                    showIcon
                    style={{ marginTop: 16 }}
                  />
                </Card>
                
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