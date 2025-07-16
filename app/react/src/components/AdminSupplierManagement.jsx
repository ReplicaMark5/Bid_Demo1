import React, { useState, useEffect } from 'react'
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
  CalculatorOutlined
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
  const [ahpConfig, setAhpConfig] = useState({ 
    numCriteria: 3, 
    criteriaNames: ['Criteria 1', 'Criteria 2', 'Criteria 3'],
    criteriaWeights: [1.0, 1.0, 1.0],
    supplierNames: []
  })
  const [newSupplierForm] = Form.useForm()
  const [newDepotForm] = Form.useForm()

  useEffect(() => {
    fetchSubmissions()
    fetchSuppliers()
    fetchDepots()
    fetchValidationData()
    fetchApprovedData()
    fetchDepotEvaluations()
    
    // Load AHP config from localStorage
    const savedConfig = localStorage.getItem('ahpConfig')
    if (savedConfig) {
      const config = JSON.parse(savedConfig)
      // Ensure arrays exist and have correct length
      if (!config.criteriaNames || config.criteriaNames.length !== config.numCriteria) {
        config.criteriaNames = Array(config.numCriteria || 3).fill('').map((_, i) => `Criteria ${i + 1}`)
      }
      if (!config.criteriaWeights || config.criteriaWeights.length !== config.numCriteria) {
        config.criteriaWeights = Array(config.numCriteria || 3).fill(1.0)
      }
      // Don't override supplierNames from localStorage - we'll populate from database
      setAhpConfig(config)
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
      
      // Update AHP config with real supplier names
      const supplierNames = supplierList.map(supplier => supplier.name)
      setAhpConfig(prev => {
        const newConfig = { ...prev, supplierNames }
        localStorage.setItem('ahpConfig', JSON.stringify(newConfig))
        
        // Trigger storage event for cross-component sync
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'ahpConfig',
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

  const fetchDepotEvaluations = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/depot-evaluations/')
      const data = await response.json()
      setDepotEvaluations(data.evaluations || [])
    } catch (error) {
      console.error('Error fetching depot evaluations:', error)
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
        fetchDepotEvaluations()
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
              label="Depot Name"
              rules={[{ required: true, message: 'Please enter depot name' }]}
            >
              <Input placeholder="Enter depot name" />
            </Form.Item>
            <Form.Item
              name="annual_volume"
              label="Annual Volume (Litres)"
              rules={[{ required: true, message: 'Please enter annual volume' }]}
            >
              <InputNumber 
                placeholder="Enter annual volume" 
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
              onClick={fetchDepotEvaluations}
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
                    await clearDepotEvaluations()
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

  const AHPConfiguration = () => {
    console.log('AHPConfiguration render - current ahpConfig:', ahpConfig)
    
    // Temporary state for form inputs
    const [tempConfig, setTempConfig] = useState({
      numCriteria: ahpConfig.numCriteria
    })
    const [tempCriteriaNames, setTempCriteriaNames] = useState([...ahpConfig.criteriaNames])
    const [tempCriteriaWeights, setTempCriteriaWeights] = useState([...ahpConfig.criteriaWeights])
    const [pairwiseMatrix, setPairwiseMatrix] = useState([])
    const [calculatedWeights, setCalculatedWeights] = useState([])
    
    // Update temp state when ahpConfig changes
    useEffect(() => {
      setTempConfig({
        numCriteria: ahpConfig.numCriteria
      })
      setTempCriteriaNames([...ahpConfig.criteriaNames])
      setTempCriteriaWeights([...ahpConfig.criteriaWeights])
      initializePairwiseMatrix(ahpConfig.numCriteria)
    }, [ahpConfig])
    
    const initializePairwiseMatrix = (numCriteria) => {
      const matrix = Array(numCriteria).fill(null).map(() => Array(numCriteria).fill(1))
      setPairwiseMatrix(matrix)
    }
    
    const updatePairwiseValue = (i, j, value) => {
      const newMatrix = [...pairwiseMatrix]
      newMatrix[i][j] = value
      newMatrix[j][i] = 1 / value // Reciprocal value
      setPairwiseMatrix(newMatrix)
    }
    
    const calculateAHPWeights = () => {
      if (pairwiseMatrix.length === 0) return
      
      const n = pairwiseMatrix.length
      const normalizedMatrix = Array(n).fill(null).map(() => Array(n).fill(0))
      
      // Normalize each column
      for (let j = 0; j < n; j++) {
        const columnSum = pairwiseMatrix.reduce((sum, row) => sum + row[j], 0)
        for (let i = 0; i < n; i++) {
          normalizedMatrix[i][j] = pairwiseMatrix[i][j] / columnSum
        }
      }
      
      // Calculate row averages (weights)
      const weights = normalizedMatrix.map(row => 
        row.reduce((sum, val) => sum + val, 0) / n
      )
      
      setCalculatedWeights(weights)
      setTempCriteriaWeights(weights)
    }
    
    const clearDepotEvaluations = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/depot-evaluations/clear', {
          method: 'DELETE'
        })
        const result = await response.json()
        
        if (response.ok) {
          message.success(`${result.cleared_count} depot evaluations cleared successfully!`)
          fetchDepotEvaluations() // Refresh the depot evaluations list
        } else {
          throw new Error(result.detail || 'Failed to clear evaluations')
        }
      } catch (error) {
        console.error('Error clearing depot evaluations:', error)
        message.error('Failed to clear depot evaluations')
      }
    }

    const showBasicConfigWarning = () => {
      Modal.confirm({
        title: 'Warning: Configuration Change',
        content: (
          <div>
            <p>⚠️ <strong>All supplier scoring will be cleared!</strong></p>
            <p>Changing the basic configuration (number of criteria) will invalidate all existing depot manager evaluations. This action cannot be undone.</p>
            <p>Are you sure you want to proceed?</p>
          </div>
        ),
        okText: 'Yes, Clear All Evaluations',
        cancelText: 'Cancel',
        okType: 'danger',
        onOk: async () => {
          await clearDepotEvaluations()
          updateBasicConfigInternal()
        }
      })
    }

    const updateBasicConfigInternal = () => {
      console.log('updateBasicConfig called:', tempConfig)
      let newConfig = { ...ahpConfig, ...tempConfig }
      
      // If changing numCriteria, update arrays accordingly
      if (tempConfig.numCriteria !== ahpConfig.numCriteria) {
        const currentLength = ahpConfig.criteriaNames?.length || 0
        const newLength = tempConfig.numCriteria
        
        if (newLength > currentLength) {
          // Add new criteria
          const newNames = [...(ahpConfig.criteriaNames || [])]
          const newWeights = [...(ahpConfig.criteriaWeights || [])]
          for (let i = currentLength; i < newLength; i++) {
            newNames.push(`Criteria ${i + 1}`)
            newWeights.push(1.0)
          }
          newConfig.criteriaNames = newNames
          newConfig.criteriaWeights = newWeights
          setTempCriteriaNames(newNames)
          setTempCriteriaWeights(newWeights)
        } else if (newLength < currentLength) {
          // Remove excess criteria
          newConfig.criteriaNames = (ahpConfig.criteriaNames || []).slice(0, newLength)
          newConfig.criteriaWeights = (ahpConfig.criteriaWeights || []).slice(0, newLength)
          setTempCriteriaNames(newConfig.criteriaNames)
          setTempCriteriaWeights(newConfig.criteriaWeights)
        }
      }
      
      console.log('New config:', newConfig)
      setAhpConfig(newConfig)
      localStorage.setItem('ahpConfig', JSON.stringify(newConfig))
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'ahpConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      message.success('Basic configuration updated successfully!')
    }

    const updateBasicConfig = () => {
      // Check if any criteria change will happen
      if (tempConfig.numCriteria !== ahpConfig.numCriteria) {
        showBasicConfigWarning()
      } else {
        updateBasicConfigInternal()
      }
    }

    const showCriteriaNamesWarning = () => {
      Modal.confirm({
        title: 'Warning: Criteria Names Change',
        content: (
          <div>
            <p>⚠️ <strong>All supplier scoring will be cleared!</strong></p>
            <p>Changing criteria names will invalidate all existing depot manager evaluations. This action cannot be undone.</p>
            <p>Are you sure you want to proceed?</p>
          </div>
        ),
        okText: 'Yes, Clear All Evaluations',
        cancelText: 'Cancel',
        okType: 'danger',
        onOk: async () => {
          await clearDepotEvaluations()
          updateCriteriaNamesInternal()
        }
      })
    }

    const updateCriteriaNamesInternal = () => {
      console.log('updateCriteriaNames called:', tempCriteriaNames)
      const newConfig = { ...ahpConfig, criteriaNames: tempCriteriaNames }
      setAhpConfig(newConfig)
      localStorage.setItem('ahpConfig', JSON.stringify(newConfig))
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'ahpConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      message.success('Criteria names updated successfully!')
    }

    const updateCriteriaNames = () => {
      // Check if criteria names actually changed
      const currentNames = ahpConfig.criteriaNames || []
      const hasChanges = tempCriteriaNames.some((name, index) => name !== currentNames[index])
      
      if (hasChanges) {
        showCriteriaNamesWarning()
      } else {
        updateCriteriaNamesInternal()
      }
    }

    const updateCriteriaWeights = () => {
      console.log('updateCriteriaWeights called:', tempCriteriaWeights)
      const newConfig = { ...ahpConfig, criteriaWeights: tempCriteriaWeights }
      setAhpConfig(newConfig)
      localStorage.setItem('ahpConfig', JSON.stringify(newConfig))
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'ahpConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      message.success('Criteria weights updated successfully!')
    }


    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Row gutter={16}>
          <Col span={12}>
            <Card title="Basic Configuration" extra={<SettingOutlined />}>
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>
                    Number of Criteria:
                  </Text>
                  <InputNumber
                    min={1}
                    max={10}
                    value={tempConfig.numCriteria}
                    onChange={(value) => setTempConfig(prev => ({ ...prev, numCriteria: value }))}
                    style={{ width: '100%' }}
                    placeholder="Enter number of criteria (1-10)"
                  />
                  <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginTop: 4 }}>
                    Sets the number of evaluation criteria for supplier scoring
                  </Text>
                </div>
                
                
                <Button 
                  type="primary" 
                  onClick={updateBasicConfig}
                  style={{ width: '100%' }}
                  icon={<CheckOutlined />}
                >
                  Update Basic Configuration
                </Button>
              </Space>
            </Card>
          </Col>
        
        <Col span={12}>
          <Card title="Current AHP Status" extra={<BarChartOutlined />}>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Criteria Count">
                <Badge count={ahpConfig.numCriteria} style={{ backgroundColor: '#52c41a' }} />
                <span style={{ marginLeft: 8 }}>Active Criteria</span>
              </Descriptions.Item>
              <Descriptions.Item label="Suppliers">
                <div>
                  <Badge count={ahpConfig.supplierNames?.length || 0} style={{ backgroundColor: '#1890ff' }} />
                  <span style={{ marginLeft: 8 }}>Database Suppliers</span>
                  <div style={{ marginTop: 8 }}>
                    {ahpConfig.supplierNames?.map((name, index) => (
                      <Tag key={index} style={{ margin: '2px' }}>{name}</Tag>
                    )) || <Text type="secondary">No suppliers found</Text>}
                  </div>
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="Configuration Status">
                <Tag color="green" icon={<CheckCircleOutlined />}>
                  Ready for AHP Analysis
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            
            <div style={{ marginTop: 16 }}>
              <Text strong>Next Steps:</Text>
              <ol style={{ marginTop: 8, paddingLeft: 16 }}>
                <li>Configure criteria names and weights below</li>
                <li>Go to AHP Supplier Scoring tab</li>
                <li>Enter supplier information</li>
                <li>Calculate AHP scores</li>
              </ol>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="Step 1: Define Supplier Selection Criteria" style={{ marginTop: 24 }}>
        <Row gutter={[16, 16]}>
          {tempCriteriaNames.map((name, index) => (
            <Col span={8} key={index}>
              <Text strong>Criteria {index + 1} name:</Text>
              <Input
                value={name}
                onChange={(e) => {
                  const newNames = [...tempCriteriaNames]
                  newNames[index] = e.target.value
                  setTempCriteriaNames(newNames)
                }}
                placeholder={`Criteria ${index + 1}`}
                style={{ marginTop: 8 }}
              />
            </Col>
          ))}
        </Row>
        <Button 
          type="primary" 
          onClick={updateCriteriaNames}
          style={{ width: '100%', marginTop: 16 }}
          icon={<CheckOutlined />}
        >
          Update Criteria Names
        </Button>
      </Card>

      <Card title="Step 2: Assign Criteria Weights (Relative Importance)" style={{ marginTop: 24 }}>
        <Alert
          style={{ marginBottom: 16 }}
          message="AHP Pairwise Comparison Matrix"
          description="Compare each pair of criteria using the scale below. For each cell, select how much more important the row criterion is compared to the column criterion. Use reciprocal values (1/2, 1/3, etc.) when the row criterion is less important than the column criterion."
          type="info"
          showIcon
        />
        
        <div style={{ marginBottom: 16, padding: 16, backgroundColor: '#f9f9f9', borderRadius: 6 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>Interpretation of Entries in Pairwise Comparison Matrix:</Text>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li><strong>1:</strong> Criteria are of equal importance</li>
            <li><strong>3:</strong> Row criterion is weakly more important than column criterion</li>
            <li><strong>5:</strong> Experience and judgment indicate that row criterion is strongly more important than column criterion</li>
            <li><strong>7:</strong> Row criterion is very strongly or demonstrably more important than column criterion</li>
            <li><strong>9:</strong> Row criterion is absolutely more important than column criterion</li>
            <li><strong>2, 4, 6, 8:</strong> Intermediate values—for example, a value of 8 means that row criterion is midway between strongly and absolutely more important than column criterion</li>
            <li><strong>1/2, 1/3, 1/4, etc.:</strong> Use reciprocal values when the row criterion is less important than the column criterion</li>
          </ul>
        </div>
        
        <div style={{ overflowX: 'auto', marginBottom: 16 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid #d9d9d9', padding: '8px', background: '#fafafa' }}></th>
                {tempCriteriaNames.map((name, index) => (
                  <th key={index} style={{ border: '1px solid #d9d9d9', padding: '8px', background: '#fafafa', textAlign: 'center' }}>
                    {name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tempCriteriaNames.map((rowName, i) => (
                <tr key={i}>
                  <td style={{ border: '1px solid #d9d9d9', padding: '8px', background: '#fafafa', fontWeight: 'bold' }}>
                    {rowName}
                  </td>
                  {tempCriteriaNames.map((colName, j) => (
                    <td key={j} style={{ border: '1px solid #d9d9d9', padding: '8px', textAlign: 'center' }}>
                      {i === j ? (
                        <span style={{ fontWeight: 'bold' }}>1</span>
                      ) : i < j ? (
                        <Select
                          value={pairwiseMatrix[i]?.[j] || 1}
                          onChange={(value) => updatePairwiseValue(i, j, value)}
                          style={{ width: '80px' }}
                        >
                          <Option value={1/9}>1/9</Option>
                          <Option value={1/8}>1/8</Option>
                          <Option value={1/7}>1/7</Option>
                          <Option value={1/6}>1/6</Option>
                          <Option value={1/5}>1/5</Option>
                          <Option value={1/4}>1/4</Option>
                          <Option value={1/3}>1/3</Option>
                          <Option value={1/2}>1/2</Option>
                          <Option value={1}>1</Option>
                          <Option value={2}>2</Option>
                          <Option value={3}>3</Option>
                          <Option value={4}>4</Option>
                          <Option value={5}>5</Option>
                          <Option value={6}>6</Option>
                          <Option value={7}>7</Option>
                          <Option value={8}>8</Option>
                          <Option value={9}>9</Option>
                        </Select>
                      ) : (
                        <span style={{ color: '#666' }}>
                          {pairwiseMatrix[i]?.[j] ? (1 / pairwiseMatrix[j][i]).toFixed(2) : '1.00'}
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <Button 
          type="primary" 
          onClick={calculateAHPWeights}
          style={{ marginBottom: 16 }}
          icon={<CalculatorOutlined />}
        >
          Calculate Weights from Matrix
        </Button>
        
        {calculatedWeights.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Title level={5}>Calculated Weights:</Title>
            <Row gutter={[16, 8]}>
              {tempCriteriaNames.map((name, index) => (
                <Col span={8} key={index}>
                  <Text strong>{name}:</Text>
                  <Text style={{ marginLeft: 8 }}>{(calculatedWeights[index] * 100).toFixed(1)}%</Text>
                </Col>
              ))}
            </Row>
          </div>
        )}
        
        <Button 
          type="primary" 
          onClick={updateCriteriaWeights}
          style={{ width: '100%', marginTop: 16 }}
          icon={<CheckOutlined />}
          disabled={calculatedWeights.length === 0}
        >
          Update Criteria Weights
        </Button>
        <Alert
          style={{ marginTop: 16 }}
          message="Criteria Configuration Complete"
          description="These criteria names and weights will be used in the AHP Supplier Scoring interface for evaluation."
          type="success"
          showIcon
        />
      </Card>
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
            key: 'ahp-config',
            label: (
              <span>
                <SettingOutlined />
                AHP Configuration
              </span>
            ),
            children: <AHPConfiguration />
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
    </div>
  )
}

export default AdminSupplierManagement