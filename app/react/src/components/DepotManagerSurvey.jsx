import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Typography, 
  Button, 
  Row, 
  Col, 
  Select, 
  InputNumber, 
  Form, 
  Input, 
  Alert, 
  Divider,
  Tag,
  Checkbox,
  Space,
  message,
  Spin
} from 'antd'
import { SaveOutlined, CheckOutlined, UserOutlined } from '@ant-design/icons'

const { Title, Text } = Typography
const { Option } = Select

const DepotManagerSurvey = ({ onSurveyComplete }) => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [suppliers, setSuppliers] = useState([])
  const [depots, setDepots] = useState([])
  const [criteriaNames, setCriteriaNames] = useState([])
  const [selectedSuppliers, setSelectedSuppliers] = useState([])
  const [evaluations, setEvaluations] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchSuppliers()
    fetchDepots()
    loadCriteriaFromConfig()
  }, [])

  const fetchSuppliers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/suppliers/')
      const data = await response.json()
      setSuppliers(data.suppliers || [])
    } catch (error) {
      console.error('Error fetching suppliers:', error)
      message.error('Failed to fetch suppliers')
    }
  }

  const fetchDepots = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/depots/')
      const data = await response.json()
      setDepots(data.depots || [])
    } catch (error) {
      console.error('Error fetching depots:', error)
      message.error('Failed to fetch depots')
    }
  }

  const loadCriteriaFromConfig = () => {
    const savedConfig = localStorage.getItem('ahpConfig')
    if (savedConfig) {
      const config = JSON.parse(savedConfig)
      setCriteriaNames(config.criteriaNames || [])
    }
  }

  const handleSupplierSelection = (supplierIds) => {
    setSelectedSuppliers(supplierIds)
    // Initialize evaluations for selected suppliers
    const newEvaluations = { ...evaluations }
    supplierIds.forEach(supplierId => {
      if (!newEvaluations[supplierId]) {
        newEvaluations[supplierId] = {}
      }
    })
    setEvaluations(newEvaluations)
  }

  const handleEvaluationChange = (supplierId, criterion, value) => {
    setEvaluations(prev => ({
      ...prev,
      [supplierId]: {
        ...prev[supplierId],
        [criterion]: value
      }
    }))
  }

  const handleSubmit = async (values) => {
    setSubmitting(true)
    try {
      const { depot_id, manager_name, manager_email } = values
      
      // Prepare evaluations array
      const evaluationsArray = []
      selectedSuppliers.forEach(supplierId => {
        criteriaNames.forEach(criterion => {
          const score = evaluations[supplierId]?.[criterion]
          if (score !== undefined && score !== null) {
            evaluationsArray.push({
              supplier_id: parseInt(supplierId),
              criterion_name: criterion,
              score: parseFloat(score)
            })
          }
        })
      })

      if (evaluationsArray.length === 0) {
        message.warning('Please provide at least one evaluation before submitting')
        return
      }

      // Submit batch evaluation
      const response = await fetch('http://localhost:8000/api/depot-evaluations/submit-batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          depot_id: parseInt(depot_id),
          manager_name,
          manager_email,
          evaluations: evaluationsArray
        })
      })

      if (response.ok) {
        const result = await response.json()
        message.success(`Successfully submitted ${result.count} evaluations!`)
        form.resetFields()
        setSelectedSuppliers([])
        setEvaluations({})
        
        if (onSurveyComplete) {
          onSurveyComplete()
        }
      } else {
        throw new Error('Failed to submit evaluations')
      }
    } catch (error) {
      console.error('Error submitting evaluations:', error)
      message.error('Failed to submit evaluations. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const getCompletionStatus = () => {
    let totalRequired = selectedSuppliers.length * criteriaNames.length
    let completed = 0
    
    selectedSuppliers.forEach(supplierId => {
      criteriaNames.forEach(criterion => {
        if (evaluations[supplierId]?.[criterion] !== undefined) {
          completed++
        }
      })
    })
    
    return { completed, total: totalRequired }
  }

  const completionStatus = getCompletionStatus()

  return (
    <div>
      <Card>
        <Title level={3}>
          <UserOutlined /> Depot Manager Supplier Evaluation Survey
        </Title>
        <Text type="secondary">
          Please evaluate suppliers based on your depot's experience with them. 
          Only evaluate suppliers you have worked with directly.
        </Text>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="depot_id"
                label="Select Your Depot"
                rules={[{ required: true, message: 'Please select your depot' }]}
              >
                <Select placeholder="Select depot">
                  {depots.map(depot => (
                    <Option key={depot.id} value={depot.id}>
                      {depot.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="manager_name"
                label="Your Name"
                rules={[{ required: true, message: 'Please enter your name' }]}
              >
                <Input placeholder="Enter your full name" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="manager_email"
                label="Your Email"
                rules={[
                  { required: true, message: 'Please enter your email' },
                  { type: 'email', message: 'Please enter a valid email' }
                ]}
              >
                <Input placeholder="Enter your email address" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />

          <Title level={4}>Step 1: Select Suppliers You Have Experience With</Title>
          <Alert
            message="Important"
            description="Only select suppliers that your depot has worked with. You should have direct experience with these suppliers to provide accurate evaluations."
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          
          <Checkbox.Group
            value={selectedSuppliers}
            onChange={handleSupplierSelection}
            style={{ width: '100%' }}
          >
            <Row gutter={[16, 16]}>
              {suppliers.map(supplier => (
                <Col span={8} key={supplier.id}>
                  <Checkbox value={supplier.id.toString()}>
                    {supplier.name}
                  </Checkbox>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>

          {selectedSuppliers.length > 0 && (
            <>
              <Divider />
              <Title level={4}>Step 2: Evaluate Selected Suppliers</Title>
              <Alert
                message="Evaluation Scale"
                description="Rate each criterion on a scale of 1-10, where 1 is poor performance and 10 is excellent performance."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <div style={{ marginBottom: 16 }}>
                <Text strong>Progress: </Text>
                <Tag color={completionStatus.completed === completionStatus.total ? 'green' : 'orange'}>
                  {completionStatus.completed} / {completionStatus.total} evaluations completed
                </Tag>
              </div>

              {selectedSuppliers.map(supplierId => {
                const supplier = suppliers.find(s => s.id.toString() === supplierId)
                return (
                  <Card 
                    key={supplierId} 
                    style={{ marginBottom: 16 }}
                    title={supplier?.name || `Supplier ${supplierId}`}
                    size="small"
                  >
                    <Row gutter={[16, 16]}>
                      {criteriaNames.map(criterion => (
                        <Col span={8} key={criterion}>
                          <div>
                            <Text strong>{criterion}:</Text>
                            <InputNumber
                              min={1}
                              max={10}
                              step={0.1}
                              value={evaluations[supplierId]?.[criterion]}
                              onChange={(value) => handleEvaluationChange(supplierId, criterion, value)}
                              style={{ width: '100%', marginTop: 4 }}
                              placeholder="Rate 1-10"
                            />
                          </div>
                        </Col>
                      ))}
                    </Row>
                  </Card>
                )
              })}

              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={submitting}
                  size="large"
                  disabled={completionStatus.completed !== completionStatus.total || completionStatus.total === 0}
                >
                  Submit Evaluations
                </Button>
              </div>
            </>
          )}
        </Form>
      </Card>
    </div>
  )
}

export default DepotManagerSurvey