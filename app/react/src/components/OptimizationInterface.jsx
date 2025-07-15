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
  Slider,
  Select,
  Checkbox,
  Collapse,
  Statistic,
  Tabs,
  Tag
} from 'antd'
import { 
  RocketOutlined, 
  SearchOutlined, 
  DownloadOutlined, 
  FileExcelOutlined
} from '@ant-design/icons'
import Plot from 'react-plotly.js'
import { optimizationAPI } from '../services/api'

const { Title, Text } = Typography
const { Panel } = Collapse
const { Option } = Select

const OptimizationInterface = ({ ahpResults }) => {
  const [filePath, setFilePath] = useState("/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Demo3.xlsx")
  const [sheetNames, setSheetNames] = useState({
    obj1: 'Obj1_Coeff',
    obj2: 'Obj2_Coeff',
    volumes: 'Annual Volumes'
  })
  const [nPoints, setNPoints] = useState(21)
  const [constraintType, setConstraintType] = useState('cost')
  const [enableRanking, setEnableRanking] = useState(true)
  const [rankingMetric, setRankingMetric] = useState('cost_effectiveness')
  const [showRankingInUI, setShowRankingInUI] = useState(true)
  const [randomSeed, setRandomSeed] = useState(42)
  
  const [dataLoaded, setDataLoaded] = useState(false)
  const [optimizerData, setOptimizerData] = useState(null)
  const [optimizationResults, setOptimizationResults] = useState(null)
  const [selectedSolution, setSelectedSolution] = useState(null)
  const [rankingAnalysis, setRankingAnalysis] = useState(null)
  
  const [loading, setLoading] = useState(false)
  const [optimizing, setOptimizing] = useState(false)

  const initializeData = async () => {
    setLoading(true)
    try {
      const config = {
        file_path: filePath,
        sheet_names: sheetNames,
        random_seed: randomSeed
      }
      
      const response = await optimizationAPI.initializeOptimizer(config)
      setOptimizerData(response)
      setDataLoaded(true)
      
      notification.success({
        message: 'Data Loaded',
        description: 'Data loaded and analyzed successfully!'
      })
    } catch (error) {
      console.error('Error initializing optimizer:', error)
      notification.error({
        message: 'Initialization Error',
        description: 'Failed to load and analyze data. Please check the file path and try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  const initializeFromDatabase = async () => {
    setLoading(true)
    try {
      const config = {
        random_seed: randomSeed
      }
      
      const response = await optimizationAPI.initializeFromDatabase(config)
      setOptimizerData(response)
      setDataLoaded(true)
      
      notification.success({
        message: 'Data Loaded from Database',
        description: 'Supplier data loaded from database successfully!'
      })
    } catch (error) {
      console.error('Error initializing optimizer from database:', error)
      notification.error({
        message: 'Database Initialization Error',
        description: 'Failed to load data from database. Please ensure supplier data is complete and approved.'
      })
    } finally {
      setLoading(false)
    }
  }

  const runOptimization = async () => {
    setOptimizing(true)
    try {
      const params = {
        n_points: nPoints,
        constraint_type: constraintType,
        enable_ranking: enableRanking,
        ranking_metric: rankingMetric,
        show_ranking_in_ui: showRankingInUI
      }
      
      // Always use the simple optimization first to avoid complexity
      const response = await optimizationAPI.runOptimization(params)
      
      setOptimizationResults(response)
      if (response.ranking_analysis) {
        setRankingAnalysis(response.ranking_analysis)
      }
      
      notification.success({
        message: 'Optimization Complete',
        description: 'Optimization completed successfully!'
      })
    } catch (error) {
      console.error('Error running optimization:', error)
      notification.error({
        message: 'Optimization Error',
        description: 'Failed to run optimization. Please try again.'
      })
    } finally {
      setOptimizing(false)
    }
  }

  const handlePlotClick = (data) => {
    if (data.points && data.points.length > 0) {
      const pointIndex = data.points[0].pointIndex
      setSelectedSolution(pointIndex)
    }
  }

  const exportResults = async (format = 'csv') => {
    try {
      const blob = await optimizationAPI.exportResults(format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `optimization_results.${format}`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error exporting results:', error)
      notification.error({
        message: 'Export Error',
        description: 'Failed to export results.'
      })
    }
  }

  const renderAHPSummary = () => {
    if (!ahpResults) {
      return (
        <Alert
          message="💡 Complete the AHP scoring first to see supplier rankings here."
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )
    }

    const ahpData = ahpResults.suppliers.map((supplier, index) => ({
      key: index,
      supplier,
      score: ahpResults.scores[index].toFixed(2)
    })).sort((a, b) => parseFloat(b.score) - parseFloat(a.score))

    const columns = [
      {
        title: 'Supplier',
        dataIndex: 'supplier',
        key: 'supplier',
      },
      {
        title: 'AHP Score',
        dataIndex: 'score',
        key: 'score',
      }
    ]

    const barData = [{
      x: ahpData.map(r => r.supplier),
      y: ahpData.map(r => parseFloat(r.score)),
      type: 'bar',
      marker: { color: 'rgba(54, 162, 235, 0.8)' }
    }]

    const barLayout = {
      title: 'AHP Supplier Rankings',
      height: 300,
      margin: { t: 40, b: 40, l: 40, r: 40 }
    }

    return (
      <Card title="📊 AHP Results Summary" style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col span={12}>
            <Table 
              dataSource={ahpData} 
              columns={columns} 
              pagination={false}
              size="small"
            />
          </Col>
          <Col span={12}>
            <Plot
              data={barData}
              layout={barLayout}
              style={{ width: '100%', height: '300px' }}
            />
          </Col>
        </Row>
      </Card>
    )
  }

  const renderDataAnalysis = () => {
    if (!dataLoaded || !optimizerData) return null

    const availabilityData = optimizerData.availability?.map(item => ({
      key: `${item.depot}-${item.supplier}`,
      depot: `Depot ${item.depot}`,
      supplier: `Supplier ${item.supplier}`,
      operations: item.operations.join(', ') || 'None',
      collection: item.collection ? '✅' : '❌',
      delivery: item.delivery ? '✅' : '❌'
    })) || []

    const columns = [
      { title: '🏭 Depot', dataIndex: 'depot', key: 'depot' },
      { title: '🏢 Supplier', dataIndex: 'supplier', key: 'supplier' },
      { title: 'Available Operations', dataIndex: 'operations', key: 'operations' },
      { title: 'Collection', dataIndex: 'collection', key: 'collection' },
      { title: 'Delivery', dataIndex: 'delivery', key: 'delivery' }
    ]

    return (
      <Card title="📊 Data Analysis" style={{ marginBottom: 24 }}>
        <div className="metrics-row">
          <Statistic title="🏭 Depots" value={optimizerData.n_depots} />
          <Statistic title="🚛 Suppliers" value={optimizerData.n_suppliers} />
          <Statistic title="🔗 Total Pairs" value={optimizerData.total_pairs} />
        </div>

        <Collapse>
          <Panel header="🔍 Depot-Supplier Availability Analysis" key="availability">
            <Table 
              dataSource={availabilityData} 
              columns={columns} 
              pagination={{ pageSize: 10 }}
              size="small"
            />
            
            <div style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="Total Pairs" value={optimizerData.total_pairs} />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="Collection Available" 
                    value={`${optimizerData.collection_available} (${((optimizerData.collection_available / optimizerData.total_pairs) * 100).toFixed(1)}%)`} 
                  />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="Delivery Available" 
                    value={`${optimizerData.delivery_available} (${((optimizerData.delivery_available / optimizerData.total_pairs) * 100).toFixed(1)}%)`} 
                  />
                </Col>
              </Row>
            </div>
          </Panel>
        </Collapse>
      </Card>
    )
  }

  const renderParetoFront = () => {
    if (!optimizationResults) return null

    const feasibleSolutions = optimizationResults.solutions.filter(s => s.status === 'Optimal')
    
    if (feasibleSolutions.length === 0) {
      return (
        <Alert
          message="No feasible solutions found"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )
    }

    const plotData = [{
      x: feasibleSolutions.map(s => s.cost),
      y: feasibleSolutions.map(s => s.score),
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: 'red',
        size: 10
      },
      text: feasibleSolutions.map((_, i) => `Solution ${i}`),
      customdata: feasibleSolutions.map((_, i) => i),
      hovertemplate: 
        '<b>ε-Constraint Solution %{text}</b><br>' +
        'Cost: R%{x:,.0f}<br>' +
        'Score: %{y:.2f}<br>' +
        '<b>👆 Click to see details</b><br>' +
        '<extra></extra>'
    }]

    const layout = {
      title: 'Pareto Front: ε-Constraint Optimization',
      xaxis: { title: 'Total Cost (R)' },
      yaxis: { title: 'Supplier Score' },
      hovermode: 'closest',
      height: 500
    }

    const histData = [{
      x: feasibleSolutions.map(s => s.cost),
      type: 'histogram',
      marker: { color: 'red', opacity: 0.7 },
      name: 'ε-Constraint'
    }]

    const histLayout = {
      title: 'Cost Distribution',
      xaxis: { title: 'Cost' },
      yaxis: { title: 'Frequency' },
      height: 200
    }

    return (
      <div className="pareto-container">
        <Card title="📈 Interactive Pareto Front" className="pareto-plot">
          <Plot
            data={plotData}
            layout={layout}
            style={{ width: '100%', height: '500px' }}
            onClick={handlePlotClick}
          />
        </Card>
        
        <Card title="📊 Solution Overview" className="pareto-overview">
          <Statistic 
            title="ε-Constraint Solutions" 
            value={feasibleSolutions.length}
            style={{ marginBottom: 24 }}
          />
          
          <Title level={5}>📈 Cost Distribution:</Title>
          <Plot
            data={histData}
            layout={histLayout}
            style={{ width: '100%', height: '200px' }}
          />
        </Card>
      </div>
    )
  }

  const renderSolutionDetails = () => {
    if (!optimizationResults || selectedSolution === null) return null

    const solution = optimizationResults.solutions.filter(s => s.status === 'Optimal')[selectedSolution]
    if (!solution) return null

    const allocations = solution.allocations.split(' ').filter(a => a.length > 0)
    
    const allocationData = allocations.map(alloc => {
      const operation = alloc[0]
      const params = alloc.slice(2, -1).split(',')
      return {
        key: alloc,
        depot: `Depot ${params[0]}`,
        supplier: `Supplier ${params[1]}`,
        operation: operation === 'C' ? 'Collection' : 'Delivery',
        code: alloc
      }
    })

    const allocationColumns = [
      { title: '🏭 Depot', dataIndex: 'depot', key: 'depot' },
      { title: '🏢 Supplier', dataIndex: 'supplier', key: 'supplier' },
      { title: '📋 Operation', dataIndex: 'operation', key: 'operation' },
      { title: '🔧 Code', dataIndex: 'code', key: 'code' }
    ]

    const solutionTabs = [
      {
        key: 'allocations',
        label: '🏭 Allocations',
        children: (
          <div>
            <Row gutter={24}>
              <Col span={12}>
                <Title level={5}>🏭 Detailed Allocations:</Title>
                <Table 
                  dataSource={allocationData} 
                  columns={allocationColumns} 
                  pagination={false}
                  size="small"
                />
              </Col>
              <Col span={12}>
                <Title level={5}>📈 Allocation Summary:</Title>
                <div>
                  <Text strong>Total Operations:</Text> {allocations.length}
                  <br />
                  <Text strong>Collection:</Text> {allocations.filter(a => a.startsWith('C')).length}
                  <br />
                  <Text strong>Delivery:</Text> {allocations.filter(a => a.startsWith('D')).length}
                </div>
              </Col>
            </Row>
          </div>
        )
      },
      {
        key: 'rankings',
        label: '🏆 Supplier Rankings',
        children: (
          <div>
            <Text>Supplier rankings will be displayed here when ranking analysis is enabled.</Text>
          </div>
        )
      },
      {
        key: 'summary',
        label: '📊 Summary',
        children: (
          <div>
            <Row gutter={24}>
              <Col span={8}>
                <Statistic title="🏭 Total Depots" value={new Set(allocationData.map(a => a.depot)).size} />
              </Col>
              <Col span={8}>
                <Statistic title="📦 Collection Operations" value={allocations.filter(a => a.startsWith('C')).length} />
              </Col>
              <Col span={8}>
                <Statistic title="🚚 Delivery Operations" value={allocations.filter(a => a.startsWith('D')).length} />
              </Col>
            </Row>
          </div>
        )
      }
    ]

    return (
      <Card title={`🔍 ε-Constraint Solution ${selectedSolution} Details`} className="solution-details">
        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Statistic title="💰 Total Cost" value={`R${solution.cost.toLocaleString()}`} />
          </Col>
          <Col span={12}>
            <Statistic title="⭐ Score" value={solution.score.toFixed(2)} />
          </Col>
        </Row>

        <Tabs items={solutionTabs} />

        <div style={{ marginTop: 24 }}>
          <Title level={5}>🔤 Raw Allocation String:</Title>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '12px', 
            borderRadius: '4px',
            fontFamily: 'monospace'
          }}>
            {solution.allocations || 'No allocation data'}
          </div>
        </div>

        <Button 
          onClick={() => setSelectedSolution(null)}
          style={{ marginTop: 16 }}
        >
          ❌ Close Details
        </Button>
      </Card>
    )
  }

  const renderSidebar = () => (
    <Card title="📁 Data Configuration" style={{ marginBottom: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Text strong>Excel File Path:</Text>
        <Input
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          placeholder="Path to your Excel file"
          style={{ marginTop: 8 }}
        />
      </div>

      <Title level={5}>📋 Sheet Names</Title>
      <div style={{ marginBottom: 16 }}>
        <Text strong>Objective 1 Coefficients:</Text>
        <Input
          value={sheetNames.obj1}
          onChange={(e) => setSheetNames({...sheetNames, obj1: e.target.value})}
          style={{ marginTop: 8 }}
        />
      </div>
      <div style={{ marginBottom: 16 }}>
        <Text strong>Objective 2 Coefficients:</Text>
        <Input
          value={sheetNames.obj2}
          onChange={(e) => setSheetNames({...sheetNames, obj2: e.target.value})}
          style={{ marginTop: 8 }}
        />
      </div>
      <div style={{ marginBottom: 24 }}>
        <Text strong>Annual Volumes:</Text>
        <Input
          value={sheetNames.volumes}
          onChange={(e) => setSheetNames({...sheetNames, volumes: e.target.value})}
          style={{ marginTop: 8 }}
        />
      </div>

      <Title level={5}>⚙️ ε-Constraint Parameters</Title>
      <div style={{ marginBottom: 16 }}>
        <Text strong>Number of Epsilon Points: {nPoints}</Text>
        <Slider
          min={5}
          max={400}
          value={nPoints}
          onChange={setNPoints}
          style={{ marginTop: 8 }}
        />
      </div>
      <div style={{ marginBottom: 24 }}>
        <Text strong>Constraint Type:</Text>
        <Select
          value={constraintType}
          onChange={setConstraintType}
          style={{ width: '100%', marginTop: 8 }}
        >
          <Option value="cost">Cost</Option>
          <Option value="score">Score</Option>
        </Select>
      </div>

      <Title level={5}>🔍 Supplier Ranking Analysis</Title>
      <div style={{ marginBottom: 16 }}>
        <Checkbox
          checked={enableRanking}
          onChange={(e) => setEnableRanking(e.target.checked)}
        >
          Enable Supplier Ranking Analysis
        </Checkbox>
      </div>
      
      {enableRanking && (
        <>
          <div style={{ marginBottom: 16 }}>
            <Text strong>Ranking Metric:</Text>
            <Select
              value={rankingMetric}
              onChange={setRankingMetric}
              style={{ width: '100%', marginTop: 8 }}
            >
              <Option value="cost_effectiveness">Cost Effectiveness</Option>
              <Option value="cost_impact">Cost Impact</Option>
              <Option value="score_impact">Score Impact</Option>
              <Option value="combined">Combined</Option>
            </Select>
          </div>
          <div style={{ marginBottom: 16 }}>
            <Checkbox
              checked={showRankingInUI}
              onChange={(e) => setShowRankingInUI(e.target.checked)}
            >
              Show Ranking Analysis in UI
            </Checkbox>
          </div>
        </>
      )}

      <div style={{ marginBottom: 24 }}>
        <Text strong>Random Seed:</Text>
        <InputNumber
          value={randomSeed}
          onChange={setRandomSeed}
          style={{ width: '100%', marginTop: 8 }}
        />
      </div>

      <Button
        type="secondary"
        icon={<SearchOutlined />}
        onClick={initializeData}
        loading={loading}
        style={{ width: '100%', marginBottom: 16 }}
      >
        🔍 Initialize & Analyze Data
      </Button>

      <Button
        type="secondary"
        icon={<FileExcelOutlined />}
        onClick={initializeFromDatabase}
        loading={loading}
        style={{ width: '100%', marginBottom: 16 }}
      >
        📊 Load from Database
      </Button>

      {dataLoaded && (
        <Button
          type="primary"
          icon={<RocketOutlined />}
          onClick={runOptimization}
          loading={optimizing}
          style={{ width: '100%' }}
        >
          🚀 Run Optimization
        </Button>
      )}
    </Card>
  )

  return (
    <div>
      <Title level={2}>🏭 Supply Chain Optimizer</Title>
      <Text style={{ fontStyle: 'italic' }}>
        Multi-objective optimization using ε-Constraint method with selective NA handling
      </Text>

      {renderAHPSummary()}

      <Row gutter={24}>
        <Col span={6}>
          {renderSidebar()}
        </Col>
        <Col span={18}>
          {dataLoaded && renderDataAnalysis()}
          {optimizationResults && renderParetoFront()}
          {selectedSolution !== null && renderSolutionDetails()}
          
          {optimizationResults && (
            <Card title="Export Results" style={{ marginTop: 24 }}>
              <div className="export-buttons">
                <Button
                  icon={<FileExcelOutlined />}
                  onClick={() => exportResults('csv')}
                >
                  💾 Export Results to CSV
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => exportResults('csv')}
                >
                  📥 Download Results CSV
                </Button>
              </div>
            </Card>
          )}

          {!dataLoaded && (
            <div className="welcome-content">
              <Title level={3}>🎯 About This ε-Constraint Optimizer</Title>
              <Text>
                This application uses <strong>ε-Constraint</strong> method for supply chain optimization with <strong>selective NA handling</strong>.
              </Text>
              
              <div className="feature-grid">
                <div className="feature-card">
                  <Title level={4}>🔍 ε-Constraint Optimization</Title>
                  <Text>Systematic exploration of Pareto front</Text>
                </div>
                <div className="feature-card">
                  <Title level={4}>📊 Pareto Front Visualization</Title>
                  <Text>Interactive visualization of optimal solutions</Text>
                </div>
                <div className="feature-card">
                  <Title level={4}>🎯 Multi-objective Optimization</Title>
                  <Text>Minimizes cost while maximizing supplier scores</Text>
                </div>
                <div className="feature-card">
                  <Title level={4}>📈 Interactive Analysis</Title>
                  <Text>Click points to explore solutions</Text>
                </div>
              </div>
            </div>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default OptimizationInterface