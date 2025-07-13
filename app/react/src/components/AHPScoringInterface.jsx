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
  Divider
} from 'antd'
import { CalculatorOutlined, CheckOutlined } from '@ant-design/icons'
import Plot from 'react-plotly.js'
import { ahpAPI } from '../services/api'

const { Title, Text } = Typography

const AHPScoringInterface = ({ ahpResults, setAhpResults, setCurrentPhase }) => {
  const [numCriteria, setNumCriteria] = useState(3)
  const [numSuppliers, setNumSuppliers] = useState(3)
  const [criteriaNames, setCriteriaNames] = useState([])
  const [criteriaWeights, setCriteriaWeights] = useState([])
  const [supplierNames, setSupplierNames] = useState([])
  const [supplierDescriptions, setSupplierDescriptions] = useState({})
  const [aiScores, setAiScores] = useState({})
  const [loading, setLoading] = useState(false)
  const [loadingAI, setLoadingAI] = useState({})

  useEffect(() => {
    // Initialize arrays when counts change
    setCriteriaNames(Array(numCriteria).fill('').map((_, i) => `Criteria ${i + 1}`))
    setCriteriaWeights(Array(numCriteria).fill(1.0))
    setSupplierNames(Array(numSuppliers).fill('').map((_, i) => `Supplier ${i + 1}`))
    setSupplierDescriptions({})
    setAiScores({})
  }, [numCriteria, numSuppliers])

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

  const handleSupplierNameChange = (index, value) => {
    const newNames = [...supplierNames]
    newNames[index] = value || `Supplier ${index + 1}`
    setSupplierNames(newNames)
  }

  const handleDescriptionChange = async (supplierIndex, criteriaIndex, description) => {
    const key = `${supplierIndex}-${criteriaIndex}`
    
    setSupplierDescriptions(prev => ({
      ...prev,
      [key]: description
    }))

    if (description.trim()) {
      setLoadingAI(prev => ({ ...prev, [key]: true }))
      
      try {
        const response = await ahpAPI.getAIScore(description, criteriaNames[criteriaIndex])
        setAiScores(prev => ({
          ...prev,
          [key]: response.score
        }))
      } catch (error) {
        console.error('Error getting AI score:', error)
        notification.error({
          message: 'AI Scoring Error',
          description: 'Failed to get AI score. Using default score of 5.'
        })
        setAiScores(prev => ({
          ...prev,
          [key]: 5
        }))
      } finally {
        setLoadingAI(prev => ({ ...prev, [key]: false }))
      }
    }
  }

  const calculateAHPScores = async () => {
    setLoading(true)
    
    try {
      // Prepare scores matrix
      const scoresMatrix = []
      for (let s = 0; s < numSuppliers; s++) {
        const supplierScores = []
        for (let c = 0; c < numCriteria; c++) {
          const key = `${s}-${c}`
          const score = aiScores[key] || 5
          supplierScores.push(score)
        }
        scoresMatrix.push(supplierScores)
      }

      // Normalize weights
      const weightSum = criteriaWeights.reduce((sum, w) => sum + w, 0)
      const normalizedWeights = criteriaWeights.map(w => w / weightSum)

      const data = {
        criteria_names: criteriaNames,
        criteria_weights: normalizedWeights,
        supplier_names: supplierNames,
        scores_matrix: scoresMatrix
      }

      const response = await ahpAPI.calculateAHPScores(data)
      
      setAhpResults({
        suppliers: supplierNames,
        scores: response.weighted_scores,
        criteria: criteriaNames,
        weights: normalizedWeights,
        scores_matrix: scoresMatrix
      })

      notification.success({
        message: 'AHP Calculation Complete',
        description: 'AHP scoring completed successfully! You can now proceed to the Supply Chain Optimization tab.'
      })

    } catch (error) {
      console.error('Error calculating AHP scores:', error)
      notification.error({
        message: 'Calculation Error',
        description: 'Failed to calculate AHP scores. Please try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  const renderResults = () => {
    if (!ahpResults) return null

    const resultsData = ahpResults.suppliers.map((supplier, index) => ({
      key: index,
      supplier,
      score: ahpResults.scores[index].toFixed(2)
    }))

    const sortedResults = [...resultsData].sort((a, b) => b.score - a.score)

    const weightsData = ahpResults.criteria.map((criteria, index) => ({
      key: index,
      criteria,
      weight: ahpResults.weights[index].toFixed(3)
    }))

    const resultsColumns = [
      {
        title: 'Supplier',
        dataIndex: 'supplier',
        key: 'supplier',
      },
      {
        title: 'AHP Score',
        dataIndex: 'score',
        key: 'score',
        sorter: (a, b) => parseFloat(a.score) - parseFloat(b.score),
        sortOrder: 'descend'
      }
    ]

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

    // Create bar chart data
    const barData = [{
      x: resultsData.map(r => r.supplier),
      y: resultsData.map(r => parseFloat(r.score)),
      type: 'bar',
      marker: {
        color: 'rgba(54, 162, 235, 0.8)'
      }
    }]

    const barLayout = {
      title: 'AHP Supplier Scores',
      xaxis: { title: 'Supplier' },
      yaxis: { title: 'AHP Score' },
      height: 400
    }

    // Create pie chart data
    const pieData = [{
      values: ahpResults.weights,
      labels: ahpResults.criteria,
      type: 'pie',
      hole: 0.4
    }]

    const pieLayout = {
      title: 'Criteria Weight Distribution',
      height: 400
    }

    return (
      <div>
        <Title level={4}>📊 Results: AHP Weighted Supplier Scores</Title>
        
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
            <Card title="📊 Supplier Scores Comparison">
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
          message="AHP scoring completed! You can now proceed to the Supply Chain Optimization tab."
          type="success"
          showIcon
          icon={<CheckOutlined />}
          style={{ marginTop: 24 }}
        />
      </div>
    )
  }

  return (
    <div>
      <Title level={2}>🧮 AHP Supplier Scoring</Title>
      <Text style={{ fontStyle: 'italic' }}>
        Evaluate suppliers using AHP methodology with AI-assisted scoring
      </Text>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>🔧 AHP Configuration</Title>
        <Row gutter={16}>
          <Col span={8}>
            <Text strong>Number of Criteria:</Text>
            <InputNumber
              min={1}
              max={10}
              value={numCriteria}
              onChange={setNumCriteria}
              style={{ width: '100%', marginTop: 8 }}
            />
          </Col>
          <Col span={8}>
            <Text strong>Number of Suppliers:</Text>
            <InputNumber
              min={1}
              max={10}
              value={numSuppliers}
              onChange={setNumSuppliers}
              style={{ width: '100%', marginTop: 8 }}
            />
          </Col>
          <Col span={8}>
            {ahpResults && (
              <div>
                <Text strong>✅ AHP Scores Calculated</Text>
                <div style={{ marginTop: 8 }}>
                  <Text strong>Supplier Rankings:</Text>
                  {ahpResults.suppliers.map((supplier, i) => (
                    <div key={i}>
                      <Text>{i + 1}. {supplier}: {ahpResults.scores[i].toFixed(2)}</Text>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Col>
        </Row>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>Step 1: Define Supplier Selection Criteria</Title>
        <div className="criteria-input-grid">
          {criteriaNames.map((name, index) => (
            <div key={index}>
              <Text strong>Criteria {index + 1} name:</Text>
              <Input
                value={name}
                onChange={(e) => handleCriteriaNameChange(index, e.target.value)}
                placeholder={`Criteria ${index + 1}`}
                style={{ marginTop: 8 }}
              />
            </div>
          ))}
        </div>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>Step 2: Assign Criteria Weights (Relative Importance)</Title>
        <div className="criteria-input-grid">
          {criteriaNames.map((name, index) => (
            <div key={index}>
              <Text strong>Weight for '{name}':</Text>
              <InputNumber
                min={0}
                step={0.1}
                value={criteriaWeights[index]}
                onChange={(value) => handleCriteriaWeightChange(index, value)}
                style={{ width: '100%', marginTop: 8 }}
              />
            </div>
          ))}
        </div>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>Step 3: Enter Supplier Scores per Criterion</Title>
        {supplierNames.map((supplierName, supplierIndex) => (
          <div key={supplierIndex} className="supplier-input-section">
            <Title level={5}>Supplier {supplierIndex + 1}</Title>
            <Input
              value={supplierName}
              onChange={(e) => handleSupplierNameChange(supplierIndex, e.target.value)}
              placeholder={`Name of Supplier ${supplierIndex + 1}`}
              style={{ marginBottom: 16 }}
            />
            
            <div className="supplier-criteria-grid">
              {criteriaNames.map((criteria, criteriaIndex) => {
                const key = `${supplierIndex}-${criteriaIndex}`
                const isLoadingAI = loadingAI[key]
                const aiScore = aiScores[key]
                
                return (
                  <div key={criteriaIndex}>
                    <Text strong>Describe {criteria} for {supplierName}:</Text>
                    <Input.TextArea
                      value={supplierDescriptions[key] || ''}
                      onChange={(e) => handleDescriptionChange(supplierIndex, criteriaIndex, e.target.value)}
                      placeholder={`Describe ${criteria} performance`}
                      rows={2}
                      style={{ marginTop: 8 }}
                    />
                    <div className="ai-score-display">
                      {isLoadingAI ? (
                        <Spin size="small" />
                      ) : (
                        <Text>AI Score: {aiScore || 5}</Text>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Button
          type="primary"
          icon={<CalculatorOutlined />}
          onClick={calculateAHPScores}
          loading={loading}
          size="large"
          style={{ marginBottom: 24 }}
        >
          🔍 Calculate AHP Supplier Scores
        </Button>

        {renderResults()}
      </Card>
    </div>
  )
}

export default AHPScoringInterface