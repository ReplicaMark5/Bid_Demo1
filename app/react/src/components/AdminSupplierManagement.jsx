import React, { useState, useEffect, useRef } from 'react'
import { 
  Card, 
  Table, 
  Space,
  Button,
  Typography,
  Tag,
  Modal,
  Descriptions,
  Select,
  Alert,
  Statistic,
  Row,
  Col,
  Tabs,
  message,
  Popconfirm,
  Form,
  Input,
  InputNumber,
  Divider,
  Badge
} from 'antd'
import { 
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  UserOutlined,
  HomeOutlined,
  PlusOutlined,
  BarChartOutlined,
  SettingOutlined,
  CheckOutlined,
  CloseOutlined,
  CalculatorOutlined,
  EditOutlined
} from '@ant-design/icons'

const { Title, Text } = Typography
const { Option } = Select

const AdminSupplierManagement = () => {
  const [suppliers, setSuppliers] = useState([])
  const [depots, setDepots] = useState([])
  const [submissions, setSubmissions] = useState([])
  const [approvedData, setApprovedData] = useState([])
  const [depotEvaluations, setDepotEvaluations] = useState([])
  const [loading, setLoading] = useState(false)
  const [validationData, setValidationData] = useState(null)
  const [detailsModal, setDetailsModal] = useState({ visible: false, submission: null })
  const [criteriaWarningModal, setCriteriaWarningModal] = useState({ 
    visible: false, 
    type: null, // 'basic' or 'names'
    pendingConfig: null 
  })
  const [bwmConfig, setBwmConfig] = useState({ 
    numCriteria: 3, 
    criteriaNames: ['Criteria 1', 'Criteria 2', 'Criteria 3'],
    criteriaWeights: [1.0, 1.0, 1.0],
    supplierNames: [],
    bestCriterion: null,
    worstCriterion: null,
    bestToOthers: {},
    othersToWorst: {},
    consistencyRatio: null
  })
  const [newSupplierForm] = Form.useForm()
  const [newDepotForm] = Form.useForm()

  useEffect(() => {
    fetchSubmissions()
    fetchSuppliers()
    fetchDepots()
    fetchValidationData()
    fetchApprovedData()
    fetchSupplierEvaluations()
    
    // Load BWM config from localStorage
    const savedConfig = localStorage.getItem('bwmConfig')
    if (savedConfig) {
      const config = JSON.parse(savedConfig)
      // Ensure arrays exist and have correct length
      if (!config.criteriaNames || config.criteriaNames.length !== config.numCriteria) {
        config.criteriaNames = Array(config.numCriteria || 3).fill('').map((_, i) => `Criteria ${i + 1}`)
      }
      if (!config.criteriaWeights || config.criteriaWeights.length !== config.numCriteria) {
        config.criteriaWeights = Array(config.numCriteria || 3).fill(1.0)
      }
      // Initialize BWM-specific fields if not present
      if (!config.bestCriterion) config.bestCriterion = null
      if (!config.worstCriterion) config.worstCriterion = null
      if (!config.bestToOthers) config.bestToOthers = {}
      if (!config.othersToWorst) config.othersToWorst = {}
      if (!config.consistencyRatio) config.consistencyRatio = null
      // Don't override supplierNames from localStorage - we'll populate from database
      setBwmConfig(config)
    }
    
  }, [])

  const fetchSubmissions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/submissions/')
      const data = await response.json()
      setSubmissions(data.submissions || [])
    } catch (error) {
      console.error('Error fetching submissions:', error)
    }
  }

  const fetchSuppliers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/suppliers/')
      const data = await response.json()
      const supplierList = data.suppliers || []
      setSuppliers(supplierList)
      
      // Update BWM config with real supplier names
      const supplierNames = supplierList.map(supplier => supplier.name)
      setBwmConfig(prev => {
        const newConfig = { ...prev, supplierNames }
        localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
        
        // Trigger storage event for cross-component sync
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'bwmConfig',
          newValue: JSON.stringify(newConfig),
          storageArea: localStorage
        }))
        
        return newConfig
      })
    } catch (error) {
      console.error('Error fetching suppliers:', error)
    }
  }

  const fetchDepots = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/depots/')
      const data = await response.json()
      setDepots(data.depots || [])
    } catch (error) {
      console.error('Error fetching depots:', error)
    }
  }

  const fetchValidationData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/validation/check-data/')
      const data = await response.json()
      setValidationData(data)
    } catch (error) {
      console.error('Error fetching validation data:', error)
    }
  }

  const fetchApprovedData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/approved-data/')
      const data = await response.json()
      
      // Debug: Check for duplicates
      const approvedData = data.approved_data || []
      const submissionIds = approvedData.map(item => item.submission_id)
      const duplicates = submissionIds.filter((id, index) => submissionIds.indexOf(id) !== index)
      if (duplicates.length > 0) {
        console.warn('⚠️ Duplicate submission IDs found:', duplicates)
        console.warn('📊 Full data:', approvedData)
      }
      
      setApprovedData(approvedData)
    } catch (error) {
      console.error('Error fetching approved data:', error)
    }
  }

  const fetchSupplierEvaluations = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/supplier-evaluations/')
      const data = await response.json()
      setDepotEvaluations(data.evaluations || [])
    } catch (error) {
      console.error('Error fetching supplier evaluations:', error)
    }
  }

  const handleBulkApprove = async (supplierId) => {
    try {
      // Check for potential duplicates before approving
      const pendingSubmissions = submissions.filter(s => s.supplier_id === supplierId && s.status === 'pending')
      const alreadyApproved = approvedData.filter(a => a.supplier_id === supplierId)
      
      const duplicateDepots = pendingSubmissions.filter(pending => 
        alreadyApproved.some(approved => approved.depot_id === pending.depot_id)
      ).map(d => d.depot_name)
      
      if (duplicateDepots.length > 0) {
        message.warning(`⚠️ Duplicate detected: Supplier already has approved submissions for depot(s): ${duplicateDepots.join(', ')}. Please review manually.`)
        return
      }

      const response = await fetch('http://localhost:8000/api/admin/submissions/bulk-approve/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier_id: supplierId,
          approved_by: 'Admin'
        })
      })

      if (response.ok) {
        message.success('Complete supplier submission approved successfully')
        fetchValidationData()
        fetchApprovedData()
      } else {
        message.error('Failed to approve supplier submission')
      }
    } catch (error) {
      message.error('Error approving submissions')
    }
  }

  const handleBulkReject = async (supplierId) => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/submissions/bulk-reject/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier_id: supplierId,
          approved_by: 'Admin'
        })
      })

      if (response.ok) {
        message.success('Complete supplier submission rejected successfully')
        fetchValidationData()
        fetchApprovedData()
      } else {
        message.error('Failed to reject supplier submission')
      }
    } catch (error) {
      message.error('Error rejecting submissions')
    }
  }

  const createSupplier = async (values) => {
    try {
      const response = await fetch('http://localhost:8000/api/suppliers/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })

      if (response.ok) {
        message.success('Supplier created successfully')
        newSupplierForm.resetFields()
        fetchSuppliers()
      } else {
        message.error('Failed to create supplier')
      }
    } catch (error) {
      message.error('Error creating supplier')
    }
  }

  const createDepot = async (values) => {
    try {
      const response = await fetch('http://localhost:8000/api/depots/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })

      if (response.ok) {
        message.success('Depot created successfully')
        newDepotForm.resetFields()
        fetchDepots()
        fetchValidationData()
        fetchApprovedData()
      } else {
        message.error('Failed to create depot')
      }
    } catch (error) {
      message.error('Error creating depot')
    }
  }

  const handleCleanupDuplicates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/cleanup-duplicates/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        const result = await response.json()
        message.success(`${result.message}. Cleaned ${result.cleaned} duplicate submissions.`)
        fetchApprovedData()
        fetchSupplierEvaluations()
      } else {
        message.error('Failed to clean duplicates')
      }
    } catch (error) {
      message.error('Error cleaning duplicates')
    }
  }

  const getStatusTag = (status) => {
    const statusConfig = {
      'pending': { color: 'orange', icon: <ClockCircleOutlined /> },
      'approved': { color: 'green', icon: <CheckCircleOutlined /> },
      'rejected': { color: 'red', icon: <CloseCircleOutlined /> }
    }
    const config = statusConfig[status] || statusConfig['pending']
    return <Tag color={config.color} icon={config.icon}>{status.toUpperCase()}</Tag>
  }



  const ValidationStatus = () => (
    <Card title="Data Validation Status" extra={<BarChartOutlined />}>
      {validationData && (
        <>
          <Alert
            message={validationData.is_complete ? "All required data is complete" : "Some data is missing"}
            type={validationData.is_complete ? "success" : "warning"}
            showIcon
            style={{ marginBottom: '16px' }}
          />
          
          {validationData.missing_data && validationData.missing_data.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <Title level={5}>Missing Data:</Title>
              <ul>
                {validationData.missing_data.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          
          <Row gutter={16}>
            <Col span={8}>
              <Statistic title="Total Suppliers" value={validationData.statistics?.total_suppliers || 0} />
            </Col>
            <Col span={8}>
              <Statistic title="Total Depots" value={validationData.statistics?.total_depots || 0} />
            </Col>
            <Col span={8}>
              <Statistic 
                title="Coverage" 
                value={validationData.statistics?.coverage_percentage || 0} 
                suffix="%" 
                precision={1}
              />
            </Col>
          </Row>
        </>
      )}
    </Card>
  )

  const PendingSubmissionsGrouped = () => {
    const [loading, setLoading] = useState(true)
    const [pendingSubmissions, setPendingSubmissions] = useState([])
    const [groupedSubmissions, setGroupedSubmissions] = useState({})

    useEffect(() => {
      fetchPendingSubmissions()
    }, [])

    const fetchPendingSubmissions = async () => {
      try {
        setLoading(true)
        const response = await fetch('http://localhost:8000/api/admin/submissions/pending/')
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        
        // Ensure data is an array
        const submissions = Array.isArray(data) ? data : []
        setPendingSubmissions(submissions)
        
        // Group submissions by supplier
        const grouped = submissions.reduce((acc, submission) => {
          const supplierId = submission.supplier_id
          if (!acc[supplierId]) {
            acc[supplierId] = {
              supplier_name: submission.supplier_name,
              supplier_id: supplierId,
              submissions: []
            }
          }
          acc[supplierId].submissions.push(submission)
          return acc
        }, {})
        
        setGroupedSubmissions(grouped)
      } catch (error) {
        console.error('Error fetching pending submissions:', error)
        message.error('Failed to fetch pending submissions')
        setPendingSubmissions([])
        setGroupedSubmissions({})
      } finally {
        setLoading(false)
      }
    }

    const expandedRowRender = (record) => {
      const columns = [
        {
          title: 'Depot',
          dataIndex: 'depot_name',
          key: 'depot_name',
          width: 150,
        },
        {
          title: 'COC Rebate (R/L)',
          dataIndex: 'coc_rebate',
          key: 'coc_rebate',
          width: 120,
          render: (value) => value ? `R${parseFloat(value).toFixed(2)}` : 'N/A',
        },
        {
          title: 'Cost of Collection (R/L)',
          dataIndex: 'cost_of_collection',
          key: 'cost_of_collection',
          width: 150,
          render: (value) => value ? `R${parseFloat(value).toFixed(2)}` : 'N/A',
        },
        {
          title: 'DEL Rebate (R/L)',
          dataIndex: 'del_rebate',
          key: 'del_rebate',
          width: 120,
          render: (value) => value ? `R${parseFloat(value).toFixed(2)}` : 'N/A',
        },
        {
          title: 'Zone Differential',
          dataIndex: 'zone_differential',
          key: 'zone_differential',
          width: 120,
          render: (value) => value ? parseFloat(value).toFixed(2) : 'N/A',
        },
        {
          title: 'Distance (km)',
          dataIndex: 'distance_km',
          key: 'distance_km',
          width: 100,
          render: (value) => value ? `${parseFloat(value).toFixed(1)} km` : 'N/A',
        },
        {
          title: 'Submitted At',
          dataIndex: 'submitted_at',
          key: 'submitted_at',
          width: 150,
          render: (value) => new Date(value).toLocaleString(),
        }
      ]

      return (
        <div style={{ padding: '16px', backgroundColor: '#fafafa' }}>
          <Alert
            message="Review all depot data below. Use the bulk actions above to approve or reject the entire submission."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={columns}
            dataSource={record.submissions}
            pagination={false}
            rowKey={(submission) => `${submission.id || submission.supplier_id}-${submission.depot_id}-${submission.submitted_at}`}
            size="small"
            scroll={{ x: 800 }}
          />
        </div>
      )
    }

    const mainColumns = [
      {
        title: 'Supplier',
        dataIndex: 'supplier_name',
        key: 'supplier_name',
        width: 200,
      },
      {
        title: 'Depots Submitted',
        key: 'submissions_count',
        width: 150,
        render: (_, record) => (
          <div style={{ textAlign: 'center' }}>
            <Badge count={record.submissions.length} style={{ backgroundColor: '#1890ff' }} />
            <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
              {record.submissions.length} depot{record.submissions.length !== 1 ? 's' : ''}
            </div>
          </div>
        ),
      },
      {
        title: 'Submission Date',
        key: 'submitted_at',
        width: 180,
        render: (_, record) => {
          const latestSubmission = record.submissions.reduce((latest, current) => 
            new Date(current.submitted_at) > new Date(latest.submitted_at) ? current : latest
          )
          return (
            <div>
              <div>{new Date(latestSubmission.submitted_at).toLocaleDateString()}</div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {new Date(latestSubmission.submitted_at).toLocaleTimeString()}
              </div>
            </div>
          )
        },
      },
      {
        title: 'Submission Status',
        key: 'status',
        width: 120,
        render: (_, record) => (
          <Tag color="orange" icon={<ClockCircleOutlined />}>
            PENDING
          </Tag>
        ),
      },
      {
        title: 'Review & Approve',
        key: 'bulk_actions',
        width: 250,
        render: (_, record) => (
          <Space direction="vertical" size="small">
            <Popconfirm
              title={`Approve entire submission for ${record.supplier_name}?`}
              description={`This will approve all ${record.submissions.length} depot submissions at once.`}
              onConfirm={() => {
                handleBulkApprove(record.supplier_id)
                fetchPendingSubmissions()
              }}
              okText="Approve All"
              cancelText="Cancel"
              okButtonProps={{ type: 'primary' }}
            >
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                block
              >
                Approve Entire Submission
              </Button>
            </Popconfirm>
            <Popconfirm
              title={`Reject entire submission for ${record.supplier_name}?`}
              description={`This will reject all ${record.submissions.length} depot submissions at once.`}
              onConfirm={() => {
                handleBulkReject(record.supplier_id)
                fetchPendingSubmissions()
              }}
              okText="Reject All"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
            >
              <Button
                danger
                size="small"
                icon={<CloseOutlined />}
                block
              >
                Reject Entire Submission
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ]

    const dataSource = Object.values(groupedSubmissions)

    return (
      <Card 
        title="Pending Supplier Submissions" 
        extra={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge count={pendingSubmissions.length} style={{ backgroundColor: '#fa8c16' }} />
            <span style={{ fontSize: '12px', color: '#666' }}>
              {pendingSubmissions.length} depot{pendingSubmissions.length !== 1 ? 's' : ''} pending
            </span>
          </div>
        }
      >
        <Alert
          message="Whole Submission Approval"
          description="Each row represents a complete supplier submission containing data for all their depots. Approve or reject the entire submission as a unit. Click the expand button to review individual depot data."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Table
          dataSource={dataSource}
          columns={mainColumns}
          rowKey="supplier_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender,
            rowExpandable: (record) => record.submissions.length > 0,
            expandIcon: ({ expanded, onExpand, record }) => (
              <Button
                type="text"
                size="small"
                icon={expanded ? <CloseOutlined /> : <EyeOutlined />}
                onClick={(e) => onExpand(record, e)}
              >
                {expanded ? 'Hide' : 'Review'} Details
              </Button>
            ),
          }}
        />
      </Card>
    )
  }

  const ManagementForms = () => (
    <Row gutter={16}>
      <Col span={12}>
        <Card title="Add New Supplier" extra={<UserOutlined />}>
          <Form form={newSupplierForm} onFinish={createSupplier} layout="vertical">
            <Form.Item
              name="name"
              label="Supplier Name"
              rules={[{ required: true, message: 'Please enter supplier name' }]}
            >
              <Input placeholder="Enter supplier name" />
            </Form.Item>
            <Form.Item
              name="email"
              label="Email"
              rules={[{ type: 'email', message: 'Please enter a valid email' }]}
            >
              <Input placeholder="Enter email (optional)" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                Create Supplier
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>
      <Col span={12}>
        <Card title="Add New Depot" extra={<HomeOutlined />}>
          <Form form={newDepotForm} onFinish={createDepot} layout="vertical">
            <Form.Item
              name="name"
              label="Site Name"
              rules={[{ required: true, message: 'Please enter site name' }]}
            >
              <Input placeholder="Enter site name" />
            </Form.Item>
            <Form.Item
              name="country"
              label="Country"
              rules={[{ required: true, message: 'Please enter country' }]}
            >
              <Input placeholder="Enter country" />
            </Form.Item>
            <Form.Item
              name="town"
              label="Town"
              rules={[{ required: true, message: 'Please enter town' }]}
            >
              <Input placeholder="Enter town" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="lats"
                  label="Latitude"
                  rules={[{ required: true, message: 'Please enter latitude' }]}
                >
                  <InputNumber 
                    placeholder="Enter latitude" 
                    style={{ width: '100%' }}
                    step={0.000001}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="longs"
                  label="Longitude"
                  rules={[{ required: true, message: 'Please enter longitude' }]}
                >
                  <InputNumber 
                    placeholder="Enter longitude" 
                    style={{ width: '100%' }}
                    step={0.000001}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="fuel_zone"
              label="Fuel Zone"
              rules={[{ required: true, message: 'Please enter fuel zone' }]}
            >
              <Input placeholder="Enter fuel zone" />
            </Form.Item>
            <Form.Item
              name="tankage_size"
              label="Tankage Size (LT)"
              rules={[{ required: true, message: 'Please enter tankage size' }]}
            >
              <InputNumber 
                placeholder="Enter tankage size" 
                style={{ width: '100%' }}
                min={0}
              />
            </Form.Item>
            <Form.Item
              name="number_of_pumps"
              label="Number of Pumps"
              rules={[{ required: true, message: 'Please enter number of pumps' }]}
            >
              <InputNumber 
                placeholder="Enter number of pumps" 
                style={{ width: '100%' }}
                min={0}
              />
            </Form.Item>
            <Form.Item
              name="annual_volume"
              label="Annual Volume (LT)"
              rules={[{ required: true, message: 'Please enter annual volume' }]}
            >
              <InputNumber 
                placeholder="Enter annual volume" 
                style={{ width: '100%' }}
                min={0}
              />
            </Form.Item>
            <Form.Item
              name="equipment_value"
              label="Equipment Value - Estimate"
              rules={[{ required: true, message: 'Please enter equipment value' }]}
            >
              <InputNumber 
                placeholder="Enter equipment value" 
                style={{ width: '100%' }}
                min={0}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                Create Depot
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>
    </Row>
  )

  const ApprovedData = () => {
    const columns = [
      {
        title: 'Supplier',
        dataIndex: 'supplier_name',
        key: 'supplier_name',
        sorter: (a, b) => a.supplier_name.localeCompare(b.supplier_name),
      },
      {
        title: 'Depot',
        dataIndex: 'depot_name',
        key: 'depot_name',
        sorter: (a, b) => a.depot_name.localeCompare(b.depot_name),
      },
      {
        title: 'Annual Volume',
        dataIndex: 'annual_volume',
        key: 'annual_volume',
        render: (value) => value ? `${value.toLocaleString()} tons` : 'N/A',
        sorter: (a, b) => (a.annual_volume || 0) - (b.annual_volume || 0),
      },
      {
        title: 'CoC Rebate',
        dataIndex: 'coc_rebate',
        key: 'coc_rebate',
        render: (value) => value !== null ? `R${value}` : 'N/A',
        sorter: (a, b) => (a.coc_rebate || 0) - (b.coc_rebate || 0),
      },
      {
        title: 'Cost of Collection',
        dataIndex: 'cost_of_collection',
        key: 'cost_of_collection',
        render: (value) => value !== null ? `R${value}` : 'N/A',
        sorter: (a, b) => (a.cost_of_collection || 0) - (b.cost_of_collection || 0),
      },
      {
        title: 'Delivery Rebate',
        dataIndex: 'del_rebate',
        key: 'del_rebate',
        render: (value) => value !== null ? `R${value}` : 'N/A',
        sorter: (a, b) => (a.del_rebate || 0) - (b.del_rebate || 0),
      },
      {
        title: 'Zone Differential',
        dataIndex: 'zone_differential',
        key: 'zone_differential',
        render: (value) => `R${value}`,
        sorter: (a, b) => a.zone_differential - b.zone_differential,
      },
      {
        title: 'Distance (km)',
        dataIndex: 'distance_km',
        key: 'distance_km',
        render: (value) => value !== null ? `${value} km` : 'N/A',
        sorter: (a, b) => (a.distance_km || 0) - (b.distance_km || 0),
      },
      {
        title: 'Supplier Score',
        dataIndex: 'total_score',
        key: 'total_score',
        render: (value) => value !== null ? value.toFixed(3) : 'No Score',
        sorter: (a, b) => (a.total_score || 0) - (b.total_score || 0),
      },
      {
        title: 'Approved Date',
        dataIndex: 'approved_at',
        key: 'approved_at',
        render: (value) => new Date(value).toLocaleDateString(),
        sorter: (a, b) => new Date(a.approved_at) - new Date(b.approved_at),
      },
      {
        title: 'Approved By',
        dataIndex: 'approved_by',
        key: 'approved_by',
      }
    ]

    return (
      <Card 
        title="Approved Optimization Data" 
        extra={
          <div>
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              onClick={handleCleanupDuplicates}
              style={{ marginRight: 8 }}
              size="small"
            >
              Clean Duplicates
            </Button>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          </div>
        }
      >
        <Alert
          message={`${approvedData.length} approved supplier-depot combinations ready for optimization`}
          type="success"
          style={{ marginBottom: 16 }}
          showIcon
        />
        <Table
          columns={columns}
          dataSource={approvedData}
          rowKey={(record) => {
            // Use submission_id with additional unique fields to handle duplicates
            if (record.submission_id) {
              return `submission-${record.submission_id}-${record.supplier_id}-${record.depot_id}`;
            }
            // For records without submission_id, use composite key with timestamp
            return `${record.supplier_id || 'unknown'}-${record.depot_id || 'unknown'}-${record.submitted_at || record.approved_at || Math.random()}`;
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `Total ${total} items`
          }}
          scroll={{ x: 1200 }}
          size="small"
        />
      </Card>
    )
  }

  const DepotEvaluations = () => {
    const columns = [
      {
        title: 'Depot',
        dataIndex: 'depot_name',
        key: 'depot_name',
        sorter: (a, b) => a.depot_name.localeCompare(b.depot_name),
      },
      {
        title: 'Supplier',
        dataIndex: 'supplier_name',
        key: 'supplier_name',
        sorter: (a, b) => a.supplier_name.localeCompare(b.supplier_name),
      },
      {
        title: 'Criterion',
        dataIndex: 'criterion_name',
        key: 'criterion_name',
        sorter: (a, b) => a.criterion_name.localeCompare(b.criterion_name),
      },
      {
        title: 'Score',
        dataIndex: 'score',
        key: 'score',
        render: (value) => (
          <Tag color={value >= 7 ? 'green' : value >= 5 ? 'orange' : 'red'}>
            {value.toFixed(1)}
          </Tag>
        ),
        sorter: (a, b) => a.score - b.score,
      },
      {
        title: 'Manager',
        dataIndex: 'manager_name',
        key: 'manager_name',
        render: (value) => value || 'N/A',
      },
      {
        title: 'Submitted',
        dataIndex: 'submitted_at',
        key: 'submitted_at',
        render: (value) => new Date(value).toLocaleDateString(),
        sorter: (a, b) => new Date(a.submitted_at) - new Date(b.submitted_at),
      }
    ]

    return (
      <Card 
        title="Depot Manager Evaluations" 
        extra={
          <div>
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={fetchSupplierEvaluations}
              style={{ marginRight: 8 }}
              size="small"
            >
              Refresh
            </Button>
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: 'Clear All Depot Evaluations',
                  content: (
                    <div>
                      <p>⚠️ <strong>This will permanently delete all depot evaluations!</strong></p>
                      <p>This action cannot be undone. All supplier scoring data from depot managers will be lost.</p>
                      <p>Are you sure you want to proceed?</p>
                    </div>
                  ),
                  okText: 'Yes, Clear All',
                  cancelText: 'Cancel',
                  okType: 'danger',
                  onOk: async () => {
                    await clearSupplierEvaluations()
                  }
                })
              }}
              style={{ marginRight: 8 }}
              size="small"
            >
              Clear All
            </Button>
            <UserOutlined style={{ color: '#1890ff' }} />
          </div>
        }
      >
        <Alert
          message={`${depotEvaluations.length} depot evaluations submitted for PROMETHEE II analysis`}
          type="info"
          style={{ marginBottom: 16 }}
          showIcon
        />
        <Table
          columns={columns}
          dataSource={depotEvaluations}
          rowKey={(record) => `eval-${record.depot_id}-${record.supplier_id}-${record.criterion_name}`}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `Total ${total} evaluations`
          }}
          scroll={{ x: 800 }}
          size="small"
        />
      </Card>
    )
  }

  const confirmCriteriaUpdate = async () => {
    try {
      setLoading(true)
      
      const { pendingConfig, type } = criteriaWarningModal
      
      // Call backend API to clear evaluations and update criteria
      const response = await fetch('http://localhost:8000/api/criteria/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          old_criteria_names: bwmConfig.criteriaNames,
          new_criteria_names: pendingConfig.criteriaNames,
          default_score: 5.0
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to update criteria configuration')
      }
      
      const result = await response.json()
      
      // Update config with new values
      const newConfig = {
        ...bwmConfig,
        numCriteria: pendingConfig.numCriteria,
        criteriaNames: pendingConfig.criteriaNames,
        criteriaWeights: Array(pendingConfig.numCriteria).fill(1.0),
        // Reset BWM-specific values when changing criteria
        bestCriterion: null,
        worstCriterion: null,
        bestToOthers: {},
        othersToWorst: {},
        consistencyRatio: null
      }
      
      setBwmConfig(newConfig)
      localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
      
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'bwmConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      // Close modal
      setCriteriaWarningModal({ visible: false, type: null, pendingConfig: null })
      setIsShowingModal(false)
      
      message.success(`Criteria configuration updated successfully! ${result.message}`)
      
      // Refresh evaluations to show cleared data
      fetchSupplierEvaluations()
      
    } catch (error) {
      console.error('Error updating criteria:', error)
      message.error('Failed to update criteria configuration. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const BWMConfiguration = () => {
    // Removed excessive logging to reduce console noise
    
    // Temporary state for form inputs
    const [tempConfig, setTempConfig] = useState({
      numCriteria: bwmConfig.numCriteria
    })
    const [tempCriteriaNames, setTempCriteriaNames] = useState([...bwmConfig.criteriaNames])
    const [tempBestCriterion, setTempBestCriterion] = useState(bwmConfig.bestCriterion)
    const [tempWorstCriterion, setTempWorstCriterion] = useState(bwmConfig.worstCriterion)
    const [tempBestToOthers, setTempBestToOthers] = useState({...bwmConfig.bestToOthers})
    const [tempOthersToWorst, setTempOthersToWorst] = useState({...bwmConfig.othersToWorst})
    const [bwmLoading, setBwmLoading] = useState(false)
    const [savedBwmWeights, setSavedBwmWeights] = useState(null)
    const [isShowingModal, setIsShowingModal] = useState(false)
    
    
    // Update temp state when bwmConfig changes (but not when warning modal is showing)
    useEffect(() => {
      // Don't reset temp state if warning modal is visible or about to be shown
      if (criteriaWarningModal.visible || isShowingModal) {
        return
      }
      
      setTempConfig({
        numCriteria: bwmConfig.numCriteria
      })
      setTempCriteriaNames([...bwmConfig.criteriaNames])
      setTempBestCriterion(bwmConfig.bestCriterion)
      setTempWorstCriterion(bwmConfig.worstCriterion)
      setTempBestToOthers({...bwmConfig.bestToOthers})
      setTempOthersToWorst({...bwmConfig.othersToWorst})
    }, [bwmConfig, criteriaWarningModal.visible, isShowingModal])
    
    // Load saved BWM weights from backend
    const loadSavedBwmWeights = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/bwm/weights/')
        const data = await response.json()
        
        if (response.ok && data.success && data.data) {
          setSavedBwmWeights(data.data)
        } else {
          setSavedBwmWeights(null)
        }
      } catch (error) {
        console.error('Error loading saved BWM weights:', error)
        setSavedBwmWeights(null)
      }
    }
    
    // Load saved weights on component mount
    useEffect(() => {
      loadSavedBwmWeights()
    }, [])
    
    const clearSupplierEvaluations = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/supplier-evaluations/clear', {
          method: 'DELETE'
        })
        const result = await response.json()
        
        if (response.ok) {
          message.success(`${result.cleared_count} supplier evaluations cleared successfully!`)
          fetchSupplierEvaluations() // Refresh the supplier evaluations list
        } else {
          throw new Error(result.detail || 'Failed to clear evaluations')
        }
      } catch (error) {
        console.error('Error clearing depot evaluations:', error)
        message.error('Failed to clear depot evaluations')
      }
    }
    
    const updateBasicConfig = () => {
      console.log('updateBasicConfig called, tempConfig:', tempConfig)
      console.log('Current criteriaWarningModal state:', criteriaWarningModal)
      
      // Set flag to prevent state resets
      setIsShowingModal(true)
      
      // Show warning modal with pending configuration
      // Preserve existing criteria names and only add new ones if increasing
      const newNames = Array(tempConfig.numCriteria).fill('').map((_, i) => {
        if (i < tempCriteriaNames.length && tempCriteriaNames[i]) {
          return tempCriteriaNames[i] // Keep existing name
        } else {
          return `Criteria ${i + 1}` // Add default name for new criteria
        }
      })
      const pendingConfig = {
        numCriteria: tempConfig.numCriteria,
        criteriaNames: newNames
      }
      
      console.log('Setting criteriaWarningModal to:', {
        visible: true,
        type: 'basic',
        pendingConfig
      })
      
      setCriteriaWarningModal({
        visible: true,
        type: 'basic',
        pendingConfig
      })
    }
    
    const updateCriteriaNamesInternal = () => {
      console.log('updateCriteriaNames called:', tempCriteriaNames)
      console.log('Current criteriaWarningModal state:', criteriaWarningModal)
      
      // Set flag to prevent state resets
      setIsShowingModal(true)
      
      // Show warning modal with pending configuration
      const pendingConfig = {
        numCriteria: bwmConfig.numCriteria,
        criteriaNames: tempCriteriaNames
      }
      
      console.log('Setting criteriaWarningModal to:', {
        visible: true,
        type: 'names',
        pendingConfig
      })
      
      setCriteriaWarningModal({
        visible: true,
        type: 'names',
        pendingConfig
      })
    }
    
    const calculateBWMWeights = async () => {
      console.log('🚀 BWM CALCULATION & SAVE STARTED')
      
      if (!tempBestCriterion || !tempWorstCriterion) {
        message.error('Please select both best and worst criteria')
        return
      }
      
      if (tempBestCriterion === tempWorstCriterion) {
        message.error('Best and worst criteria must be different')
        return
      }
      
      // Check if all comparisons are filled
      const missingBestToOthers = tempCriteriaNames.some(criterion => 
        criterion !== tempBestCriterion && !tempBestToOthers[criterion]
      )
      const missingOthersToWorst = tempCriteriaNames.some(criterion => 
        criterion !== tempWorstCriterion && !tempOthersToWorst[criterion]
      )
      
      if (missingBestToOthers || missingOthersToWorst) {
        message.error('Please fill in all comparison values')
        return
      }
      
      setBwmLoading(true)
      
      try {
        // Step 1: Calculate BWM weights
        const calculateResponse = await fetch('http://localhost:8000/api/bwm/calculate/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            criteria: tempCriteriaNames,
            best_criterion: tempBestCriterion,
            worst_criterion: tempWorstCriterion,
            best_to_others: tempBestToOthers,
            others_to_worst: tempOthersToWorst
          })
        })
        
        if (!calculateResponse.ok) {
          throw new Error('Failed to calculate BWM weights')
        }
        
        const calculateData = await calculateResponse.json()
        
        if (!calculateData.success || !calculateData.data) {
          throw new Error('Invalid response from BWM calculation')
        }
        
        console.log('BWM calculation successful:', calculateData.data)
        
        // Step 2: Save weights to database immediately
        const saveResponse = await fetch('http://localhost:8000/api/bwm/save/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            criteria_names: tempCriteriaNames,
            weights: calculateData.data.weights,
            best_criterion: tempBestCriterion,
            worst_criterion: tempWorstCriterion,
            best_to_others: tempBestToOthers,
            others_to_worst: tempOthersToWorst,
            consistency_ratio: calculateData.data.consistency_ratio,
            consistency_interpretation: calculateData.data.consistency_interpretation,
            created_by: 'admin'
          })
        })
        
        if (!saveResponse.ok) {
          throw new Error('Failed to save BWM weights to database')
        }
        
        const saveData = await saveResponse.json()
        console.log('BWM weights saved to database:', saveData)
        
        // Update the config with calculated weights
        const newConfig = {
          ...bwmConfig,
          criteriaWeights: tempCriteriaNames.map(name => calculateData.data.weights[name]),
          bestCriterion: tempBestCriterion,
          worstCriterion: tempWorstCriterion,
          bestToOthers: tempBestToOthers,
          othersToWorst: tempOthersToWorst,
          consistencyRatio: calculateData.data.consistency_ratio
        }
        
        setBwmConfig(newConfig)
        localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
        
        // Trigger storage event for cross-component sync
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'bwmConfig',
          newValue: JSON.stringify(newConfig),
          storageArea: localStorage
        }))
        
        const consistencyText = calculateData.data.consistency_ratio <= 0.1 ? 'excellent' : 
                              calculateData.data.consistency_ratio <= 0.2 ? 'good' : 'acceptable'
        
        message.success(
          `BWM weights calculated and saved successfully! Consistency: ${consistencyText} (${calculateData.data.consistency_ratio.toFixed(4)})`
        )
        
        // Refresh the saved weights display
        loadSavedBwmWeights()
        
      } catch (error) {
        console.error('Error in BWM calculation/save:', error)
        message.error(`Failed to calculate and save BWM weights: ${error.message}`)
      } finally {
        setBwmLoading(false)
      }
    }
    
    
    return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="Step 1: Basic Configuration" extra={<SettingOutlined />}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>Number of Criteria:</Text>
            <InputNumber
              min={2}
              max={10}
              value={tempConfig.numCriteria}
              onChange={(value) => setTempConfig({ ...tempConfig, numCriteria: value })}
              style={{ marginLeft: '10px' }}
            />
          </div>
          <Button type="primary" onClick={updateBasicConfig}>
            Update Basic Configuration
          </Button>
        </Space>
      </Card>

      <Card title="Step 2: Criteria Names" extra={<EditOutlined />}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>Criteria Names:</Text>
            <div style={{ marginTop: '10px' }}>
              {tempCriteriaNames.map((name, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <Text>{`Criteria ${index + 1}:`}</Text>
                  <Input
                    value={name}
                    onChange={(e) => {
                      const newNames = [...tempCriteriaNames]
                      newNames[index] = e.target.value
                      setTempCriteriaNames(newNames)
                    }}
                    placeholder={`Enter name for criteria ${index + 1}`}
                    style={{ marginLeft: '10px', width: '300px' }}
                  />
                </div>
              ))}
            </div>
          </div>
          <Button type="primary" onClick={updateCriteriaNamesInternal}>
            Update Criteria Names
          </Button>
        </Space>
      </Card>

      <Card title="Step 3: Best-Worst Method Comparisons" extra={<BarChartOutlined />}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Alert
            message="Best-Worst Method Instructions"
            description="BWM requires fewer comparisons than AHP. Select the most important (best) and least important (worst) criteria, then compare them with others using a 1-9 scale."
            type="info"
            showIcon
          />
          
          <Row gutter={16}>
            <Col span={12}>
              <div>
                <Text strong>Best Criterion (Most Important):</Text>
                <Select
                  value={tempBestCriterion}
                  onChange={setTempBestCriterion}
                  style={{ width: '100%', marginTop: '8px' }}
                  placeholder="Select the most important criterion"
                >
                  {tempCriteriaNames.map(name => (
                    <Option key={name} value={name}>{name}</Option>
                  ))}
                </Select>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <Text strong>Worst Criterion (Least Important):</Text>
                <Select
                  value={tempWorstCriterion}
                  onChange={setTempWorstCriterion}
                  style={{ width: '100%', marginTop: '8px' }}
                  placeholder="Select the least important criterion"
                >
                  {tempCriteriaNames.map(name => (
                    <Option key={name} value={name}>{name}</Option>
                  ))}
                </Select>
              </div>
            </Col>
          </Row>
          
          {tempBestCriterion && (
            <div>
              <Text strong>Best-to-Others Comparisons:</Text>
              <Text type="secondary" style={{ display: 'block', marginBottom: '10px' }}>
                How much more important is "{tempBestCriterion}" compared to each other criterion?
              </Text>
              {tempCriteriaNames.filter(name => name !== tempBestCriterion).map(name => (
                <div key={name} style={{ marginBottom: '8px' }}>
                  <Text>{`${tempBestCriterion} vs ${name}:`}</Text>
                  <InputNumber
                    min={1}
                    max={9}
                    value={tempBestToOthers[name]}
                    onChange={(value) => setTempBestToOthers({
                      ...tempBestToOthers,
                      [name]: value
                    })}
                    style={{ marginLeft: '10px', width: '100px' }}
                    placeholder="1-9"
                  />
                  <Text type="secondary" style={{ marginLeft: '10px' }}>
                    (1=equal, 9=extremely more important)
                  </Text>
                </div>
              ))}
            </div>
          )}
          
          {tempWorstCriterion && (
            <div>
              <Text strong>Others-to-Worst Comparisons:</Text>
              <Text type="secondary" style={{ display: 'block', marginBottom: '10px' }}>
                How much more important is each criterion compared to "{tempWorstCriterion}"?
              </Text>
              {tempCriteriaNames.filter(name => name !== tempWorstCriterion).map(name => (
                <div key={name} style={{ marginBottom: '8px' }}>
                  <Text>{`${name} vs ${tempWorstCriterion}:`}</Text>
                  <InputNumber
                    min={1}
                    max={9}
                    value={tempOthersToWorst[name]}
                    onChange={(value) => setTempOthersToWorst({
                      ...tempOthersToWorst,
                      [name]: value
                    })}
                    style={{ marginLeft: '10px', width: '100px' }}
                    placeholder="1-9"
                  />
                  <Text type="secondary" style={{ marginLeft: '10px' }}>
                    (1=equal, 9=extremely more important)
                  </Text>
                </div>
              ))}
            </div>
          )}
          
          <Button type="primary" onClick={calculateBWMWeights} loading={bwmLoading}>
            Calculate BWM Weights
          </Button>
        </Space>
      </Card>

      {savedBwmWeights && (
        <Card title="Current Saved BWM Weights" extra={<CheckCircleOutlined style={{ color: '#52c41a' }} />}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Weights: </Text>
              {savedBwmWeights.criteria_names.map((name, index) => (
                <Tag key={index} color="blue" style={{ margin: '2px' }}>
                  {name}: {savedBwmWeights.weights[name].toFixed(4)}
                </Tag>
              ))}
            </div>
            
            <div>
              <Text strong>Consistency: </Text>
              <Tag color={savedBwmWeights.consistency_ratio <= 0.1 ? 'green' : savedBwmWeights.consistency_ratio <= 0.2 ? 'orange' : 'red'}>
                {savedBwmWeights.consistency_ratio.toFixed(4)} - {savedBwmWeights.consistency_interpretation}
              </Tag>
            </div>
            
            <div>
              <Text strong>Created: </Text>
              <Text type="secondary">
                {new Date(savedBwmWeights.created_at).toLocaleString()} by {savedBwmWeights.created_by}
              </Text>
            </div>
            
            <Alert
              message="These are the weights currently used in PROMETHEE II calculations"
              type="info"
              showIcon
              style={{ marginTop: '8px' }}
            />
          </Space>
        </Card>
      )}

    </Space>
    )
  }

  return (
    <div>
      <Tabs
        defaultActiveKey="pending"
        items={[
          {
            key: 'pending',
            label: (
              <span>
                <ClockCircleOutlined />
                Pending Submissions
              </span>
            ),
            children: <PendingSubmissionsGrouped />
          },
          {
            key: 'approved',
            label: (
              <span>
                <CheckCircleOutlined />
                Approved Data
              </span>
            ),
            children: <ApprovedData />
          },
          {
            key: 'evaluations',
            label: (
              <span>
                <UserOutlined />
                Depot Evaluations
              </span>
            ),
            children: <DepotEvaluations />
          },
          {
            key: 'validation',
            label: (
              <span>
                <BarChartOutlined />
                Validation
              </span>
            ),
            children: <ValidationStatus />
          },
          {
            key: 'bwm-config',
            label: (
              <span>
                <SettingOutlined />
                BWM Configuration
              </span>
            ),
            children: <BWMConfiguration />
          },
          {
            key: 'management',
            label: (
              <span>
                <PlusOutlined />
                Management
              </span>
            ),
            children: <ManagementForms />
          }
        ]}
      />

      <Modal
        title="Submission Details"
        open={detailsModal.visible}
        onCancel={() => setDetailsModal({ visible: false, submission: null })}
        footer={null}
        width={700}
      >
        {detailsModal.submission && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="Supplier" span={2}>
                {detailsModal.submission.supplier_name}
              </Descriptions.Item>
              <Descriptions.Item label="Depot" span={2}>
                {detailsModal.submission.depot_name}
              </Descriptions.Item>
              <Descriptions.Item label="COC Rebate (R/L)">
                {detailsModal.submission.coc_rebate !== null ? `R${detailsModal.submission.coc_rebate}` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Collection Cost (R/L)">
                {detailsModal.submission.cost_of_collection !== null ? `R${detailsModal.submission.cost_of_collection}` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="DEL Rebate (R/L)">
                {detailsModal.submission.del_rebate !== null ? `R${detailsModal.submission.del_rebate}` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Zone Differential">
                {detailsModal.submission.zone_differential}
              </Descriptions.Item>
              <Descriptions.Item label="Distance (Km)">
                {detailsModal.submission.distance_km !== null ? `${detailsModal.submission.distance_km} km` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                {getStatusTag(detailsModal.submission.status)}
              </Descriptions.Item>
            </Descriptions>
            
            <Divider />
            
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Submitted At">
                {new Date(detailsModal.submission.submitted_at).toLocaleString()}
              </Descriptions.Item>
              {detailsModal.submission.approved_at && (
                <Descriptions.Item label="Approved At">
                  {new Date(detailsModal.submission.approved_at).toLocaleString()}
                </Descriptions.Item>
              )}
              {detailsModal.submission.approved_by && (
                <Descriptions.Item label="Approved By">
                  {detailsModal.submission.approved_by}
                </Descriptions.Item>
              )}
            </Descriptions>
            
            {detailsModal.submission.status === 'pending' && (
              <div style={{ marginTop: '16px', textAlign: 'right' }}>
                <Space>
                  <Button 
                    type="primary" 
                    icon={<CheckCircleOutlined />}
                    onClick={() => {
                      handleApprove(detailsModal.submission.id)
                      setDetailsModal({ visible: false, submission: null })
                    }}
                  >
                    Approve
                  </Button>
                  <Button 
                    danger 
                    icon={<CloseCircleOutlined />}
                    onClick={() => {
                      handleReject(detailsModal.submission.id)
                      setDetailsModal({ visible: false, submission: null })
                    }}
                  >
                    Reject
                  </Button>
                </Space>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Criteria Update Warning Modal */}
      <Modal
        title={
          <div style={{ color: '#ff4d4f' }}>
            <CloseCircleOutlined style={{ marginRight: 8 }} />
            ⚠️ Warning: This will clear all depot evaluations
          </div>
        }
        open={criteriaWarningModal.visible}
        onCancel={() => {
          setCriteriaWarningModal({ visible: false, type: null, pendingConfig: null })
          setIsShowingModal(false)
        }}
        footer={[
          <Button 
            key="cancel" 
            onClick={() => {
              setCriteriaWarningModal({ visible: false, type: null, pendingConfig: null })
              setIsShowingModal(false)
            }}
          >
            Cancel
          </Button>,
          <Button 
            key="confirm" 
            type="primary" 
            danger
            loading={loading}
            onClick={confirmCriteriaUpdate}
          >
            Yes, Clear and Update
          </Button>
        ]}
        width={600}
      >
        <div style={{ padding: '16px 0' }}>
          <Alert
            message="Important: This action cannot be undone"
            description={
              <div>
                <p><strong>What will happen:</strong></p>
                <ul style={{ paddingLeft: '20px', margin: '8px 0' }}>
                  <li>All existing depot manager evaluations will be permanently deleted</li>
                  <li>Criteria configuration will be updated</li>
                  <li>Depot managers will need to re-evaluate all suppliers with the new criteria</li>
                  <li>PROMETHEE II rankings will be reset</li>
                </ul>
                
                {criteriaWarningModal.pendingConfig && (
                  <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                    <p><strong>New Configuration:</strong></p>
                    <p>Number of Criteria: <strong>{criteriaWarningModal.pendingConfig.numCriteria}</strong></p>
                    <p>Criteria Names:</p>
                    <ul style={{ paddingLeft: '20px', margin: '4px 0' }}>
                      {criteriaWarningModal.pendingConfig.criteriaNames?.map((name, index) => (
                        <li key={index}><strong>{name}</strong></li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            }
            type="warning"
            showIcon
            style={{ marginBottom: '16px' }}
          />
          
          <div style={{ textAlign: 'center', fontSize: '16px', fontWeight: 'bold', color: '#ff4d4f' }}>
            Are you sure you want to proceed?
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default AdminSupplierManagement