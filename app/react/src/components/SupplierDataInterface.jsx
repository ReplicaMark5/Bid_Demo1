import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { 
  Card, 
  Form, 
  Input, 
  InputNumber, 
  Select, 
  Button, 
  Table, 
  Space,
  Typography,
  Alert,
  Tabs,
  Spin,
  message,
  Modal,
  Tag,
  Descriptions,
  Row,
  Col,
  Switch,
  Checkbox
} from 'antd'
import { HotTable } from '@handsontable/react'
import { registerAllModules } from 'handsontable/registry'
import 'handsontable/dist/handsontable.full.min.css'

// Register all Handsontable modules
registerAllModules()

// Add custom styles
const customStyles = `
  .custom-handsontable .depot-column {
    background-color: #f5f5f5 !important;
    font-weight: bold !important;
  }
  .custom-handsontable .ht_master table {
    font-size: 14px;
  }
  .custom-handsontable .htCenter {
    text-align: center;
  }
  .custom-handsontable .htLeft {
    text-align: left;
  }
  .custom-handsontable .htMiddle {
    vertical-align: middle;
  }
`

// Inject custom styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style')
  styleElement.innerHTML = customStyles
  document.head.appendChild(styleElement)
}
import { 
  PlusOutlined, 
  SaveOutlined, 
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  FileTextOutlined,
  UserOutlined
} from '@ant-design/icons'

const { Title, Text } = Typography
const { Option } = Select
const { TextArea } = Input

