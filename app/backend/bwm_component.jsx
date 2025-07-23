  const BWMConfiguration = () => {
    console.log('BWMConfiguration render - current bwmConfig:', bwmConfig)
    
    // Temporary state for form inputs
    const [tempConfig, setTempConfig] = useState({
      numCriteria: bwmConfig.numCriteria
    })
    const [tempCriteriaNames, setTempCriteriaNames] = useState([...bwmConfig.criteriaNames])
    const [tempBestCriterion, setTempBestCriterion] = useState(bwmConfig.bestCriterion)
    const [tempWorstCriterion, setTempWorstCriterion] = useState(bwmConfig.worstCriterion)
    const [tempBestToOthers, setTempBestToOthers] = useState({...bwmConfig.bestToOthers})
    const [tempOthersToWorst, setTempOthersToWorst] = useState({...bwmConfig.othersToWorst})
    const [bwmResults, setBwmResults] = useState(null)
    const [bwmLoading, setBwmLoading] = useState(false)
    
    // Update temp state when bwmConfig changes
    useEffect(() => {
      setTempConfig({
        numCriteria: bwmConfig.numCriteria
      })
      setTempCriteriaNames([...bwmConfig.criteriaNames])
      setTempBestCriterion(bwmConfig.bestCriterion)
      setTempWorstCriterion(bwmConfig.worstCriterion)
      setTempBestToOthers({...bwmConfig.bestToOthers})
      setTempOthersToWorst({...bwmConfig.othersToWorst})
    }, [bwmConfig])
    
    const updateBasicConfig = () => {
      console.log('updateBasicConfig called, tempConfig:', tempConfig)
      
      // Update config with new values
      const newConfig = { 
        ...bwmConfig, 
        numCriteria: tempConfig.numCriteria,
        criteriaNames: Array(tempConfig.numCriteria).fill('').map((_, i) => `Criteria ${i + 1}`),
        criteriaWeights: Array(tempConfig.numCriteria).fill(1.0),
        bestCriterion: null,
        worstCriterion: null,
        bestToOthers: {},
        othersToWorst: {},
        consistencyRatio: null
      }
      
      // Update the temporary names
      const newNames = Array(tempConfig.numCriteria).fill('').map((_, i) => `Criteria ${i + 1}`)
      
      if (tempCriteriaNames.length !== tempConfig.numCriteria) {
        setTempCriteriaNames(newNames)
      }
      
      // Reset BWM-specific fields
      setTempBestCriterion(null)
      setTempWorstCriterion(null)
      setTempBestToOthers({})
      setTempOthersToWorst({})
      setBwmResults(null)
      
      console.log('New config:', newConfig)
      setBwmConfig(newConfig)
      localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'bwmConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      message.success('Basic configuration updated successfully!')
    }
    
    const updateCriteriaNamesInternal = () => {
      console.log('updateCriteriaNames called:', tempCriteriaNames)
      const newConfig = { ...bwmConfig, criteriaNames: tempCriteriaNames }
      setBwmConfig(newConfig)
      localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
      
      // Trigger storage event for cross-component sync
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'bwmConfig',
        newValue: JSON.stringify(newConfig),
        storageArea: localStorage
      }))
      
      message.success('Criteria names updated successfully!')
    }
    
    const calculateBWMWeights = async () => {
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
        const response = await fetch('http://localhost:8000/api/bwm/calculate/', {
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
        
        if (!response.ok) {
          throw new Error('Failed to calculate BWM weights')
        }
        
        const data = await response.json()
        setBwmResults(data.data)
        
        // Update the config with calculated weights
        const newConfig = {
          ...bwmConfig,
          criteriaWeights: tempCriteriaNames.map(name => data.data.weights[name]),
          bestCriterion: tempBestCriterion,
          worstCriterion: tempWorstCriterion,
          bestToOthers: tempBestToOthers,
          othersToWorst: tempOthersToWorst,
          consistencyRatio: data.data.consistency_ratio
        }
        
        setBwmConfig(newConfig)
        localStorage.setItem('bwmConfig', JSON.stringify(newConfig))
        
        // Trigger storage event for cross-component sync
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'bwmConfig',
          newValue: JSON.stringify(newConfig),
          storageArea: localStorage
        }))
        
        message.success('BWM weights calculated successfully!')
        
      } catch (error) {
        console.error('Error calculating BWM weights:', error)
        message.error('Failed to calculate BWM weights')
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

      {bwmResults && (
        <Card title="Step 4: BWM Results" extra={<CheckCircleOutlined />}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Calculated Weights:</Text>
              <div style={{ marginTop: '10px' }}>
                {tempCriteriaNames.map((name, index) => (
                  <div key={index} style={{ marginBottom: '8px' }}>
                    <Text>{`${name}: ${bwmResults.weights[name]?.toFixed(4) || 'N/A'}`}</Text>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <Text strong>Consistency Ratio: </Text>
              <Text type={bwmResults.consistency_ratio <= 0.1 ? 'success' : 'warning'}>
                {bwmResults.consistency_ratio?.toFixed(4)} 
                ({bwmResults.consistency_interpretation})
              </Text>
            </div>
            
            <Alert
              message="Configuration Complete"
              description="These criteria names and weights will be used in the PROMETHEE II Supplier Scoring interface for evaluation."
              type="success"
              showIcon
            />
          </Space>
        </Card>
      )}
    </Space>
    )
  }