const SupplierDataInterface = () => {
  const [suppliers, setSuppliers] = useState([])
  const [depots, setDepots] = useState([])
  const [selectedSupplier, setSelectedSupplier] = useState(null)
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [detailsModal, setDetailsModal] = useState({ visible: false, submission: null })
  const [profileForm] = Form.useForm()
  const [profileData, setProfileData] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)

  useEffect(() => {
    fetchSuppliers()
    fetchDepots()
  }, [])

  useEffect(() => {
    if (selectedSupplier) {
      fetchSupplierSubmissions(selectedSupplier)
      fetchSupplierProfile(selectedSupplier)
    }
  }, [selectedSupplier])

  const fetchSuppliers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/suppliers/')
      const data = await response.json()
      setSuppliers(data.suppliers || [])
    } catch (error) {
      message.error('Failed to fetch suppliers')
      console.error('Error fetching suppliers:', error)
    }
  }

  const fetchDepots = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/depots/')
      const data = await response.json()
      setDepots(data.depots || [])
    } catch (error) {
      message.error('Failed to fetch depots')
      console.error('Error fetching depots:', error)
    }
  }

  const fetchSupplierSubmissions = async (supplierId) => {
    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/suppliers/${supplierId}/submissions/`)
      const data = await response.json()
      setSubmissions(data.submissions || [])
    } catch (error) {
      message.error('Failed to fetch submissions')
      console.error('Error fetching submissions:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSupplierProfile = async (supplierId) => {
    try {
      setProfileLoading(true)
      const response = await fetch(`http://localhost:8000/api/suppliers/${supplierId}/profile/`)
      const data = await response.json()
      
      // Convert delivery_types_offered string back to array for checkbox component
      const processedData = {
        ...data.supplier,
        delivery_types_offered: data.supplier?.delivery_types_offered 
          ? data.supplier.delivery_types_offered.split(', ').filter(item => item.trim()) 
          : []
      }
      
      setProfileData(processedData || {})
      profileForm.setFieldsValue(processedData || {})
    } catch (error) {
      message.error('Failed to fetch profile')
      console.error('Error fetching profile:', error)
    } finally {
      setProfileLoading(false)
    }
  }

  const updateSupplierProfile = async (values) => {
    try {
      setProfileLoading(true)
      
      // Convert checkbox array to comma-separated string for delivery_types_offered
      const processedValues = {
        ...values,
        delivery_types_offered: Array.isArray(values.delivery_types_offered) 
          ? values.delivery_types_offered.join(', ') 
          : values.delivery_types_offered
      }
      
      const response = await fetch(`http://localhost:8000/api/suppliers/${selectedSupplier}/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(processedValues),
      })
      
      if (response.ok) {
        message.success('Profile updated successfully')
        await fetchSupplierProfile(selectedSupplier)
      } else {
        const errorData = await response.json()
        message.error(`Failed to update profile: ${errorData.detail}`)
      }
    } catch (error) {
      message.error('Failed to update profile')
      console.error('Error updating profile:', error)
    } finally {
      setProfileLoading(false)
    }
  }

  const handleSubmit = async (values) => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/api/suppliers/submit-data/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supplier_id: selectedSupplier,
          ...values
        })
      })

      if (response.ok) {
        message.success('Data submitted successfully and is pending approval')
        form.resetFields()
        fetchSupplierSubmissions(selectedSupplier)
      } else {
        const errorData = await response.json()
        message.error(errorData.detail || 'Failed to submit data')
      }
    } catch (error) {
      message.error('Failed to submit data')
      console.error('Error submitting data:', error)
    } finally {
      setLoading(false)
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

  const showDetails = (submission) => {
    setDetailsModal({ visible: true, submission })
  }

  const submissionColumns = [
    {
      title: 'Depot',
      dataIndex: 'depot_name',
      key: 'depot_name',
    },
    {
      title: 'COC Rebate (R/L)',
      dataIndex: 'coc_rebate',
      key: 'coc_rebate',
      render: (value) => value !== null ? `R${value}` : <Text type="secondary">N/A</Text>
    },
    {
      title: 'Cost of Collection (R/L)',
      dataIndex: 'cost_of_collection',
      key: 'cost_of_collection',
      render: (value) => value !== null ? `R${value}` : <Text type="secondary">N/A</Text>
    },
    {
      title: 'DEL Rebate (R/L)',
      dataIndex: 'del_rebate',
      key: 'del_rebate',
      render: (value) => value !== null ? `R${value}` : <Text type="secondary">N/A</Text>
    },
    {
      title: 'Zone Differential',
      dataIndex: 'zone_differential',
      key: 'zone_differential',
      render: (value) => value !== null ? value : <Text type="secondary">N/A</Text>
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status)
    },
    {
      title: 'Submitted',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      render: (date) => new Date(date).toLocaleDateString()
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />} 
          onClick={() => showDetails(record)}
        >
          Details
        </Button>
      )
    }
  ]

  const DataSubmissionForm = () => {
    const [tableData, setTableData] = useState([])
    const hotTableRef = useRef(null)

    useEffect(() => {
      const initializeTableData = () => {
        // Create data array with depot names as first column
        const data = depots.map(depot => [
          depot.name,     // Depot name (read-only)
          '',            // COC Rebate
          '',            // Cost of Collection
          '',            // DEL Rebate
          '',            // Zone Differential
          ''             // Distance
        ])
        setTableData(data)
      }
      
      if (depots.length > 0) {
        initializeTableData()
      }
    }, [depots])

    const columns = useMemo(() => [
      {
        title: 'Depot',
        readOnly: true,
        className: 'htLeft htMiddle depot-column',
        width: 150
      },
      {
        title: 'COC Rebate (R/L)',
        type: 'numeric',
        numericFormat: {
          pattern: '0,0.00',
          culture: 'en-US'
        },
        className: 'htCenter htMiddle',
        width: 150
      },
      {
        title: 'Cost of Collection (R/L)',
        type: 'numeric',
        numericFormat: {
          pattern: '0,0.00',
          culture: 'en-US'
        },
        className: 'htCenter htMiddle',
        width: 180
      },
      {
        title: 'DEL Rebate (R/L)',
        type: 'numeric',
        numericFormat: {
          pattern: '0,0.00',
          culture: 'en-US'
        },
        className: 'htCenter htMiddle',
        width: 150
      },
      {
        title: 'Zone Differential',
        type: 'numeric',
        numericFormat: {
          pattern: '0,0.00',
          culture: 'en-US'
        },
        className: 'htCenter htMiddle',
        width: 150
      },
      {
        title: 'Distance (Km)',
        type: 'numeric',
        numericFormat: {
          pattern: '0,0.0',
          culture: 'en-US'
        },
        className: 'htCenter htMiddle',
        width: 130
      }
    ], [])

    const afterChange = useCallback((changes) => {
      if (changes) {
        // Update the tableData state when changes occur
        const hot = hotTableRef.current.hotInstance
        if (hot) {
          setTableData(hot.getData())
        }
      }
    }, [])

    const handleSubmitAll = async () => {
      try {
        setLoading(true)
        
        // Prepare submission data
        const submissionData = tableData.map((row, index) => {
          if (index < depots.length) {
            return {
              depot_id: depots[index].id,
              coc_rebate: row[1] || null,
              cost_of_collection: row[2] || null,
              del_rebate: row[3] || null,
              zone_differential: row[4] || null,
              distance_km: row[5] || null
            }
          }
          return null
        }).filter(item => item !== null)

        const response = await fetch('http://localhost:8000/api/suppliers/submit-bulk-data/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            supplier_id: selectedSupplier,
            submissions: submissionData
          })
        })

        if (response.ok) {
          message.success('All data submitted successfully and is pending approval')
          
          // Reset table data
          const resetData = depots.map(depot => [
            depot.name,
            '',
            '',
            '',
            '',
            ''
          ])
          setTableData(resetData)
          
          fetchSupplierSubmissions(selectedSupplier)
        } else {
          const errorData = await response.json()
          message.error(errorData.detail || 'Failed to submit data')
        }
      } catch (error) {
        message.error('Failed to submit data')
        console.error('Error submitting data:', error)
      } finally {
        setLoading(false)
      }
    }

    return (
      <Card title="Submit Data for All Depots" extra={<FileTextOutlined />}>
        <Alert
          message={
            <div>
              <strong>Instructions for bulk data entry from Excel:</strong>
              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                <li><strong>Single Column:</strong> Copy a column from Excel, click the first cell of target column here, paste (Ctrl+V)</li>
                <li><strong>Multiple Columns:</strong> Copy multiple columns from Excel, click the first cell of first target column, paste</li>
                <li><strong>Entire Table:</strong> Copy the entire data table from Excel, click the first data cell (COC Rebate), paste</li>
                <li>Data will automatically populate the correct cells based on Excel structure</li>
                <li>Leave fields empty if your supplier cannot provide that service</li>
              </ul>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <div style={{ marginBottom: 16 }}>
          <HotTable
            ref={hotTableRef}
            data={tableData}
            columns={columns}
            colHeaders={['Depot', 'COC Rebate (R/L)', 'Cost of Collection (R/L)', 'DEL Rebate (R/L)', 'Zone Differential', 'Distance (Km)']}
            rowHeaders={true}
            height={400}
            width="100%"
            licenseKey="non-commercial-and-evaluation"
            afterChange={afterChange}
            contextMenu={true}
            copyPaste={true}
            fillHandle={true}
            manualColumnResize={true}
            manualRowResize={true}
            stretchH="all"
            className="custom-handsontable"
            cells={(row, col) => {
              const cellProperties = {}
              
              if (col === 0) {
                // First column (depot names) should be read-only
                cellProperties.readOnly = true
                cellProperties.className = 'htLeft htMiddle depot-column'
              } else {
                // Other columns are editable
                cellProperties.type = 'numeric'
                cellProperties.className = 'htCenter htMiddle'
              }
              
              return cellProperties
            }}
          />
        </div>

        <Space>
          <Button 
            type="primary" 
            onClick={handleSubmitAll}
            icon={<SaveOutlined />}
            loading={loading}
            size="large"
          >
            Submit All Data
          </Button>
          <Button 
            onClick={() => {
              const resetData = depots.map(depot => [
                depot.name,
                '',
                '',
                '',
                '',
                ''
              ])
              setTableData(resetData)
              
              // Also update the Handsontable instance
              if (hotTableRef.current) {
                hotTableRef.current.hotInstance.loadData(resetData)
              }
            }}
            size="large"
          >
            Clear All Data
          </Button>
        </Space>
      </Card>
    )
  }

  const SubmissionHistory = () => (
    <Card title="Submission History" extra={<Text type="secondary">{submissions.length} submissions</Text>}>
      <Table
        dataSource={submissions}
        columns={submissionColumns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  )

  const ProfileForm = () => (
    <Card title="Company Profile" extra={<UserOutlined />}>
      <Spin spinning={profileLoading}>
        <Form
          form={profileForm}
          layout="vertical"
          onFinish={updateSupplierProfile}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="company_profile"
                label="Company Profile"
                rules={[{ required: true, message: 'Please enter company profile' }]}
              >
                <TextArea rows={4} placeholder="Enter company profile description" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="annual_revenue"
                label="Annual Revenue"
                rules={[{ required: true, message: 'Please enter annual revenue' }]}
              >
                <InputNumber
                  placeholder="Enter annual revenue"
                  style={{ width: '100%' }}
                  min={0}
                  formatter={(value) => `R ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => value.replace(/R\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="number_of_employees"
                label="Number of Employees"
                rules={[{ required: true, message: 'Please enter number of employees' }]}
              >
                <InputNumber
                  placeholder="Enter number of employees"
                  style={{ width: '100%' }}
                  min={1}
                />
              </Form.Item>
            </Col>
          </Row>

          <Title level={5} style={{ marginTop: 24 }}>B-BBEE Certificate</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="bbee_level"
                label="Current Level (1-8)"
                rules={[{ required: true, message: 'Please enter B-BBEE level' }]}
              >
                <Select placeholder="Select B-BBEE level">
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(level => (
                    <Option key={level} value={level}>Level {level}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="black_ownership_percent"
                label="Black Ownership %"
                rules={[{ required: true, message: 'Please enter black ownership percentage' }]}
              >
                <InputNumber
                  placeholder="Enter percentage"
                  style={{ width: '100%' }}
                  min={0}
                  max={100}
                  formatter={(value) => `${value}%`}
                  parser={(value) => value.replace('%', '')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="black_female_ownership_percent"
                label="Black Female Ownership %"
                rules={[{ required: true, message: 'Please enter black female ownership percentage' }]}
              >
                <InputNumber
                  placeholder="Enter percentage"
                  style={{ width: '100%' }}
                  min={0}
                  max={100}
                  formatter={(value) => `${value}%`}
                  parser={(value) => value.replace('%', '')}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="bbee_compliant"
                label="B-BBEE Compliant"
                valuePropName="checked"
              >
                <Switch checkedChildren="Yes" unCheckedChildren="No" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="cipc_cor_documents"
                label="CIPC or COR Documents"
                rules={[{ required: true, message: 'Please select CIPC or COR documents status' }]}
              >
                <Select placeholder="Select CIPC or COR documents status">
                  <Option value="Yes">Yes</Option>
                  <Option value="No">No</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="tax_certificate"
                label="Tax Certificate"
                rules={[{ required: true, message: 'Please select tax certificate status' }]}
              >
                <Select placeholder="Select tax certificate status">
                  <Option value="Yes">Yes</Option>
                  <Option value="No">No</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="fuel_products_offered"
                label="Fuel Products Offered"
                rules={[{ required: true, message: 'Please enter fuel products offered' }]}
              >
                <TextArea rows={3} placeholder="Enter fuel products offered" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="product_service_type"
                label="Product / Service Type"
                rules={[{ required: true, message: 'Please select product/service type' }]}
              >
                <Select placeholder="Select product/service type">
                  <Option value="Both">Both</Option>
                  <Option value="Only Depot">Only Depot</Option>
                  <Option value="Only On-road">Only On-road</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="geographical_network"
                label="Geographical Network"
                rules={[{ required: true, message: 'Please select geographical network' }]}
              >
                <Select placeholder="Select geographical network">
                  <Option value="Both">Both</Option>
                  <Option value="Only RSA">Only RSA</Option>
                  <Option value="Only SADC excluding RSA">Only SADC excluding RSA</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="delivery_types_offered"
                label="Delivery Types Offered"
                rules={[{ required: true, message: 'Please select at least one delivery type' }]}
              >
                <Checkbox.Group
                  options={[
                    { label: 'COC', value: 'COC' },
                    { label: 'Self-Delivered', value: 'Self-Delivered' },
                    { label: 'Outsourced', value: 'Outsourced' }
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="method_of_sourcing"
                label="Method of Sourcing"
                rules={[{ required: true, message: 'Please select method of sourcing' }]}
              >
                <Select placeholder="Select method of sourcing">
                  <Option value="Direct Import and Refined Locally">Direct Import and Refined Locally</Option>
                  <Option value="Direct Import or Refined Locally">Direct Import or Refined Locally</Option>
                  <Option value="Trade/Resell only">Trade/Resell only</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="invest_in_refuelling_equipment"
                label="Invest in Refuelling Equipment"
                rules={[{ required: true, message: 'Please select investment in refuelling equipment' }]}
              >
                <Select placeholder="Select investment in refuelling equipment">
                  <Option value="Yes">Yes</Option>
                  <Option value="No">No</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="reciprocal_business"
                label="Reciprocal Business"
                rules={[{ required: true, message: 'Please select reciprocal business' }]}
              >
                <Select placeholder="Select reciprocal business">
                  <Option value="Yes">Yes</Option>
                  <Option value="No">No</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={profileLoading}>
              Update Profile
            </Button>
          </Form.Item>
        </Form>
      </Spin>
    </Card>
  )

  if (!selectedSupplier) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Title level={4}>Select Your Supplier Account</Title>
          <Text type="secondary">Choose your supplier to submit data</Text>
          <div style={{ marginTop: '24px' }}>
            <Select
              placeholder="Select your supplier"
              size="large"
              style={{ width: '300px' }}
              onChange={setSelectedSupplier}
            >
              {suppliers.map(supplier => (
                <Option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </Option>
              ))}
            </Select>
          </div>
        </div>
      </Card>
    )
  }

  const selectedSupplierData = suppliers.find(s => s.id === selectedSupplier)

  return (
    <div>
      <Card style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              Welcome, {selectedSupplierData?.name}
            </Title>
            <Text type="secondary">Submit your depot-specific pricing data</Text>
          </div>
          <Button onClick={() => setSelectedSupplier(null)}>
            Switch Supplier
          </Button>
        </div>
      </Card>

      <Tabs
        defaultActiveKey="submit"
        items={[
          {
            key: 'submit',
            label: (
              <span>
                <PlusOutlined />
                Submit Data
              </span>
            ),
            children: <DataSubmissionForm />
          },
          {
            key: 'history',
            label: (
              <span>
                <FileTextOutlined />
                Submission History
              </span>
            ),
            children: <SubmissionHistory />
          },
          {
            key: 'profile',
            label: (
              <span>
                <UserOutlined />
                Profile
              </span>
            ),
            children: <ProfileForm />
          }
        ]}
      />

      <Modal
        title="Submission Details"
        open={detailsModal.visible}
        onCancel={() => setDetailsModal({ visible: false, submission: null })}
        footer={null}
        width={600}
      >
        {detailsModal.submission && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="Depot">{detailsModal.submission.depot_name}</Descriptions.Item>
            <Descriptions.Item label="COC Rebate (R/L)">
              {detailsModal.submission.coc_rebate !== null ? `R${detailsModal.submission.coc_rebate}` : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Cost of Collection (R/L)">
              {detailsModal.submission.cost_of_collection !== null ? `R${detailsModal.submission.cost_of_collection}` : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="DEL Rebate (R/L)">
              {detailsModal.submission.del_rebate !== null ? `R${detailsModal.submission.del_rebate}` : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Zone Differential">{detailsModal.submission.zone_differential}</Descriptions.Item>
            <Descriptions.Item label="Distance (Km)">
              {detailsModal.submission.distance_km !== null ? `${detailsModal.submission.distance_km} km` : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              {getStatusTag(detailsModal.submission.status)}
            </Descriptions.Item>
            <Descriptions.Item label="Submitted At">
              {new Date(detailsModal.submission.submitted_at).toLocaleString()}
            </Descriptions.Item>
            {detailsModal.submission.approved_at && (
              <Descriptions.Item label="Approved At">
                {new Date(detailsModal.submission.approved_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {detailsModal.submission.approved_by && (
              <Descriptions.Item label="Approved By">{detailsModal.submission.approved_by}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default SupplierDataInterface